"""Tests for rebalancer.py — E2 rebalancer v2 (Phase 3, sub-spec 4)."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from rebalancer import DEFAULT_BAND_CONFIG, compute_bands  # noqa: E402


def test_compute_bands_in_band_when_drift_within_band():
    # target 5.5%, band = max(5.5*0.20, 1.5) = 1.5pp; current 4.5% -> drift -1.0pp, in band
    bands = compute_bands({"NBIS": 4.5}, {"NBIS": 5.5}, DEFAULT_BAND_CONFIG)
    assert bands["NBIS"]["inBand"] is True
    assert bands["NBIS"]["bandPct"] == pytest.approx(1.5)
    assert bands["NBIS"]["driftPct"] == pytest.approx(-1.0)


def test_compute_bands_out_of_band_when_drift_exceeds_band():
    # target 5.5%, band 1.5pp; current 2.1% -> drift -3.4pp, out of band
    bands = compute_bands({"NBIS": 2.1}, {"NBIS": 5.5}, DEFAULT_BAND_CONFIG)
    assert bands["NBIS"]["inBand"] is False


def test_compute_bands_relative_band_dominates_for_large_targets():
    # target 20% -> relative band = 20*0.20 = 4.0pp > 1.5pp absolute floor
    bands = compute_bands({"BIG": 16.5}, {"BIG": 20.0}, DEFAULT_BAND_CONFIG)
    assert bands["BIG"]["bandPct"] == pytest.approx(4.0)
    assert bands["BIG"]["inBand"] is True  # drift -3.5pp within 4.0pp band


def test_compute_bands_boundary_drift_equal_to_band_is_in_band():
    bands = compute_bands({"X": 4.0}, {"X": 5.5}, DEFAULT_BAND_CONFIG)  # drift exactly -1.5pp
    assert bands["X"]["inBand"] is True


def test_compute_bands_ticker_missing_from_one_side_defaults_to_zero():
    bands = compute_bands({"ORPHAN": 2.0}, {}, DEFAULT_BAND_CONFIG)
    assert bands["ORPHAN"]["targetWeight"] == 0.0
    assert bands["ORPHAN"]["bandPct"] == pytest.approx(1.5)  # absolute floor, target*rel=0
