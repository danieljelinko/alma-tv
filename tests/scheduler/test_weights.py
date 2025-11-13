"""Tests for weight calculation."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from alma_tv.database import Feedback, PlayHistory, Session, Video, get_db, init_db
from alma_tv.database.models import Rating, SessionStatus
from alma_tv.scheduler.weights import WeightCalculator


@pytest.fixture(scope="function")
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"

    with patch("alma_tv.config.get_settings") as mock_settings:
        mock_settings.return_value.database_url = f"sqlite:///{db_path}"
        mock_settings.return_value.debug = False

        init_db()
        yield


@pytest.fixture
def sample_videos_with_feedback(test_db):
    """Create sample videos with feedback."""
    videos = [
        Video(
            series="Bluey",
            season=1,
            episode_code="S01E01",
            path="/media/bluey_s01e01.mp4",
            duration_seconds=420,
            disabled=False,
        ),
        Video(
            series="Bluey",
            season=1,
            episode_code="S01E02",
            path="/media/bluey_s01e02.mp4",
            duration_seconds=430,
            disabled=False,
        ),
        Video(
            series="Paw Patrol",
            season=1,
            episode_code="S01E01",
            path="/media/pawpatrol_s01e01.mp4",
            duration_seconds=600,
            disabled=False,
        ),
    ]

    with get_db() as db:
        for video in videos:
            db.add(video)
        db.flush()

        # Create session
        session = Session(
            show_date=datetime.utcnow() - timedelta(days=10),
            status=SessionStatus.COMPLETED,
        )
        db.add(session)
        db.flush()

        # Video 1: liked
        play1 = PlayHistory(
            session_id=session.id,
            video_id=1,
            slot_order=1,
            started_at=datetime.utcnow() - timedelta(days=10),
            ended_at=datetime.utcnow() - timedelta(days=10),
            completed=True,
        )
        db.add(play1)
        db.flush()

        feedback1 = Feedback(play_history_id=play1.id, rating=Rating.LIKED)
        db.add(feedback1)

        # Video 2: never again
        play2 = PlayHistory(
            session_id=session.id,
            video_id=2,
            slot_order=2,
            started_at=datetime.utcnow() - timedelta(days=10),
            ended_at=datetime.utcnow() - timedelta(days=10),
            completed=True,
        )
        db.add(play2)
        db.flush()

        feedback2 = Feedback(play_history_id=play2.id, rating=Rating.NEVER)
        db.add(feedback2)

        # Video 3: no feedback

    return videos


def test_baseline_weight(test_db):
    """Test baseline weight for video without feedback."""
    with get_db() as db:
        video = Video(
            series="Test",
            season=1,
            episode_code="S01E01",
            path="/test.mp4",
            duration_seconds=420,
        )
        db.add(video)
        db.flush()
        video_id = video.id

    calc = WeightCalculator()
    weight = calc.calculate_weight(video_id)

    assert weight == WeightCalculator.BASELINE_WEIGHT


def test_liked_bonus(sample_videos_with_feedback):
    """Test that liked feedback increases weight."""
    calc = WeightCalculator()
    weight = calc.calculate_weight(1)  # Video with liked feedback

    # Should be baseline + liked bonus (with some decay)
    assert weight > WeightCalculator.BASELINE_WEIGHT
    assert weight < WeightCalculator.BASELINE_WEIGHT + WeightCalculator.LIKED_BONUS * 1.5


def test_never_again_weight(sample_videos_with_feedback):
    """Test that 'never again' feedback sets weight to zero."""
    calc = WeightCalculator()
    weight = calc.calculate_weight(2)  # Video marked never again

    assert weight == WeightCalculator.NEVER_AGAIN_WEIGHT


def test_weight_decay(test_db):
    """Test that liked bonus decays over time."""
    with get_db() as db:
        video = Video(
            series="Test",
            season=1,
            episode_code="S01E01",
            path="/test.mp4",
            duration_seconds=420,
        )
        db.add(video)
        db.flush()

        session = Session(show_date=datetime.utcnow(), status=SessionStatus.COMPLETED)
        db.add(session)
        db.flush()

        # Liked 7 days ago (one half-life)
        play = PlayHistory(
            session_id=session.id,
            video_id=video.id,
            slot_order=1,
            started_at=datetime.utcnow() - timedelta(days=7),
            ended_at=datetime.utcnow() - timedelta(days=7),
            completed=True,
        )
        db.add(play)
        db.flush()

        feedback = Feedback(
            play_history_id=play.id,
            rating=Rating.LIKED,
            submitted_at=datetime.utcnow() - timedelta(days=7),
        )
        db.add(feedback)
        video_id = video.id

    calc = WeightCalculator()

    # Weight now
    weight_now = calc.calculate_weight(video_id)

    # Weight 7 days ago (should be higher due to less decay)
    weight_past = calc.calculate_weight(video_id, datetime.utcnow() - timedelta(days=7))

    assert weight_now < weight_past


def test_freshness_boost(test_db):
    """Test that videos not played recently get a boost."""
    with get_db() as db:
        video = Video(
            series="Test",
            season=1,
            episode_code="S01E01",
            path="/test.mp4",
            duration_seconds=420,
        )
        db.add(video)
        db.flush()

        session = Session(show_date=datetime.utcnow(), status=SessionStatus.COMPLETED)
        db.add(session)
        db.flush()

        # Played 30 days ago
        play = PlayHistory(
            session_id=session.id,
            video_id=video.id,
            slot_order=1,
            started_at=datetime.utcnow() - timedelta(days=30),
            ended_at=datetime.utcnow() - timedelta(days=30),
            completed=True,
        )
        db.add(play)
        video_id = video.id

    calc = WeightCalculator()
    weight = calc.calculate_weight(video_id)

    # Should have freshness boost
    assert weight > WeightCalculator.BASELINE_WEIGHT


def test_batch_calculation(sample_videos_with_feedback):
    """Test batch weight calculation."""
    calc = WeightCalculator()
    weights = calc.calculate_weights_batch([1, 2, 3])

    assert len(weights) == 3
    assert 1 in weights
    assert 2 in weights
    assert 3 in weights

    # Video 2 should have zero weight (never again)
    assert weights[2] == 0.0


def test_weight_distribution(sample_videos_with_feedback):
    """Test weight distribution statistics."""
    calc = WeightCalculator()
    stats = calc.get_weight_distribution([1, 2, 3])

    assert "min" in stats
    assert "max" in stats
    assert "mean" in stats
    assert "stddev" in stats

    # Video 2 has weight 0, so min should be 0
    assert stats["min"] == 0.0


def test_top_weighted_videos(sample_videos_with_feedback):
    """Test getting top weighted videos."""
    calc = WeightCalculator()
    top = calc.get_top_weighted_videos(limit=5)

    assert len(top) <= 5
    assert all(isinstance(item, tuple) for item in top)
    assert all(len(item) == 2 for item in top)

    # Check sorted descending
    weights = [w for _, w in top]
    assert weights == sorted(weights, reverse=True)


def test_update_weight_hook(sample_videos_with_feedback):
    """Test weight update hook."""
    calc = WeightCalculator()

    # Should not raise an error
    calc.update_weight_for_feedback(1)
