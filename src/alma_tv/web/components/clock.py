"""Clock component for Web App."""

from datetime import datetime, timedelta
from fasthtml.common import *
from alma_tv.clock.renderer import ClockRenderer
from alma_tv.config import get_settings
from alma_tv.web.components.logo import Logo

# Initialize renderer once
# clock_renderer = ClockRenderer(width=800, height=600)

def ClockView():
    return Div(
        _render_clock_content(),
        Logo(),
        id="clock-container",
        # Radical 80s gradient background applied to the whole container
        style="width: 100vw; height: 100vh; background: linear-gradient(135deg, #FF6B9D 0%, #C371E3 50%, #4FACFE 100%); display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 2rem;",
        hx_get="/clock/update",
        hx_trigger="every 60s",
        hx_swap="innerHTML"
    )

def _render_clock_content():
    """Generate the inner content of the clock view."""
    settings = get_settings()
    now = datetime.now()
    
    # Parse start time
    start_hour, start_minute = map(int, settings.start_time.split(":"))
    target_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)
        
    # Calculate countdown text
    seconds_until_show = (target_time - now).total_seconds()
    if seconds_until_show > 60:
        minutes = int(seconds_until_show // 60)
        countdown_text = f"{minutes} MIN TO SHOW"
    elif seconds_until_show > 0:
        countdown_text = f"{int(seconds_until_show)} SECONDS!"
    else:
        countdown_text = "Show time! 🎉"

    # Calculate harmonized color for countdown
    # Transition from Cool Blue (220) -> Purple (280) -> Hot Pink (330) -> Red (360/0)
    # This avoids the "random" green/yellow/orange phase
    max_seconds = 4 * 3600
    progress = 1.0 - min(1.0, max(0.0, seconds_until_show / max_seconds))
    
    # Map progress (0.0 to 1.0) to Hue (220 to 360)
    hue = 220 + (progress * 140)
    countdown_color = f"hsl({hue}, 100%, 60%)"

    # Render SVG without text (transparent background)
    renderer = ClockRenderer(width=800, height=800)
    svg_content = renderer.render(now, target_time, with_text=False)
    
    return Div(
        # Font Loader (Codystar for Dot Matrix look)
        Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Codystar:wght@400;800&display=swap"),
        
        # CSS for Blinking Animation
        Style("""
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0; }
            }
            .blink {
                animation: blink 1s infinite;
            }
        """),
        
        # Top: Countdown (Harmonized Color)
        H1(countdown_text, style=f"font-family: 'Arial Black', sans-serif; font-size: 6rem; color: {countdown_color}; text-shadow: 3px 3px 0px #000; margin-top: 5vh; text-align: center; z-index: 10; transition: color 1s linear;"),
        
        # Middle: Clock SVG (Centered with padding)
        Div(NotStr(svg_content), style="flex-grow: 1; display: flex; align-items: center; justify-content: center; width: 100%; max-height: 60vh; padding: 2rem;"),
        
        # Countdown Button
        Button(
            "🚀 Start in 10 Minutes",
            hx_post="/countdown/start",
            hx_target="body",
            hx_swap="innerHTML",
            style="padding: 1.5rem 3rem; font-size: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 20px; cursor: pointer; font-weight: bold; box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); margin: 2rem 0; transition: transform 0.2s, box-shadow 0.2s; z-index: 10;",
            onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 8px 25px rgba(102, 126, 234, 0.6)';",
            onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.4)';"
        ),
        
        # Bottom: Digital Time (Dot Matrix LED Style with CSS Blinking Colon)
        Div(
            H2(
                Span(now.strftime('%H')),
                Span(":", cls="blink"),
                Span(now.strftime('%M')),
                style="font-family: 'Codystar', sans-serif; font-weight: 800; font-size: 6rem; color: #FF0000; margin: 0; letter-spacing: 5px; text-shadow: 0 0 10px #FF0000, 0 0 20px #FF0000;"
            ),
            style="background: #000; padding: 1rem 3rem; border: 4px solid #333; border-radius: 10px; box-shadow: 0 0 15px rgba(255, 0, 0, 0.3); margin-bottom: 5vh; z-index: 10; display: flex; justify-content: center;"
        )
    )

def _render_svg():
    """Helper for HTMX updates."""
    return _render_clock_content()  # NotStr prevents escaping of SVG HTML
