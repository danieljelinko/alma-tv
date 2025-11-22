"""Clock Service daemon."""

import time
from datetime import datetime
from pathlib import Path

from alma_tv.clock.renderer import ClockRenderer
from alma_tv.config import get_settings
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class ClockService:
    """Service to generate clock SVG updates."""

    def __init__(self):
        """Initialize clock service."""
        self.settings = get_settings()
        self.renderer = ClockRenderer()
        # Use configured path or default to /tmp
        self.output_path = Path(getattr(self.settings, "clock_output_path", "/tmp/alma_clock.svg"))

    def run_daemon(self) -> None:
        """Run the clock service loop."""
        logger.info(f"Clock service started, outputting to {self.output_path}")
        
        while True:
            try:
                self.update_clock()
                
                # Sleep until next second (or minute?)
                # For smooth second hand, we'd need JS or frequent updates.
                # But for static SVG, maybe every second is too much I/O?
                # Let's do every second for now to see the second hand move.
                # If performance is an issue, we can switch to JS-based clock.
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Clock service stopped")
                break
            except Exception as e:
                logger.error(f"Error in clock service: {e}")
                time.sleep(5)

    def update_clock(self) -> None:
        """Generate and save updated clock SVG."""
        now = datetime.now()
        svg_content = self.renderer.render(now)
        
        # Atomic write
        temp_path = self.output_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            f.write(svg_content)
        
        temp_path.replace(self.output_path)
