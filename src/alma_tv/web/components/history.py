"""History and Schedule Browser component."""

from datetime import datetime, timedelta
from fasthtml.common import *
from alma_tv.web.state import state, AppStatus
from alma_tv.database.session import get_db
from alma_tv.database.models import Session, SessionStatus, PlayHistory

def HistoryView(view_type="schedule"):
    """Render the History/Schedule view."""
    
    content = _render_schedule() if view_type == "schedule" else _render_history()
    
    return Div(
        _render_nav(view_type),
        Div(content, style="padding: 2rem; overflow-y: auto; width: 100%; display: flex; flex-direction: column; align-items: center;"),
        id="main-content",
        style="background: #1a1a1a; min-height: 100vh; display: flex; flex-direction: column;"
    )

def _render_nav(active_tab):
    """Render navigation menu."""
    return Nav(
        Ul(
            Li(A("🕰️ Clock", href="/", hx_get="/", hx_target="body", style="color: white;")),
            Li(A("📅 Schedule", href="#", hx_get="/history/schedule", hx_target="#main-content", 
                 style=f"color: {'#FF6B35' if active_tab == 'schedule' else 'white'}; font-weight: bold;")),
            Li(A("📜 History", href="#", hx_get="/history/past", hx_target="#main-content", 
                 style=f"color: {'#4ECDC4' if active_tab == 'history' else 'white'}; font-weight: bold;")),
            style="display: flex; gap: 2rem; list-style: none; margin: 0; padding: 0; justify-content: center;"
        ),
        style="padding: 1rem; background: #333; position: sticky; top: 0; z-index: 100;"
    )

def _render_schedule():
    """Render upcoming schedule."""
    try:
        with get_db() as db:
            from sqlalchemy.orm import joinedload
            from alma_tv.logging.config import get_logger
            logger = get_logger(__name__)
            
            logger.info("Querying schedule...")
            # Get planned sessions from today onwards
            from datetime import datetime
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            sessions = db.query(Session).options(
                joinedload(Session.play_history).joinedload(PlayHistory.video)
            ).filter(Session.status == SessionStatus.PLANNED).filter(Session.show_date >= today).order_by(Session.show_date.asc()).limit(10).all()
            
            logger.info(f"Found {len(sessions)} planned sessions")
            
            cards = []
            if not sessions:
                cards.append(Div(
                    P("No shows scheduled yet!", style="color: #666; font-size: 1.2rem;"),
                    P("Use the Admin panel to create today's lineup!", style="color: #999; margin-top: 0.5rem;"),
                    A("Go to Admin →", href="/admin", style="color: #FF6B35; text-decoration: none; font-weight: bold;"),
                    style="padding: 2rem; text-align: center;"
                ))
            else:
                for s in sessions:
                    logger.info(f"Processing session {s.id}")
                    titles = [ph.video.title for ph in s.play_history]
                    cards.append(_session_card(s, titles, "planned"))
    except Exception as e:
        from alma_tv.logging.config import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error rendering schedule: {e}", exc_info=True)
        return Div(f"Error loading schedule: {e}", style="color: red;")
            
    return Div(
        H2("📅 Upcoming Shows", style="color: #FF6B35; margin-bottom: 1rem; text-align: center;"),
        *cards,
        style="width: 100%; max-width: 800px; margin: 0 auto;"
    )

def _render_history():
    """Render past history."""
    # Query DB for completed sessions
    try:
        # get_db is a context manager, use with statement
        with get_db() as db:
            # Eager load relationships to avoid detached instance errors
            from sqlalchemy.orm import joinedload
            from alma_tv.logging.config import get_logger
            logger = get_logger(__name__)
            
            logger.info("Querying history...")
            sessions = db.query(Session).options(
                joinedload(Session.play_history).joinedload(PlayHistory.video)
            ).filter(Session.status == SessionStatus.COMPLETED).order_by(Session.show_date.desc()).limit(10).all()
            logger.info(f"Found {len(sessions)} sessions")
            
            cards = []
            if not sessions:
                cards.append(P("No history yet!", style="color: #666;"))
            else:
                for s in sessions:
                    logger.info(f"Processing session {s.id}")
                    titles = [ph.video.title for ph in s.play_history]
                    cards.append(_session_card(s.show_date, f"Session #{s.id}", titles, "completed"))
    except Exception as e:
        from alma_tv.logging.config import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error rendering history: {e}", exc_info=True)
        return Div(f"Error loading history: {e}", style="color: red;")
            
    return Div(
        H2("📜 Past Shows", style="color: #4ECDC4; margin-bottom: 1rem; text-align: center;"),
        *cards,
        style="width: 100%; max-width: 800px; margin: 0 auto;"
    )

def _session_card(session_or_date, title_or_episodes, episodes_or_status, status=None):
    """Render a session card. Supports both old (date, title, episodes, status) and new (session, episodes, status) signatures."""
    # Handle both signatures for backward compatibility
    if isinstance(session_or_date, Session):
        session = session_or_date
        date = session.show_date
        title = f"Session #{session.id}"
        episodes = title_or_episodes
        status = episodes_or_status
        session_id = session.id
    else:
        date = session_or_date
        title = title_or_episodes
        episodes = episodes_or_status
        status = status
        session_id = None
    
    color = "#FF6B35" if status == "planned" else "#4ECDC4"
    
    # Add Play Now button for planned sessions
    action_button = ""
    if status == "planned" and session_id:
        action_button = Button(
            "▶️ Play Now",
            hx_post=f"/admin/play_now/{session_id}",
            hx_target="body",
            hx_swap="innerHTML",
            style="background: #38a169; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-weight: bold;"
        )
    
    return Article(
        Header(
            H3(date.strftime("%A, %b %d"), style="margin: 0; color: #333;"),
            Div(
                Span(status.upper(), style=f"background: {color}; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; color: white; font-weight: bold; margin-right: 0.5rem;"),
                action_button
            , style="display: flex; gap: 0.5rem; align-items: center;")
        , style="display: flex; justify-content: space-between; align-items: center; background: #f0f0f0; padding: 1rem; border-radius: 8px 8px 0 0; border-bottom: 1px solid #ddd;"),
        
        Div(
            H4(title, style="margin-top: 0.5rem; color: #ccc; font-size: 1.1rem;"),
            Ul(
                *[Li(ep if ep else "Unknown Episode", style="color: white; margin-bottom: 0.5rem;") for ep in episodes],
                style="list-style-type: disc; padding-left: 1.5rem; margin-top: 1rem;"
            ),
            style="padding: 1.5rem;"
        ),
        style="margin-bottom: 1.5rem; background: #2a2a2a; border: 1px solid #444; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);"
    )
