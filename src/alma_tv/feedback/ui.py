"""Child-friendly feedback UI using Flask."""

from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

from alma_tv.config import get_settings
from alma_tv.database import Session, get_db, init_db
from alma_tv.feedback.api import FeedbackService
from alma_tv.logging.config import get_logger

logger = get_logger(__name__)


# Simple HTML template with large buttons
FEEDBACK_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alma TV Feedback</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            font-size: 3em;
            margin-bottom: 40px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .episode-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }
        .episode-title {
            font-size: 2em;
            margin-bottom: 20px;
        }
        .feedback-buttons {
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .feedback-btn {
            flex: 1;
            min-width: 200px;
            padding: 40px 20px;
            font-size: 1.8em;
            border: none;
            border-radius: 15px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: bold;
        }
        .feedback-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }
        .feedback-btn:active {
            transform: scale(0.95);
        }
        .btn-liked {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-okay {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        .btn-never {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            color: white;
        }
        .btn-selected {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .done-message {
            text-align: center;
            font-size: 3em;
            margin-top: 100px;
            animation: bounce 1s;
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }
        .submit-btn {
            display: block;
            margin: 50px auto;
            padding: 30px 80px;
            font-size: 2em;
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            border: none;
            border-radius: 15px;
            cursor: pointer;
            font-weight: bold;
        }
        .submit-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>How did you like the episodes?</h1>

        {% if done %}
        <div class="done-message">
            🎉 Thank you! 🎉
        </div>
        {% else %}
        <form id="feedbackForm" method="POST" action="/submit">
            {% for episode in episodes %}
            <div class="episode-card">
                <div class="episode-title">
                    {{ episode.series }} - {{ episode.episode_code }}
                    {% if episode.title %}
                        <br><small style="font-size: 0.7em;">{{ episode.title }}</small>
                    {% endif %}
                </div>
                <div class="feedback-buttons">
                    <button type="button" class="feedback-btn btn-liked"
                            onclick="selectFeedback({{ episode.slot_order }}, 'liked', this)">
                        😍 Loved It!
                    </button>
                    <button type="button" class="feedback-btn btn-okay"
                            onclick="selectFeedback({{ episode.slot_order }}, 'okay', this)">
                        😊 It Was Okay
                    </button>
                    <button type="button" class="feedback-btn btn-never"
                            onclick="selectFeedback({{ episode.slot_order }}, 'never', this)">
                        😢 Never Again
                    </button>
                </div>
                <input type="hidden" name="rating_{{ episode.slot_order }}" id="rating_{{ episode.slot_order }}">
            </div>
            {% endfor %}

            <button type="submit" class="submit-btn">Submit Feedback</button>
        </form>
        {% endif %}
    </div>

    <script>
        let ratings = {};

        function selectFeedback(slot, rating, button) {
            ratings[slot] = rating;
            document.getElementById('rating_' + slot).value = rating;

            // Visual feedback
            const buttons = button.parentElement.querySelectorAll('.feedback-btn');
            buttons.forEach(btn => {
                btn.classList.remove('btn-selected');
            });
            button.classList.add('btn-selected');
        }

        document.getElementById('feedbackForm').addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const data = {};

            for (let [key, value] of formData.entries()) {
                if (key.startsWith('rating_') && value) {
                    const slot = key.replace('rating_', '');
                    data[slot] = value;
                }
            }

            fetch('/submit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    window.location.reload();
                }
            });
        });

        // Auto-timeout after 2 minutes
        setTimeout(function() {
            if (!document.querySelector('.done-message')) {
                alert('Time\'s up! Marking remaining as okay...');
                document.getElementById('feedbackForm').submit();
            }
        }, {{ timeout_ms }});
    </script>
</body>
</html>
"""


def create_feedback_app() -> Flask:
    """Create Flask app for feedback UI."""
    app = Flask(__name__)
    settings = get_settings()
    feedback_service = FeedbackService()

    init_db()

    @app.route("/")
    def index():
        """Show feedback form for latest session."""
        # Get today's session
        from datetime import date

        today = date.today()

        with get_db() as db:
            session = (
                db.query(Session)
                .filter(Session.show_date == datetime.combine(today, datetime.min.time()))
                .first()
            )

            if not session:
                return "No session found for today", 404

            # Check if feedback already submitted
            feedback_data = feedback_service.get_session_feedback(session.id)
            all_submitted = all(f["has_feedback"] for f in feedback_data.values())

            if all_submitted:
                return render_template_string(FEEDBACK_TEMPLATE, done=True, episodes=[])

            # Prepare episode data
            episodes = []
            for slot_order, data in sorted(feedback_data.items()):
                episodes.append({
                    "slot_order": slot_order,
                    "series": data["series"],
                    "episode_code": data["episode_code"],
                    "title": "",  # Title not in data dict
                })

            return render_template_string(
                FEEDBACK_TEMPLATE,
                done=False,
                episodes=episodes,
                timeout_ms=settings.feedback_timeout * 1000,
            )

    @app.route("/submit", methods=["POST"])
    def submit():
        """Handle feedback submission."""
        from datetime import date

        today = date.today()
        data = request.json or {}

        with get_db() as db:
            session = (
                db.query(Session)
                .filter(Session.show_date == datetime.combine(today, datetime.min.time()))
                .first()
            )

            if not session:
                return jsonify({"success": False, "error": "Session not found"}), 404

            # Submit ratings
            ratings = {int(k): v for k, v in data.items()}
            results = feedback_service.submit_session_feedback(session.id, ratings)

            # Mark remaining as okay (timeout)
            feedback_service.mark_as_okay_timeout(session.id)

            return jsonify({"success": True, "results": results})

    return app


def run_feedback_ui(port: Optional[int] = None, debug: bool = False) -> None:
    """
    Run feedback UI server.

    Args:
        port: Port to run on (defaults to config)
        debug: Enable Flask debug mode
    """
    settings = get_settings()
    port = port or settings.feedback_port

    app = create_feedback_app()

    logger.info(f"Starting feedback UI on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
