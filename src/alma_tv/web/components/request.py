"""Show Request component for kids to pick tomorrow's shows."""

from fasthtml.common import *
from alma_tv.config import get_settings
from alma_tv.database import get_db, Request
from datetime import datetime, timedelta

# Map of available shows with emoji icons
SHOW_MAP = {
    "Bluey": {"emoji": "🐶", "color": "#4285F4"},
    "Peppa Pig": {"emoji": "🐷", "color": "#FF69B4"},
    "Trotro": {"emoji": "🐴", "color": "#FF8C00"},
}

def RequestView(success=False):
    """Render the show request interface."""
    settings = get_settings()
    max_shows = settings.nr_shows_per_night
    
    if success:
        return _success_view()
    
    # Get current request if any
    current_request = _get_current_request()
    
    return Div(
        # Title
        H1("🌟 Pick Tomorrow's Shows! 🌟", 
           style="color: #333; text-align: center; margin-bottom: 2rem; font-size: 3rem; text-shadow: 2px 2px 0px rgba(0,0,0,0.1);"),
        
        # Instructions
        Div(
            P(f"Choose up to {max_shows} shows!", 
              style="font-size: 1.5rem; color: #666; margin: 0;"),
            Div(id="counter-display", 
                style="font-size: 2rem; font-weight: bold; color: #4285F4; margin-top: 0.5rem;",
                **{"hx-get": "/request/counter", "hx-trigger": "load, counter-changed from:body", "hx-swap": "innerHTML"}
            ),
            style="text-align: center; margin-bottom: 3rem; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"
        ),
        
        # Show selection grid
        Div(
            *[_show_card(show_name, show_info, current_request.get(show_name, 0) if current_request else 0) 
              for show_name, show_info in SHOW_MAP.items()],
            style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 2rem; margin-bottom: 3rem;"
        ),
        
        # Save button
        Div(
            Button(
                "💾 Save My Request!",
                hx_post="/request/save",
                hx_target="body",
                style="font-size: 2rem; padding: 1.5rem 3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 50px; cursor: pointer; box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4); transition: transform 0.2s;",
                onmouseover="this.style.transform='scale(1.05)'",
                onmouseout="this.style.transform='scale(1)'"
            ),
            style="text-align: center;"
        ),
        
        # Hidden state to track counts
        Script("""
            window.showCounts = {%s};
            
            function updateCounter() {
                let total = Object.values(window.showCounts).reduce((a, b) => a + b, 0);
                htmx.trigger('body', 'counter-changed', {detail: total});
            }
            
            function changeCount(show, delta) {
                let maxShows = %d;
                let current = window.showCounts[show] || 0;
                let total = Object.values(window.showCounts).reduce((a, b) => a + b, 0);
                
                // Check if we can increment
                if (delta > 0 && total >= maxShows) return;
                if (delta < 0 && current <= 0) return;
                
                window.showCounts[show] = Math.max(0, current + delta);
                
                // Update display
                document.getElementById('count-' + show).innerText = window.showCounts[show];
                updateCounter();
            }
        """ % (
            ", ".join([f'"{show}": {current_request.get(show, 0) if current_request else 0}' for show in SHOW_MAP.keys()]),
            max_shows
        )),
        
        style="padding: 2rem; max-width: 1200px; margin: 0 auto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; font-family: system-ui;"
    )

def _show_card(show_name, show_info, initial_count=0):
    """Render a show selection card with +/- buttons."""
    return Div(
        # Show icon and name
        Div(
            Div(show_info["emoji"], style="font-size: 5rem; margin-bottom: 1rem;"),
            H2(show_name, style="margin: 0; color: #333; font-size: 1.5rem;"),
            style="text-align: center; margin-bottom: 1.5rem;"
        ),
        
        # Counter controls
        Div(
            Button(
                "-",
                onclick=f"changeCount('{show_name}', -1)",
                style=f"font-size: 2.5rem; width: 60px; height: 60px; border-radius: 50%; border: none; background: {show_info['color']}; color: white; cursor: pointer; box-shadow: 0 4px 8px rgba(0,0,0,0.2); transition: transform 0.1s;",
                onmousedown="this.style.transform='scale(0.95)'",
                onmouseup="this.style.transform='scale(1)'"
            ),
            Div(
                Span(str(initial_count), id=f"count-{show_name}", style="font-size: 3rem; font-weight: bold; color: #333;"),
                style="min-width: 80px; display: flex; align-items: center; justify-content: center;"
            ),
            Button(
                "+",
                onclick=f"changeCount('{show_name}', 1)",
                style=f"font-size: 2.5rem; width: 60px; height: 60px; border-radius: 50%; border: none; background: {show_info['color']}; color: white; cursor: pointer; box-shadow: 0 4px 8px rgba(0,0,0,0.2); transition: transform 0.1s;",
                onmousedown="this.style.transform='scale(0.95)'",
                onmouseup="this.style.transform='scale(1)'"
            ),
            style="display: flex; align-items: center; justify-content: center; gap: 1rem;"
        ),
        
        style=f"background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.15); border-top: 8px solid {show_info['color']};"
    )

def _success_view():
    """Show success message after saving."""
    return Div(
        Div(
            H1("🎉 Request Saved! 🎉", style="color: white; font-size: 4rem; margin-bottom: 1rem; text-shadow: 3px 3px 0px rgba(0,0,0,0.2);"),
            P("Your shows are ready for tomorrow!", style="font-size: 2rem; color: rgba(255,255,255,0.9); margin-bottom: 2rem;"),
            A(
                "← Back to Admin",
                href="/admin",
                style="font-size: 1.5rem; padding: 1rem 2rem; background: white; color: #667eea; text-decoration: none; border-radius: 10px; display: inline-block; font-weight: bold;"
            ),
            style="text-align: center; padding: 4rem; background: rgba(255,255,255,0.1); border-radius: 30px; backdrop-filter: blur(10px);"
        ),
        style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem;"
    )

def _get_current_request():
    """Get the current pending request for tomorrow."""
    try:
        with get_db() as db:
            tomorrow = datetime.now() + timedelta(days=1)
            tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Look for unfulfilled request
            req = db.query(Request).filter(
                Request.fulfilled == False,
                Request.request_date >= tomorrow_start
            ).order_by(Request.request_date.desc()).first()
            
            if req and req.payload and "requests" in req.payload:
                # Convert to show_name: count dict
                result = {}
                for r in req.payload["requests"]:
                    result[r["series"]] = r["count"]
                return result
    except Exception:
        pass
    
    return {}
