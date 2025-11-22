"""Media library scanner with watchdog integration."""

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from alma_tv.config import get_settings
from alma_tv.database import Video, get_db
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class Scanner:
    """
    Scans media library and extracts metadata.

    Supports recursive directory scanning, filename parsing,
    and ffprobe duration extraction.
    """

    SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".m4v", ".mov"}
    EPISODE_PATTERN = re.compile(
        r"(?P<series>.+?)_S(?P<season>\d+)E(?P<episode>\d+)(?:_(?P<title>.+))?",
        re.IGNORECASE,
    )

    def __init__(self, media_root: Optional[Path] = None):
        """
        Initialize scanner.

        Args:
            media_root: Root directory to scan (defaults to config value)
        """
        self.settings = get_settings()
        self.media_root = media_root or self.settings.media_root

    def parse_filename(self, file_path: Path) -> Optional[dict]:
        """
        Parse video filename to extract metadata.

        Expected format: SeriesName_SxxEyy_Title.ext

        Args:
            file_path: Path to video file

        Returns:
            Dict with series, season, episode_code, and optional title,
            or None if parsing fails
        """
        stem = file_path.stem
        match = self.EPISODE_PATTERN.match(stem)

        if not match:
            logger.warning(f"Could not parse filename: {file_path.name}")
            return None

        data = match.groupdict()
        return {
            "series": data["series"].replace("_", " ").strip(),
            "season": int(data["season"]),
            "episode_code": f"S{int(data['season']):02d}E{int(data['episode']):02d}",
            "title": data.get("title", "").replace("_", " ").strip() if data.get("title") else None,
        }

    def get_duration(self, file_path: Path, retry_count: int = 3) -> Optional[int]:
        """
        Extract video duration using ffprobe.

        Args:
            file_path: Path to video file
            retry_count: Number of retries on failure

        Returns:
            Duration in seconds, or None if extraction fails
        """
        for attempt in range(retry_count):
            try:
                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        str(file_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0 and result.stdout.strip():
                    duration = float(result.stdout.strip())
                    return int(duration)

            except (subprocess.TimeoutExpired, ValueError) as e:
                logger.warning(f"ffprobe attempt {attempt + 1} failed for {file_path}: {e}")
                if attempt == retry_count - 1:
                    return None

        return None

    def compute_file_hash(self, file_path: Path) -> str:
        """
        Compute hash of file path and modification time.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash string
        """
        stat = file_path.stat()
        hash_input = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def scan_file(self, file_path: Path) -> Optional[dict]:
        """
        Scan a single file and extract metadata.

        Args:
            file_path: Path to video file

        Returns:
            Metadata dict or None if file cannot be processed
        """
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return None

        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return None

        # Parse filename
        metadata = self.parse_filename(file_path)
        if not metadata:
            return None

        # Get duration
        duration = self.get_duration(file_path)
        if duration is None:
            logger.warning(f"Could not extract duration: {file_path}")
            return None

        # Compute hash
        file_hash = self.compute_file_hash(file_path)

        metadata.update(
            {
                "path": str(file_path.absolute()),
                "duration_seconds": duration,
                "file_hash": file_hash,
                "disabled": False,
            }
        )

        return metadata

    def upsert_video(self, metadata: dict) -> bool:
        """
        Insert or update video in database.

        Args:
            metadata: Video metadata dict

        Returns:
            True if upserted, False otherwise
        """
        try:
            with get_db() as db:
                # Check if video exists by path
                existing = db.query(Video).filter(Video.path == metadata["path"]).first()

                if existing:
                    # Check if file has changed
                    if existing.file_hash == metadata["file_hash"]:
                        logger.debug(f"Video unchanged: {metadata['path']}")
                        return False

                    # Update existing video
                    for key, value in metadata.items():
                        setattr(existing, key, value)
                    logger.info(f"Updated video: {metadata['path']}")
                else:
                    # Insert new video
                    video = Video(**metadata)
                    db.add(video)
                    logger.info(f"Added new video: {metadata['path']}")

                return True

        except Exception as e:
            logger.error(f"Failed to upsert video {metadata.get('path')}: {e}")
            return False

    def scan_directory(self, directory: Optional[Path] = None) -> dict:
        """
        Recursively scan directory for media files.

        Args:
            directory: Directory to scan (defaults to media_root)

        Returns:
            Summary dict with counts
        """
        scan_dir = directory or self.media_root
        logger.info(f"Starting scan of {scan_dir}")

        summary = {"scanned": 0, "added": 0, "updated": 0, "failed": 0}

        for file_path in scan_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                summary["scanned"] += 1

                metadata = self.scan_file(file_path)
                if metadata:
                    if self.upsert_video(metadata):
                        summary["added"] += 1
                else:
                    summary["failed"] += 1

        logger.info(f"Scan complete: {summary}")

        # Emit change log for benchmarking
        self._emit_change_log(summary)

        return summary

    def _emit_change_log(self, summary: dict) -> None:
        """
        Emit change log entry as JSON for benchmarking/tracing.

        Args:
            summary: Scan summary dict
        """
        try:
            from datetime import datetime, timezone
            
            log_dir = Path("/var/log/alma")
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / "scan_changes.jsonl"
            with open(log_file, "a") as f:
                json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), **summary}, f)
                f.write("\n")
        except (PermissionError, OSError) as e:
            logger.debug(f"Could not write change log: {e}")


class MediaLibraryEventHandler(FileSystemEventHandler):
    """Watch for filesystem changes in media library."""

    def __init__(self, scanner: Scanner):
        """
        Initialize event handler.

        Args:
            scanner: Scanner instance to use for processing changes
        """
        self.scanner = scanner
        super().__init__()

    def on_created(self, event):
        """Handle file creation."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in Scanner.SUPPORTED_EXTENSIONS:
                logger.info(f"New file detected: {file_path}")
                metadata = self.scanner.scan_file(file_path)
                if metadata:
                    self.scanner.upsert_video(metadata)

    def on_modified(self, event):
        """Handle file modification."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in Scanner.SUPPORTED_EXTENSIONS:
                logger.info(f"File modified: {file_path}")
                metadata = self.scanner.scan_file(file_path)
                if metadata:
                    self.scanner.upsert_video(metadata)


def watch_directory(directory: Optional[Path] = None) -> Observer:
    """
    Start watching directory for changes.

    Args:
        directory: Directory to watch (defaults to media_root)

    Returns:
        Observer instance (caller should call .stop() when done)
    """
    settings = get_settings()
    watch_dir = directory or settings.media_root

    scanner = Scanner(watch_dir)
    event_handler = MediaLibraryEventHandler(scanner)

    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=True)
    observer.start()

    logger.info(f"Started watching {watch_dir}")
    return observer


# Import datetime for change log
from datetime import datetime
