"""Placeholder test to verify CI wiring."""

import pytest


def test_sanity() -> None:
    """Sanity check test."""
    assert True


def test_imports() -> None:
    """Test that the main package can be imported."""
    import alma_tv

    assert alma_tv.__version__ == "0.1.0"
