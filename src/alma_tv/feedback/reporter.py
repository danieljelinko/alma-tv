"""Feedback reporting and statistics."""

import csv
import json
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from alma_tv.database import Feedback, PlayHistory, Video, get_db
from alma_tv.database.models import Rating
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class FeedbackReporter:
    """Generates reports on user feedback."""

    def get_recent_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary statistics for recent feedback.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with stats
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        with get_db() as db:
            total = (
                db.query(func.count(Feedback.id))
                .filter(Feedback.submitted_at >= cutoff)
                .scalar()
            ) or 0

            if total == 0:
                return {
                    "total_feedback": 0,
                    "liked": 0, "liked_percentage": 0.0,
                    "okay": 0, "okay_percentage": 0.0,
                    "never": 0, "never_percentage": 0.0,
                }

            liked = (
                db.query(func.count(Feedback.id))
                .filter(Feedback.submitted_at >= cutoff, Feedback.rating == Rating.LIKED)
                .scalar()
            ) or 0

            okay = (
                db.query(func.count(Feedback.id))
                .filter(Feedback.submitted_at >= cutoff, Feedback.rating == Rating.OKAY)
                .scalar()
            ) or 0

            never = (
                db.query(func.count(Feedback.id))
                .filter(Feedback.submitted_at >= cutoff, Feedback.rating == Rating.NEVER)
                .scalar()
            ) or 0

            return {
                "total_feedback": total,
                "liked": liked,
                "liked_percentage": (liked / total) * 100,
                "okay": okay,
                "okay_percentage": (okay / total) * 100,
                "never": never,
                "never_percentage": (never / total) * 100,
            }

    def get_top_liked_episodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get episodes with the most 'liked' ratings."""
        with get_db() as db:
            results = (
                db.query(Video, func.count(Feedback.id).label("likes"))
                .select_from(Video)
                .join(PlayHistory, Video.id == PlayHistory.video_id)
                .join(Feedback, PlayHistory.id == Feedback.play_history_id)
                .filter(Feedback.rating == Rating.LIKED)
                .group_by(Video.id)
                .order_by(func.count(Feedback.id).desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "series": v.series,
                    "episode_code": v.episode_code,
                    "title": v.title,
                    "like_count": count,
                }
                for v, count in results
            ]

    def get_never_again_episodes(self) -> List[Dict[str, Any]]:
        """Get episodes marked as 'never again'."""
        with get_db() as db:
            results = (
                db.query(Video, func.count(Feedback.id).label("nevers"))
                .select_from(Video)
                .join(PlayHistory, Video.id == PlayHistory.video_id)
                .join(Feedback, PlayHistory.id == Feedback.play_history_id)
                .filter(Feedback.rating == Rating.NEVER)
                .group_by(Video.id)
                .all()
            )

            return [
                {
                    "series": v.series,
                    "episode_code": v.episode_code,
                    "title": v.title,
                    "never_count": count,
                }
                for v, count in results
            ]

    def export_to_csv(self, days: int = 30) -> str:
        """Export feedback data to CSV string."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Date", "Series", "Episode", "Rating"])

        with get_db() as db:
            feedbacks = (
                db.query(Feedback, PlayHistory, Video)
                .select_from(Feedback)
                .join(PlayHistory, Feedback.play_history_id == PlayHistory.id)
                .join(Video, PlayHistory.video_id == Video.id)
                .filter(Feedback.submitted_at >= cutoff)
                .order_by(Feedback.submitted_at.desc())
                .all()
            )

            for fb, ph, v in feedbacks:
                writer.writerow([
                    fb.submitted_at.isoformat(),
                    v.series,
                    v.episode_code,
                    fb.rating.value
                ])

        return output.getvalue()

    def export_to_json(self, days: int = 30) -> str:
        """Export feedback data to JSON string."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with get_db() as db:
            feedbacks = (
                db.query(Feedback, PlayHistory, Video)
                .select_from(Feedback)
                .join(PlayHistory, Feedback.play_history_id == PlayHistory.id)
                .join(Video, PlayHistory.video_id == Video.id)
                .filter(Feedback.submitted_at >= cutoff)
                .order_by(Feedback.submitted_at.desc())
                .all()
            )

            data = [
                {
                    "date": fb.submitted_at.isoformat(),
                    "series": v.series,
                    "episode_code": v.episode_code,
                    "rating": fb.rating.value,
                }
                for fb, ph, v in feedbacks
            ]

        return json.dumps(data, indent=2)
