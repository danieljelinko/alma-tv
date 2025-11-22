#!/usr/bin/env python
"""Generate component-specific test notebooks."""

import nbformat as nbf
from pathlib import Path

def create_config_notebook():
    """Create notebook for configuration testing."""
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Configuration Testing\n\nTest and demonstrate the configuration system."),
        nbf.v4.new_code_cell("%load_ext autoreload\n%autoreload 2"),
        nbf.v4.new_code_cell("from alma_tv.config import get_settings"),
        
        nbf.v4.new_markdown_cell("## Load Settings"),
        nbf.v4.new_code_cell("""settings = get_settings()
print(f"Media Root: {settings.media_root}")
print(f"Database Path: {settings.database_path}")
print(f"Repeat Cooldown Days: {settings.repeat_cooldown_days}")
print(f"Keyword Map: {settings.keyword_map}")
"""),
        
        nbf.v4.new_markdown_cell("## Environment Variables Override"),
        nbf.v4.new_code_cell("""import os
# Demonstrate that env vars can override config.yaml
os.environ['ALMA_REPEAT_COOLDOWN_DAYS'] = '7'

# Reload settings (in practice, restart the app)
from importlib import reload
import alma_tv.config.settings as settings_module
reload(settings_module)
new_settings = settings_module.get_settings()
print(f"Cooldown after env override: {new_settings.repeat_cooldown_days}")
"""),
    ]
    return nb

def create_library_scanner_notebook():
    """Create notebook for scanner testing."""
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Library Scanner Testing\n\nTest the media scanner with realistic file structures."),
        nbf.v4.new_code_cell("%load_ext autoreload\n%autoreload 2"),
        nbf.v4.new_code_cell("""import shutil
from pathlib import Path
from unittest.mock import patch

from alma_tv.library.scanner import Scanner
from alma_tv.database import get_db, Video, init_db
"""),
        
        nbf.v4.new_markdown_cell("## Setup Test Media Directory"),
        nbf.v4.new_code_cell("""# Create temp directory
temp_media = Path("temp_test_media")
if temp_media.exists():
    shutil.rmtree(temp_media)
temp_media.mkdir()

# Create realistic file structure
(temp_media / "Bluey").mkdir()
(temp_media / "Bluey" / "Bluey_S01E01_MagicXylophone.mp4").touch()
(temp_media / "Bluey" / "Bluey_S01E02_Hospital.mp4").touch()
(temp_media / "Bluey" / "Bluey_S02E01_DanceMode.mp4").touch()

(temp_media / "Peppa_Pig").mkdir()
(temp_media / "Peppa_Pig" / "PeppaPig_S01E01_MuddyPuddles.mp4").touch()
(temp_media / "Peppa_Pig" / "PeppaPig_S01E02_MrDinosaurIsLost.mp4").touch()

print(f"Created test media in: {temp_media.absolute()}")
"""),
        
        nbf.v4.new_markdown_cell("## Scan Directory"),
        nbf.v4.new_code_cell("""scanner = Scanner(media_root=temp_media)

# Mock ffprobe to avoid dependency on actual media files
with patch.object(scanner, 'get_duration', return_value=420):
    summary = scanner.scan_directory()

print(f"Scan Summary: {summary}")
"""),
        
        nbf.v4.new_markdown_cell("## Verify Database"),
        nbf.v4.new_code_cell("""with get_db() as db:
    videos = db.query(Video).all()
    print(f"Total videos in DB: {len(videos)}")
    for v in videos:
        print(f"  {v.series} {v.episode_code} - {v.duration_seconds}s")
"""),
        
        nbf.v4.new_markdown_cell("## Test Incremental Scan"),
        nbf.v4.new_code_cell("""# Add a new file
(temp_media / "Bluey" / "Bluey_S02E02_Hammerbarn.mp4").touch()

# Rescan
with patch.object(scanner, 'get_duration', return_value=430):
    summary = scanner.scan_directory()

print(f"Incremental Scan: {summary}")
"""),
        
        nbf.v4.new_markdown_cell("## Cleanup"),
        nbf.v4.new_code_cell("# shutil.rmtree(temp_media)"),
    ]
    return nb

def create_library_service_notebook():
    """Create notebook for library service testing."""
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Library Service Testing\n\nTest query and selection APIs."),
        nbf.v4.new_code_cell("%load_ext autoreload\n%autoreload 2"),
        nbf.v4.new_code_cell("""from alma_tv.library.service import LibraryService
from alma_tv.database import get_db, Video
from unittest.mock import patch
from pathlib import Path
import shutil

# Setup test data
from alma_tv.library.scanner import Scanner
temp_media = Path("temp_test_media")
if not temp_media.exists():
    temp_media.mkdir()
    (temp_media / "Bluey").mkdir()
    for i in range(1, 6):
        (temp_media / "Bluey" / f"Bluey_S01E{i:02d}_Episode{i}.mp4").touch()
    
    scanner = Scanner(media_root=temp_media)
    with patch.object(scanner, 'get_duration', return_value=420):
        scanner.scan_directory()
"""),
        
        nbf.v4.new_markdown_cell("## List Series"),
        nbf.v4.new_code_cell("""service = LibraryService()
series = service.list_series()
for s in series:
    print(f"{s['series']}: {s['episode_count']} episodes, {s['total_duration_seconds']}s total")
"""),
        
        nbf.v4.new_markdown_cell("## List Episodes"),
        nbf.v4.new_code_cell("""episodes = service.list_episodes(series="Bluey")
print(f"Bluey episodes: {len(episodes)}")
for ep in episodes[:3]:
    print(f"  {ep.episode_code}: {ep.path}")
"""),
        
        nbf.v4.new_markdown_cell("## Random Selection"),
        nbf.v4.new_code_cell("""random_ep = service.random_episode(series="Bluey")
if random_ep:
    print(f"Random selection: {random_ep.series} {random_ep.episode_code}")
"""),
        
        nbf.v4.new_markdown_cell("## Series Stats (Cached)"),
        nbf.v4.new_code_cell("""stats = service.get_series_stats("Bluey")
print(f"Stats: {stats}")
"""),
    ]
    return nb

def create_scheduler_parser_notebook():
    """Create notebook for request parser testing."""
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Request Parser Testing\n\nTest natural language request parsing."),
        nbf.v4.new_code_cell("%load_ext autoreload\n%autoreload 2"),
        nbf.v4.new_code_cell("from alma_tv.scheduler.parser import RequestParser"),
        
        nbf.v4.new_markdown_cell("## Basic Parsing"),
        nbf.v4.new_code_cell("""parser = RequestParser()

# Test various inputs
test_inputs = [
    "one blueie",
    "tomorrow two blueie",
    "today one blueie and two throw throw",
    "3 peppa",
]

for text in test_inputs:
    offset, requests = parser.parse(text)
    print(f"Input: '{text}'")
    print(f"  Offset: {offset} days")
    print(f"  Requests: {requests}")
    print()
"""),
        
        nbf.v4.new_markdown_cell("## Keyword Mapping"),
        nbf.v4.new_code_cell("""# Check config for keyword mappings
from alma_tv.config import get_settings
settings = get_settings()
print("Configured keyword mappings:")
for keyword, series in settings.keyword_map.items():
    print(f"  '{keyword}' -> '{series}'")
"""),
        
        nbf.v4.new_markdown_cell("## Fuzzy Matching"),
        nbf.v4.new_code_cell("""# Test fuzzy matching for series not in keyword map
offset, requests = parser.parse("one peppa")
print(f"Fuzzy match result: {requests}")
"""),
    ]
    return nb

def create_scheduler_lineup_notebook():
    """Create notebook for lineup generation testing."""
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell("# Lineup Generator Testing\n\nTest schedule generation with requests."),
        nbf.v4.new_code_cell("%load_ext autoreload\n%autoreload 2"),
        nbf.v4.new_code_cell("""from datetime import date, timedelta
from alma_tv.scheduler.lineup import LineupGenerator
from alma_tv.scheduler.parser import RequestParser
from alma_tv.database import get_db, Session
from unittest.mock import patch
from pathlib import Path
import shutil

# Ensure we have test data
from alma_tv.library.scanner import Scanner
temp_media = Path("temp_test_media")
if not temp_media.exists():
    temp_media.mkdir()
    (temp_media / "Bluey").mkdir()
    for i in range(1, 6):
        (temp_media / "Bluey" / f"Bluey_S01E{i:02d}_Episode{i}.mp4").touch()
    (temp_media / "Peppa_Pig").mkdir()
    for i in range(1, 4):
        (temp_media / "Peppa_Pig" / f"PeppaPig_S01E{i:02d}_Episode{i}.mp4").touch()
    
    scanner = Scanner(media_root=temp_media)
    with patch.object(scanner, 'get_duration', return_value=420):
        scanner.scan_directory()
"""),
        
        nbf.v4.new_markdown_cell("## Parse Request"),
        nbf.v4.new_code_cell("""parser = RequestParser()
text = "tomorrow one blueie"
offset, requests = parser.parse(text)
print(f"Parsed request: {requests}")
print(f"Target date offset: {offset} days")
"""),
        
        nbf.v4.new_markdown_cell("## Generate Lineup"),
        nbf.v4.new_code_cell("""generator = LineupGenerator(seed=42)
target_date = date.today() + timedelta(days=offset)

session_id = generator.generate_lineup(
    target_date=target_date,
    request_payload={"requests": requests}
)

print(f"Generated Session ID: {session_id}")
"""),
        
        nbf.v4.new_markdown_cell("## Inspect Generated Lineup"),
        nbf.v4.new_code_cell("""if session_id:
    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id).first()
        print(f"Session for {session.show_date}")
        print(f"Status: {session.status}")
        print(f"Total duration: {session.total_duration_seconds}s")
        print("\\nLineup:")
        for ph in session.play_history:
            print(f"  {ph.slot_order}. {ph.video.series} {ph.video.episode_code}")
"""),
        
        nbf.v4.new_markdown_cell("## Test Without Request"),
        nbf.v4.new_code_cell("""# Generate a lineup without specific requests
session_id_auto = generator.generate_lineup(
    target_date=date.today() + timedelta(days=2),
    min_episodes=3,
    max_episodes=5
)

if session_id_auto:
    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id_auto).first()
        print(f"\\nAuto-generated lineup for {session.show_date}:")
        for ph in session.play_history:
            print(f"  {ph.slot_order}. {ph.video.series} {ph.video.episode_code}")
"""),
    ]
    return nb

# Generate all notebooks
notebooks = {
    "nbs/config.ipynb": create_config_notebook(),
    "nbs/library_scanner.ipynb": create_library_scanner_notebook(),
    "nbs/library_service.ipynb": create_library_service_notebook(),
    "nbs/scheduler_parser.ipynb": create_scheduler_parser_notebook(),
    "nbs/scheduler_lineup.ipynb": create_scheduler_lineup_notebook(),
}

for path, nb in notebooks.items():
    with open(path, 'w') as f:
        nbf.write(nb, f)
    print(f"Created {path}")

print("\nAll component notebooks created successfully!")
