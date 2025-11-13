"""Feedback API and storage."""

from datetime import datetime
from typing import List, Optional

from alma_tv.database import Feedback, PlayHistory, get_db
from alma_tv.database.models import Rating
from alma_tv.logging.config import get_logger
from alma_tv.scheduler.weights import WeightCalculator

logger = get_logger(__name__)


class FeedbackService:
    """Service for managing feedback collection and storage."""

    def __init__(self):
        """Initialize feedback service."""
        self.weights = WeightCalculator()

    def submit_feedback(
        self,
        play_history_id: int,
        rating: str,
    ) -> bool:
        """
        Submit feedback for a played episode.

        Args:
            play_history_id: PlayHistory ID
            rating: Rating value ('liked', 'okay', 'never')

        Returns:
            True if successful
        """
        try:
            # Validate rating
            if rating not in ["liked", "okay", "never"]:
                logger.error(f"Invalid rating: {rating}")
                return False

            rating_enum = Rating[rating.upper()]

            with get_db() as db:
                # Check if play history exists
                play_history = (
                    db.query(PlayHistory).filter(PlayHistory.id == play_history_id).first()
                )

                if not play_history:
                    logger.error(f"PlayHistory not found: {play_history_id}")
                    return False

                # Check if feedback already exists
                existing = (
                    db.query(Feedback).filter(Feedback.play_history_id == play_history_id).first()
                )

                if existing:
                    # Update existing feedback
                    existing.rating = rating_enum
                    existing.submitted_at = datetime.utcnow()
                    logger.info(f"Updated feedback for play_history {play_history_id}: {rating}")
                else:
                    # Create new feedback
                    feedback = Feedback(
                        play_history_id=play_history_id,
                        rating=rating_enum,
                    )
                    db.add(feedback)
                    logger.info(f"Submitted feedback for play_history {play_history_id}: {rating}")

                # Trigger weight update
                self.weights.update_weight_for_feedback(play_history.video_id)

                return True

        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}", exc_info=True)
            return False

    def submit_session_feedback(
        self,
        session_id: int,
        ratings: dict[int, str],
    ) -> dict[int, bool]:
        """
        Submit feedback for multiple episodes in a session.

        Args:
            session_id: Session ID
            ratings: Dict mapping slot_order to rating

        Returns:
            Dict mapping slot_order to success status
        """
        results = {}

        with get_db() as db:
            play_histories = (
                db.query(PlayHistory)
                .filter(PlayHistory.session_id == session_id)
                .all()
            )

            for ph in play_histories:
                if ph.slot_order in ratings:
                    rating = ratings[ph.slot_order]
                    success = self.submit_feedback(ph.id, rating)
                    results[ph.slot_order] = success

        return results

    def get_episode_feedback(self, video_id: int) -> List[dict]:
        """
        Get all feedback for a specific video.

        Args:
            video_id: Video ID

        Returns:
            List of feedback dicts
        """
        with get_db() as db:
            feedbacks = (
                db.query(Feedback)
                .join(PlayHistory)
                .filter(PlayHistory.video_id == video_id)
                .all()
            )

            return [
                {
                    "rating": f.rating.value,
                    "submitted_at": f.submitted_at.isoformat(),
                    "play_history_id": f.play_history_id,
                }
                for f in feedbacks
            ]

    def get_session_feedback(self, session_id: int) -> dict:
        """
        Get feedback summary for a session.

        Args:
            session_id: Session ID

        Returns:
            Dict with feedback status
        """
        with get_db() as db:
            play_histories = (
                db.query(PlayHistory)
                .filter(PlayHistory.session_id == session_id)
                .all()
            )

            feedback_data = {}

            for ph in play_histories:
                feedback = (
                    db.query(Feedback).filter(Feedback.play_history_id == ph.id).first()
                )

                feedback_data[ph.slot_order] = {
                    "video_id": ph.video_id,
                    "series": ph.video.series,
                    "episode_code": ph.video.episode_code,
                    "has_feedback": feedback is not None,
                    "rating": feedback.rating.value if feedback else None,
                }

            return feedback_data

    def mark_as_okay_timeout(self, session_id: int) -> int:
        """
        Mark all episodes without feedback as 'okay' (timeout).

        Args:
            session_id: Session ID

        Returns:
            Number of episodes marked as okay
        """
        count = 0

        with get_db() as db:
            play_histories = (
                db.query(PlayHistory)
                .filter(PlayHistory.session_id == session_id)
                .all()
            )

            for ph in play_histories:
                # Check if feedback exists
                existing = (
                    db.query(Feedback).filter(Feedback.play_history_id == ph.id).first()
                )

                if not existing:
                    # Create 'okay' feedback
                    feedback = Feedback(
                        play_history_id=ph.id,
                        rating=Rating.OKAY,
                    )
                    db.add(feedback)
                    count += 1

        logger.info(f"Marked {count} episodes as 'okay' (timeout)")
        return count
