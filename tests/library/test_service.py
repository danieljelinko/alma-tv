"""Tests for library service API."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from alma_tv.database import Feedback, PlayHistory, Session, Video, get_db, init_db
from alma_tv.database.models import Rating, SessionStatus
from alma_tv.library.service import LibraryService


@pytest.fixture
def sample_videos(db_session):
    """Create sample videos in database."""
    videos = [
        Video(
            series="Bluey",
            season=1,
            episode_code="S01E01",
            title="Magic Xylophone",
            path="/media/bluey_s01e01.mp4",
            duration_seconds=420,
            disabled=False,
        ),
        Video(
            series="Bluey",
            season=1,
            episode_code="S01E02",
            title="Hospital",
            path="/media/bluey_s01e02.mp4",
            duration_seconds=430,
            disabled=False,
        ),
        Video(
            series="Bluey",
            season=2,
            episode_code="S02E01",
            title="Dance Mode",
            path="/media/bluey_s02e01.mp4",
            duration_seconds=440,
            disabled=False,
        ),
        Video(
            series="Paw Patrol",
            season=1,
            episode_code="S01E01",
            title="Pups Save the Day",
            path="/media/pawpatrol_s01e01.mp4",
            duration_seconds=600,
            disabled=False,
        ),
        Video(
            series="Paw Patrol",
            season=1,
            episode_code="S01E02",
            title="Pups Fall Festival",
            path="/media/pawpatrol_s01e02.mp4",
            duration_seconds=610,
            disabled=True,  # Disabled video
        ),
    ]

    for video in videos:
        db_session.add(video)
    db_session.commit()

    return videos


def test_list_series(sample_videos):
    """Test listing all series."""
    service = LibraryService()
    series_list = service.list_series()

    assert len(series_list) == 2  # Only non-disabled
    assert any(s["series"] == "Bluey" for s in series_list)
    assert any(s["series"] == "Paw Patrol" for s in series_list)

    # Check Bluey stats
    bluey = next(s for s in series_list if s["series"] == "Bluey")
    assert bluey["episode_count"] == 3
    assert bluey["total_duration_seconds"] == 1290  # 420 + 430 + 440


def test_list_episodes_all(sample_videos):
    """Test listing all episodes."""
    service = LibraryService()
    episodes = service.list_episodes()

    # Should return 4 enabled videos
    assert len(episodes) == 4
    assert all(not ep.disabled for ep in episodes)


def test_list_episodes_by_series(sample_videos):
    """Test listing episodes filtered by series."""
    service = LibraryService()
    episodes = service.list_episodes(series="Bluey")

    assert len(episodes) == 3
    assert all(ep.series == "Bluey" for ep in episodes)


def test_list_episodes_by_season(sample_videos):
    """Test listing episodes filtered by season."""
    service = LibraryService()
    episodes = service.list_episodes(series="Bluey", season=1)

    assert len(episodes) == 2
    assert all(ep.series == "Bluey" and ep.season == 1 for ep in episodes)


def test_list_episodes_include_disabled(sample_videos):
    """Test listing episodes including disabled."""
    service = LibraryService()
    episodes = service.list_episodes(disabled=True)

    # Should return all 5 videos
    assert len(episodes) == 5


def test_get_video_by_id(sample_videos):
    """Test getting video by ID."""
    service = LibraryService()
    video = service.get_video_by_id(1)

    assert video is not None
    assert video.series == "Bluey"


def test_get_video_by_path(sample_videos):
    """Test getting video by path."""
    service = LibraryService()
    video = service.get_video_by_path("/media/bluey_s01e01.mp4")

    assert video is not None
    assert video.series == "Bluey"
    assert video.episode_code == "S01E01"


def test_random_episode(sample_videos):
    """Test random episode selection."""
    service = LibraryService()
    episode = service.random_episode()

    assert episode is not None
    assert not episode.disabled


def test_random_episode_by_series(sample_videos):
    """Test random episode selection for specific series."""
    service = LibraryService()
    episode = service.random_episode(series="Bluey")

    assert episode is not None
    assert episode.series == "Bluey"


def test_random_episode_duration_filter(sample_videos):
    """Test random episode with duration filters."""
    service = LibraryService()

    # Only short episodes (< 500 seconds)
    episode = service.random_episode(min_duration=400, max_duration=500)

    assert episode is not None
    assert 400 <= episode.duration_seconds <= 500


def test_random_episode_exclude_ids(sample_videos):
    """Test random episode excluding specific IDs."""
    service = LibraryService()

    # Exclude Bluey episodes (IDs 1, 2, 3)
    episode = service.random_episode(exclude_video_ids=[1, 2, 3])

    assert episode is not None
    assert episode.id == 4  # Should be Paw Patrol S01E01


def test_random_episode_with_cooldown(sample_videos):
    """Test random episode respects cooldown period."""
    service = LibraryService()

    # Create a session and play history for video 1
    with get_db() as db:
        session = Session(
            show_date=datetime.now(timezone.utc),
            status=SessionStatus.COMPLETED,
        )
        db.add(session)
        db.flush()

        play = PlayHistory(
            session_id=session.id,
            video_id=1,
            slot_order=1,
            started_at=datetime.now(timezone.utc) - timedelta(days=7),
            ended_at=datetime.now(timezone.utc) - timedelta(days=7),
            completed=True,
        )
        db.add(play)

    # Video 1 should be excluded (within 14-day cooldown)
    episode = service.random_episode(series="Bluey", cooldown_days=14)

    # Should get video 2 or 3, but not 1
    assert episode is not None
    assert episode.id != 1


def test_random_episode_never_again(sample_videos):
    """Test random episode excludes 'never again' videos."""
    service = LibraryService()

    # Mark video 1 as "never again"
    with get_db() as db:
        session = Session(show_date=datetime.now(timezone.utc), status=SessionStatus.COMPLETED)
        db.add(session)
        db.flush()

        play = PlayHistory(
            session_id=session.id,
            video_id=1,
            slot_order=1,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            completed=True,
        )
        db.add(play)
        db.flush()

        feedback = Feedback(play_history_id=play.id, rating=Rating.NEVER)
        db.add(feedback)

    # Video 1 should be excluded
    episode = service.random_episode(series="Bluey")

    assert episode is not None
    assert episode.id != 1


def test_random_episodes_multiple(sample_videos):
    """Test selecting multiple random episodes."""
    service = LibraryService()
    episodes = service.random_episodes(count=3)

    assert len(episodes) <= 3
    assert len(set(ep.id for ep in episodes)) == len(episodes)  # All unique


def test_random_episodes_diversity(sample_videos):
    """Test random episodes ensures diversity."""
    service = LibraryService()
    episodes = service.random_episodes(count=2, ensure_diversity=True)

    # With diversity, should try to select from different series/seasons
    assert len(episodes) <= 2


def test_get_series_stats(sample_videos):
    """Test getting series statistics."""
    service = LibraryService()
    stats = service.get_series_stats("Bluey")

    assert stats["series"] == "Bluey"
    assert stats["episode_count"] == 3
    assert stats["season_count"] == 2
    assert stats["seasons"] == [1, 2]
    assert stats["total_duration_seconds"] == 1290


def test_disable_video(sample_videos):
    """Test disabling a video."""
    service = LibraryService()
    result = service.disable_video(1)

    assert result is True

    video = service.get_video_by_id(1)
    assert video.disabled is True


def test_enable_video(sample_videos):
    """Test enabling a video."""
    service = LibraryService()

    # Video 5 is disabled
    result = service.enable_video(5)
    assert result is True

    video = service.get_video_by_id(5)
    assert video.disabled is False


def test_cache_clearing(sample_videos):
    """Test cache can be cleared."""
    service = LibraryService()

    # Populate cache
    stats1 = service.get_series_stats("Bluey")
    assert stats1 is not None

    # Clear cache
    service.clear_cache()

    # Should still work after clearing
    stats2 = service.get_series_stats("Bluey")
    assert stats2 is not None

def test_get_recently_played(sample_videos):
    """Test getting recently played videos."""
    service = LibraryService()

    with get_db() as db:
        # Create a session and play history
        session = Session(
            show_date=datetime.now(timezone.utc),
            status=SessionStatus.COMPLETED,
        )
        db.add(session)
        db.flush()

        # Play video 1 (recent)
        play1 = PlayHistory(
            session_id=session.id,
            video_id=1,
            slot_order=1,
            started_at=datetime.now(timezone.utc) - timedelta(days=2),
            ended_at=datetime.now(timezone.utc) - timedelta(days=2),
            completed=True,
        )
        db.add(play1)

        # Play video 2 (old)
        play2 = PlayHistory(
            session_id=session.id,
            video_id=2,
            slot_order=2,
            started_at=datetime.now(timezone.utc) - timedelta(days=20),
            ended_at=datetime.now(timezone.utc) - timedelta(days=20),
            completed=True,
        )
        db.add(play2)

    # Should only get video 1 (within 14 days default)
    recent = service.get_recently_played(days=14)
    assert len(recent) == 1
    assert recent[0].id == 1

    # Should get both if we look back 30 days
    recent_all = service.get_recently_played(days=30)
    assert len(recent_all) == 2
