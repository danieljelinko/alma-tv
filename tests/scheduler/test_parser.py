"""Tests for request parser."""

from unittest.mock import MagicMock, patch

import pytest

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
def mock_db_series(db_session):
    """Mock database series."""
    from alma_tv.database import Video
    
    videos = [
        Video(series="Bluey", season=1, episode_code="S01E01", path="/tmp/1.mp4", duration_seconds=60),
        Video(series="Throw_Throw_Burrito", season=1, episode_code="S01E01", path="/tmp/2.mp4", duration_seconds=60),
        Video(series="Peppa Pig", season=1, episode_code="S01E01", path="/tmp/3.mp4", duration_seconds=60),
    ]
    for v in videos:
        db_session.add(v)
    db_session.commit()
    return videos


def test_parse_simple_request(mock_settings, mock_db_series):
    """Test parsing a simple request."""
    parser = RequestParser()
    offset, requests = parser.parse("one blueie")
    
    assert offset == 0
    assert len(requests) == 1
    assert requests[0]["series"] == "Bluey"
    assert requests[0]["count"] == 1


def test_parse_multiple_requests(mock_settings, mock_db_series):
    """Test parsing multiple requests."""
    parser = RequestParser()
    offset, requests = parser.parse("one blueie and two throw throw")
    
    assert offset == 0
    assert len(requests) == 2
    assert requests[0]["series"] == "Bluey"
    assert requests[0]["count"] == 1
    assert requests[1]["series"] == "Throw_Throw_Burrito"
    assert requests[1]["count"] == 2


def test_parse_fuzzy_match(mock_settings, mock_db_series):
    """Test fuzzy matching."""
    parser = RequestParser()
    # "peppa" should match "Peppa Pig"
    offset, requests = parser.parse("three peppa")
    
    assert offset == 0
    assert len(requests) == 1
    assert requests[0]["series"] == "Peppa Pig"
    assert requests[0]["count"] == 3


def test_parse_unknown_series(mock_settings, mock_db_series):
    """Test parsing unknown series."""
    parser = RequestParser()
    offset, requests = parser.parse("one unknown_show")
    
    assert offset == 0
    assert len(requests) == 0


def test_parse_numeric_count(mock_settings, mock_db_series):
    """Test parsing numeric count."""
    parser = RequestParser()
    offset, requests = parser.parse("2 blueie")
    
    assert offset == 0
    assert len(requests) == 1
    assert requests[0]["series"] == "Bluey"
    assert requests[0]["count"] == 2

def test_parse_date_keywords(mock_settings, mock_db_series):
    """Test parsing date keywords."""
    parser = RequestParser()
    
    offset, requests = parser.parse("tomorrow one blueie")
    assert offset == 1
    assert len(requests) == 1
    
    offset, requests = parser.parse("today one blueie")
    assert offset == 0
    assert len(requests) == 1
