"""Benchmark for library scanner performance."""

import json
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from alma_tv.library.scanner import Scanner


def scan_directory_wrapper(directory: Path) -> List[dict]:
    """Wrapper to adapt Scanner.scan_directory for benchmark."""
    # Mock upsert to avoid DB overhead in pure scanner bench
    with patch("alma_tv.library.scanner.Scanner.upsert_video") as mock_upsert:
        mock_upsert.return_value = True
        # Mock duration to avoid ffprobe overhead
        with patch("alma_tv.library.scanner.Scanner.get_duration") as mock_duration:
            mock_duration.return_value = 420
            
            scanner = Scanner(media_root=directory)
            summary = scanner.scan_directory()
            # Return list of "scanned" items (we can't easily get the list from summary, 
            # so we'll just return a dummy list of length 'scanned')
            return [{} for _ in range(summary["scanned"])]


@pytest.mark.benchmark
def test_scanner_performance(benchmark, sample_media_files, tmp_path):
    """Benchmark scanner performance on sample dataset."""
    media_dir, files = sample_media_files

    # Benchmark the scanner
    result = benchmark(scan_directory_wrapper, media_dir)

    # Verify results
    assert len(result) == len(files)

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

    # Create 1000 files with unique names
    for i in range(1000):
        series_num = i % 10
        season_num = (i // 10) % 5 + 1
        ep_num = i % 100 + 1
        # Include 'i' to ensure uniqueness
        file_path = media_dir / f"Series{series_num}_S{season_num:02d}E{ep_num:02d}_{i}.mp4"
        file_path.touch()

    # Benchmark
    result = benchmark(scan_directory_wrapper, media_dir)
    assert len(result) == 1000
