# Alma TV Implementation Plan

This plan translates the Alma TV ideas and PRD into an executable specification. It provides every detail needed by an autonomous coding agent to implement, test, and benchmark the system without additional context.

---
## 1. Scope & Objectives
- Automate a daily 30-minute viewing block (7:00–7:30 PM) consisting of intro → 3–5 episodes → outro → feedback. Number of episodes or time range is configurable.
- Run entirely on a Raspberry Pi using locally stored video files.
- Learn from play history and child feedback to personalize future schedules while respecting explicit show requests.
- Present an SVG-based analog clock between shows to visualize time remaining until the next session.
- Maintain auditable history (library, schedules, playback, feedback) inside a lightweight database.

### Success Criteria
1. **Content Awareness**: The library scanner discovers all supported video files (including nested directories) and records metadata with ≥99% accuracy in under 60 s for a 1 TB drive.
2. **Daily Programming**: Scheduler produces a valid block for any requested day, honoring intro/outro constraints, requested shows, and anti-repetition rules.
3. **Playback Reliability**: Playback daemon starts automatically at the configured time, plays the planned sequence without gaps >1 s, and logs completion per video.
4. **Feedback Loop**: Feedback UI captures one of three responses per episode, stores the result, and adjusts future selection weights.
5. **Clock Display**: SVG clock renders at least 30 FPS on Raspberry Pi, displays current time, and highlights the next program window with distinct colors.
6. **Benchmarking & Tests**: Automated tests cover metadata parsing, scheduling heuristics, playback queue assembly, feedback persistence, and clock rendering math. Benchmarks simulate a week of schedules in <2 min on Pi 4.

---
## 2. High-Level Architecture
```
┌─────────────────┐      ┌────────────────────┐      ┌─────────────────┐
│ Video Repository│ ---> │ Library Service    │ ---> │ Scheduler       │
└─────────────────┘      └────────────────────┘      └─────────────────┘
          │                       │                         │
          │                       ▼                         ▼
          │                ┌────────────┐             ┌──────────────┐
          └--------------> │ Metadata DB│ <-----------│ Play History │
                           └────────────┘             └──────────────┘
                                   │                         │
                                   ▼                         ▼
                             ┌────────────┐           ┌──────────────┐
                             │ Playback   │<-------->│ Feedback UI  │
                             │ Orchestrator│         │ (child input)│
                             └────────────┘           └──────────────┘
                                   │
                                   ▼
                              ┌─────────┐
                              │ SVG Clock│
                              └─────────┘
```

### Components Summary
1. **Repository Scanner** (Background Programming Module)
   - Recursively scans configured directories for media files.
   - Extracts metadata (series, season, episode, duration) from file names + FFprobe.
   - Publishes structured records to the Metadata DB and emits change events for scheduler warm-up.

2. **Library Service API**
   - Provides read/query endpoints (e.g., `list_series`, `episodes_for_show`, `random_episode(filters)`), abstracting raw SQL.

3. **Scheduler**
   - Generates the next viewing block using available episodes, play history, feedback weights, and optional ad-hoc requests ("play 3 Bluey episodes").
   - Balances diversity across series and seasons, enforces anti-repeat window (default 14 days), and guarantees runtime within 30 ± 1 minutes.

4. **Playback Orchestrator**
   - Watches for the scheduled start time (default 19:00). Launches intro, queue of selected episodes (3–5), outro, and triggers feedback UI.
   - Interfaces with `omxplayer`/`vlc` (configurable) and records playback events.

5. **Feedback Module**
   - Presents three emoji-based buttons (Really Liked / Okay / Never Again) for every episode shown.
   - Stores responses and updates per-episode selection weights.

6. **Clock Display Module**
   - Headless service that renders an SVG analog clock (via Chromium or custom SDL window) whenever playback is idle.
   - Highlights the next session window using color blocks (cartoon vs. future vocabulary program).

7. **Benchmarking & Test Harness**
   - CLI tool `alma bench --days 7` builds 7 days of schedules, replays them against stubbed players, and produces KPIs (mean runtime, scheduling latency, repeat rate).
   - Pytest suites per module plus end-to-end scenario (mock repository + fake feedback inputs).

---
## 3. Detailed Design

### 3.1 Data Storage
- **Database**: SQLite for portability on Raspberry Pi; can be swapped for PostgreSQL if remote access is required.
- **Tables** (minimum):
  - `videos(id, series, season, episode_code, path, duration_seconds, added_at, disabled)`
  - `play_history(id, show_date, slot_order, video_id, started_at, ended_at)`
  - `feedback(id, play_history_id, rating ENUM('liked','okay','never'), submitted_at)`
  - `sessions(id, show_date, status ENUM('planned','completed'), generated_at, intro_path, outro_path)`
  - `requests(id, request_date, requester_notes, payload JSONB)` for parent/child show requests.
- **Indexes**: on `series`, `season`, `show_date`, and `video_id` for fast lookups.

### 3.2 Repository Scanner & Library Service
- **Input**: `ALMA_MEDIA_ROOT` (default `/mnt/media/cartoons`).
- **Process**:
  1. Walk directories using `watchdog` or periodic cron (every 6 h).
  2. For each media file (`.mp4`, `.mkv`, `.avi`):
     - Parse filename pattern `SeriesName_SxxEyy_Title.ext`.
     - Call `ffprobe` to confirm duration, codec, resolution.
     - Hash path+mtime; skip if unchanged.
  3. Upsert metadata into `videos` table.
- **Outputs**: Database rows + optional JSON manifest (`var/cache/library.json`) for offline testing.
- **Dependencies**: Python 3.11, `ffmpeg`, `watchdog`, `pydantic` for validation.
- **Testing/Benchmarking**:
  - Unit tests stub filesystem and ffprobe responses.
  - Benchmark: scan a synthetic tree of 10k files; goal <90 s on Pi 4 (document results in `/benchmarks/scanner.md`).

### 3.3 Scheduler
- **Inputs**: library API, play history window (past 14 days), feedback weights, optional request payload.
- **Algorithm**:
  1. Always reserve intro/outro (configured via settings table).
  2. Determine number of episodes (3–5) by summing durations closest to 30 minutes minus intro/outro length.
  3. Build candidate pool filtered by:
     - `disabled = false`
     - Not played within `repeat_cooldown_days`.
     - Not marked "never again" unless manual override.
  4. Apply weights:
     - baseline weight = 1
     - `liked` adds +0.5 per vote, decays weekly.
     - `okay` leaves baseline.
     - `never` sets weight = 0.
     - Requested shows multiply weight ×3 but require season diversity.
  5. Randomly sample episodes respecting weight distribution and ensuring distinct seasons when possible.
  6. Persist planned session + lineup to DB.
- **Outputs**: `sessions` row + ordered list of `play_history` stubs (status `planned`).
- **Testing**:
  - Deterministic tests with seeded RNG to verify distribution rules.
  - Integration test ensuring runtime tolerance (±60 s) and absence of duplicates.
  - Benchmark: `alma bench scheduler` simulating 30 days to ensure <5 s per day on Pi 4.

### 3.4 Playback Orchestrator
- **Service**: systemd unit `alma-playback.service` or Python daemon.
- **Flow**:
  1. Poll scheduler output for today; if missing, trigger generation.
  2. At `start_time` (default 19:00) launch intro via media player.
  3. Play episodes sequentially; after each file, log actual start/end.
  4. Play outro.
  5. Trigger feedback UI by sending DBus/websocket event.
- **Error Handling**: fallback to next episode on failure, notify parent via log/email.
- **Testing**:
  - Mock player to assert command invocation order.
  - Hardware smoke test using sample MP4 files.
  - Benchmark: measure gap between files; requirement <1 s average.

### 3.5 Feedback Module
- **UI Tech**: lightweight web app (Flask + HTMX) or Kivy touchscreen UI.
- **Behavior**:
  - Auto-launch after outro; display cards for each episode with three large buttons (Happy/Neutral/Sad icons).
  - Persist rating, mark timestamp.
  - Provide skip timeout (auto mark as `okay` after 2 minutes of no input).
- **Data Impact**: updates selection weights used by scheduler.
- **Testing**:
  - UI snapshot tests (Playwright) to ensure button accessibility.
  - API tests verifying rating writes and weight recalculation.

### 3.6 SVG Clock Module
- **Rendering**: Python service outputs SVG every minute; optionally animates with CSS.
- **Features**:
  - Real-time hour/minute hands.
  - Colored arc from now to next show start; distinct palette for cartoon vs. vocabulary block (future use).
  - Simple textual note (“Cartoons start at 7:00 PM”).
- **Deployment**: run continuously except during playback (screen blanked or overlay hidden).
- **Testing**:
  - Unit tests for geometry math (angles, arcs).
  - Visual regression tests comparing generated SVG to golden files.

### 3.7 Configuration & Secrets
- YAML or `.env` file containing paths, start time, repeat window, etc.
- Provide CLI to edit config (`alma config set key value`).

---
## 4. Dependencies & Environments
- **System**: Raspberry Pi OS (64-bit), Python 3.11+, ffmpeg, sqlite3, systemd.
- **Python Packages**: `pydantic`, `sqlalchemy`, `typer`, `watchdog`, `python-vlc` or `omxplayer-wrapper`, `jinja2`, `svgwrite`, `pytest`, `pytest-benchmark`, `playwright` (optional UI tests).
- **Hardware**: Pi 4 (4 GB+) recommended; HDMI display for playback clock.

---
## 5. Benchmarking & Testing Strategy
1. **Unit Tests**: Stored under `tests/<module>/`; run via `pytest`. Mandatory for scanners, scheduler heuristics, playback queue builder, feedback weight updates, and clock geometry.
2. **Integration Tests**:
   - `tests/integration/test_full_session.py` simulates a full day using mock players and verifies DB side effects.
   - `tests/ui/test_feedback_flow.py` uses Playwright (headed or headless) to ensure touch targets, icons, and persistence.
3. **Benchmarks**:
   - `benchmarks/scanner_bench.py` (pytest-benchmark) for filesystem scan throughput.
   - `benchmarks/scheduler_bench.py` measuring scheduling latency over 30 simulated days.
   - `benchmarks/playback_gap.py` to measure time between videos when running with mock player.
   - Store benchmark baselines in `benchmarks/results/*.json`; compare in CI to catch regressions.
4. **Hardware Smoke Tests**:
   - `scripts/run_pi_smoke.sh` copies small MP4 fixtures and exercises playback + clock overlay on actual Pi hardware.
   - Record log output to `/var/log/alma/` for manual review.
5. **CI Pipeline**:
   - GitHub Actions workflow running unit tests + benchmarks (with reduced dataset) on Ubuntu.
   - Optional nightly job that spins Raspberry Pi self-hosted runner for hardware smoke tests.

---
## 6. Implementation Phases
1. **Phase 0 – Foundations**
   - Scaffold repo (pyproject, src layout, tests, sample media fixtures, config loader).
   - Implement lightweight logging + configuration helpers.
2. **Phase 1 – Library Intelligence**
   - Build repository scanner, metadata parser, and persistence layer.
   - Deliver CLI commands: `alma scan`, `alma library list`.
3. **Phase 2 – Scheduling Engine**
   - Implement scheduling logic, request ingestion, weight adjustments, and anti-repeat policy.
   - Produce CLI: `alma schedule today`, `alma schedule --date YYYY-MM-DD`.
4. **Phase 3 – Playback + Clock**
   - Playback orchestrator service + clock renderer + parent configuration overrides.
5. **Phase 4 – Feedback Loop**
   - UI, API, and integration with scheduler weights.
6. **Phase 5 – Benchmarks & Ops**
   - Finalize automated test suites, benchmarking scripts, monitoring hooks, and documentation.

Each phase has accompanying tasks in `TODOs.md` with acceptance tests.

---
## 7. Risks & Mitigations
- **Large Media Libraries**: mitigate via incremental scanning + hashing to avoid full rescans.
- **Playback Failures**: implement retries, fallback players, and audible/visual alerts.
- **Child Interaction**: ensure UI works offline, with oversized buttons and minimal text.
- **Data Loss**: schedule nightly SQLite backups to `/var/backups/alma`. Document restore process.

---
## 8. Future Extensions (Not in MVP)
- Vocabulary learning mini-games leveraging episode transcripts.
- Multi-color clock arcs for additional daily programs.
- Parent dashboard + remote monitoring.
- Cloud sync for play history and analytics.

This plan, combined with the `TODOs.md` execution roadmap, empowers autonomous agents to deliver the Alma TV system end-to-end.
