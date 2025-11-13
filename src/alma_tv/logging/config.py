"""Logging configuration utilities."""

import logging
import sys
from pathlib import Path
from typing import Optional


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_console: bool = True,
) -> None:
    """
    Configure logging for Alma TV.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        enable_console: Whether to enable console logging
    """
    # Create logger
    logger = logging.getLogger("alma_tv")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"alma_tv.{name}")
