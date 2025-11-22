import nbformat as nbf

nb = nbf.v4.new_notebook()

nb.cells = [
    nbf.v4.new_markdown_cell("# Alma TV Manual Test Notebook\n\nUse this notebook to manually verify the functionality of the Alma TV system."),
    
    nbf.v4.new_code_cell("""%load_ext autoreload
%autoreload 2

import shutil
from pathlib import Path
from datetime import date, timedelta

from alma_tv.config import get_settings
from alma_tv.library.scanner import Scanner
from alma_tv.library.service import LibraryService
from alma_tv.scheduler.parser import RequestParser
from alma_tv.scheduler.lineup import LineupGenerator
from alma_tv.database import init_db, get_db, Video
"""),

    nbf.v4.new_markdown_cell("## 1. Configuration\nCheck if settings are loaded correctly."),
    nbf.v4.new_code_cell("""settings = get_settings()
print(f"Media Root: {settings.media_root}")
print(f"Keyword Map: {settings.keyword_map}")
"""),

    nbf.v4.new_markdown_cell("## 2. Setup Dummy Media\nCreate some dummy files to scan."),
    nbf.v4.new_code_cell("""# Create a temp directory for testing
temp_media = Path("temp_media_test")
if temp_media.exists():
    shutil.rmtree(temp_media)
temp_media.mkdir()

# Create some files
(temp_media / "Bluey_S01E01_MagicXylophone.mp4").touch()
(temp_media / "Bluey_S01E02_Hospital.mp4").touch()
(temp_media / "PeppaPig_S01E01_MuddyPuddles.mp4").touch()

print(f"Created temp media in {temp_media.absolute()}")
"""),

    nbf.v4.new_markdown_cell("## 3. Library Scanner\nScan the dummy directory and populate the database."),
    nbf.v4.new_code_cell("""# Initialize scanner with temp root
scanner = Scanner(media_root=temp_media)

# Mock duration extraction since files are empty
import unittest.mock
with unittest.mock.patch("alma_tv.library.scanner.Scanner.get_duration", return_value=420):
    summary = scanner.scan_directory()

print("Scan Summary:", summary)
"""),

    nbf.v4.new_markdown_cell("## 4. Library Service\nQuery the library for series and episodes."),
    nbf.v4.new_code_cell("""service = LibraryService()
series = service.list_series()
print("Series Stats:", series)

episodes = service.list_episodes(series="Bluey")
print(f"Bluey Episodes: {len(episodes)}")
for ep in episodes:
    print(f"- {ep.series} {ep.episode_code}: {ep.path}")
"""),

    nbf.v4.new_markdown_cell("## 5. Request Parsing\nTest natural language request parsing."),
    nbf.v4.new_code_cell("""parser = RequestParser()
text = "tomorrow one blueie"
offset, requests = parser.parse(text)

print(f"Input: '{text}'")
print(f"Offset: {offset} (days)")
print(f"Requests: {requests}")
"""),

    nbf.v4.new_markdown_cell("## 6. Lineup Generation\nGenerate a schedule based on the request."),
    nbf.v4.new_code_cell("""generator = LineupGenerator()

target_date = date.today() + timedelta(days=offset)
print(f"Generating lineup for: {target_date}")

session_id = generator.generate_lineup(
    target_date=target_date,
    request_payload={"requests": requests}
)

print(f"Generated Session ID: {session_id}")

if session_id:
    from alma_tv.database import Session
    with get_db() as db:
        session = db.query(Session).filter(Session.id == session_id).first()
        print(f"Session Status: {session.status}")
        print("Lineup:")
        for ph in session.play_history:
            print(f"  {ph.slot_order}. {ph.video.series} - {ph.video.episode_code}")
"""),

    nbf.v4.new_markdown_cell("## 7. Cleanup\nRemove temporary files."),
    nbf.v4.new_code_cell("""# shutil.rmtree(temp_media)
print("Cleanup skipped for manual inspection. Run 'shutil.rmtree(temp_media)' to clean up.")
""")
]

with open('nbs/manual_test.ipynb', 'w') as f:
    nbf.write(nb, f)

print("Created nbs/manual_test.ipynb")
