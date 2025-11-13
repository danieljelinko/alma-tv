"""Benchmark for library scanner performance."""

import json
from pathlib import Path
from typing import List

import pytest


def scan_directory_mock(directory: Path) -> List[dict]:
    """
    Mock scanner that walks directory and extracts metadata.

    This is a placeholder until the actual scanner is implemented.
    """
    results = []

    for file_path in directory.rglob("*.mp4"):
        # Mock metadata extraction
        parts = file_path.stem.split("_")
        if len(parts) >= 2:
            series = parts[0]
            episode_code = parts[1] if len(parts) > 1 else "S01E01"
        else:
            series = "Unknown"
            episode_code = "S01E01"

        results.append(
            {
                "path": str(file_path),
                "series": series,
                "episode_code": episode_code,
                "duration": 420,  # Mock 7-minute duration
            }
        )

    return results


@pytest.mark.benchmark
def test_scanner_performance(benchmark, sample_media_files, tmp_path):
    """Benchmark scanner performance on sample dataset."""
    media_dir, files = sample_media_files

    # Benchmark the scanner
    result = benchmark(scan_directory_mock, media_dir)

    # Verify results
    assert len(result) == len(files)
    assert all("path" in item for item in result)

    # Save results
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    results_file = results_dir / "scanner.json"
    with open(results_file, "w") as f:
        json.dump(
            {
                "success": True,
                "summary": f"Scanned {len(files)} files",
                "file_count": len(files),
                "benchmark_stats": {
                    "mean": benchmark.stats.get("mean", 0),
                    "stddev": benchmark.stats.get("stddev", 0),
                },
            },
            f,
            indent=2,
        )


@pytest.mark.benchmark
def test_scanner_scaling(benchmark, tmp_path):
    """Test scanner performance scales with file count."""
    # Create larger dataset
    media_dir = tmp_path / "large_media"
    media_dir.mkdir()

    # Create 1000 files
    for i in range(1000):
        series_num = i % 10
        season_num = (i // 10) % 5 + 1
        ep_num = i % 100 + 1
        file_path = media_dir / f"Series{series_num}_S{season_num:02d}E{ep_num:02d}.mp4"
        file_path.touch()

    # Benchmark
    result = benchmark(scan_directory_mock, media_dir)
    assert len(result) == 1000
