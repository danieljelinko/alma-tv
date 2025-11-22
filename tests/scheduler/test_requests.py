"""Tests for end-to-end request handling."""

from datetime import date
from unittest.mock import patch

import pytest

from alma_tv.database import Session, Video
from alma_tv.scheduler.lineup import LineupGenerator
from alma_tv.scheduler.parser import RequestParser


@pytest.fixture
def mock_settings(test_settings):
    """Mock settings with keyword map."""
    test_settings.keyword_map = {
        "blueie": "Bluey",
        "throw throw": "Throw_Throw_Burrito",
    }
    return test_settings


@pytest.fixture
def sample_videos(db_session):
    """Create sample videos."""
    videos = []
    # 5 Bluey episodes
    for i in range(1, 6):
        videos.append(Video(series="Bluey", season=1, episode_code=f"S01E{i:02d}", path=f"/tmp/b{i}.mp4", duration_seconds=420))
    
    # 5 Throw Throw episodes
    for i in range(1, 6):
        videos.append(Video(series="Throw_Throw_Burrito", season=1, episode_code=f"S01E{i:02d}", path=f"/tmp/t{i}.mp4", duration_seconds=420))
        
    # 5 Peppa Pig episodes (filler)
    for i in range(1, 6):
        videos.append(Video(series="Peppa Pig", season=1, episode_code=f"S01E{i:02d}", path=f"/tmp/p{i}.mp4", duration_seconds=300))

    for v in videos:
        db_session.add(v)
    db_session.commit()
    return videos


@patch("alma_tv.scheduler.lineup.LineupGenerator._get_file_duration")
def test_request_flow(mock_duration, mock_settings, sample_videos, db_session):
    """Test parsing a request and generating a lineup."""
    mock_duration.return_value = 10
    
    # 1. Parse request
    parser = RequestParser()
    input_text = "one blueie and two throw throw"
    offset, requests = parser.parse(input_text)
    
    assert offset == 0
    assert len(requests) == 2
    assert requests[0] == {"series": "Bluey", "count": 1}
    assert requests[1] == {"series": "Throw_Throw_Burrito", "count": 2}
    
    # 2. Generate lineup
    generator = LineupGenerator(seed=42)
    session_id = generator.generate_lineup(
        target_date=date(2025, 11, 14),
        request_payload={"requests": requests}
    )
    
    assert session_id is not None
    
    # 3. Verify lineup content
    session = db_session.query(Session).filter(Session.id == session_id).first()
    series_counts = {}
    for ph in session.play_history:
        series = ph.video.series
        series_counts[series] = series_counts.get(series, 0) + 1
        
    # Should have exactly 1 Bluey and 2 Throw Throw
    assert series_counts.get("Bluey") == 1
    assert series_counts.get("Throw_Throw_Burrito") == 2
    
    # Should have filler (Peppa Pig) to reach min episodes (3) or duration
    # Total requested: 3 episodes. Min episodes default is 3.
    # Duration: 3 * 420 = 1260s. Target 30m = 1800s.
    # Should fill with Peppa Pig.
    
    total_episodes = len(session.play_history)
    assert total_episodes >= 3
    
    # Check if filler was added
    if total_episodes > 3:
        assert "Peppa Pig" in series_counts
