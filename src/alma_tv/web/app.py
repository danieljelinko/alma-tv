"""Main Web Application for Alma TV."""

from fasthtml.common import *
from alma_tv.web.state import state, AppStatus
from alma_tv.config import get_settings
from alma_tv.logging.config import get_logger

# Initialize logging
# Initialize logging
logger = get_logger(__name__)
settings = get_settings()
settings.ensure_directories()

# Create FastHTML app
app, rt = fast_app(
    hdrs=(
        Meta(charset="UTF-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        Style("""
            body { 
                margin: 0; 
                padding: 0; 
                background: black; 
                color: white; 
                font-family: system-ui, sans-serif;
                overflow: hidden; /* Prevent scrolling in Kiosk mode */
            }
            .container {
                width: 100vw;
                height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
        """),
    )
)


from alma_tv.web.components.clock import ClockView, _render_svg
from alma_tv.web.components.player import PlayerView
from alma_tv.web.components.feedback import FeedbackView, ThankYouView
from alma_tv.web.routes.stream import stream_video
from pathlib import Path

@rt("/")
def get():
    """Root route - dispatches to current state view."""
    return Div(
        _get_view_for_state(),
        id="main-content",
        cls="container",
        hx_get="/poll",      # Poll for state changes
        hx_trigger="every 2s",
        hx_swap="innerHTML"
    )


@rt("/poll")
def poll():
    """Poll endpoint to check for state changes."""
    # In a real implementation, we would check if state changed before re-rendering
    # For now, just return the current view
    return _get_view_for_state()

@rt("/clock/update")
def update_clock():
    """Endpoint for clock polling."""
    if state.status != AppStatus.IDLE:
        return "" # Stop updating if not idle
    return _render_svg()

@rt("/stream")
def get_stream(request: Request, path: str):
    """Stream video file."""
    return stream_video(request, Path(path))

@rt("/player/next")
def next_video():
    """Get next video in playlist."""
    # If playlist finished, state will change to FEEDBACK
    # The poll loop will catch this, but we can also return the feedback view directly
    if state.status == AppStatus.FEEDBACK:
        return FeedbackView()
    return PlayerView()

@rt("/feedback/submit")
def submit_feedback(rating: str):
    """Handle feedback submission."""
    # In a real implementation, save to DB using state.current_session_id
    logger.info(f"Feedback received: {rating}")
    
    # Show Thank You message
    # Show Thank You message
    return ThankYouView()

@rt("/feedback/skip")
def skip_feedback():
    """Handle feedback timeout/skip."""
    logger.info("Feedback skipped/timed out")
    # Reset state to IDLE (Clock)
    state.reset()
    return _get_view_for_state()

def _get_view_for_state():
    """Render the component for the current state."""
    if state.status == AppStatus.IDLE:
        return ClockView()
    elif state.status == AppStatus.PLAYING:
        return PlayerView()
    elif state.status == AppStatus.FEEDBACK:
        return FeedbackView()
    elif state.status == AppStatus.COUNTDOWN:
        from alma_tv.web.components.countdown import CountdownView
        return CountdownView()
    return Div("Unknown State")


@rt("/reset")
def post_reset():
    """Debug endpoint to reset state."""
    state.reset()
    return _get_view_for_state()

@rt("/debug/force_play")
def force_play():
    """Debug endpoint to force start a session."""
    # Create a dummy playlist with the intro video (or a placeholder)
    # We'll use the intro path if it exists, otherwise just a dummy entry
    playlist = []
    if settings.intro_path and settings.intro_path.exists():
        playlist.append({"path": str(settings.intro_path), "title": "Intro"})
    else:
        # Fallback for testing if no media exists
        dummy_path = Path("dummy.mp4")
        if not dummy_path.exists():
            # Create a dummy file if it doesn't exist (just empty for now, browser might complain but it won't crash 404)
            # Better: try to find ANY mp4 in the media root
            found_video = next(settings.media_root.rglob("*.mp4"), None)
            if found_video:
                playlist.append({"path": str(found_video), "title": "Test Video (Found)"})
            else:
                # Last resort
                with open(dummy_path, "wb") as f:
                    f.write(b"dummy video content")
                playlist.append({"path": "dummy.mp4", "title": "Dummy Video"})
        else:
             playlist.append({"path": "dummy.mp4", "title": "Dummy Video"})
        
    state.start_session(999, playlist)
    return _get_view_for_state()

@rt("/debug/full_flow")
def full_flow():
    """Debug endpoint to test the full evening flow (Intro -> Video -> Outro)."""
    playlist = []
    
    # 1. Intro
    if settings.intro_path and settings.intro_path.exists():
        playlist.append({"path": str(settings.intro_path), "title": "Intro"})
    else:
        # Create dummy intro if needed
        dummy_intro = Path("dummy_intro.mp4")
        if not dummy_intro.exists():
            with open(dummy_intro, "wb") as f: f.write(b"dummy intro")
        playlist.append({"path": "dummy_intro.mp4", "title": "Dummy Intro"})

    # 2. Main Cartoon (Dummy)
    dummy_cartoon = Path("dummy_cartoon.mp4")
    if not dummy_cartoon.exists():
        with open(dummy_cartoon, "wb") as f: f.write(b"dummy cartoon")
    playlist.append({"path": "dummy_cartoon.mp4", "title": "Dummy Cartoon"})
    
    # 3. Outro
    if settings.outro_path and settings.outro_path.exists():
        playlist.append({"path": str(settings.outro_path), "title": "Outro"})
    else:
        # Create dummy outro if needed
        dummy_outro = Path("dummy_outro.mp4")
        if not dummy_outro.exists():
            with open(dummy_outro, "wb") as f: f.write(b"dummy outro")
        playlist.append({"path": "dummy_outro.mp4", "title": "Dummy Outro"})

    state.start_session(888, playlist)
    return _get_view_for_state()

from alma_tv.web.routes.admin import admin_routes

# Register Admin Routes
admin_routes(app, rt)

from alma_tv.web.components.history import HistoryView

@rt("/history/schedule")
def get_schedule():
    """Show schedule view."""
    return HistoryView("schedule")

@rt("/history/past")
def get_history():
    """Show history view."""
    return HistoryView("history")

# --- Background Scheduler ---
import threading
import time
from datetime import datetime
from alma_tv.scheduler.lineup import LineupGenerator

def scheduler_loop():
    """Background loop to check for showtime."""
    logger.info("Scheduler loop started")
    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        # Check if it's start time and we are IDLE
        if current_time_str == settings.start_time and state.status == AppStatus.IDLE:
            logger.info("It's showtime! Generating lineup...")
            try:
                # Generate lineup
                generator = LineupGenerator()
                session = generator.generate_daily_lineup(now.date())
                
                if session and session.play_history:
                    # Build playlist
                    playlist = []
                    # Add intro if configured
                    if settings.intro_path and settings.intro_path.exists():
                        playlist.append({"path": str(settings.intro_path), "title": "Intro"})
                    
                    # Add episodes
                    for ph in session.play_history:
                        playlist.append({
                            "path": ph.video.path, 
                            "title": f"{ph.video.series} - {ph.video.title}"
                        })
                        
                    # Add outro if configured
                    if settings.outro_path and settings.outro_path.exists():
                        playlist.append({"path": str(settings.outro_path), "title": "Outro"})
                        
                    # Start session
                    state.start_session(session.id, playlist)
                    logger.info(f"Session started with {len(playlist)} videos")
                else:
                    logger.warning("No lineup generated")
                    
            except Exception as e:
                logger.error(f"Failed to start session: {e}", exc_info=True)
                
        time.sleep(10) # Check every 10 seconds

# Setup countdown routes
from alma_tv.web.routes.countdown import setup_countdown_routes
setup_countdown_routes(app)

# Start scheduler thread
threading.Thread(target=scheduler_loop, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("alma_tv.web.app:app", host="0.0.0.0", port=8001, reload=True)
