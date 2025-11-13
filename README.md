# Alma TV

Alma TV is a Raspberry Pi–friendly automation suite that assembles, schedules, and plays a curated block of children’s programming every evening. The system scans a local cartoon library, builds a 30-minute lineup (intro + 3–5 episodes + outro), presents an SVG-based clock between shows, and collects playful feedback from the child to personalize future lineups.

## Repository Goals
- Provide implementation-ready documentation for the core Alma TV experience (library management, scheduling, playback, feedback, clock display).
- Describe the testing/benchmarking context needed to validate the automation loop on a Raspberry Pi or developer workstation.
- Offer a phased roadmap that autonomous coding agents can execute without additional tribal knowledge.

## Basic Usage
1. Clone this repository on your development host or Raspberry Pi.
2. Follow `plan.md` to understand the architecture, required services, and data contracts.
3. Execute the phase-specific tasks in `TODOs.md`. Each checklist item is designed for hands-off agent execution, including the validation steps and success criteria.
4. Once the automation stack is coded, run the provided tests/benchmarks (outlined in `plan.md`) to validate library discovery, scheduling logic, playback sequencing, feedback persistence, and clock rendering.

## Development Environment Setup

### Prerequisites
- Python 3.11 or higher
- FFmpeg (for media file metadata extraction)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-account>/alma-tv.git
cd alma-tv

# Create and activate a Python 3.11+ virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy environment configuration
cp .env.example .env
# Edit .env to match your local setup

# Install FFmpeg (if not already installed)
# Ubuntu/Debian:
# sudo apt-get install ffmpeg
# macOS:
# brew install ffmpeg
# Raspberry Pi OS:
# sudo apt-get install ffmpeg
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/library            # verifies repository scanning
pytest tests/scheduler          # validates daily lineup generation
pytest tests/integration        # covers playback + feedback loop

# Run with coverage
pytest --cov=alma_tv --cov-report=html

# Run benchmarks
pytest benchmarks/ --benchmark-only
```

### CLI Usage

```bash
# Show configuration
alma config show

# Scan media library
alma scan

# List available series
alma library list

# Generate today's schedule
alma schedule today

# Preview schedule for specific date
alma schedule --date 2025-11-13 --preview

# Run playback daemon (typically run via systemd)
alma playback run

# Run clock service
alma clock run
```

### Raspberry Pi Smoke Test

On Raspberry Pi hardware, run the smoke test to validate the full stack:

```bash
bash scripts/run_pi_smoke.sh
```

Refer to `plan.md` for deeper implementation notes and to `TODOs.md` for the detailed execution plan.
