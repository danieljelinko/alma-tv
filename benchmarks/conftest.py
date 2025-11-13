"""Pytest configuration for benchmarks."""

import pytest


@pytest.fixture
def sample_media_files(tmp_path):
    """Create sample media files for benchmarking."""
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    # Create directory structure with mock files
    series = ["Bluey", "PawPatrol", "PeppaRig"]
    episodes_per_series = 10

    files = []
    for series_name in series:
        series_dir = media_dir / series_name
        series_dir.mkdir()

        for season in range(1, 3):
            season_dir = series_dir / f"Season{season}"
            season_dir.mkdir()

            for ep in range(1, episodes_per_series + 1):
                ep_file = season_dir / f"{series_name}_S{season:02d}E{ep:02d}_Episode{ep}.mp4"
                # Create empty file (no actual video content needed for benchmarks)
                ep_file.touch()
                files.append(ep_file)

    return media_dir, files
