"""Library service API for querying video metadata."""

import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from alma_tv.database import Feedback, PlayHistory, Video, get_db
from alma_tv.database.models import Rating
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class LibraryService:
    """Service for querying and managing video library."""

    def __init__(self):
        """Initialize library service."""
        self._cache_timestamp = datetime.now(timezone.utc)

    def list_series(self) -> List[dict]:
        """
        List all series in the library.

        Returns:
            List of dicts with series name and episode count
        """
        with get_db() as db:
            results = (
                db.query(
                    Video.series,
                    func.count(Video.id).label("episode_count"),
                    func.sum(Video.duration_seconds).label("total_duration"),
                )
                .filter(Video.disabled == False)
                .group_by(Video.series)
                .all()
            )

            return [
                {
                    "series": row.series,
                    "episode_count": row.episode_count,
                    "total_duration_seconds": row.total_duration or 0,
                }
                for row in results
            ]

    def list_episodes(
        self,
        series: Optional[str] = None,
        season: Optional[int] = None,
        disabled: bool = False,
    ) -> List[Video]:
        """
        List episodes with optional filtering.

        Args:
            series: Filter by series name
            season: Filter by season number
            disabled: Include disabled videos

        Returns:
            List of Video objects
        """
        with get_db() as db:
            query = db.query(Video)

            if not disabled:
                query = query.filter(Video.disabled == False)

            if series:
                query = query.filter(Video.series == series)

            if season is not None:
                query = query.filter(Video.season == season)

            results = query.order_by(Video.series, Video.season, Video.episode_code).all()
            for video in results:
                db.expunge(video)
            return results

    def get_video_by_id(self, video_id: int) -> Optional[Video]:
        """
        Get video by ID.

        Args:
            video_id: Video ID

        Returns:
            Video object or None
        """
        with get_db() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                db.expunge(video)
            return video

    def get_video_by_path(self, path: str) -> Optional[Video]:
        """
        Get video by file path.

        Args:
            path: File path

        Returns:
            Video object or None
        """
        with get_db() as db:
            video = db.query(Video).filter(Video.path == path).first()
            if video:
                db.expunge(video)
            return video

    def random_episode(
        self,
        series: Optional[str] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        exclude_video_ids: Optional[List[int]] = None,
        cooldown_days: int = 14,
    ) -> Optional[Video]:
        """
        Select a random episode with filters.

        Args:
            series: Filter by series name
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            exclude_video_ids: Video IDs to exclude
            cooldown_days: Exclude videos played within this many days

        Returns:
            Random Video object or None
        """
        with get_db() as db:
            query = db.query(Video).filter(Video.disabled == False)

            # Filter by series
            if series:
                query = query.filter(Video.series == series)

            # Filter by duration
            if min_duration is not None:
                query = query.filter(Video.duration_seconds >= min_duration)
            if max_duration is not None:
                query = query.filter(Video.duration_seconds <= max_duration)

            # Exclude specific videos
            if exclude_video_ids:
                query = query.filter(~Video.id.in_(exclude_video_ids))

            # Exclude recently played videos (cooldown)
            cooldown_date = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
            recent_plays = (
                db.query(PlayHistory.video_id)
                .filter(PlayHistory.started_at >= cooldown_date)
                .filter(PlayHistory.completed == True)
            )
            query = query.filter(~Video.id.in_(recent_plays))

            # Exclude "never again" videos
            never_again = (
                db.query(PlayHistory.video_id)
                .join(Feedback)
                .filter(Feedback.rating == Rating.NEVER)
            )
            query = query.filter(~Video.id.in_(never_again))

            # Get all matching videos
            candidates = query.all()

            if not candidates:
                logger.warning("No episodes match the criteria")
                return None

            # Random selection
            selected = random.choice(candidates)
            db.expunge(selected)
            return selected

    def random_episodes(
        self,
        count: int,
        series: Optional[str] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        cooldown_days: int = 14,
        ensure_diversity: bool = True,
    ) -> List[Video]:
        """
        Select multiple random episodes.

        Args:
            count: Number of episodes to select
            series: Filter by series name
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            cooldown_days: Exclude videos played within this many days
            ensure_diversity: Try to select from different series/seasons

        Returns:
            List of Video objects
        """
        selected = []
        exclude_ids = []

        for _ in range(count):
            episode = self.random_episode(
                series=series,
                min_duration=min_duration,
                max_duration=max_duration,
                exclude_video_ids=exclude_ids,
                cooldown_days=cooldown_days,
            )

            if not episode:
                break

            selected.append(episode)
            exclude_ids.append(episode.id)

            # If ensuring diversity, also exclude other episodes from same season
            if ensure_diversity:
                with get_db() as db:
                    same_season = (
                        db.query(Video.id)
                        .filter(Video.series == episode.series)
                        .filter(Video.season == episode.season)
                        .all()
                    )
                    exclude_ids.extend([v.id for v in same_season])

        return selected

    @lru_cache(maxsize=128)
    def get_series_stats(self, series: str) -> dict:
        """
        Get statistics for a series (cached).

        Args:
            series: Series name

        Returns:
            Dict with episode count, seasons, avg duration, etc.
        """
        with get_db() as db:
            episodes = (
                db.query(Video)
                .filter(Video.series == series)
                .filter(Video.disabled == False)
                .all()
            )

            if not episodes:
                return {}

            seasons = set(ep.season for ep in episodes)
            durations = [ep.duration_seconds for ep in episodes]

            return {
                "series": series,
                "episode_count": len(episodes),
                "season_count": len(seasons),
                "seasons": sorted(seasons),
                "avg_duration_seconds": sum(durations) // len(durations),
                "total_duration_seconds": sum(durations),
            }

    def get_recently_played(self, days: int = 14) -> List[Video]:
        """
        Get videos played in the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of Video objects
        """
        with get_db() as db:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            results = (
                db.query(Video)
                .join(PlayHistory)
                .filter(PlayHistory.started_at >= cutoff_date)
                .filter(PlayHistory.completed == True)
                .distinct()
                .all()
            )

            return results

    def disable_video(self, video_id: int) -> bool:
        """
        Disable a video.

        Args:
            video_id: Video ID

        Returns:
            True if successful
        """
        try:
            with get_db() as db:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.disabled = True
                    logger.info(f"Disabled video: {video.series} {video.episode_code}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to disable video {video_id}: {e}")
            return False

    def enable_video(self, video_id: int) -> bool:
        """
        Enable a video.

        Args:
            video_id: Video ID

        Returns:
            True if successful
        """
        try:
            with get_db() as db:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.disabled = False
                    logger.info(f"Enabled video: {video.series} {video.episode_code}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to enable video {video_id}: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear LRU cache."""
        self.get_series_stats.cache_clear()
        self._cache_timestamp = datetime.now(timezone.utc)
        logger.debug("Library service cache cleared")
