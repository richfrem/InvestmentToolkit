"""Test for the E2 globalSettings migration (task 9)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATIONS_DIR = REPO_ROOT / "investment_screener/backend/py_services/migrations"
sys.path.insert(0, str(MIGRATIONS_DIR))

from remove_drift_threshold_fields import strip_drift_threshold_fields  # noqa: E402


def test_strip_removes_both_fields():
    data = {"globalSettings": {"driftThresholdPct": 3.0, "criticalDriftPct": 5.0, "rebalanceFrequency": "quarterly"}}
    removed = strip_drift_threshold_fields(data)
    assert set(removed) == {"driftThresholdPct", "criticalDriftPct"}
    assert "driftThresholdPct" not in data["globalSettings"]
    assert "criticalDriftPct" not in data["globalSettings"]
    assert data["globalSettings"]["rebalanceFrequency"] == "quarterly"  # untouched


def test_strip_is_idempotent():
    data = {"globalSettings": {"rebalanceFrequency": "quarterly"}}
    assert strip_drift_threshold_fields(data) == []
