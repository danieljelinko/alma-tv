"""Generate a demo clock SVG with a forced time."""

from datetime import datetime
from pathlib import Path
from alma_tv.clock.renderer import ClockRenderer

# Force time to 18:30 (30 mins before 19:00)
forced_time = datetime.now().replace(hour=18, minute=30, second=0)

renderer = ClockRenderer()
svg = renderer.render(forced_time)

output_path = Path("/tmp/demo_clock_active.svg")
output_path.write_text(svg)

print(f"Generated demo clock at {output_path}")
