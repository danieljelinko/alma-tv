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

## Quick Start
```bash
# Clone
git clone https://github.com/<your-account>/alma-tv.git
cd alma-tv

# Create and activate a Python 3.11+ virtual environment
python -m venv .venv
source .venv/bin/activate

# Install core dependencies once implemented in pyproject/requirements
pip install -r requirements.txt  # placeholder until code exists

# Run smoke test scripts (defined in plan.md) once the modules land
pytest tests/library            # verifies repository scanning
pytest tests/scheduler          # validates daily lineup generation
pytest tests/integration        # covers playback + feedback loop
```

Refer to `plan.md` for deeper implementation notes and to `TODOs.md` for the detailed execution plan.
