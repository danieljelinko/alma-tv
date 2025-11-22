"""Tests for media library scanner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from alma_tv.library.scanner import Scanner


@pytest.fixture
def sample_videos(tmp_path):
    """Create sample video files for testing."""
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create valid files
    files = [
        media_dir / "Bluey_S01E01_MagicXylophone.mp4",
        media_dir / "Bluey_S01E02_Hospital.mp4",
        media_dir / "PawPatrol_S02E05_Rescue.mkv",
    ]

    for f in files:
        f.touch()

    # Create nested directory
    nested = media_dir / "More_Shows" / "Season1"
    nested.mkdir(parents=True)
    nested_file = nested / "PeppaRig_S01E03_Muddy_Puddles.mp4"
    nested_file.touch()
    files.append(nested_file)

    # Create invalid file
    invalid = media_dir / "invalid_name.mp4"
    invalid.touch()

    return media_dir, files


def test_scanner_initialization(tmp_path):
    """Test scanner can be initialized."""
    scanner = Scanner(media_root=tmp_path)
    assert scanner.media_root == tmp_path


def test_parse_filename_valid():
    """Test parsing valid filenames."""
    scanner = Scanner()

    # With title
    result = scanner.parse_filename(Path("Bluey_S01E01_Magic_Xylophone.mp4"))
    assert result is not None
    assert result["series"] == "Bluey"
    assert result["season"] == 1
    assert result["episode_code"] == "S01E01"
    assert result["title"] == "Magic Xylophone"

    # Without title
    result = scanner.parse_filename(Path("Paw_Patrol_S02E05.mp4"))
    assert result is not None
    assert result["series"] == "Paw Patrol"
    assert result["season"] == 2
    assert result["episode_code"] == "S02E05"
    assert result["title"] is None

    # With underscores in title
    result = scanner.parse_filename(Path("Peppa_Pig_S01E03_Muddy_Puddles.mp4"))
    assert result is not None
    assert result["series"] == "Peppa Pig"
    assert result["title"] == "Muddy Puddles"


def test_parse_filename_invalid():
    """Test parsing invalid filenames returns None."""
    scanner = Scanner()

    # Missing episode code
    result = scanner.parse_filename(Path("Bluey.mp4"))
    assert result is None

    # Wrong format
    result = scanner.parse_filename(Path("random_file.mp4"))
    assert result is None


def test_parse_filename_case_insensitive():
    """Test filename parsing is case insensitive."""
    scanner = Scanner()

    result = scanner.parse_filename(Path("bluey_s01e01_test.mp4"))
    assert result is not None
    assert result["episode_code"] == "S01E01"


@patch("subprocess.run")
def test_get_duration_success(mock_run):
    """Test successful duration extraction."""
    mock_run.return_value = MagicMock(returncode=0, stdout="420.5\n")

    scanner = Scanner()
    duration = scanner.get_duration(Path("test.mp4"))

    assert duration == 420
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_get_duration_failure(mock_run):
    """Test duration extraction failure."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")

    scanner = Scanner()
    duration = scanner.get_duration(Path("test.mp4"), retry_count=1)

    assert duration is None


@patch("subprocess.run")
def test_get_duration_retry(mock_run):
    """Test duration extraction with retry."""
    # First two calls fail, third succeeds
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout=""),
        MagicMock(returncode=1, stdout=""),
        MagicMock(returncode=0, stdout="600.0\n"),
    ]

    scanner = Scanner()
    duration = scanner.get_duration(Path("test.mp4"), retry_count=3)

    assert duration == 600
    assert mock_run.call_count == 3


def test_compute_file_hash(tmp_path):
    """Test file hash computation."""
    file_path = tmp_path / "test.mp4"
    file_path.write_text("test content")

    scanner = Scanner()
    hash1 = scanner.compute_file_hash(file_path)
    hash2 = scanner.compute_file_hash(file_path)

    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest length

    # Modifying file should change hash
    file_path.write_text("different content")
    hash3 = scanner.compute_file_hash(file_path)
    assert hash1 != hash3


@patch("alma_tv.library.scanner.Scanner.get_duration")
@patch("alma_tv.library.scanner.Scanner.upsert_video")
def test_scan_file_success(mock_upsert, mock_duration, tmp_path):
    """Test scanning a valid file."""
    mock_duration.return_value = 420

    file_path = tmp_path / "Bluey_S01E01_Test.mp4"
    file_path.touch()

    scanner = Scanner()
    metadata = scanner.scan_file(file_path)

    assert metadata is not None
    assert metadata["series"] == "Bluey"
    assert metadata["season"] == 1
    assert metadata["episode_code"] == "S01E01"
    assert metadata["duration_seconds"] == 420
    assert metadata["path"] == str(file_path.absolute())
    assert "file_hash" in metadata


@patch("alma_tv.library.scanner.Scanner.get_duration")
def test_scan_file_unsupported_extension(mock_duration, tmp_path):
    """Test scanning file with unsupported extension."""
    file_path = tmp_path / "Bluey_S01E01.txt"
    file_path.touch()

    scanner = Scanner()
    metadata = scanner.scan_file(file_path)

    assert metadata is None
    mock_duration.assert_not_called()


@patch("alma_tv.library.scanner.Scanner.get_duration")
def test_scan_file_no_duration(mock_duration, tmp_path):
    """Test scanning file when duration extraction fails."""
    mock_duration.return_value = None

    file_path = tmp_path / "Bluey_S01E01_Test.mp4"
    file_path.touch()

    scanner = Scanner()
    metadata = scanner.scan_file(file_path)

    assert metadata is None


@patch("alma_tv.library.scanner.Scanner.scan_file")
@patch("alma_tv.library.scanner.Scanner.upsert_video")
def test_scan_directory(mock_upsert, mock_scan, sample_videos):
    """Test scanning entire directory."""
    media_dir, files = sample_videos

    # Mock successful scans
    mock_scan.return_value = {"series": "Test", "path": "test.mp4"}
    mock_upsert.return_value = True

    scanner = Scanner(media_root=media_dir)
    summary = scanner.scan_directory()

    # Should find 5 files (4 valid + 1 invalid)
    assert summary["scanned"] == 5
    assert mock_scan.call_count == 5


@patch("alma_tv.library.scanner.Scanner.scan_file")
@patch("alma_tv.library.scanner.Scanner.upsert_video")
def test_scan_directory_with_failures(mock_upsert, mock_scan, sample_videos):
    """Test scan directory handles failures gracefully."""
    media_dir, files = sample_videos

    # Mock some failures
    mock_scan.side_effect = [
        {"series": "Test1"},  # Success
        None,  # Failure
        {"series": "Test2"},  # Success
        None,  # Failure
        {"series": "Test3"},  # Success
    ]
    mock_upsert.return_value = True

    scanner = Scanner(media_root=media_dir)
    summary = scanner.scan_directory()

    assert summary["scanned"] == 5
    assert summary["added"] == 3
    assert summary["failed"] == 2


def test_supported_extensions():
    """Test that scanner recognizes supported extensions."""
    scanner = Scanner()

    supported = [".mp4", ".mkv", ".avi", ".m4v", ".mov"]
    for ext in supported:
        assert ext in scanner.SUPPORTED_EXTENSIONS

    # Case insensitive
    assert Path("test.MP4").suffix.lower() in scanner.SUPPORTED_EXTENSIONS
