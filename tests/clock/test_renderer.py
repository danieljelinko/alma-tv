"""Tests for clock renderer."""

from datetime import datetime
from alma_tv.clock.renderer import ClockRenderer

def test_render_output():
    """Test that render produces valid-looking SVG."""
    renderer = ClockRenderer()
    now = datetime(2024, 1, 1, 18, 30, 0) # 18:30
    
    svg = renderer.render(now)
    
    assert "<svg" in svg
    assert "width=\"800\"" in svg
    assert "height=\"600\"" in svg
    assert "18:30:00" in svg
    
    # Should have a sector since it's within 60 mins of 19:00 (default)
    # Assuming default start_time is 19:00
    # 18:30 to 19:00 is 30 mins
    assert "path" in svg # The sector path
    assert "rgba(100, 200, 100, 0.3)" in svg

def test_render_no_sector_past_time():
    """Test that no sector is drawn if time is past target."""
    renderer = ClockRenderer()
    now = datetime(2024, 1, 1, 19, 30, 0)
    
    svg = renderer.render(now)
    
    # Should NOT have the sector color
    assert "rgba(100, 200, 100, 0.3)" not in svg
