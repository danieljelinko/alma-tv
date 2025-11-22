#!/usr/bin/env python3
"""
Automated End-to-End Verification Script for Alma TV.

This script verifies the full system lifecycle:
1. Scheduling: Generates a schedule.
2. Playback: Verifies the player starts the correct video (using a mock player).
3. Feedback: Verifies the UI is serving and accepts feedback.

It runs in a temporary environment to avoid affecting the user's real data.
"""

import os
import sys
import time
import shutil
import signal
import subprocess
import tempfile
import sqlite3
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def log(msg, color=None):
    if color:
        print(f"{color}{msg}{RESET}")
    else:
        print(msg)

def main():
    # 1. Setup Temporary Environment
    log("--- Setting up E2E Environment ---", GREEN)
    temp_dir = Path(tempfile.mkdtemp(prefix="alma_e2e_"))
    log(f"Temp dir: {temp_dir}")

    media_root = temp_dir / "media"
    media_root.mkdir()
    
    db_path = temp_dir / "alma.db"
    log_file = temp_dir / "alma.log"
    vlc_log = temp_dir / "vlc.log"

    # Create dummy media files
    # Filenames must match regex: Series_SxxEyy_Title.mp4
    (media_root / "intro.mp4").touch()
    (media_root / "outro.mp4").touch()
    
    series_dir = media_root / "Test_Series" / "Season_1"
    series_dir.mkdir(parents=True)
    episode_path = series_dir / "Test_Series_S01E01_Test_Episode.mp4"
    episode_path.touch()

    # Create Mock VLC
    # This script replaces the real vlc. It logs its arguments to vlc_log and sleeps.
    bin_dir = temp_dir / "bin"
    bin_dir.mkdir()
    
    mock_vlc_path = bin_dir / "vlc"
    mock_vlc_path.write_text(f"""#!/bin/sh
echo "$(date) - VLC started with args: $@" >> {vlc_log}
# Simulate playback duration
sleep 5
""")
    mock_vlc_path.chmod(0o755)

    # Create Mock ffprobe
    # Returns a fixed duration of 600 seconds
    mock_ffprobe_path = bin_dir / "ffprobe"
    mock_ffprobe_path.write_text("""#!/bin/sh
echo "600.0"
""")
    mock_ffprobe_path.chmod(0o755)

    # Setup Environment Variables
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["ALMA_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALMA_LOG_FILE"] = str(log_file)
    env["ALMA_MEDIA_ROOT"] = str(media_root)
    env["ALMA_FEEDBACK_PORT"] = "18080" # Use non-default port
    
    # Set start time to now to trigger daemon playback
    env["ALMA_START_TIME"] = datetime.now().strftime("%H:%M")
    
    # We need to override settings to point to our media
    # Since settings are loaded from config.yaml or env, we can use env vars if supported
    # or we rely on the fact that we are passing ALMA_MEDIA_ROOT (if supported by Settings)
    # Checking Settings model... it uses env vars with prefix ALMA_.
    
    processes = []

    try:
        # 2. Generate Schedule
        log("\n--- Generating Schedule ---", GREEN)
        # We need to scan first to populate DB
        subprocess.run(["uv", "run", "alma", "library", "scan"], env=env, check=True)
        
        # Generate schedule for NOW
        # Note: --force is not a valid option, checking help output...
        # If no schedule exists, it generates one. If one exists, we might need to delete it or just run.
        # Let's try without flags first.
        subprocess.run(["uv", "run", "alma", "schedule", "generate"], env=env, check=True)

        # 3. Start UI Daemon
        log("\n--- Starting UI Daemon ---", GREEN)
        feedback_proc = subprocess.Popen(
            ["uv", "run", "alma", "feedback", "ui"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(feedback_proc)
        log(f"Feedback UI started (PID {feedback_proc.pid})")

        # 4. Run Playback (Synchronously)
        log("\n--- Running Playback ---", GREEN)
        # Use 'run' command to play immediately without waiting for schedule
        subprocess.run(["uv", "run", "alma", "playback", "run"], env=env, check=True)
        
        # 5. Verify Playback
        log("\n--- Verifying Playback ---", GREEN)
        if vlc_log.exists() and vlc_log.stat().st_size > 0:
            content = vlc_log.read_text()
            if str(episode_path) in content:
                log("✅ VLC started with correct episode file", GREEN)
            else:
                log(f"❌ VLC log does not contain episode path: {content}", RED)
                raise Exception("Playback verification failed")
        else:
            log("❌ VLC log not found or empty", RED)
            raise Exception("Playback verification failed")

        # 6. Verify Feedback UI
        log("\n--- Verifying Feedback UI ---", GREEN)
        
        # Retry loop for UI connection
        ui_url = "http://localhost:18080"
        ui_connected = False
        for i in range(10):
            try:
                resp = requests.get(ui_url)
                if resp.status_code == 200:
                    log("✅ UI is accessible", GREEN)
                    if "Test Series" in resp.text:
                        log("✅ UI shows correct episode title", GREEN)
                    else:
                        log("❌ UI does not show episode title", RED)
                        # Print response content for debugging
                        # log(f"Response content: {resp.text[:500]}...")
                    ui_connected = True
                    break
                else:
                    log(f"❌ UI returned status {resp.status_code}", RED)
            except requests.exceptions.ConnectionError:
                log(f"Waiting for UI... ({i+1}/10)")
                time.sleep(1)
                
        if not ui_connected:
            log("❌ Failed to connect to UI after retries", RED)
            # Check if UI process is still running
            if feedback_proc.poll() is not None:
                log(f"UI process exited with code {feedback_proc.returncode}", RED)
                stdout, stderr = feedback_proc.communicate()
                print("--- UI Stdout ---")
                print(stdout.decode())
                print("--- UI Stderr ---")
                print(stderr.decode())
            raise Exception("UI verification failed")

        # 6. Submit Feedback
        log("\n--- Submitting Feedback ---", GREEN)
        # We need the play_history_id. We can query the DB or parse it from UI.
        # Let's query the DB for robustness.
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM play_history ORDER BY id DESC LIMIT 1")
        ph_id = cursor.fetchone()[0]
        conn.close()
        
        log(f"Found PlayHistory ID: {ph_id}")
        
        submit_url = f"{ui_url}/submit/{ph_id}/liked"
        resp = requests.post(submit_url)
        if resp.status_code == 200:
            log("✅ Feedback submitted successfully", GREEN)
        else:
            log(f"❌ Feedback submission failed: {resp.status_code}", RED)
            raise Exception("Feedback failed")

        # Verify in DB
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT rating FROM feedback WHERE play_history_id=?", (ph_id,))
        row = cursor.fetchone()
        
        if row:
            log(f"Found feedback row: {row}", GREEN)
            # SQLAlchemy Enum stores member name by default (LIKED)
            if row[0] in ["liked", "LIKED"]:
                log("✅ Feedback verified in database", GREEN)
            else:
                log(f"❌ Feedback rating mismatch: expected 'liked'/'LIKED', got '{row[0]}'", RED)
                raise Exception("DB verification failed")
        else:
            log("❌ Feedback not found in database", RED)
            # Debug: list all feedback
            cursor.execute("SELECT * FROM feedback")
            all_feedback = cursor.fetchall()
            log(f"All feedback in DB: {all_feedback}", RED)
            raise Exception("DB verification failed")
            
        conn.close()

        log("\n🎉 E2E VERIFICATION SUCCESSFUL! 🎉", GREEN)

    except Exception as e:
        log(f"\n❌ E2E FAILED: {e}", RED)
        if log_file.exists():
            print("\n--- Alma Log Tail ---")
            print(log_file.read_text()[-1000:])
        sys.exit(1)
        
    finally:
        log("\n--- Teardown ---", GREEN)
        for p in processes:
            p.terminate()
            p.wait()
        
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        log("Cleaned up temp files")

if __name__ == "__main__":
    main()
