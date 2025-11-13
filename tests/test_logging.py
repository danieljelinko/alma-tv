"""Tests for logging configuration."""

import logging
from pathlib import Path

import pytest

from alma_tv.logging.config import configure_logging, get_logger


def test_configure_logging_defaults() -> None:
    """Test logging configuration with defaults."""
    configure_logging()
    logger = logging.getLogger("alma_tv")
    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0


def test_configure_logging_debug_level() -> None:
    """Test logging configuration with DEBUG level."""
    configure_logging(log_level="DEBUG")
    logger = logging.getLogger("alma_tv")
    assert logger.level == logging.DEBUG


def test_configure_logging_with_file(tmp_path: Path) -> None:
    """Test logging configuration with file output."""
    log_file = tmp_path / "test.log"
    configure_logging(log_level="INFO", log_file=log_file)

    logger = logging.getLogger("alma_tv")
    logger.info("Test message")

    assert log_file.exists()
    content = log_file.read_text()
    assert "Test message" in content


def test_configure_logging_no_console(tmp_path: Path) -> None:
    """Test logging configuration without console output."""
    log_file = tmp_path / "test.log"
    configure_logging(log_level="INFO", log_file=log_file, enable_console=False)

    logger = logging.getLogger("alma_tv")
    # Should only have file handler, not console handler
    handler_types = [type(h).__name__ for h in logger.handlers]
    assert "FileHandler" in handler_types
    assert "StreamHandler" not in handler_types


def test_get_logger() -> None:
    """Test get_logger function."""
    configure_logging()
    logger = get_logger("test_module")
    assert logger.name == "alma_tv.test_module"
    assert isinstance(logger, logging.Logger)


def test_logging_format(tmp_path: Path) -> None:
    """Test that log messages have correct format."""
    log_file = tmp_path / "test.log"
    configure_logging(log_level="INFO", log_file=log_file, enable_console=False)

    logger = get_logger("test")
    logger.info("Test message")

    content = log_file.read_text()
    # Should contain timestamp, logger name, level, and message
    assert "alma_tv.test" in content
    assert "INFO" in content
    assert "Test message" in content
    # Check for timestamp pattern (YYYY-MM-DD HH:MM:SS)
    assert "|" in content  # Our format uses pipes as separators
