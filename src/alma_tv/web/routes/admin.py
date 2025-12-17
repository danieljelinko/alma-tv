"""Admin Dashboard routes."""

from fasthtml.common import *
from alma_tv.config import get_settings
from alma_tv.database import get_db, Feedback, PlayHistory, Session, Video
from alma_tv.database.models import Rating
from alma_tv.web.components.history import HistoryView
from alma_tv.web.state import state

def admin_routes(app, rt):
    """Register admin routes."""

    @rt("/admin")
    def admin_dashboard():
        """Main Admin Dashboard."""
        return Div(
            H1("Alma TV Admin", style="color: #333; margin-bottom: 2rem;"),
            Div(
                _admin_card("🎮 Debug Actions", [
                    Button("Force Play (Dummy)", hx_post="/debug/force_play", hx_target="body", cls="btn"),
                    Button("Play Scheduled (Today)", hx_post="/admin/play_scheduled", hx_target="body", cls="btn"),
                    Button("Test Full Flow", hx_post="/debug/full_flow", hx_target="body", cls="btn"),
                    Button("Reset State", hx_post="/reset", hx_target="body", cls="btn"),
                ]),
                _admin_card("📅 Schedule Management", [
                    A("Generate Schedules", href="/admin/generate", cls="btn-link"),
                    A("View Schedule", href="/admin/schedule", cls="btn-link"),
                ]),
                _admin_card("📊 Data & Logs", [
                    A("🎬 Request Shows", href="/request", cls="btn-link"),
                    A("📝 User Feedback", href="/admin/feedback", cls="btn-link"),
                    A("⚙️ Configuration", href="/admin/config", cls="btn-link"),
                    A("📅 Schedule", href="/admin/schedule", cls="btn-link"),
                    A("📜 History", href="/admin/history", cls="btn-link"),
                ]),
                style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; width: 100%; max-width: 1000px;"
            ),
            style="display: flex; flex-direction: column; align-items: center; padding: 2rem; min-height: 100vh; background: #f0f4f8; font-family: system-ui;"
        )

    @rt("/admin/feedback")
    def admin_feedback():
        """View User Feedback."""
        with get_db() as db:
            feedbacks = (
                db.query(Feedback)
                .join(PlayHistory)
                .join(Video)
                .order_by(Feedback.submitted_at.desc())
                .limit(50)
                .all()
            )
            
            rows = []
            for f in feedbacks:
                video = f.play_history.video
                rating_emoji = {
                    Rating.LIKED: "😍",
                    Rating.OKAY: "😐",
                    Rating.NEVER: "⛔"
                }.get(f.rating, str(f.rating))
                
                rows.append(Tr(
                    Td(f.submitted_at.strftime("%Y-%m-%d %H:%M")),
                    Td(f"{video.series} - {video.title}"),
                    Td(rating_emoji),
                ))
                
        return _admin_page(
            "User Feedback",
            Table(
                Thead(Tr(Th("Date"), Th("Video"), Th("Rating"))),
                Tbody(*rows),
                style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);"
            )
        )

    @rt("/admin/config")
    def admin_config():
        """View Configuration."""
        settings = get_settings()
        rows = []
        for key, value in settings.model_dump().items():
            rows.append(Tr(
                Td(key, style="font-weight: bold;"),
                Td(str(value), style="font-family: monospace;")
            ))
            
        return _admin_page(
            "Configuration",
            Table(
                Thead(Tr(Th("Setting"), Th("Value"))),
                Tbody(*rows),
                style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);"
            )
        )

    @rt("/admin/schedule")
    def admin_schedule():
        return _admin_page("Schedule", HistoryView("schedule"), back_link="/admin")

    @rt("/admin/history")
    def admin_history():
        return _admin_page("History", HistoryView("history"), back_link="/admin")

    @rt("/admin/play_now/{session_id}")
    def play_now(session_id: int):
        """Play a scheduled session immediately and mark it as completed."""
        from pathlib import Path
        from alma_tv.database.models import SessionStatus
        
        with get_db() as db:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                return Div(H1("Session not found"), style="color: red; padding: 2rem;")
            
            # Build playlist
            playlist = []
            if session.intro_path and Path(session.intro_path).exists():
                playlist.append({"path": session.intro_path, "title": "Intro"})
            
            for ph in session.play_history:
                playlist.append({
                    "path": ph.video.path,
                    "title": f"{ph.video.series} - {ph.video.title}"
                })
            
            if session.outro_path and Path(session.outro_path).exists():
                playlist.append({"path": session.outro_path, "title": "Outro"})
            
            # Mark session as completed (so it won't play at scheduled time)
            session.status = SessionStatus.COMPLETED
            db.commit()
            
            # Start playing
            from alma_tv.logging.config import get_logger
            logger = get_logger(__name__)
            logger.info(f"Play Now triggered for session {session.id}. Playlist size: {len(playlist)}")
            state.start_session(session.id, playlist)
        
        from alma_tv.web.app import _get_view_for_state
        return _get_view_for_state()

    @rt("/admin/play_scheduled")
    def play_scheduled():
        """Generate and play today's scheduled lineup immediately."""
        from datetime import date
        from alma_tv.scheduler.lineup import LineupGenerator
        from pathlib import Path
        
        generator = LineupGenerator()
        session_id = generator.generate_daily_lineup(date.today())
        
        if not session_id:
            return Div(H1("Failed to generate lineup"), P("Check logs for details"), style="color: red; padding: 2rem;")
            
        # Retrieve session details to build playlist
        with get_db() as db:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                 return Div(H1("Session not found"), style="color: red; padding: 2rem;")
                 
            playlist = []
            # Intro
            if session.intro_path and Path(session.intro_path).exists():
                playlist.append({"path": session.intro_path, "title": "Intro"})
                
            # Episodes
            for ph in session.play_history:
                playlist.append({
                    "path": ph.video.path,
                    "title": f"{ph.video.series} - {ph.video.title}"
                })
                
            # Outro
            if session.outro_path and Path(session.outro_path).exists():
                playlist.append({"path": session.outro_path, "title": "Outro"})
                
            state.start_session(session.id, playlist)
            
        from alma_tv.web.app import _get_view_for_state
        return _get_view_for_state()

    @rt("/request")
    def show_request():
        """Show the request interface for kids."""
        from alma_tv.web.components.request import RequestView
        return RequestView()

    @rt("/request/counter")
    def request_counter():
        """Dynamic counter display."""
        from alma_tv.web.components.request import SHOW_MAP
        import json
        settings = get_settings()
        max_shows = settings.nr_shows_per_night
        
        # This will be called via HTMX, we return just the counter display
        return Script("""
        setTimeout(() => {
            let total = Object.values(window.showCounts || {}).reduce((a, b) => a + b, 0);
            let maxShows = %d;
            let elem = document.getElementById('counter-display');
            if (elem) {
                elem.innerHTML = total + ' of ' + maxShows + ' shows picked';
                elem.style.color = (total >= maxShows) ? '#38a169' : '#4285F4';
            }
        }, 100);
        """ % max_shows)

    @rt("/request/save")
    def save_request():
        """Save the show request to the database."""
        from datetime import datetime, timedelta, date
        from alma_tv.database.models import Request as RequestModel
        
        # Get counts from the client-side JavaScript (we'll use a hidden form approach)
        # For now, let's use a simpler approach with cookies or we extract from the page state
        # Actually, we need to send the data from client. Let me use a form approach.
        # But we're using JS state. Let me add an endpoint that accepts JSON.
        
        # For simplicity, let's have the JS send the data
        # Actually, HTMX can trigger with values. Let me restructure.
        
        return """
        <form hx-post="/request/submit" hx-target="body">
            <input type="hidden" name="requests" id="requests-data" />
            <script>
                // Populate the hidden field with current counts
                let counts = window.showCounts || {};
                let requestsArray = [];
                for (let [show, count] of Object.entries(counts)) {
                    if (count > 0) {
                        requestsArray.push({series: show, count: count});
                    }
                }
                document.getElementById('requests-data').value = JSON.stringify(requestsArray);
                // Auto-submit
                document.querySelector('form').requestSubmit();
            </script>
        </form>
        """

    @rt("/request/submit")
    def submit_request(requests: str):
        """Handle the request submission."""
        import json
        from datetime import datetime, timedelta
        from alma_tv.database.models import Request as RequestModel
        from alma_tv.web.components.request import RequestView
        
        try:
            requests_data = json.loads(requests)
            
            if not requests_data:
                return RequestView()  # No shows selected
            
            # Create request payload
            payload = {"requests": requests_data}
            
            # Save to database
            with get_db() as db:
                # Check if there's already a request for tomorrow
                tomorrow = datetime.now() + timedelta(days=1)
                tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                
                existing = db.query(RequestModel).filter(
                    RequestModel.fulfilled == False,
                    RequestModel.request_date >= tomorrow_start
                ).first()
                
                if existing:
                    # Update existing request
                    existing.payload = payload
                    existing.request_date = datetime.now()
                else:
                    # Create new request
                    new_request = RequestModel(
                        request_date=datetime.now(),
                        payload=payload,
                        fulfilled=False
                    )
                    db.add(new_request)
                
                db.commit()
            
            return RequestView(success=True)
            
        except Exception as e:
            from alma_tv.logging.config import get_logger
            logger = get_logger(__name__)
            logger.error(f"Error saving request: {e}", exc_info=True)
            return Div(f"Error saving request: {e}", style="color: red; padding: 2rem;")

    @rt("/admin/generate")
    def admin_generate():
        """Show schedule generation interface."""
        from datetime import date, timedelta
        
        today = date.today()
        dates_options = []
        for i in range(14):  # Next 2 weeks
            d = today + timedelta(days=i)
            label = d.strftime("%A, %B %d, %Y")
            if i == 0:
                label += " (Today)"
            elif i == 1:
                label += " (Tomorrow)"
            dates_options.append((d.isoformat(), label))
        
        return _admin_page(
            "Generate Schedules",
            Div(
                H2("Plan Lineups for Future Dates", style="color: #333; margin-bottom: 1.5rem;"),
                P("Generate lineups for specific dates. If you've made show requests, they'll be used automatically!", 
                  style="color: #666; margin-bottom: 2rem;"),
                
                Form(
                    Div(
                        Label("Select Date:", style="font-weight: bold; color: #333; display: block; margin-bottom: 0.5rem;"),
                        Select(
                            *[Option(label, value=value) for value, label in dates_options],
                            name="date",
                            style="padding: 0.75rem; font-size: 1rem; border: 2px solid #e2e8f0; border-radius: 8px; width: 100%; max-width: 400px;"
                        ),
                        style="margin-bottom: 1.5rem;"
                    ),
                    Button(
                        "✨ Generate Lineup",
                        type="submit",
                        style="padding: 1rem 2rem; font-size: 1.1rem; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);",
                        onmouseover="this.style.background='#5a67d8'",
                        onmouseout="this.style.background='#667eea'"
                    ),
                    hx_post="/admin/generate/submit",
                    hx_target="#result",
                    style="background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-width: 600px;"
                ),
                
                Div(id="result", style="margin-top: 2rem;"),
                
                style="max-width: 800px;"
            )
        )

    @rt("/admin/generate/submit")
    def generate_submit(date: str, force: str = "false"):
        """Generate lineup for selected date."""
        from datetime import datetime
        from alma_tv.scheduler.lineup import LineupGenerator
        
        try:
            target_date = datetime.fromisoformat(date).date()
            
            # If force=true, delete existing session first
            if force == "true":
                with get_db() as db:
                    existing = db.query(Session).filter(
                        Session.show_date == datetime.combine(target_date, datetime.min.time())
                    ).first()
                    if existing:
                        # Delete play_history records first (they have NOT NULL constraint on session_id)
                        db.query(PlayHistory).filter(PlayHistory.session_id == existing.id).delete()
                        # Now delete the session
                        db.delete(existing)
                        db.commit()

            target_date = datetime.fromisoformat(date).date()
            
            # Check if already exists
            with get_db() as db:
                from alma_tv.database.models import SessionStatus
                from sqlalchemy.orm import joinedload
                
                existing = db.query(Session).options(
                    joinedload(Session.play_history).joinedload(PlayHistory.video)
                ).filter(
                    Session.show_date == datetime.combine(target_date, datetime.min.time())
                ).first()
                
                if existing:
                    # Show existing session details with option to regenerate
                    episode_list = [f"{ph.video.series} - {ph.video.title}" for ph in existing.play_history]
                    
                    return Div(
                        H3("⚠️ Schedule Already Exists", style="color: #d97706; margin-bottom: 1rem;"),
                        P(f"A lineup for {target_date.strftime('%A, %B %d')} already exists.", style="color: #666; margin-bottom: 0.5rem;"),
                        P(f"Session ID: {existing.id} | Status: {existing.status.value}", style="font-family: monospace; color: #999; margin-bottom: 1rem;"),
                        Details(
                            Summary("👁️ View Current Episodes", style="cursor: pointer; color: #667eea; margin-bottom: 1rem;"),
                            Ul(*[Li(ep) for ep in episode_list], style="color: #666;")
                        ),
                        Div(
                            Form(
                                Button(
                                    "🔄 Regenerate (Replace Existing)",
                                    type="submit",
                                    style="background: #dc2626; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; margin-right: 1rem;"
                                ),
                                Input(type="hidden", name="date", value=date),
                                Input(type="hidden", name="force", value="true"),
                                hx_post="/admin/generate/submit",
                                hx_target="#result"
                            ),
                            A("← Back", href="/admin/generate", style="color: #667eea; text-decoration: none; padding: 0.75rem 1.5rem;"),
                            style="margin-top: 1.5rem;"
                        ),
                        style="background: #fef3c7; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #d97706;"
                    )
            
            # Generate new lineup
            generator = LineupGenerator()
            session_id = generator.generate_daily_lineup(target_date)
            
            if not session_id:
                # Check if it's because of empty library
                with get_db() as db:
                    video_count = db.query(Video).filter(Video.disabled == False).count()
                    
                    if video_count == 0:
                        return Div(
                            H3("📺 No Videos in Library", style="color: #d97706; margin-bottom: 1rem;"),
                            P("Your media library is empty! You need to scan your videos first.", style="color: #666; margin-bottom: 1rem;"),
                            Div(
                                H4("To scan your library:", style="color: #333; margin-bottom: 0.5rem;"),
                                Pre("uv run alma library scan", style="background: #1f2937; color: #10b981; padding: 1rem; border-radius: 4px; font-family: monospace;"),
                                P("This will scan your media_root directory and add all videos to the database.", style="color: #666; font-size: 0.9rem; margin-top: 0.5rem;")
                            ),
                            style="background: #fef3c7; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #d97706;"
                        )
                
                return Div(
                    H3("❌ Generation Failed", style="color: #dc2626;"),
                    P("Could not generate lineup. Check logs for details.", style="color: #666;"),
                    P("This might be because there aren't enough videos matching the criteria.", style="color: #999; font-size: 0.9rem;"),
                    style="background: #fee2e2; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #dc2626;"
                )

            
            # Get session details to show what was generated
            with get_db() as db:
                from sqlalchemy.orm import joinedload
                session = db.query(Session).options(
                    joinedload(Session.play_history).joinedload(PlayHistory.video)
                ).filter(Session.id == session_id).first()
                
                episode_list = [f"{ph.video.series} - {ph.video.title}" for ph in session.play_history]
            
            return Div(
                H3("✅ Lineup Generated!", style="color: #059669; margin-bottom: 1rem;"),
                P(f"Scheduled for: {target_date.strftime('%A, %B %d, %Y')}", style="font-weight: bold; color: #333; margin-bottom: 0.5rem;"),
                P(f"Session ID: {session_id}", style="font-family: monospace; color: #999; margin-bottom: 1rem;"),
                Div(
                    H4("Episodes:", style="color: #333; margin-bottom: 0.5rem;"),
                    Ul(*[Li(ep) for ep in episode_list], style="color: #666;")
                ),
                Div(
                    A("View Schedule →", href="/admin/schedule", style="color: #667eea; text-decoration: none; font-weight: bold; margin-right: 1rem;"),
                    A("Generate Another", href="/admin/generate", style="color: #667eea; text-decoration: none; font-weight: bold;"),
                    style="margin-top: 1.5rem;"
                ),
                style="background: #d1fae5; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #059669;"
            )
            
        except Exception as e:
            from alma_tv.logging.config import get_logger
            logger = get_logger(__name__)
            logger.error(f"Error generating schedule: {e}", exc_info=True)
            return Div(
                H3("❌ Error", style="color: #dc2626;"),
                P(str(e), style="color: #666;"),
                style="background: #fee2e2; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #dc2626;"
            )


    # Helper components
    def _admin_card(title, items):
        return Div(
            H2(title, style="font-size: 1.2rem; color: #666; margin-bottom: 1rem; border-bottom: 2px solid #eee; padding-bottom: 0.5rem;"),
            Div(*items, style="display: flex; flex-direction: column; gap: 0.5rem;"),
            style="background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);"
        )

    def _admin_page(title, content, back_link="/admin"):
        return Div(
            Div(
                A("← Back", href=back_link, style="text-decoration: none; color: #666; margin-right: 1rem;"),
                H1(title, style="margin: 0; font-size: 1.5rem; color: #333;"),
                style="display: flex; align-items: center; margin-bottom: 2rem;"
            ),
            content,
            style="padding: 2rem; max-width: 1000px; margin: 0 auto; font-family: system-ui;"
        )

    # Styles
    return Style("""
        .btn { padding: 0.5rem 1rem; background: #3182ce; color: white; border: none; border-radius: 4px; cursor: pointer; text-align: center; text-decoration: none; }
        .btn:hover { background: #2c5282; }
        .btn-link { padding: 0.5rem 1rem; background: #edf2f7; color: #2d3748; border-radius: 4px; text-decoration: none; display: block; }
        .btn-link:hover { background: #e2e8f0; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f7fafc; font-weight: 600; color: #4a5568; }
    """)
