"""SVG analog clock renderer with program highlighting."""

import math
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import svgwrite

from alma_tv.config import get_settings
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class ClockRenderer:
    """
    Renders SVG analog clock with next program highlight.

    Features:
    - Hour and minute hands
    - Colored arc showing time until next program
    - Simple text label for next program
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 800,
        clock_radius: int = 300,
    ):
        """
        Initialize clock renderer.

        Args:
            width: SVG width in pixels
            height: SVG height in pixels
            clock_radius: Clock face radius
        """
        self.width = width
        self.height = height
        self.clock_radius = clock_radius
        self.center_x = width // 2
        self.center_y = height // 2

        self.settings = get_settings()

    def render(
        self,
        current_time: Optional[datetime] = None,
        next_program_time: Optional[datetime] = None,
        program_label: str = "Cartoons",
    ) -> svgwrite.Drawing:
        """
        Render clock at specific time.

        Args:
            current_time: Current time (defaults to now)
            next_program_time: Next program start time
            program_label: Label for next program

        Returns:
            SVG drawing
        """
        if current_time is None:
            current_time = datetime.now()

        if next_program_time is None:
            # Default to configured start time
            hour, minute = map(int, self.settings.start_time.split(":"))
            next_program_time = current_time.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

            # If that time has passed today, use tomorrow
            if next_program_time <= current_time:
                next_program_time += timedelta(days=1)

        # Create SVG
        dwg = svgwrite.Drawing(size=(self.width, self.height))

        # Background
        dwg.add(
            dwg.rect(
                (0, 0),
                (self.width, self.height),
                fill="#1a1a2e",
            )
        )

        # Draw clock face
        self._draw_clock_face(dwg)

        # Draw program arc
        self._draw_program_arc(dwg, current_time, next_program_time)

        # Draw hour markers
        self._draw_hour_markers(dwg)

        # Draw hands
        self._draw_hands(dwg, current_time)

        # Draw center dot
        dwg.add(
            dwg.circle(
                center=(self.center_x, self.center_y),
                r=12,
                fill="#ffffff",
            )
        )

        # Draw program label
        self._draw_program_label(dwg, next_program_time, program_label)

        return dwg

    def _draw_clock_face(self, dwg: svgwrite.Drawing) -> None:
        """Draw clock face background."""
        # Outer circle
        dwg.add(
            dwg.circle(
                center=(self.center_x, self.center_y),
                r=self.clock_radius,
                fill="#16213e",
                stroke="#0f3460",
                stroke_width=4,
            )
        )

    def _draw_hour_markers(self, dwg: svgwrite.Drawing) -> None:
        """Draw hour markers (1-12)."""
        for hour in range(12):
            angle = math.radians(hour * 30 - 90)  # Start at 12 o'clock
            outer_x = self.center_x + (self.clock_radius - 20) * math.cos(angle)
            outer_y = self.center_y + (self.clock_radius - 20) * math.sin(angle)
            inner_x = self.center_x + (self.clock_radius - 40) * math.cos(angle)
            inner_y = self.center_y + (self.clock_radius - 40) * math.sin(angle)

            dwg.add(
                dwg.line(
                    start=(inner_x, inner_y),
                    end=(outer_x, outer_y),
                    stroke="#4a5568",
                    stroke_width=3,
                )
            )

    def _draw_program_arc(
        self,
        dwg: svgwrite.Drawing,
        current_time: datetime,
        next_program_time: datetime,
    ) -> None:
        """Draw colored arc highlighting time until next program."""
        # Calculate angles
        current_angle = self._time_to_angle(current_time)
        next_angle = self._time_to_angle(next_program_time)

        # Adjust if next program is tomorrow
        if next_angle < current_angle:
            next_angle += 360

        # Create path for arc
        radius = self.clock_radius + 30
        arc_path = self._create_arc_path(
            self.center_x,
            self.center_y,
            radius,
            current_angle,
            next_angle,
        )

        dwg.add(
            dwg.path(
                d=arc_path,
                fill="none",
                stroke="#e63946",  # Red color for cartoon time
                stroke_width=20,
                opacity=0.8,
            )
        )

    def _draw_hands(self, dwg: svgwrite.Drawing, current_time: datetime) -> None:
        """Draw hour and minute hands."""
        hour = current_time.hour % 12
        minute = current_time.minute

        # Hour hand
        hour_angle = math.radians((hour + minute / 60) * 30 - 90)
        hour_length = self.clock_radius * 0.5
        hour_x = self.center_x + hour_length * math.cos(hour_angle)
        hour_y = self.center_y + hour_length * math.sin(hour_angle)

        dwg.add(
            dwg.line(
                start=(self.center_x, self.center_y),
                end=(hour_x, hour_y),
                stroke="#ffffff",
                stroke_width=8,
                stroke_linecap="round",
            )
        )

        # Minute hand
        minute_angle = math.radians(minute * 6 - 90)
        minute_length = self.clock_radius * 0.75
        minute_x = self.center_x + minute_length * math.cos(minute_angle)
        minute_y = self.center_y + minute_length * math.sin(minute_angle)

        dwg.add(
            dwg.line(
                start=(self.center_x, self.center_y),
                end=(minute_x, minute_y),
                stroke="#ffffff",
                stroke_width=6,
                stroke_linecap="round",
            )
        )

    def _draw_program_label(
        self,
        dwg: svgwrite.Drawing,
        next_program_time: datetime,
        program_label: str,
    ) -> None:
        """Draw label for next program."""
        time_str = next_program_time.strftime("%I:%M %p").lstrip("0")
        text_y = self.center_y + self.clock_radius + 80

        # Program name
        dwg.add(
            dwg.text(
                program_label,
                insert=(self.center_x, text_y),
                text_anchor="middle",
                font_size=36,
                font_family="Arial, sans-serif",
                fill="#e63946",
                font_weight="bold",
            )
        )

        # Time
        dwg.add(
            dwg.text(
                f"at {time_str}",
                insert=(self.center_x, text_y + 40),
                text_anchor="middle",
                font_size=28,
                font_family="Arial, sans-serif",
                fill="#ffffff",
            )
        )

    def _time_to_angle(self, dt: datetime) -> float:
        """
        Convert time to clock angle in degrees.

        Args:
            dt: Datetime

        Returns:
            Angle in degrees (0 = 12 o'clock, clockwise)
        """
        hour = dt.hour % 12
        minute = dt.minute
        total_minutes = hour * 60 + minute
        angle = (total_minutes / 720) * 360  # 720 minutes in 12 hours
        return angle

    def _create_arc_path(
        self,
        cx: float,
        cy: float,
        radius: float,
        start_angle: float,
        end_angle: float,
    ) -> str:
        """
        Create SVG path for an arc.

        Args:
            cx: Center X
            cy: Center Y
            radius: Arc radius
            start_angle: Start angle in degrees
            end_angle: End angle in degrees

        Returns:
            SVG path string
        """
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)

        start_x = cx + radius * math.cos(start_rad)
        start_y = cy + radius * math.sin(start_rad)
        end_x = cx + radius * math.cos(end_rad)
        end_y = cy + radius * math.sin(end_rad)

        large_arc = 1 if (end_angle - start_angle) > 180 else 0

        return f"M {start_x} {start_y} A {radius} {radius} 0 {large_arc} 1 {end_x} {end_y}"

    def save(
        self,
        output_path: Optional[Path] = None,
        current_time: Optional[datetime] = None,
    ) -> Path:
        """
        Render and save clock to file.

        Args:
            output_path: Output file path (defaults to config)
            current_time: Current time

        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = self.settings.clock_svg_path

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Render
        dwg = self.render(current_time=current_time)

        # Save
        dwg.saveas(str(output_path))
        logger.debug(f"Clock saved to {output_path}")

        return output_path

    def run_update_loop(self, interval: Optional[int] = None) -> None:
        """
        Run continuous update loop.

        Args:
            interval: Update interval in seconds (defaults to config)
        """
        if interval is None:
            interval = self.settings.clock_update_interval

        logger.info(f"Starting clock update loop (interval: {interval}s)")

        try:
            while True:
                self.save()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Clock update loop stopped")
