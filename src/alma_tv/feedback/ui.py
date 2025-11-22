"""Feedback UI using FastHTML."""

from datetime import datetime
from typing import Optional

import uvicorn
from fasthtml.common import *

from alma_tv.config import get_settings
from alma_tv.database import Feedback, PlayHistory, Session, get_db
from alma_tv.database.models import Rating, SessionStatus
from alma_tv.logging.config import get_logger
from alma_tv.scheduler.weights import WeightCalculator

logger = get_logger(__name__)


def create_app(debug: bool = False):
    """Create and configure the FastHTML app."""
    app, rt = fast_app(
        hdrs=(
            Meta(charset="UTF-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            Style("""
                body { 
                    font-family: system-ui, sans-serif; 
                    background: #f0f4f8; 
                    display: flex; 
                    flex-direction: column; 
                    align-items: center; 
                    justify-content: center; 
                    min-height: 100vh; 
                    margin: 0; 
                    padding: 20px;
                }
                .card {
                    background: white;
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    width: 100%;
                    margin-bottom: 20px;
                }
                h1 { color: #2d3748; margin-bottom: 10px; }
                h2 { color: #4a5568; font-size: 1.2rem; margin-bottom: 30px; }
                .buttons { display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }
                .btn {
                    border: none;
                    background: white;
                    border-radius: 15px;
                    padding: 20px;
                    font-size: 3rem;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    min-width: 120px;
                }
                .btn:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
                .btn span { font-size: 1rem; margin-top: 10px; color: #718096; font-weight: bold; }
                .btn.love { color: #e53e3e; }
                .btn.okay { color: #d69e2e; }
                .btn.never { color: #718096; }
                .success { color: #38a169; font-size: 1.5rem; font-weight: bold; animation: pop 0.5s ease-out; }
                @keyframes pop { 0% { transform: scale(0.8); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
            """),
        )
    )

    @rt("/")
    def get():
        """Show feedback options for the latest completed session."""
        with get_db() as db:
            # Find latest completed session
            session = (
                db.query(Session)
                .filter(Session.status == SessionStatus.COMPLETED)
                .order_by(Session.show_date.desc())
                .first()
            )

            if not session:
                return Div(
                    H1("No recent shows found"),
                    P("Check back later!"),
                    cls="card"
                )

            # Find episodes without feedback
            pending_episodes = []
            for ph in session.play_history:
                if not ph.feedback:
                    pending_episodes.append(ph)
            
            if not pending_episodes:
                return Div(
                    H1("All done! 🎉"),
                    P("Thanks for your feedback!"),
                    cls="card"
                )

            # Show feedback for the first pending episode
            current_ph = pending_episodes[0]
            video = current_ph.video
            
            return Div(
                H1("How was the show?"),
                H2(f"{video.series} - {video.episode_code}"),
                Div(
                    Button(
                        "😍", Span("Love it!"), 
                        cls="btn love", 
                        hx_post=f"/submit/{current_ph.id}/liked", 
                        hx_target="body"
                    ),
                    Button(
                        "😊", Span("It was okay"), 
                        cls="btn okay", 
                        hx_post=f"/submit/{current_ph.id}/okay", 
                        hx_target="body"
                    ),
                    Button(
                        "😢", Span("Never again"), 
                        cls="btn never", 
                        hx_post=f"/submit/{current_ph.id}/never", 
                        hx_target="body",
                        hx_confirm="Are you sure you never want to see this again?"
                    ),
                    cls="buttons"
                ),
                cls="card"
            )

    @rt("/submit/{ph_id}/{rating_str}")
    def post(ph_id: int, rating_str: str):
        """Handle feedback submission."""
        rating_map = {
            "liked": Rating.LIKED,
            "okay": Rating.OKAY,
            "never": Rating.NEVER,
        }
        
        if rating_str not in rating_map:
            return "Invalid rating", 400
            
        rating = rating_map[rating_str]
        
        with get_db() as db:
            ph = db.query(PlayHistory).filter(PlayHistory.id == ph_id).first()
            if not ph:
                return "Episode not found", 404
                
            # Save feedback
            feedback = Feedback(
                play_history_id=ph.id,
                rating=rating,
                submitted_at=datetime.utcnow()
            )
            db.add(feedback)
            db.commit()
            
            # Update weights hook
            calc = WeightCalculator()
            calc.update_weight_for_feedback(ph.video_id)
            
        # Return to main page to show next episode or success
        return get()

    return app


def run_feedback_ui(port: Optional[int] = None, debug: bool = False):
    """Run the feedback UI server."""
    settings = get_settings()
    port = port or settings.feedback_port
    
    app = create_app(debug=debug)
    
    logger.info(f"Starting feedback UI on port {port}")
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
        logger.info("Feedback UI server stopped")
    except Exception as e:
        logger.error(f"Feedback UI server failed: {e}", exc_info=True)
        raise
