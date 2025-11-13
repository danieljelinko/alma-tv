"""Tests for configuration settings."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from alma_tv.config.settings import Settings


def test_default_settings() -> None:
    """Test that default settings can be instantiated."""
    settings = Settings()
    assert settings.media_root == Path("/mnt/media/cartoons")
    assert settings.start_time == "19:00"
    assert settings.target_duration_minutes == 30
    assert settings.repeat_cooldown_days == 14
    assert settings.log_level == "INFO"
    assert settings.player == "vlc"
    assert settings.debug is False


def test_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variables override defaults."""
    monkeypatch.setenv("ALMA_MEDIA_ROOT", "/custom/media/path")
    monkeypatch.setenv("ALMA_START_TIME", "18:30")
    monkeypatch.setenv("ALMA_TARGET_DURATION_MINUTES", "45")
    monkeypatch.setenv("ALMA_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ALMA_DEBUG", "true")

    settings = Settings()
    assert settings.media_root == Path("/custom/media/path")
    assert settings.start_time == "18:30"
    assert settings.target_duration_minutes == 45
    assert settings.log_level == "DEBUG"
    assert settings.debug is True


def test_time_validation_valid() -> None:
    """Test valid time formats."""
    settings = Settings(start_time="00:00")
    assert settings.start_time == "00:00"

    settings = Settings(start_time="23:59")
    assert settings.start_time == "23:59"

    settings = Settings(start_time="12:30")
    assert settings.start_time == "12:30"


def test_time_validation_invalid_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test invalid time formats raise validation errors."""
    with pytest.raises(ValidationError, match="Time must be in HH:MM format"):
        Settings(start_time="19:00:00")

    with pytest.raises(ValidationError, match="Time must be in HH:MM format"):
        Settings(start_time="19")

    with pytest.raises(ValidationError, match="Time must be in HH:MM format"):
        Settings(start_time="not-a-time")


def test_time_validation_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test invalid time values raise validation errors."""
    with pytest.raises(ValidationError, match="Invalid time"):
        Settings(start_time="25:00")

    with pytest.raises(ValidationError, match="Invalid time"):
        Settings(start_time="12:60")

    with pytest.raises(ValidationError, match="Invalid time"):
        Settings(start_time="-1:00")


def test_duration_validation() -> None:
    """Test duration validation constraints."""
    # Valid durations
    settings = Settings(target_duration_minutes=15)
    assert settings.target_duration_minutes == 15

    settings = Settings(target_duration_minutes=60)
    assert settings.target_duration_minutes == 60

    # Invalid durations
    with pytest.raises(ValidationError):
        Settings(target_duration_minutes=10)  # Too short

    with pytest.raises(ValidationError):
        Settings(target_duration_minutes=61)  # Too long


def test_cooldown_validation() -> None:
    """Test cooldown validation constraints."""
    settings = Settings(repeat_cooldown_days=1)
    assert settings.repeat_cooldown_days == 1

    settings = Settings(repeat_cooldown_days=30)
    assert settings.repeat_cooldown_days == 30

    with pytest.raises(ValidationError):
        Settings(repeat_cooldown_days=0)


def test_feedback_port_validation() -> None:
    """Test feedback port validation."""
    settings = Settings(feedback_port=8080)
    assert settings.feedback_port == 8080

    settings = Settings(feedback_port=1024)
    assert settings.feedback_port == 1024

    settings = Settings(feedback_port=65535)
    assert settings.feedback_port == 65535

    with pytest.raises(ValidationError):
        Settings(feedback_port=1023)  # Too low

    with pytest.raises(ValidationError):
        Settings(feedback_port=65536)  # Too high


def test_path_expansion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that paths are expanded correctly."""
    home_dir = Path.home()

    settings = Settings(media_root="~/media")
    assert settings.media_root == home_dir / "media"

    # Test environment variable expansion
    monkeypatch.setenv("MEDIA_BASE", "/mnt/storage")
    settings = Settings(media_root="$MEDIA_BASE/cartoons")
    assert settings.media_root == Path("/mnt/storage/cartoons")


def test_raspberry_pi_paths() -> None:
    """Test Raspberry Pi specific paths."""
    settings = Settings(
        media_root="/mnt/media/cartoons",
        log_file="/var/log/alma/alma.log",
        database_url="sqlite:///var/lib/alma/alma.db",
    )

    assert settings.media_root == Path("/mnt/media/cartoons")
    assert settings.log_file == Path("/var/log/alma/alma.log")
    assert "sqlite:///var/lib/alma/alma.db" in settings.database_url


def test_ensure_directories(tmp_path: Path) -> None:
    """Test that ensure_directories creates required directories."""
    log_file = tmp_path / "logs" / "test.log"
    clock_svg = tmp_path / "cache" / "clock.svg"
    db_url = f"sqlite:///{tmp_path / 'db' / 'test.db'}"

    settings = Settings(
        log_file=log_file,
        clock_svg_path=clock_svg,
        database_url=db_url,
    )

    settings.ensure_directories()

    assert log_file.parent.exists()
    assert clock_svg.parent.exists()
    assert (tmp_path / "db").exists()


def test_player_options() -> None:
    """Test media player options."""
    settings = Settings(player="vlc")
    assert settings.player == "vlc"

    settings = Settings(player="omxplayer")
    assert settings.player == "omxplayer"

    # Invalid player should fail validation
    with pytest.raises(ValidationError):
        Settings(player="invalid_player")


def test_log_level_options() -> None:
    """Test log level options."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        settings = Settings(log_level=level)
        assert settings.log_level == level

    with pytest.raises(ValidationError):
        Settings(log_level="INVALID")
