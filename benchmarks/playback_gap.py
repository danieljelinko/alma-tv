"""Benchmark for playback gap measurement."""

import json
import time
from pathlib import Path
from typing import List

import pytest


def simulate_playback_sequence(files: List[str]) -> List[float]:
    """
    Simulate playback sequence and measure gaps.

    This is a placeholder until the actual playback orchestrator is implemented.
    """
    gaps = []

    for i in range(len(files) - 1):
        # Simulate gap between files
        start = time.perf_counter()

        # Mock work: file loading, player initialization
        time.sleep(0.001)  # Minimal delay to simulate processing

        end = time.perf_counter()
        gap = end - start
        gaps.append(gap)

    return gaps


@pytest.mark.benchmark
def test_playback_gap_measurement(benchmark):
    """Benchmark playback gap between consecutive files."""
    files = [f"episode_{i}.mp4" for i in range(5)]

    gaps = benchmark(simulate_playback_sequence, files)

    # Verify gaps exist
    assert len(gaps) == len(files) - 1

    # Calculate average gap
    avg_gap = sum(gaps) / len(gaps) if gaps else 0

    # Log results
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    results_file = results_dir / "playback_gap.json"
    with open(results_file, "w") as f:
        json.dump(
            {
                "success": True,
                "summary": f"Average gap: {avg_gap*1000:.1f}ms",
                "average_gap_ms": avg_gap * 1000,
                "max_gap_ms": max(gaps) * 1000 if gaps else 0,
                "target_ms": 1000,
                "meets_target": avg_gap < 1.0,
            },
            f,
            indent=2,
        )


@pytest.mark.benchmark
def test_playback_gap_consistency(benchmark):
    """Test consistency of playback gaps across multiple runs."""
    files = [f"episode_{i}.mp4" for i in range(10)]

    gaps = benchmark(simulate_playback_sequence, files)

    # Check for consistency
    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        max_deviation = max(abs(g - avg_gap) for g in gaps)

        # Gaps should be relatively consistent
        assert max_deviation < 0.5  # 500ms max deviation
