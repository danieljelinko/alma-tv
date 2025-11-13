"""Benchmark for scheduler performance."""

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import List

import pytest


def generate_lineup_mock(available_episodes: List[dict], target_duration: int = 1800) -> List[dict]:
    """
    Mock lineup generator.

    This is a placeholder until the actual scheduler is implemented.
    """
    selected = []
    total_duration = 0

    # Randomly select episodes until we reach target duration
    pool = available_episodes.copy()
    random.shuffle(pool)

    for episode in pool:
        if total_duration + episode["duration"] <= target_duration:
            selected.append(episode)
            total_duration += episode["duration"]

        if len(selected) >= 5 or abs(total_duration - target_duration) < 120:
            break

    return selected


@pytest.mark.benchmark
def test_scheduler_performance(benchmark):
    """Benchmark scheduler for single day lineup generation."""
    # Create mock episode library
    episodes = []
    for series_id in range(10):
        for season in range(1, 4):
            for ep in range(1, 21):
                episodes.append(
                    {
                        "id": f"s{series_id}_s{season}_e{ep}",
                        "series": f"Series{series_id}",
                        "season": season,
                        "episode": ep,
                        "duration": random.randint(300, 600),  # 5-10 minutes
                    }
                )

    # Benchmark lineup generation
    result = benchmark(generate_lineup_mock, episodes, 1800)

    assert len(result) >= 3
    assert len(result) <= 5
    total_duration = sum(ep["duration"] for ep in result)
    assert abs(total_duration - 1800) <= 120  # Within 2 minutes


@pytest.mark.benchmark
def test_scheduler_30_day_simulation(benchmark, tmp_path):
    """Benchmark 30-day schedule generation (per plan.md requirement)."""
    # Create episode library
    episodes = []
    for series_id in range(15):
        for season in range(1, 5):
            for ep in range(1, 26):
                episodes.append(
                    {
                        "id": f"s{series_id}_s{season}_e{ep}",
                        "series": f"Series{series_id}",
                        "season": season,
                        "episode": ep,
                        "duration": random.randint(300, 600),
                    }
                )

    def simulate_30_days():
        """Simulate generating 30 daily schedules."""
        schedules = []
        start_date = date(2025, 11, 1)

        for day in range(30):
            current_date = start_date + timedelta(days=day)
            lineup = generate_lineup_mock(episodes)
            schedules.append({"date": current_date.isoformat(), "lineup": lineup})

        return schedules

    # Benchmark
    result = benchmark(simulate_30_days)

    assert len(result) == 30
    assert all(len(schedule["lineup"]) >= 3 for schedule in result)

    # Save results
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    results_file = results_dir / "scheduler.json"
    with open(results_file, "w") as f:
        json.dump(
            {
                "success": True,
                "summary": f"Generated 30 days in {benchmark.stats.get('mean', 0):.3f}s",
                "days_generated": 30,
                "benchmark_stats": {
                    "mean": benchmark.stats.get("mean", 0),
                    "stddev": benchmark.stats.get("stddev", 0),
                },
            },
            f,
            indent=2,
        )
