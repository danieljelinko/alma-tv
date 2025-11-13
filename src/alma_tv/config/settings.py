"""Settings and configuration management using Pydantic."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Alma TV configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="ALMA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Media Library
    media_root: Path = Field(
        default=Path("/mnt/media/cartoons"),
        description="Root directory for media files",
    )
    intro_path: Path = Field(
        default=Path("/mnt/media/intros/alma_intro.mp4"),
        description="Path to intro video",
    )
    outro_path: Path = Field(
        default=Path("/mnt/media/outros/alma_outro.mp4"),
        description="Path to outro video",
    )

    # Scheduling
    start_time: str = Field(
        default="19:00",
        description="Daily start time in HH:MM format",
    )
    target_duration_minutes: int = Field(
        default=30,
        ge=15,
        le=60,
        description="Target duration for viewing block in minutes",
    )
    repeat_cooldown_days: int = Field(
        default=14,
        ge=1,
        description="Minimum days before repeating an episode",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///var/lib/alma/alma.db",
        description="Database connection URL",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_file: Path = Field(
        default=Path("/var/log/alma/alma.log"),
        description="Log file path",
    )

    # Playback
    player: Literal["vlc", "omxplayer"] = Field(
        default="vlc",
        description="Media player to use",
    )
    display: str = Field(
        default=":0",
        description="X display for video output",
    )

    # Clock Display
    clock_update_interval: int = Field(
        default=60,
        ge=1,
        description="Clock update interval in seconds",
    )
    clock_svg_path: Path = Field(
        default=Path("/var/cache/alma/clock.svg"),
        description="Path to save generated clock SVG",
    )

    # Feedback UI
    feedback_timeout: int = Field(
        default=120,
        ge=30,
        description="Feedback UI timeout in seconds",
    )
    feedback_port: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        description="Port for feedback web UI",
    )

    # Development
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    dry_run: bool = Field(
        default=False,
        description="Dry run mode (no actual playback)",
    )

    @field_validator("start_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time is in HH:MM format."""
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time values")
        except ValueError as e:
            raise ValueError(f"Invalid time format: {e}") from e
        return v

    @field_validator("media_root", "intro_path", "outro_path", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        """Expand environment variables and user paths."""
        if isinstance(v, str):
            v = os.path.expandvars(os.path.expanduser(v))
        return Path(v)

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        # Create log directory
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create clock cache directory
        self.clock_svg_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database directory
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    return settings
