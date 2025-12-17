"""Global state management for Alma TV Web App."""

import threading
from enum import Enum
from typing import Optional
from datetime import datetime

from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class AppStatus(Enum):
    """Application status."""
    IDLE = "idle"          # Showing Clock
    PLAYING = "playing"    # Showing Video Player
    FEEDBACK = "feedback"  # Showing Feedback UI
    COUNTDOWN = "countdown"  # Showing Countdown Timer


class AppState:
    """Singleton state manager."""
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AppState, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.status = AppStatus.IDLE
        self.current_session_id: Optional[int] = None
        self.current_playlist = []  # List of video paths/IDs
        self.current_video_index = 0
        self.last_activity = datetime.now()
        
        # Countdown state
        self.countdown_target_time: Optional[datetime] = None
        self.countdown_session_id: Optional[int] = None
        
        logger.info("AppState initialized")

    def set_status(self, status: AppStatus):
        """Update application status."""
        logger.info(f"State transition: {self.status.value} -> {status.value}")
        self.status = status
        self.last_activity = datetime.now()

    def start_session(self, session_id: int, playlist: list):
        """Start a playback session."""
        logger.info(f"Starting session {session_id} with {len(playlist)} videos")
        for i, item in enumerate(playlist):
            logger.debug(f"  [{i}] {item.get('title')} ({item.get('path')})")
            
        self.current_session_id = session_id
        self.current_playlist = playlist
        self.current_video_index = 0
        self.set_status(AppStatus.PLAYING)

    def next_video(self) -> Optional[dict]:
        """Get next video in playlist or finish session."""
        logger.info(f"next_video called. Index: {self.current_video_index}, Playlist length: {len(self.current_playlist)}")
        
        if self.current_video_index < len(self.current_playlist):
            video = self.current_playlist[self.current_video_index]
            logger.info(f"Playing video {self.current_video_index}: {video.get('title')}")
            self.current_video_index += 1
            return video
        
        # Playlist finished
        logger.info("Playlist finished, switching to FEEDBACK")
        self.set_status(AppStatus.FEEDBACK)
        return None

    def reset(self):
        """Reset to IDLE state."""
        self.current_session_id = None
        self.current_playlist = []
        self.current_video_index = 0
        self.set_status(AppStatus.IDLE)


# Global instance
state = AppState()
