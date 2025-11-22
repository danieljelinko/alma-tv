#!/usr/bin/env python
"""Generate component-specific test notebooks including weights."""

import nbformat as nbf
from pathlib import Path

# ... (keeping existing notebook creation functions)

def create_weights_notebook():
    """Create notebook for weight calculation demonstration."""
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Weight Calculation System\n\nDemonstrate how video selection weights are calculated."),
        nbf.v4.new_code_cell("%load_ext autoreload\n%autoreload 2"),
        nbf.v4.new_code_cell("""from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from unittest.mock import patch

from alma_tv.database import get_db, Video, Session, PlayHistory, Feedback, SessionStatus, Rating
from alma_tv.scheduler.weights import WeightCalculator
from alma_tv.library.scanner import Scanner
"""),
        
        nbf.v4.new_markdown_cell("## Setup: Create Sample Videos"),
        nbf.v4.new_code_cell("""temp_media = Path("temp_weights_demo")
if temp_media.exists():
    shutil.rmtree(temp_media)
temp_media.mkdir()

(temp_media / "Bluey_S01E01.mp4").touch()
(temp_media / "Bluey_S01E02.mp4").touch()
(temp_media / "PeppaPig_S01E01.mp4").touch()

scanner = Scanner(media_root=temp_media)
with patch.object(scanner, 'get_duration', return_value=420):
    summary = scanner.scan_directory()
print(f"Created {summary['added']} videos")
"""),
        
        nbf.v4.new_markdown_cell("## Baseline Weights"),
        nbf.v4.new_code_cell("""calc = WeightCalculator()
with get_db() as db:
    videos = db.query(Video).all()
    
print("Baseline weights:")
for video in videos:
    weight = calc.calculate_weight(video.id)
    print(f"  {video.series} {video.episode_code}: {weight:.2f}")
"""),
        
        nbf.v4.new_markdown_cell("## Add Liked Feedback"),
        nbf.v4.new_code_cell("""with get_db() as db:
    session = Session(show_date=datetime.now(timezone.utc), status=SessionStatus.COMPLETED)
    db.add(session)
    db.flush()
    
    play = PlayHistory(
        session_id=session.id, video_id=1, slot_order=1,
        started_at=datetime.now(timezone.utc), ended_at=datetime.now(timezone.utc), completed=True
    )
    db.add(play)
    db.flush()
    
    feedback = Feedback(play_history_id=play.id, rating=Rating.LIKED, submitted_at=datetime.now(timezone.utc))
    db.add(feedback)
    db.commit()

weight = calc.calculate_weight(1)
print(f"After liking: Bluey S01E01 = {weight:.2f} (was 1.0)")
"""),
        
        nbf.v4.new_markdown_cell("## Mark as Never Again"),
        nbf.v4.new_code_cell("""with get_db() as db:
    session = db.query(Session).first()
    play = PlayHistory(
        session_id=session.id, video_id=3, slot_order=2,
        started_at=datetime.now(timezone.utc), ended_at=datetime.now(timezone.utc), completed=True
    )
    db.add(play)
    db.flush()
    
    feedback = Feedback(play_history_id=play.id, rating=Rating.NEVER, submitted_at=datetime.now(timezone.utc))
    db.add(feedback)
    db.commit()

weight = calc.calculate_weight(3)
print(f"Never again: Peppa Pig = {weight:.2f} (excluded)")
"""),
        
        nbf.v4.new_markdown_cell("## Weight Distribution"),
        nbf.v4.new_code_cell("""with get_db() as db:
    video_ids = [v.id for v in db.query(Video).all()]

stats = calc.get_weight_distribution(video_ids)
print("Distribution:", {k: f"{v:.3f}" for k, v in stats.items()})
"""),
    ]
    return nb

# Update the notebooks dict to include weights
notebooks = {
    # ... existing notebooks ...
    "nbs/scheduler_weights.ipynb": create_weights_notebook(),
}

# Generate (same as before)
for path, nb in notebooks.items():
    with open(path, 'w') as f:
        nbf.write(nb, f)
    print(f"Created {path}")
