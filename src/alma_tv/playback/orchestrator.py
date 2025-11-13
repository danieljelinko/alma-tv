"""Playback orchestration for scheduled viewing sessions."""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from alma_tv.config import get_settings
from alma_tv.database import PlayHistory, Session, get_db
from alma_tv.database.models import SessionStatus
from alma_tv.logging.config import get_logger
from alma_tv.playback.players import get_player
from alma_tv.scheduler import LineupGenerator

logger = get_logger(__name__)


class PlaybackOrchestrator:
    """
    Orchestrates scheduled playback sessions.

    Responsibilities:
    - Wait for scheduled start time
    - Play intro + episodes + outro in sequence
    - Log playback events
    - Handle failures gracefully
    - Trigger feedback UI after completion
    """

    def __init__(self):
        """Initialize playback orchestrator."""
        self.settings = get_settings()
        self.player = get_player(
            player_type=self.settings.player,
            display=self.settings.display,
        )

    def run_daemon(self) -> None:
        """
        Run as daemon, checking for scheduled sessions.

        This is the main loop for systemd service.
        """
        logger.info("Playback orchestrator daemon started")

        while True:
            try:
                # Check if it's time to play
                if self._should_play_now():
                    logger.info("Scheduled playback time reached")
                    self.play_today_session()

                # Sleep for 30 seconds before checking again
                time.sleep(30)

            except KeyboardInterrupt:
                logger.info("Playback orchestrator stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in playback daemon: {e}", exc_info=True)
                time.sleep(60)  # Wait a bit before retrying

    def _should_play_now(self) -> bool:
        """
        Check if current time matches scheduled start time.

        Returns:
            True if it's time to play
        """
        now = datetime.now()
        scheduled_time = self.settings.start_time

        # Parse scheduled time (HH:MM)
        hour, minute = map(int, scheduled_time.split(":"))

        # Check if we're within 1 minute of scheduled time
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        diff = abs((now - target).total_seconds())

        return diff < 60

    def play_today_session(self) -> bool:
        """
        Play today's session.

        Returns:
            True if successful
        """
        from datetime import date

        today = date.today()
        return self.play_session(today)

    def play_session(self, target_date) -> bool:
        """
        Play session for a specific date.

        Args:
            target_date: Date to play

        Returns:
            True if successful
        """
        logger.info(f"Playing session for {target_date}")

        # Get or generate session
        with get_db() as db:
            session = (
                db.query(Session)
                .filter(Session.show_date == datetime.combine(target_date, datetime.min.time()))
                .first()
            )

            if not session:
                logger.warning(f"No session found for {target_date}, generating...")
                generator = LineupGenerator()
                session_id = generator.generate_lineup(target_date=target_date)

                if not session_id:
                    logger.error("Failed to generate session")
                    return False

                session = db.query(Session).filter(Session.id == session_id).first()

        if self.settings.dry_run:
            logger.info("DRY RUN: Would play session")
            return self._dry_run_session(session)

        # Play the session
        success = self._play_session_sequence(session)

        if success:
            # Mark session as completed
            with get_db() as db:
                session = db.query(Session).filter(Session.id == session.id).first()
                session.status = SessionStatus.COMPLETED

            # TODO: Trigger feedback UI
            logger.info("Session playback completed, feedback UI should launch")

        return success

    def _play_session_sequence(self, session: Session) -> bool:
        """
        Play complete session sequence.

        Args:
            session: Session to play

        Returns:
            True if successful
        """
        # Play intro
        if session.intro_path and Path(session.intro_path).exists():
            logger.info("Playing intro")
            if not self._play_file(None, session.intro_path):
                logger.warning("Intro playback failed, continuing...")

        # Play episodes in order
        for play_history in sorted(session.play_history, key=lambda x: x.slot_order):
            video_path = play_history.video.path

            logger.info(
                f"Playing episode {play_history.slot_order}: "
                f"{play_history.video.series} {play_history.video.episode_code}"
            )

            started_at = datetime.utcnow()

            if self._play_file(play_history.id, video_path):
                ended_at = datetime.utcnow()

                # Update play history
                with get_db() as db:
                    ph = db.query(PlayHistory).filter(PlayHistory.id == play_history.id).first()
                    ph.started_at = started_at
                    ph.ended_at = ended_at
                    ph.completed = True

                logger.info(f"Episode {play_history.slot_order} completed")
            else:
                logger.error(f"Episode {play_history.slot_order} playback failed, skipping...")
                # Continue with next episode (fallback behavior)

        # Play outro
        if session.outro_path and Path(session.outro_path).exists():
            logger.info("Playing outro")
            if not self._play_file(None, session.outro_path):
                logger.warning("Outro playback failed")

        return True

    def _play_file(self, play_history_id: Optional[int], file_path: str) -> bool:
        """
        Play a single file.

        Args:
            play_history_id: PlayHistory ID (None for intro/outro)
            file_path: Path to file

        Returns:
            True if successful
        """
        path = Path(file_path)

        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        start_time = time.perf_counter()

        try:
            success = self.player.play(path, wait=True)
            end_time = time.perf_counter()

            gap_ms = (end_time - start_time) * 1000
            logger.debug(f"Playback gap: {gap_ms:.1f}ms")

            return success

        except Exception as e:
            logger.error(f"Playback error for {file_path}: {e}")
            return False

    def _dry_run_session(self, session: Session) -> bool:
        """
        Dry run mode - log what would be played.

        Args:
            session: Session to simulate

        Returns:
            Always True
        """
        logger.info("=== DRY RUN MODE ===")

        if session.intro_path:
            logger.info(f"Would play intro: {session.intro_path}")

        for ph in sorted(session.play_history, key=lambda x: x.slot_order):
            logger.info(
                f"Would play {ph.slot_order}: {ph.video.series} "
                f"{ph.video.episode_code} ({ph.video.duration_seconds}s)"
            )

        if session.outro_path:
            logger.info(f"Would play outro: {session.outro_path}")

        logger.info("=== END DRY RUN ===")
        return True

    def stop(self) -> None:
        """Stop current playback."""
        logger.info("Stopping playback")
        self.player.stop()
