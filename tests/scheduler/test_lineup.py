"""Tests for lineup generation."""

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest

from alma_tv.database import Session, Video, get_db, init_db
from alma_tv.database.models import SessionStatus
from alma_tv.scheduler.lineup import LineupGenerator


@pytest.fixture(scope="function")
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"

    with patch("alma_tv.config.get_settings") as mock_settings:
        mock_settings.return_value.database_url = f"sqlite:///{db_path}"
        mock_settings.return_value.debug = False
        mock_settings.return_value.target_duration_minutes = 30
        mock_settings.return_value.repeat_cooldown_days = 14
        mock_settings.return_value.intro_path = tmp_path / "intro.mp4"
        mock_settings.return_value.outro_path = tmp_path / "outro.mp4"

        # Create empty intro/outro files
        (tmp_path / "intro.mp4").touch()
        (tmp_path / "outro.mp4").touch()

        init_db()
        yield


@pytest.fixture
def sample_videos(test_db):
    """Create sample videos."""
    videos = []
    for series_id in range(3):
        for season in range(1, 3):
            for ep in range(1, 6):
                video = Video(
                    series=f"Series{series_id}",
                    season=season,
                    episode_code=f"S{season:02d}E{ep:02d}",
                    path=f"/media/s{series_id}_s{season}_e{ep}.mp4",
                    duration_seconds=400 + (ep * 10),  # 400-450s
                    disabled=False,
                )
                videos.append(video)

    with get_db() as db:
        for video in videos:
            db.add(video)

    return videos


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_generate_lineup_basic(mock_duration, sample_videos):
    """Test basic lineup generation."""
    # Mock intro/outro durations
    mock_duration.return_value = 10  # 10 seconds each

    generator = LineupGenerator(seed=42)
    session_id = generator.generate_lineup(target_date=date(2025, 11, 13))

    assert session_id is not None

    # Verify session created
    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id).first()
        assert session is not None
        assert session.status == SessionStatus.PLANNED

        # Verify play history
        assert len(session.play_history) >= 3
        assert len(session.play_history) <= 5


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_lineup_runtime_target(mock_duration, sample_videos):
    """Test that lineup respects runtime target."""
    mock_duration.return_value = 10

    generator = LineupGenerator(seed=42)
    session_id = generator.generate_lineup(
        target_date=date(2025, 11, 13), target_duration_minutes=30
    )

    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id).first()
        total_duration = session.total_duration_seconds

        # Target: 30 minutes = 1800s, minus 20s for intro/outro = 1780s
        # Should be within ±60s
        assert abs(total_duration - 1780) <= 60


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_lineup_diversity(mock_duration, sample_videos):
    """Test that lineup maintains series diversity."""
    mock_duration.return_value = 10

    generator = LineupGenerator(seed=42)
    session_id = generator.generate_lineup(target_date=date(2025, 11, 13))

    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id).first()

        # Check series diversity
        series_list = [ph.video.series for ph in session.play_history]
        unique_series = set(series_list)

        # Should have at least 2 different series
        assert len(unique_series) >= 2


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_lineup_handles_requests(mock_duration, sample_videos):
    """Test that lineup handles explicit requests."""
    mock_duration.return_value = 10

    generator = LineupGenerator(seed=42)
    session_id = generator.generate_lineup(
        target_date=date(2025, 11, 13), request_payload={"series": "Series0", "count": 3}
    )

    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id).first()

        # Check that requested series is heavily represented
        series_list = [ph.video.series for ph in session.play_history]
        series0_count = sum(1 for s in series_list if s == "Series0")

        # Should have at least 2 episodes from requested series
        assert series0_count >= 2


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_lineup_prevents_duplicates(mock_duration, sample_videos):
    """Test that lineup doesn't create duplicate if one exists."""
    mock_duration.return_value = 10

    generator = LineupGenerator(seed=42)

    # Create first lineup
    session_id1 = generator.generate_lineup(target_date=date(2025, 11, 13))

    # Try to create another for same date
    session_id2 = generator.generate_lineup(target_date=date(2025, 11, 13))

    # Should return same session ID
    assert session_id1 == session_id2


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_lineup_respects_cooldown(mock_duration, sample_videos):
    """Test that lineup respects cooldown period."""
    mock_duration.return_value = 10

    # Create a lineup for yesterday
    generator = LineupGenerator(seed=42)
    yesterday = date.today() - timedelta(days=1)
    session_id1 = generator.generate_lineup(target_date=yesterday)

    # Mark episodes as played
    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id1).first()
        session.status = SessionStatus.COMPLETED

        for ph in session.play_history:
            ph.started_at = datetime.utcnow() - timedelta(days=1)
            ph.ended_at = datetime.utcnow() - timedelta(days=1)
            ph.completed = True

    # Generate lineup for today
    session_id2 = generator.generate_lineup(target_date=date.today())

    # Get video IDs from both sessions
    with get_db() as db:
        session1 = db.query(Session).filter(Session.id == session_id1).first()
        session2 = db.query(Session).filter(Session.id == session_id2).first()

        videos1 = {ph.video_id for ph in session1.play_history}
        videos2 = {ph.video_id for ph in session2.play_history}

        # No overlap (cooldown enforced)
        assert len(videos1 & videos2) == 0


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_lineup_episode_count_bounds(mock_duration, sample_videos):
    """Test that lineup respects episode count bounds."""
    mock_duration.return_value = 10

    generator = LineupGenerator(seed=42)
    session_id = generator.generate_lineup(
        target_date=date(2025, 11, 13), min_episodes=3, max_episodes=5
    )

    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id).first()
        episode_count = len(session.play_history)

        assert 3 <= episode_count <= 5


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_lineup_deterministic_with_seed(mock_duration, sample_videos):
    """Test that lineup generation is deterministic with seed."""
    mock_duration.return_value = 10

    # Generate two lineups with same seed
    generator1 = LineupGenerator(seed=42)
    session_id1 = generator1.generate_lineup(target_date=date(2025, 11, 13))

    # Clear database
    with get_db() as db:
        db.query(Session).delete()

    generator2 = LineupGenerator(seed=42)
    session_id2 = generator2.generate_lineup(target_date=date(2025, 11, 13))

    # Get video selections
    with get_db() as db:
        session1 = db.query(Session).filter(Session.id == session_id1).first()
        session2 = db.query(Session).filter(Session.id == session_id2).first()

        videos1 = [ph.video_id for ph in session1.play_history]
        videos2 = [ph.video_id for ph in session2.play_history]

        # Should select same videos in same order
        assert videos1 == videos2
