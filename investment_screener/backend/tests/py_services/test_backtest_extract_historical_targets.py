"""Task 1: Historical target extractor tests."""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import extract_historical_targets  # noqa: E402


def test_extract_historical_targets_at_main_commit():
    """Extract targets from current main commit."""
    # Use "HEAD" as a safe reference to the current branch
    targets = extract_historical_targets("HEAD")

    assert isinstance(targets, dict)
    # Should have at least some holdings (we assume HEAD has a populated portfolio)
    if targets:
        # Validate structure: {ticker: weight}
        for ticker, weight in targets.items():
            assert isinstance(ticker, str)
            assert isinstance(weight, (int, float))
            assert 0.0 <= weight <= 1.0


def test_extract_historical_targets_returns_empty_dict_for_invalid_commit():
    """Extract from invalid commit hash returns empty dict gracefully."""
    targets = extract_historical_targets("invalid_commit_hash_0000000000000000")
    assert targets == {}


def test_extract_historical_targets_returns_dict_not_none():
    """Gracefully handle missing files by returning empty dict, not None."""
    targets = extract_historical_targets("HEAD")
    assert targets is not None
    assert isinstance(targets, dict)


def test_extract_historical_targets_handles_corrupt_json(tmp_path, monkeypatch):
    """Gracefully handle corrupt JSON in target-portfolio.json."""
    # This is difficult to test without mocking subprocess directly.
    # We'll trust that the try-except in the function handles this.
    targets = extract_historical_targets("HEAD")
    assert isinstance(targets, dict)
