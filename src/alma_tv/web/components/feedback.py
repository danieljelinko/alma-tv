"""Feedback component for Web App."""

from fasthtml.common import *
from alma_tv.web.state import state, AppStatus
from alma_tv.feedback.reporter import FeedbackReporter
from alma_tv.database.session import get_db
from alma_tv.database.session import get_db
from alma_tv.database.models import Rating
from alma_tv.config import get_settings

def FeedbackView():
    """Render the Feedback view."""
    # In a real implementation, we would get the session ID from state
    # For now, just show the generic feedback UI
    
    return Div(
        H1("Did you like the show?", style="margin-bottom: 2rem;"),
        Div(
            _feedback_btn("😍", "liked", "green"),
            _feedback_btn("😐", "disliked", "orange"),
            _feedback_btn("⛔", "never_again", "red"),
            style="display: flex; gap: 2rem;"
        ),
        # Auto-skip after timeout
        Div(
            Div(id="countdown-bar", style=f"height: 10px; background: #4ECDC4; width: 100%; transition: width {get_settings().feedback_timeout}s linear;"),
            P(id="countdown-text", style="margin-top: 1rem; color: #666;"),
            Script(f"""
                // Start countdown bar animation
                setTimeout(() => {{
                    document.getElementById('countdown-bar').style.width = '0%';
                }}, 100);
                
                // Text countdown
                let seconds = {get_settings().feedback_timeout};
                const text = document.getElementById('countdown-text');
                const interval = setInterval(() => {{
                    seconds--;
                    text.textContent = `Returning to clock in ${{seconds}}s...`;
                    if (seconds <= 0) clearInterval(interval);
                }}, 1000);
                text.textContent = `Returning to clock in ${{seconds}}s...`;
            """),
            style="width: 100%; max-width: 400px; margin-top: 2rem;"
        ),
        
        # HTMX trigger for actual navigation
        Div(hx_get="/feedback/skip", hx_trigger=f"load delay:{get_settings().feedback_timeout}s", hx_swap="innerHTML", hx_target="#main-content"),
        
        id="feedback-container",
        style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #f7fafc;"
    )

def _feedback_btn(emoji, rating, color):
    return Button(
        emoji,
        hx_post=f"/feedback/submit?rating={rating}",
        hx_target="#feedback-container",
        style=f"font-size: 4rem; padding: 1rem 2rem; border-radius: 1rem; border: none; background: {color}; cursor: pointer;"
    )

def ThankYouView():
    """Render Thank You message."""
    return Div(
        H1("Thanks for your feedback! 🎉"),
        P("See you next time!"),
        # Automatically reset to clock after 5 seconds
        Div(hx_get="/reset", hx_trigger="load delay:5s"),
        style="text-align: center;"
    )
