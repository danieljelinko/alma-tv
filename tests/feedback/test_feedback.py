"""Tests for feedback UI."""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from alma_tv.database import Session, PlayHistory, Video, Feedback
from alma_tv.database.models import Rating, SessionStatus
# We need to import the app creation logic, but it's inside run_feedback_ui
# So we'll mock the app for testing or restructure slightly.
# For now, let's test the logic by mocking get_db and checking the route handlers if possible.
# Or better, let's refactor ui.py slightly to expose the app factory.

# Actually, FastHTML's `fast_app` returns app, rt. We can extract that.
# But `run_feedback_ui` calls `serve`.
# Let's just test the database logic via the reporter for now, 
# and maybe a simple integration test for the UI routes if we can access the app.

from alma_tv.feedback.reporter import FeedbackReporter

def test_feedback_ui_routes(db_session):
    """Test feedback UI routes."""
    from alma_tv.feedback.ui import create_app
    
    app = create_app()
    client = TestClient(app)

    # Test index route
    response = client.get("/")
    assert response.status_code == 200
    # Expect "No recent shows found" because the DB is empty in this test
    assert "No recent shows found" in response.text

def test_feedback_submission(db_session):
    """Test submitting feedback."""
    from alma_tv.feedback.ui import create_app
    
    # Create a test session and play history
    video = Video(
        series="Test Series",
        season=1,
        episode_code="S01E01",
        path="/tmp/test.mp4",
        duration_seconds=600
    )
    db_session.add(video)
    db_session.commit()

    session = Session(show_date=datetime.utcnow(), status=SessionStatus.COMPLETED)
    db_session.add(session)
    db_session.commit()

    ph = PlayHistory(
        session_id=session.id,
        video_id=video.id,
        slot_order=1,
        completed=True
    )
    db_session.add(ph)
    db_session.commit()

    app = create_app()
    client = TestClient(app)

    # Submit feedback
    # Note: Route is /submit/{ph_id}/{rating_str}
    response = client.post(
        f"/submit/{ph.id}/liked",
        follow_redirects=True
    )
    assert response.status_code == 200
    
    # Verify feedback in DB
    feedback = db_session.query(Feedback).filter_by(play_history_id=ph.id).first()
    assert feedback is not None
    assert feedback.rating == Rating.LIKED

def test_reporter_summary(db_session):
    """Test feedback summary generation."""
    # Create sample data
    video = Video(series="Bluey", season=1, episode_code="S01E01", path="/tmp/test.mp4", duration_seconds=420)
    db_session.add(video)
    db_session.flush()
    
    session = Session(show_date=datetime.now(timezone.utc), status=SessionStatus.COMPLETED)
    db_session.add(session)
    db_session.flush()
    
    ph = PlayHistory(session_id=session.id, video_id=video.id, slot_order=1, completed=True)
    db_session.add(ph)
    db_session.flush()
    
    # Add feedback
    fb = Feedback(play_history_id=ph.id, rating=Rating.LIKED, submitted_at=datetime.now(timezone.utc))
    db_session.add(fb)
    db_session.commit()
    
    reporter = FeedbackReporter()
    summary = reporter.get_recent_summary(days=30)
    
    assert summary["total_feedback"] == 1
    assert summary["liked"] == 1
    assert summary["liked_percentage"] == 100.0
    assert summary["okay"] == 0
    assert summary["never"] == 0

def test_reporter_export_csv(db_session):
    """Test CSV export."""
    # (Setup same data as above - simplified for brevity)
    video = Video(series="Bluey", season=1, episode_code="S01E01", path="/tmp/test.mp4", duration_seconds=420)
    db_session.add(video)
    session = Session(show_date=datetime.now(timezone.utc), status=SessionStatus.COMPLETED)
    db_session.add(session)
    db_session.flush()
    ph = PlayHistory(session_id=session.id, video_id=video.id, slot_order=1, completed=True)
    db_session.add(ph)
    db_session.flush()
    fb = Feedback(play_history_id=ph.id, rating=Rating.LIKED, submitted_at=datetime.now(timezone.utc))
    db_session.add(fb)
    db_session.commit()
    
    reporter = FeedbackReporter()
    csv_data = reporter.export_to_csv(days=30)
    
    assert "Date,Series,Episode,Rating" in csv_data
    assert "Bluey,S01E01,liked" in csv_data
