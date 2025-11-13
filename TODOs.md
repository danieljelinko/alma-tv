# Alma TV TODOs

This roadmap is structured so an autonomous coding agent can implement Alma TV end-to-end using only this file and `plan.md`. Execute phases sequentially; do not advance until acceptance criteria are met and required tests/benchmarks have passed.

---
## Phase 0 – Foundations & Tooling
**Acceptance Criteria**: Repo scaffolding exists, configuration + logging utilities work on Raspberry Pi OS, CI can run lint/tests, and benchmarking harness stubs are in place.

### Component: Repository Scaffolding
- [ ] Initialize `pyproject.toml`, `src/alma_tv/` package, and `tests/` tree.
- [ ] Add `.editorconfig`, `.gitignore`, and sample `.env.example` covering media paths and schedule times.
- [ ] Create `scripts/` folder with placeholder `run_pi_smoke.sh` referencing benchmarking approach in `plan.md`.
- [ ] Document development environment setup in `README.md` (virtualenv, ffmpeg install snippet).
- **Tests**: `pytest -q tests/test_placeholder.py` (create simple sanity test to verify CI wiring).

### Component: Configuration & Logging Utilities
- [ ] Implement `alma_tv.config` that loads `.env`/YAML, validates with `pydantic`, and exposes typed settings.
- [ ] Implement `alma_tv.logging` helper that configures stdout + file logging (`/var/log/alma/alma.log`).
- [ ] Expose CLI `alma config show` (Typer command) for quick inspection.
- **Tests**: `tests/config/test_settings.py` covering env overrides, validation failures, and Raspberry Pi paths.

### Component: Benchmark Harness Skeleton
- [ ] Create `benchmarks/` package with pytest-benchmark dependency stub.
- [ ] Scaffold `benchmarks/__main__.py` to parse `alma bench --dry-run` and print baseline instructions.
- [ ] Ensure harness reads fixtures from `tests/fixtures/media/` so agents can run without large files.
- **Tests**: `pytest benchmarks --benchmark-disable` ensures harness imports cleanly on CI.

---
## Phase 1 – Library Intelligence
**Acceptance Criteria**: Scanner discovers media from nested directories, metadata persisted to SQLite, CLI exposes scan/list commands, and benchmark demonstrates scan time target per `plan.md`.

### Component: Filesystem Watcher & Scanner
- [ ] Implement recursive scanner using `watchdog` fallback to manual scan.
- [ ] Parse filenames into `series`, `season`, `episode_code`, gracefully handling unknown formats.
- [ ] Integrate `ffprobe` duration extraction with retry logic.
- [ ] Upsert metadata into `videos` table via SQLAlchemy models defined in this phase.
- [ ] Emit change log entry (JSON) for benchmarking/tracing.
- **Tests**: `tests/library/test_scanner.py` mocks filesystem + ffprobe. Include case coverage for nested folders and bad files.
- **Benchmark**: `pytest benchmarks/scanner_bench.py --benchmark-only`; ensure synthetic dataset <90 s (log result in `benchmarks/results/scanner.json`).

### Component: Library Service API
- [ ] Build query helpers (list series, list episodes, random selection with filters) exposed via Typer CLI and importable API.
- [ ] Ensure service honors `disabled` flag and duration filters.
- [ ] Add caching layer (LRU) for hot queries to reduce scheduler latency.
- **Tests**: `tests/library/test_service.py` verifying query correctness and cache behavior.

---
## Phase 2 – Scheduling Engine
**Acceptance Criteria**: `alma schedule` command produces intro/episodes/outro plan meeting runtime target, honors requests, enforces anti-repeat window, and records sessions in DB.

### Component: Weight Model & Feedback Integration Hooks
- [ ] Implement weight calculation helpers (baseline + liked bonus + decay, never-again exclusion).
- [ ] Provide API for feedback module to update weights without coupling to scheduler internals.
- **Tests**: `tests/scheduler/test_weights.py` verifying decays, overrides, and conflict resolution.

### Component: Lineup Generator
- [ ] Implement deterministic RNG seeding for reproducible tests.
- [ ] Enforce runtime (30 ± 1 minutes) by dynamically picking 3–5 episodes.
- [ ] Enforce series & season diversity when pool allows.
- [ ] Handle explicit requests (e.g., "3 Bluey episodes") via `requests` table input.
- [ ] Persist planned session + provisional play_history rows.
- **Tests**: `tests/scheduler/test_lineup.py` covering runtime bounds, request satisfaction, cooldown enforcement.
- **Benchmark**: `pytest benchmarks/scheduler_bench.py --benchmark-only` simulating 30 days <5 s/day; update results JSON.

### Component: Scheduler CLI & API
- [ ] Add `alma schedule today`, `alma schedule --date`, and `alma schedule --preview` commands.
- [ ] Provide JSON output for automation tools + human-readable table for parents.
- [ ] Log KPI metrics (weight distribution, duration variance) for benchmarking context.
- **Tests**: `tests/scheduler/test_cli.py` using Click runner.

---
## Phase 3 – Playback & Clock
**Acceptance Criteria**: At 19:00 the orchestrator launches intro + lineup + outro with <1 s gap, logs events, and clock service renders SVG arcs when idle.

### Component: Playback Orchestrator
- [ ] Implement systemd-friendly daemon (Typer command `alma playback run`).
- [ ] Integrate with `vlc`/`omxplayer`; include abstraction to swap players.
- [ ] Log start/end per file and update `play_history` row statuses.
- [ ] Handle failures (skip file, continue, alert log).
- **Tests**: `tests/playback/test_orchestrator.py` mocking media player commands.
- **Benchmark**: `benchmarks/playback_gap.py` ensures average gap <1 s (record result).

### Component: SVG Clock Service
- [ ] Create service generating SVG every minute; highlight time slice until next program using colors defined in `plan.md`.
- [ ] Provide HTTP endpoint or file drop for display layer.
- [ ] Pause clock overlay during playback via IPC signal.
- **Tests**: `tests/clock/test_renderer.py` verifying geometry + color segments; visual regression using stored SVG snapshots.

### Component: Parent/Child Display Integration
- [ ] Build lightweight front-end (Chromium kiosk or SDL window) that toggles between clock and playback overlays.
- [ ] Ensure accessibility (large icons, brightness settings) noted in plan.
- **Manual Test**: Run `scripts/run_pi_smoke.sh` on Raspberry Pi to confirm display transitions.

---
## Phase 4 – Feedback Loop
**Acceptance Criteria**: After outro, UI shows emoji buttons per episode, persists ratings, updates weights, and data appears in scheduler reports.

### Component: Feedback API & Storage
- [ ] Implement REST endpoints (`/api/feedback`) secured by local token.
- [ ] Persist rating -> `feedback` table and trigger weight recompute hook.
- **Tests**: `tests/feedback/test_api.py` verifying payload validation and DB writes.

### Component: Child-Friendly UI
- [ ] Build touchscreen-friendly interface (Flask + HTMX or Kivy) with three emotive buttons per episode.
- [ ] Auto-populate from latest session; auto-timeout marks `okay`.
- [ ] Play victory sound/animation on submission.
- **Tests**: `tests/feedback/test_ui.py` (Playwright) ensuring buttons accessible, icons load offline.
- **Manual Test**: On hardware, capture short video verifying 4-year-old-friendly UX.

### Component: Feedback Analytics & Reporting
- [ ] Extend scheduler CLI to output recent feedback summary and highlight “never again” episodes.
- [ ] Add CSV/JSON export for parents.
- **Tests**: `tests/feedback/test_reporting.py` ensuring aggregation correctness.

---
## Phase 5 – Benchmarks, CI, and Ops Hardening
**Acceptance Criteria**: Automated tests + benchmarks run in CI, artifacts stored, systemd units + backups documented, and recovery steps verified.

### Component: CI Pipeline
- [ ] Configure GitHub Actions with matrix (Python 3.11, 3.12) running lint, unit, and integration tests.
- [ ] Cache ffmpeg downloads to keep runs fast.
- [ ] Publish benchmark artifacts (`benchmarks/results/*.json`) for regression detection.
- **Tests**: Monitor CI run success; ensure benchmark job fails if regression >10%.

### Component: Ops & Monitoring
- [ ] Provide systemd service files (`alma-playback.service`, `alma-clock.service`).
- [ ] Add log rotation (`logrotate.d/alma`).
- [ ] Implement SQLite backup script + validation (`sqlite3 .dump`).
- **Manual Test**: Run backup/restore dry run on Pi; verify playback still works.

### Component: Documentation & Release Prep
- [ ] Update `README.md` with final install + usage instructions referencing real commands.
- [ ] Publish `docs/benchmarking.md` summarizing latest results and hardware setup.
- [ ] Tag v0.1.0 once all acceptance criteria satisfied.
- **Tests**: `mkdocs build` or equivalent doc linting if adopted.

---
**Reminder**: After every component, run the listed tests/benchmarks and capture outputs in `benchmarks/results/` or CI logs. Do not skip validation—future scheduling logic depends on trustworthy metrics.
