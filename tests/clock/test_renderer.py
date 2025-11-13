"""Tests for clock renderer."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from alma_tv.clock.renderer import ClockRenderer


def test_renderer_initialization():
    """Test clock renderer can be initialized."""
    renderer = ClockRenderer()
    assert renderer.width == 800
    assert renderer.height == 800
    assert renderer.clock_radius == 300


def test_renderer_custom_size():
    """Test clock renderer with custom size."""
    renderer = ClockRenderer(width=1000, height=1000, clock_radius=400)
    assert renderer.width == 1000
    assert renderer.height == 1000
    assert renderer.clock_radius == 400


def test_render_clock():
    """Test rendering clock SVG."""
    renderer = ClockRenderer()
    current_time = datetime(2025, 11, 13, 10, 30)

    dwg = renderer.render(current_time=current_time)

    assert dwg is not None
    # SVG should have content
    svg_str = dwg.tostring()
    assert len(svg_str) > 0
    assert "svg" in svg_str


def test_time_to_angle():
    """Test time to angle conversion."""
    renderer = ClockRenderer()

    # 12:00 should be 0 degrees
    angle = renderer._time_to_angle(datetime(2025, 1, 1, 12, 0))
    assert angle == 0

    # 3:00 should be 90 degrees
    angle = renderer._time_to_angle(datetime(2025, 1, 1, 3, 0))
    assert angle == 90

    # 6:00 should be 180 degrees
    angle = renderer._time_to_angle(datetime(2025, 1, 1, 6, 0))
    assert angle == 180

    # 9:00 should be 270 degrees
    angle = renderer._time_to_angle(datetime(2025, 1, 1, 9, 0))
    assert angle == 270


def test_render_with_next_program():
    """Test rendering with next program time."""
    renderer = ClockRenderer()
    current_time = datetime(2025, 11, 13, 15, 30)
    next_program = datetime(2025, 11, 13, 19, 0)

    dwg = renderer.render(
        current_time=current_time,
        next_program_time=next_program,
        program_label="Cartoons",
    )

    assert dwg is not None
    svg_str = dwg.tostring()
    assert "Cartoons" in svg_str


def test_save_clock(tmp_path):
    """Test saving clock to file."""
    renderer = ClockRenderer()
    output_path = tmp_path / "clock.svg"

    saved_path = renderer.save(output_path=output_path)

    assert saved_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_create_arc_path():
    """Test arc path creation."""
    renderer = ClockRenderer()

    # Create simple arc
    path = renderer._create_arc_path(400, 400, 100, 0, 90)

    assert path.startswith("M")
    assert "A" in path
    assert len(path) > 0
