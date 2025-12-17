"""Countdown component for 10-minute show start timer."""

from fasthtml.common import *
from datetime import datetime, timedelta
from alma_tv.web.state import state

def CountdownView():
    """Render countdown timer display."""
    if not state.countdown_target_time:
        # No countdown active, return to clock
        from alma_tv.web.components.clock import ClockView
        return ClockView()
    
    now = datetime.now()
    remaining = (state.countdown_target_time - now).total_seconds()
    
    if remaining <= 0:
        # Countdown finished, start playback
        # This will be handled by the poll route
        remaining = 0
    
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    
    return Div(
        # Countdown display
        Div(
            H1("🚀 Show Starting Soon!", style="color: white; font-size: 3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);"),
            Div(
                f"{minutes:02d}:{seconds:02d}",
                style="font-size: 10rem; font-weight: bold; color: #FF6B9D; font-family: monospace; text-shadow: 4px 4px 8px rgba(0,0,0,0.5); margin: 2rem 0;"
            ),
            P(f"Get ready for your show!", style="color: rgba(255,255,255,0.8); font-size: 1.5rem;"),
            style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 2rem;"
        ),
        # Cancel button
        Button(
            "✖ Cancel",
            hx_post="/countdown/cancel",
            hx_target="body",
            hx_swap="innerHTML",
            style="padding: 1rem 2rem; font-size: 1.2rem; background: rgba(255, 100, 100, 0.8); color: white; border: none; border-radius: 12px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);"
        ),
        # Auto-refresh every second
        hx_get="/countdown/poll",
        hx_trigger="every 1s",
        hx_target="body",
        hx_swap="innerHTML",
        id="countdown-container",
        style="width: 100vw; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem;"
    )
