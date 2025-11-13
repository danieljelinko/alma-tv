#!/bin/bash
# Raspberry Pi smoke test script
# Validates library discovery, scheduling, playback sequencing, and clock rendering
# on actual Raspberry Pi hardware

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Alma TV Raspberry Pi Smoke Test ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "WARNING: This script is designed for Raspberry Pi hardware"
    echo "Continuing anyway for development testing..."
fi

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Check dependencies
echo "Checking dependencies..."
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg not found"; exit 1; }

# Run library scanner benchmark
echo ""
echo "=== Testing Library Scanner ==="
if [ -d "$PROJECT_ROOT/tests/fixtures/media" ]; then
    pytest "$PROJECT_ROOT/benchmarks/scanner_bench.py" --benchmark-only || true
else
    echo "SKIP: No test fixtures found"
fi

# Run scheduler benchmark
echo ""
echo "=== Testing Scheduler ==="
pytest "$PROJECT_ROOT/benchmarks/scheduler_bench.py" --benchmark-only || true

# Run playback gap benchmark
echo ""
echo "=== Testing Playback Gap ==="
pytest "$PROJECT_ROOT/benchmarks/playback_gap.py" --benchmark-only || true

# Test clock rendering
echo ""
echo "=== Testing Clock Rendering ==="
python3 -m alma_tv.clock.renderer --test || true

echo ""
echo "=== Smoke Test Complete ==="
echo "Review logs at: /var/log/alma/alma.log"
echo "Review benchmark results at: $PROJECT_ROOT/benchmarks/results/"
