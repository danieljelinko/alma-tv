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
    def render(self, current_time: datetime, target_time: datetime, with_text: bool = True) -> str:
        """
        Render the clock as an SVG string.
        
        Args:
            current_time: The current time to display.
            target_time: The time the show starts.
            with_text: Whether to include text elements (countdown, digital time) in the SVG.
                       Set to False if you want to handle text in HTML/CSS.
        """
        # Calculate time difference
        if current_time >= target_time:
            seconds_until_show = 0
            progress_percent = 1.0
        else:
            total_wait = 4 * 3600  # 4 hour max wait for progress ring
            seconds_until_show = (target_time - current_time).total_seconds()
            progress_percent = max(0, min(1, 1 - (seconds_until_show / total_wait)))

        # Format countdown text
        if seconds_until_show > 60:
            minutes = int(seconds_until_show // 60)
            countdown_text = f"{minutes} MIN TO SHOW"
        elif seconds_until_show > 0:
            countdown_text = f"{int(seconds_until_show)} SECONDS!"
        else:
            countdown_text = "Show time! 🎉"
        
        # Calculate dimensions with strict zoning
        self.cx = self.width / 2
        self.cy = self.height / 2
        
        # If text is disabled, we can use more space for the clock face
        if not with_text:
            # Use 80% of the smallest dimension
            self.radius = min(self.width, self.height) * 0.40
        else:
            # Layout with text zones:
            # Top 15%: Countdown Text
            # Middle 70%: Clock Face
            # Bottom 15%: Digital Time
            max_radius_height = (self.height * 0.70) / 2
            max_radius_width = (self.width * 0.90) / 2
            self.radius = min(max_radius_height, max_radius_width) * 0.90

        # Generate progress ring
        progress_ring = self._generate_progress_ring(progress_percent, seconds_until_show)
        
        # Calculate waiting sector for clock face
        sector_svg = self._generate_sector(current_time, target_time)

        # Hands - Harmonized Colors
        hour_hand = self._generate_hand(
            (current_time.hour % 12 + current_time.minute / 60) * 30, 
            self.radius * 0.5, 
            12, 
            "#D00000"  # Dark Red (matches digital clock)
        )
        minute_hand = self._generate_hand(
            current_time.minute * 6, 
            self.radius * 0.75, 
            8, 
            "#FF0080"  # Hot Pink
        )
        # Second hand removed as per user request

        # Hour markers
        markers = self._generate_markers()

        # Text Elements (Conditional)
        text_elements = ""
        if with_text:
            text_top_y = self.height * 0.10
            text_bottom_y = self.height * 0.90
            text_elements = f"""
    <!-- Countdown Text (Top Zone) -->
    <rect x="{self.cx - 300}" y="{text_top_y - 40}" width="600" height="80" rx="20" fill="rgba(255, 255, 255, 0.8)" />
    <text x="{self.cx}" y="{text_top_y + 15}" font-family="Arial Black, sans-serif" font-size="42" font-weight="bold" text-anchor="middle" fill="#FF1744">
        {countdown_text}
    </text>

    <!-- Digital Time (Bottom Zone) -->
    <rect x="{self.cx - 100}" y="{text_bottom_y - 35}" width="200" height="50" rx="10" fill="rgba(255, 255, 255, 0.6)" />
    <text x="{self.cx}" y="{text_bottom_y}" font-family="Arial, sans-serif" font-size="32" font-weight="bold" text-anchor="middle" fill="#333">
        {current_time.strftime('%H:%M:%S')}
    </text>
            """

        svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Definitions for 80s/90s Theme -->
    <defs>
        <!-- Radical 80s gradient background (kept for reference or optional use) -->
        <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#FF6B9D;stop-opacity:1" />
            <stop offset="50%" style="stop-color:#C371E3;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#4FACFE;stop-opacity:1" />
        </linearGradient>
        
        <!-- Glow effects for neon look -->
        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="4" stdDeviation="10" flood-opacity="0.4"/>
        </filter>
        
        <filter id="textShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="3" dy="3" stdDeviation="2" flood-opacity="0.3"/>
        </filter>
        
        <filter id="handGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    
    <!-- Background is now handled by HTML container if text is disabled -->
    {f'<rect width="100%" height="100%" fill="url(#bgGradient)" />' if with_text else ''}
    
    <!-- Progress Ring -->
    {progress_ring}
    
    <!-- Clock Face with bold 80s style border -->
    <circle cx="{self.cx}" cy="{self.cy}" r="{self.radius}" fill="#FFFDE7" stroke="#D00000" stroke-width="8" filter="url(#shadow)" />
    
    <!-- Waiting Sector -->
    {sector_svg}
    
    <!-- Markers -->
    {markers}
    
    <!-- Hands -->
    {hour_hand}
    {minute_hand}
    
    <!-- Center Dot -->
    <circle cx="{self.cx}" cy="{self.cy}" r="16" fill="#D00000" stroke="#FFF" stroke-width="4" />

    {text_elements}
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
            return ""

        start_angle = (current.minute * 6) - 90
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
        
        # 80s neon green glow
        return f'<path d="{path}" fill="rgba(0, 255, 127, 0.4)" stroke="#00FF7F" stroke-width="3" />'

    def _generate_progress_ring(self, percent: float, seconds_until_show: float) -> str:
        """Generate the progress ring SVG."""
        # Radius for the ring (slightly larger than clock face)
        r = self.radius + 30
        circumference = 2 * math.pi * r
        
        # Calculate stroke dasharray
        # If percent is 1.0 (100%), dasharray is "circumference 0" (full circle)
        # If percent is 0.0, dasharray is "0 circumference" (empty)
        # We want it to fill up clockwise from top
        
        # FIX: Ensure percent is valid 0-1
        percent = max(0.0, min(1.0, percent))
        
        fill_length = circumference * percent
        gap_length = circumference - fill_length
        
        # Color based on urgency (Harmonized)
        if seconds_until_show < 60:
            color = "#FF0000"  # Red (Urgent)
        elif seconds_until_show < 300:
            color = "#FF0080"  # Hot Pink
        else:
            color = "#00E5FF"  # Cyan
            
        return f"""
        <!-- Background Ring -->
        <circle cx="{self.cx}" cy="{self.cy}" r="{r}" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="15" />
        
        <!-- Progress Arc -->
        <circle cx="{self.cx}" cy="{self.cy}" r="{r}" fill="none" stroke="{color}" stroke-width="15"
            stroke-dasharray="{fill_length} {gap_length}"
            stroke-dashoffset="{circumference/4}" 
            transform="rotate(-90 {self.cx} {self.cy})"
            stroke-linecap="round"
        />
        
        <!-- GO Marker at Top -->
        <text x="{self.cx}" y="{self.cy - r - 15}" font-family="Arial Black, sans-serif" font-size="24" font-weight="bold" text-anchor="middle" fill="#FFF">GO</text>
        """

    def _generate_hand(self, angle: float, length: float, width: float, color: str) -> str:
        """Generate a clock hand with 80s bold style."""
        angle_rad = math.radians(angle - 90)
        x2 = self.cx + length * math.cos(angle_rad)
        y2 = self.cy + length * math.sin(angle_rad)
        
        # Add a subtle glow effect for neon look
        return f'''<line x1="{self.cx}" y1="{self.cy}" x2="{x2}" y2="{y2}" 
                    stroke="{color}" stroke-width="{width}" stroke-linecap="round" 
                    filter="url(#handGlow)" />'''

    def _generate_markers(self) -> str:
        """Generate hour markers and numbers."""
        markers = []
        for i in range(12):
            angle_deg = i * 30
            angle_rad = math.radians(angle_deg - 90)
            
            # Tick marks
            x1 = self.cx + (self.radius - 20) * math.cos(angle_rad)
            y1 = self.cy + (self.radius - 20) * math.sin(angle_rad)
            x2 = self.cx + self.radius * math.cos(angle_rad)
            y2 = self.cy + self.radius * math.sin(angle_rad)
            
            width = 8 if i % 3 == 0 else 4
            color = "#D00000" if i % 3 == 0 else "#FF0080" # Harmonized
            
            markers.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" />')
            
            # Numbers (Larger and Harmonized)
            # Position numbers slightly inside the ticks
            num_radius = self.radius - 65  # Pull in slightly more for larger text
            nx = self.cx + num_radius * math.cos(angle_rad)
            ny = self.cy + num_radius * math.sin(angle_rad)
            
            # Adjust vertical alignment for text
            ny += 20 # Approximate centering for larger font
            
            num = i if i != 0 else 12
            # Huge font size (72), Dark Red color, with Shadow
            markers.append(f'<text x="{nx}" y="{ny}" font-family="Arial, sans-serif" font-size="72" font-weight="bold" text-anchor="middle" fill="#D00000" filter="url(#textShadow)">{num}</text>')
            
        return "\n".join(markers)
