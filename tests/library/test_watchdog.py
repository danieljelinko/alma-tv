"""Tests for Watchdog event handler."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from watchdog.events import FileCreatedEvent, FileModifiedEvent

from alma_tv.library.scanner import MediaLibraryEventHandler, Scanner


@pytest.fixture
def mock_scanner():
    """Mock scanner instance."""
    return MagicMock(spec=Scanner)


def test_on_created_file(mock_scanner):
    """Test handling file creation."""
    handler = MediaLibraryEventHandler(mock_scanner)
    event = FileCreatedEvent("/tmp/test.mp4")
    
    # Mock scan_file to return metadata
    mock_scanner.scan_file.return_value = {"path": "/tmp/test.mp4"}
    
    handler.on_created(event)
    
    mock_scanner.scan_file.assert_called_once_with(Path("/tmp/test.mp4"))
    mock_scanner.upsert_video.assert_called_once()


def test_on_created_directory(mock_scanner):
    """Test ignoring directory creation."""
    handler = MediaLibraryEventHandler(mock_scanner)
    event = FileCreatedEvent("/tmp/new_dir")
    event.is_directory = True
    
    handler.on_created(event)
    
    mock_scanner.scan_file.assert_not_called()


def test_on_created_unsupported_extension(mock_scanner):
    """Test ignoring unsupported extensions."""
    handler = MediaLibraryEventHandler(mock_scanner)
    event = FileCreatedEvent("/tmp/test.txt")
    
    handler.on_created(event)
    
    mock_scanner.scan_file.assert_not_called()


def test_on_modified_file(mock_scanner):
    """Test handling file modification."""
    handler = MediaLibraryEventHandler(mock_scanner)
    event = FileModifiedEvent("/tmp/test.mp4")
    
    mock_scanner.scan_file.return_value = {"path": "/tmp/test.mp4"}
    
    handler.on_modified(event)
    
    mock_scanner.scan_file.assert_called_once_with(Path("/tmp/test.mp4"))
    mock_scanner.upsert_video.assert_called_once()
