"""Weight calculation for episode selection."""

from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy import func

from alma_tv.database import Feedback, PlayHistory, Video, get_db
from alma_tv.database.models import Rating
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class WeightCalculator:
    """
    Calculate selection weights for videos based on feedback and play history.

    Weight model:
    - Baseline weight: 1.0
    - Liked bonus: +0.5 per vote, decays weekly (50% per week)
    - Okay: leaves baseline
    - Never: weight = 0 (excluded)
    - Not played recently: boost factor based on time since last play
    """

    BASELINE_WEIGHT = 1.0
    LIKED_BONUS = 0.5
    DECAY_HALF_LIFE_DAYS = 7
    NEVER_AGAIN_WEIGHT = 0.0

    def __init__(self):
        """Initialize weight calculator."""
        pass

    def calculate_weight(
        self,
        video_id: int,
        as_of_date: Optional[datetime] = None,
    ) -> float:
        """
        Calculate weight for a video.

        Args:
            video_id: Video ID
            as_of_date: Calculate weight as of this date (defaults to now)

        Returns:
            Weight value (0.0 = never, higher = more likely to be selected)
        """
        if as_of_date is None:
            as_of_date = datetime.utcnow()

        weight = self.BASELINE_WEIGHT

        with get_db() as db:
            # Check for "never again" feedback
            never_feedback = (
                db.query(Feedback)
                .join(PlayHistory)
                .filter(PlayHistory.video_id == video_id)
                .filter(Feedback.rating == Rating.NEVER)
                .first()
            )

            if never_feedback:
                logger.debug(f"Video {video_id} marked as 'never again'")
                return self.NEVER_AGAIN_WEIGHT

            # Get all feedback for this video
            feedback_records = (
                db.query(Feedback, PlayHistory)
                .join(PlayHistory)
                .filter(PlayHistory.video_id == video_id)
                .all()
            )

            # Apply liked bonuses with decay
            for feedback, play_history in feedback_records:
                if feedback.rating == Rating.LIKED:
                    # Calculate decay based on time since feedback
                    days_ago = (as_of_date - feedback.submitted_at).days
                    decay_factor = 0.5 ** (days_ago / self.DECAY_HALF_LIFE_DAYS)
                    bonus = self.LIKED_BONUS * decay_factor
                    weight += bonus
                    logger.debug(
                        f"Video {video_id}: liked bonus {bonus:.3f} (decay: {decay_factor:.3f})"
                    )

            # Boost for videos not played recently
            last_play = (
                db.query(PlayHistory)
                .filter(PlayHistory.video_id == video_id)
                .filter(PlayHistory.completed == True)
                .order_by(PlayHistory.started_at.desc())
                .first()
            )

            if last_play:
                days_since_play = (as_of_date - last_play.started_at).days
                # Boost increases linearly after 14 days
                if days_since_play > 14:
                    boost = min((days_since_play - 14) / 100, 0.5)
                    weight += boost
                    logger.debug(f"Video {video_id}: freshness boost {boost:.3f}")

        return weight

    def calculate_weights_batch(
        self,
        video_ids: list[int],
        as_of_date: Optional[datetime] = None,
    ) -> Dict[int, float]:
        """
        Calculate weights for multiple videos efficiently.

        Args:
            video_ids: List of video IDs
            as_of_date: Calculate weights as of this date

        Returns:
            Dict mapping video_id to weight
        """
        weights = {}
        for video_id in video_ids:
            weights[video_id] = self.calculate_weight(video_id, as_of_date)
        return weights

    def update_weight_for_feedback(self, video_id: int) -> None:
        """
        Trigger weight recalculation after feedback is added.

        This is a hook for the feedback module to notify the scheduler
        that weights need updating. Currently just clears any cached values.

        Args:
            video_id: Video ID that received feedback
        """
        logger.info(f"Weight update triggered for video {video_id}")
        # In a more sophisticated system, this could update a materialized view
        # or cache. For now, weights are calculated on-demand.

    def get_weight_distribution(
        self,
        video_ids: list[int],
    ) -> Dict[str, float]:
        """
        Get statistics about weight distribution.

        Args:
            video_ids: List of video IDs

        Returns:
            Dict with min, max, mean, and stddev of weights
        """
        weights = self.calculate_weights_batch(video_ids)
        weight_values = list(weights.values())

        if not weight_values:
            return {"min": 0, "max": 0, "mean": 0, "stddev": 0}

        import statistics

        return {
            "min": min(weight_values),
            "max": max(weight_values),
            "mean": statistics.mean(weight_values),
            "stddev": statistics.stdev(weight_values) if len(weight_values) > 1 else 0,
        }

    def get_top_weighted_videos(
        self,
        limit: int = 10,
        min_weight: float = 0.0,
    ) -> list[tuple[int, float]]:
        """
        Get videos with highest weights.

        Args:
            limit: Maximum number of videos to return
            min_weight: Minimum weight threshold

        Returns:
            List of (video_id, weight) tuples sorted by weight descending
        """
        with get_db() as db:
            videos = db.query(Video).filter(Video.disabled == False).all()
            video_ids = [v.id for v in videos]

        weights = self.calculate_weights_batch(video_ids)

        # Filter and sort
        weighted_videos = [
            (vid, weight) for vid, weight in weights.items() if weight >= min_weight
        ]
        weighted_videos.sort(key=lambda x: x[1], reverse=True)

        return weighted_videos[:limit]
