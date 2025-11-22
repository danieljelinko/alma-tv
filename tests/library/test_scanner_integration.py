"""Integration tests for Scanner database operations."""

from pathlib import Path

import pytest

from alma_tv.database import Video
from alma_tv.library.scanner import Scanner


def test_upsert_video_insert(db_session):
    """Test inserting a new video."""
    scanner = Scanner()
    metadata = {
        "path": "/tmp/test.mp4",
        "series": "Bluey",
        "season": 1,
        "episode_code": "S01E01",
        "title": "Magic Xylophone",
        "duration_seconds": 420,
        "file_hash": "hash123",
        "disabled": False,
    }

    result = scanner.upsert_video(metadata)
    assert result is True

    # Verify in DB
    video = db_session.query(Video).filter_by(path="/tmp/test.mp4").first()
    assert video is not None
    assert video.series == "Bluey"
    assert video.file_hash == "hash123"


def test_upsert_video_update(db_session):
    """Test updating an existing video."""
    scanner = Scanner()
    
    # Initial insert
    metadata = {
        "path": "/tmp/test.mp4",
        "series": "Bluey",
        "season": 1,
        "episode_code": "S01E01",
        "title": "Magic Xylophone",
        "duration_seconds": 420,
        "file_hash": "hash123",
        "disabled": False,
    }
    scanner.upsert_video(metadata)

    # Update with new hash and duration
    metadata["file_hash"] = "hash456"
    metadata["duration_seconds"] = 430
    
    result = scanner.upsert_video(metadata)
    assert result is True

    # Verify update
    video = db_session.query(Video).filter_by(path="/tmp/test.mp4").first()
    assert video.file_hash == "hash456"
    assert video.duration_seconds == 430


def test_upsert_video_no_change(db_session):
    """Test upserting unchanged video."""
    scanner = Scanner()
    
    metadata = {
        "path": "/tmp/test.mp4",
        "series": "Bluey",
        "season": 1,
        "episode_code": "S01E01",
        "title": "Magic Xylophone",
        "duration_seconds": 420,
        "file_hash": "hash123",
        "disabled": False,
    }
    scanner.upsert_video(metadata)

    # Try upserting same data
    result = scanner.upsert_video(metadata)
    assert result is False
