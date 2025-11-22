"""SVG Clock Renderer."""

import math
from datetime import datetime, timedelta
from typing import Tuple

from alma_tv.config import get_settings
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


class ClockRenderer:
    """Renders an analog clock as SVG."""

    def __init__(self, width: int = 800, height: int = 600):
        """
        Initialize renderer.

        Args:
            width: SVG width
            height: SVG height
        """
        self.width = width
        self.height = height
        self.cx = width // 2
        self.cy = height // 2
        self.radius = min(width, height) // 2 - 50
        self.settings = get_settings()

    def render(self, current_time: datetime) -> str:
        """
        Render clock SVG for the given time.

        Args:
            current_time: Current time

        Returns:
            SVG string
        """
        # Calculate target time (today at start_time)
        hour, minute = map(int, self.settings.start_time.split(":"))
        target_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If target is in the past (e.g. it's 20:00), target tomorrow?
        # For now, let's assume we only care about the upcoming slot today.
        # If it's past 19:00, maybe show empty or full?
        
        # Calculate waiting sector
        sector_svg = self._generate_sector(current_time, target_time)

        # Hands
        hour_hand = self._generate_hand(
            (current_time.hour % 12 + current_time.minute / 60) * 30, 
            self.radius * 0.5, 
            8, 
            "#333"
        )
        minute_hand = self._generate_hand(
            current_time.minute * 6, 
            self.radius * 0.8, 
            4, 
            "#666"
        )
        second_hand = self._generate_hand(
            current_time.second * 6, 
            self.radius * 0.9, 
            2, 
            "#d32f2f"
        )

        # Hour markers
        markers = self._generate_markers()

        svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Background -->
    <rect width="100%" height="100%" fill="#f0f0f0" />
    
    <!-- Clock Face -->
    <circle cx="{self.cx}" cy="{self.cy}" r="{self.radius}" fill="white" stroke="#333" stroke-width="4" />
    
    <!-- Waiting Sector -->
    {sector_svg}
    
    <!-- Markers -->
    {markers}
    
    <!-- Hands -->
    {hour_hand}
    {minute_hand}
    {second_hand}
    
    <!-- Center Dot -->
    <circle cx="{self.cx}" cy="{self.cy}" r="8" fill="#333" />
    
    <!-- Digital Time -->
    <text x="{self.cx}" y="{self.height - 20}" font-family="sans-serif" font-size="32" text-anchor="middle" fill="#333">
        {current_time.strftime('%H:%M:%S')}
    </text>
</svg>
"""
        return svg

    def _generate_sector(self, current: datetime, target: datetime) -> str:
        """Generate the colored sector representing remaining time."""
        if current >= target:
            return ""  # No waiting time left

        # Calculate difference in minutes
        diff = target - current
        minutes_left = diff.total_seconds() / 60
        
        # Only show sector if within 60 minutes
        if minutes_left > 60:
            # Maybe show full circle or different color?
            # For simplicity, just show max 60 mins
            start_angle = (current.minute * 6)
            end_angle = start_angle + 360 # Full circle
            # Actually, if > 60 mins, let's just not show the sector or show it differently.
            # Let's stick to the "last hour" visualization for now.
            return ""

        start_angle = (current.minute * 6) - 90 # SVG 0 is 3 o'clock, we want 12 o'clock
        end_angle = (target.minute * 6) - 90
        
        # Handle wrapping around 12
        if end_angle < start_angle:
            end_angle += 360

        # Calculate coordinates
        x1 = self.cx + self.radius * math.cos(math.radians(start_angle))
        y1 = self.cy + self.radius * math.sin(math.radians(start_angle))
        x2 = self.cx + self.radius * math.cos(math.radians(end_angle))
        y2 = self.cy + self.radius * math.sin(math.radians(end_angle))

        large_arc = 1 if (end_angle - start_angle) > 180 else 0

        path = f"M {self.cx} {self.cy} L {x1} {y1} A {self.radius} {self.radius} 0 {large_arc} 1 {x2} {y2} Z"
        
        return f'<path d="{path}" fill="rgba(100, 200, 100, 0.3)" stroke="none" />'

    def _generate_hand(self, angle: float, length: float, width: float, color: str) -> str:
        """Generate a clock hand."""
        angle_rad = math.radians(angle - 90)
        x2 = self.cx + length * math.cos(angle_rad)
        y2 = self.cy + length * math.sin(angle_rad)
        
        return f'<line x1="{self.cx}" y1="{self.cy}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" />'

    def _generate_markers(self) -> str:
        """Generate hour markers."""
        markers = []
        for i in range(12):
            angle = i * 30 - 90
            angle_rad = math.radians(angle)
            
            # Outer point
            x1 = self.cx + self.radius * math.cos(angle_rad)
            y1 = self.cy + self.radius * math.sin(angle_rad)
            
            # Inner point
            x2 = self.cx + (self.radius - 20) * math.cos(angle_rad)
            y2 = self.cy + (self.radius - 20) * math.sin(angle_rad)
            
            markers.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" stroke-width="4" />')
            
            # Numbers
            tx = self.cx + (self.radius - 40) * math.cos(angle_rad)
            ty = self.cy + (self.radius - 40) * math.sin(angle_rad)
            num = i if i != 0 else 12
            # Adjust text position slightly for centering
            ty += 5 
            
            # markers.append(f'<text x="{tx}" y="{ty}" text-anchor="middle" font-family="sans-serif">{num}</text>')
            
        return "\n".join(markers)
