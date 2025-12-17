"""Settings and configuration management using Pydantic."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from typing import Any, Dict, Tuple, Type

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A simple settings source class that loads variables from a YAML file
    at the project's root.
    """

    def get_field_value(
        self, field: Field, field_name: str
    ) -> Tuple[Any, str, bool]:
        encoding = self.config.get("env_file_encoding")
        file_content_json = yaml.safe_load(
            Path("config.yaml").read_text(encoding)
        ) if Path("config.yaml").exists() else {}
        
        field_value = file_content_json.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Field, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        encoding = self.config.get("env_file_encoding")
        
        if not Path("config.yaml").exists():
            return d
            
        try:
            file_content = yaml.safe_load(Path("config.yaml").read_text(encoding))
            if file_content:
                d.update(file_content)
        except Exception as e:
            # Log warning or ignore if config file is malformed?
            # For now, let's just print/log and continue
            print(f"Warning: Failed to load config.yaml: {e}")
            
        return d


class Settings(BaseSettings):
    """Alma TV configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="ALMA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
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
    nr_shows_per_night: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default number of shows per night (also max for requests)",
    )
    repeat_cooldown_days: int = Field(
        default=14,
        ge=1,
        description="Minimum days before repeating an episode",
    )

    # Database
    database_url: str = Field(
        default="sqlite:////home/helinko/Work/guess-class/alma-tv/data/alma.db",
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
        default=30,
        ge=5,
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
    keyword_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of keywords to series names",
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

    @field_validator("database_url", mode="before")
    @classmethod
    def expand_db_url(cls, v: str) -> str:
        """Expand environment variables in database URL."""
        if v.startswith("sqlite:///"):
            path_part = v.replace("sqlite:///", "")
            expanded_path = os.path.expandvars(os.path.expanduser(path_part))
            # If it's a relative path, make it absolute relative to CWD (or project root if we could determine it)
            # For now, just expanding ~ and env vars is a big help
            return f"sqlite:///{expanded_path}"
        return v

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
