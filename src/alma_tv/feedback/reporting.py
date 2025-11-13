"""Feedback analytics and reporting."""

import csv
import json
from datetime import datetime, timedelta
from io import StringIO
from typing import Dict, List, Optional

from sqlalchemy import func

from alma_tv.database import Feedback, PlayHistory, Video, get_db
from alma_tv.database.models import Rating
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class FeedbackReporter:
    """Generate reports and analytics from feedback data."""

    def __init__(self):
        """Initialize feedback reporter."""
        pass

    def get_recent_summary(self, days: int = 30) -> dict:
        """
        Get summary of recent feedback.

        Args:
            days: Number of days to look back

        Returns:
            Summary dict with counts and percentages
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with get_db() as db:
            feedbacks = (
                db.query(Feedback)
                .filter(Feedback.submitted_at >= cutoff_date)
                .all()
            )

            total = len(feedbacks)
            liked = sum(1 for f in feedbacks if f.rating == Rating.LIKED)
            okay = sum(1 for f in feedbacks if f.rating == Rating.OKAY)
            never = sum(1 for f in feedbacks if f.rating == Rating.NEVER)

            return {
                "period_days": days,
                "total_feedback": total,
                "liked": liked,
                "okay": okay,
                "never": never,
                "liked_percentage": (liked / total * 100) if total > 0 else 0,
                "okay_percentage": (okay / total * 100) if total > 0 else 0,
                "never_percentage": (never / total * 100) if total > 0 else 0,
            }

    def get_never_again_episodes(self) -> List[dict]:
        """
        Get list of episodes marked as 'never again'.

        Returns:
            List of video dicts
        """
        with get_db() as db:
            results = (
                db.query(Video, func.count(Feedback.id).label("never_count"))
                .join(PlayHistory)
                .join(Feedback)
                .filter(Feedback.rating == Rating.NEVER)
                .group_by(Video.id)
                .all()
            )

            return [
                {
                    "video_id": video.id,
                    "series": video.series,
                    "season": video.season,
                    "episode_code": video.episode_code,
                    "title": video.title,
                    "never_count": count,
                }
                for video, count in results
            ]

    def get_top_liked_episodes(self, limit: int = 10) -> List[dict]:
        """
        Get most liked episodes.

        Args:
            limit: Maximum number to return

        Returns:
            List of video dicts with like counts
        """
        with get_db() as db:
            results = (
                db.query(Video, func.count(Feedback.id).label("like_count"))
                .join(PlayHistory)
                .join(Feedback)
                .filter(Feedback.rating == Rating.LIKED)
                .group_by(Video.id)
                .order_by(func.count(Feedback.id).desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "video_id": video.id,
                    "series": video.series,
                    "season": video.season,
                    "episode_code": video.episode_code,
                    "title": video.title,
                    "like_count": count,
                }
                for video, count in results
            ]

    def get_series_feedback_summary(self) -> Dict[str, dict]:
        """
        Get feedback summary grouped by series.

        Returns:
            Dict mapping series name to feedback stats
        """
        with get_db() as db:
            results = (
                db.query(
                    Video.series,
                    Feedback.rating,
                    func.count(Feedback.id).label("count"),
                )
                .join(PlayHistory)
                .join(Feedback)
                .group_by(Video.series, Feedback.rating)
                .all()
            )

            series_data: Dict[str, dict] = {}

            for series, rating, count in results:
                if series not in series_data:
                    series_data[series] = {"liked": 0, "okay": 0, "never": 0}

                series_data[series][rating.value] = count

            # Calculate totals and percentages
            for series, data in series_data.items():
                total = data["liked"] + data["okay"] + data["never"]
                data["total"] = total
                data["liked_percentage"] = (data["liked"] / total * 100) if total > 0 else 0

            return series_data

    def export_to_csv(self, days: Optional[int] = None) -> str:
        """
        Export feedback data to CSV format.

        Args:
            days: Number of days to include (None for all)

        Returns:
            CSV string
        """
        with get_db() as db:
            query = (
                db.query(Feedback, PlayHistory, Video)
                .join(PlayHistory)
                .join(Video)
            )

            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Feedback.submitted_at >= cutoff)

            results = query.all()

            output = StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                "Feedback ID",
                "Rating",
                "Submitted At",
                "Series",
                "Season",
                "Episode Code",
                "Title",
                "Video ID",
            ])

            # Data rows
            for feedback, play_history, video in results:
                writer.writerow([
                    feedback.id,
                    feedback.rating.value,
                    feedback.submitted_at.isoformat(),
                    video.series,
                    video.season,
                    video.episode_code,
                    video.title or "",
                    video.id,
                ])

            return output.getvalue()

    def export_to_json(self, days: Optional[int] = None) -> str:
        """
        Export feedback data to JSON format.

        Args:
            days: Number of days to include (None for all)

        Returns:
            JSON string
        """
        with get_db() as db:
            query = (
                db.query(Feedback, PlayHistory, Video)
                .join(PlayHistory)
                .join(Video)
            )

            if days:
                cutoff = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Feedback.submitted_at >= cutoff)

            results = query.all()

            data = []
            for feedback, play_history, video in results:
                data.append({
                    "feedback_id": feedback.id,
                    "rating": feedback.rating.value,
                    "submitted_at": feedback.submitted_at.isoformat(),
                    "series": video.series,
                    "season": video.season,
                    "episode_code": video.episode_code,
                    "title": video.title,
                    "video_id": video.id,
                })

            return json.dumps(data, indent=2)
