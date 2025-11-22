"""Media player abstractions."""

import subprocess
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class Player(ABC):
    """Abstract base class for media players."""

    @abstractmethod
    def play(self, file_path: Path, wait: bool = True) -> bool:
        """
        Play a media file.

        Args:
            file_path: Path to media file
            wait: Block until playback completes

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        Stop current playback.

        Returns:
            True if successful
        """
        pass


class VLCPlayer(Player):
    """VLC media player implementation."""

    def __init__(self, display: str = ":0", fullscreen: bool = True):
        """
        Initialize VLC player.

        Args:
            display: X display to use
            fullscreen: Play in fullscreen mode
        """
        self.display = display
        self.fullscreen = fullscreen
        self.process: Optional[subprocess.Popen] = None

    def play(self, file_path: Path, wait: bool = True) -> bool:
        """
        Play a media file with VLC.

        Args:
            file_path: Path to media file
            wait: Block until playback completes

        Returns:
            True if successful
        """
        if not file_path.exists():
            logger.error(f"Media file not found: {file_path}")
            return False

        args = ["vlc", "--play-and-exit", "--no-video-title-show"]

        if self.fullscreen:
            args.append("--fullscreen")

        args.append(str(file_path))

        try:
            logger.info(f"Starting VLC playback: {file_path}")
            env = os.environ.copy()
            env["DISPLAY"] = self.display

            if wait:
                result = subprocess.run(
                    args,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                success = result.returncode == 0
                if not success:
                    logger.error(f"VLC playback failed: {result.stderr}")
                return success
            else:
                self.process = subprocess.Popen(
                    args,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                return True

        except Exception as e:
            logger.error(f"VLC playback error: {e}")
            return False

    def stop(self) -> bool:
        """Stop VLC playback."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("VLC playback stopped")
                return True
            except Exception as e:
                logger.error(f"Failed to stop VLC: {e}")
                return False
        return True


class OMXPlayer(Player):
    """OMXPlayer implementation (for older Raspberry Pi models)."""

    def __init__(self, audio_output: str = "both"):
        """
        Initialize OMXPlayer.

        Args:
            audio_output: Audio output (hdmi, local, both)
        """
        self.audio_output = audio_output
        self.process: Optional[subprocess.Popen] = None

    def play(self, file_path: Path, wait: bool = True) -> bool:
        """Play media file with OMXPlayer."""
        if not file_path.exists():
            logger.error(f"Media file not found: {file_path}")
            return False

        args = ["omxplayer", "-o", self.audio_output, "--blank", str(file_path)]

        try:
            logger.info(f"Starting OMXPlayer playback: {file_path}")

            if wait:
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                )
                success = result.returncode == 0
                if not success:
                    logger.error(f"OMXPlayer playback failed: {result.stderr}")
                return success
            else:
                self.process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                return True

        except Exception as e:
            logger.error(f"OMXPlayer error: {e}")
            return False

    def stop(self) -> bool:
        """Stop OMXPlayer playback."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("OMXPlayer stopped")
                return True
            except Exception as e:
                logger.error(f"Failed to stop OMXPlayer: {e}")
                return False
        return True


def get_player(player_type: str = "vlc", **kwargs) -> Player:
    """
    Factory function to get a player instance.

    Args:
        player_type: Type of player (vlc, omxplayer)
        **kwargs: Player-specific arguments

    Returns:
        Player instance
    """
    if player_type.lower() == "vlc":
        return VLCPlayer(**kwargs)
    elif player_type.lower() == "omxplayer":
        return OMXPlayer(**kwargs)
    else:
        raise ValueError(f"Unknown player type: {player_type}")
