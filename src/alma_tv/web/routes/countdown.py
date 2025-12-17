"""Countdown routes for 10-minute show initiation."""

from datetime import datetime, timedelta
from fasthtml.common import *
from alma_tv.web.state import state, AppStatus
from alma_tv.database.session import get_db
from alma_tv.database.models import Session, SessionStatus
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


def setup_countdown_routes(app):
    """Setup countdown-related routes."""
    
    @app.post("/countdown/start")
    def start_countdown():
        """Initialize 10-minute countdown."""
        # Find today's scheduled session
        today = datetime.now().date()
        
        with get_db() as db:
            session = db.query(Session).filter(
                Session.show_date >= datetime.combine(today, datetime.min.time()),
                Session.show_date < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                Session.status == SessionStatus.PLANNED
            ).first()
            
            if not session:
                # No session found, try to find the most recent one
                session = db.query(Session).filter(
                    Session.status == SessionStatus.PLANNED
                ).order_by(Session.show_date.desc()).first()
                
                if not session:
                    logger.warning("No scheduled sessions found for countdown")
                    # Return to clock
                    from alma_tv.web.components.clock import ClockView
                    return ClockView()
            
            # Set countdown
            state.countdown_target_time = datetime.now() + timedelta(minutes=10)
            state.countdown_session_id = session.id
            state.set_status(AppStatus.COUNTDOWN)
            
            logger.info(f"Countdown started for session {session.id}, target: {state.countdown_target_time}")
        
        from alma_tv.web.components.countdown import CountdownView
        return CountdownView()
    
    @app.get("/countdown/poll")
    def poll_countdown():
        """Poll countdown status."""
        if state.status != AppStatus.COUNTDOWN or not state.countdown_target_time:
            # Countdown not active, return to clock
            from alma_tv.web.components.clock import ClockView
            return ClockView()
        
        now = datetime.now()
        remaining = (state.countdown_target_time - now).total_seconds()
        
        if remaining <= 0:
            # Countdown finished, start playback
            logger.info("Countdown finished, starting playback")
            
            # Get the session and start playback
            with get_db() as db:
                session = db.query(Session).filter(Session.id == state.countdown_session_id).first()
                
                if session:
                    # Build playlist
                    from pathlib import Path
                    playlist = []
                    
                    for ph in session.play_history:
                        video_path = Path(ph.video.path)
                        if video_path.exists():
                            playlist.append({
                                "path": str(video_path),
                                "title": f"{ph.video.series} - S{ph.video.season:02d}E{ph.video.episode:02d}"
                            })
                    
                    # Mark session as completed
                    session.status = SessionStatus.COMPLETED
                    db.commit()
                    
                    # Start playback
                    state.countdown_target_time = None
                    state.countdown_session_id = None
                    state.start_session(session.id, playlist)
                    
                    from alma_tv.web.app import _get_view_for_state
                    return _get_view_for_state()
                else:
                    logger.error(f"Session {state.countdown_session_id} not found")
                    state.reset()
                    from alma_tv.web.components.clock import ClockView
                    return ClockView()
        
        # Continue countdown
        from alma_tv.web.components.countdown import CountdownView
        return CountdownView()
    
    @app.post("/countdown/cancel")
    def cancel_countdown():
        """Cancel countdown and return to clock."""
        logger.info("Countdown cancelled")
        state.countdown_target_time = None
        state.countdown_session_id = None
        state.reset()
        
        from alma_tv.web.components.clock import ClockView
        return ClockView()
