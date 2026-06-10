"""Tests for macro_regime.py — regime classification and degraded-data fail-safe.

The macro gate is the system's only systemic risk control. When market data is
unavailable (yfinance rate limits — which cluster during volatility spikes,
exactly when the gate matters most), the classifier must fail SAFE (RISK-OFF),
not fail open (NEUTRAL permits +4 ACCUMULATE actions).

Run:
    python3 -m pytest investment_screener/backend/tests/py_services/test_macro_regime.py -v
"""
from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from macro_regime import MacroRegimeResult, _classify_regime  # noqa: E402


class TestClassifyRegime:
    """Pure score → regime mapping with degraded-data fail-safe."""

    def test_score_two_is_risk_on(self):
        assert _classify_regime(2, unavailable=0) == ("RISK-ON", False)

    def test_score_zero_is_neutral(self):
        assert _classify_regime(0, unavailable=0) == ("NEUTRAL", False)

    def test_negative_score_is_risk_off(self):
        assert _classify_regime(-1, unavailable=0) == ("RISK-OFF", False)

    def test_one_missing_component_tolerated(self):
        """A single unavailable signal degrades resolution but not safety —
        the remaining two signals still gate accumulation."""
        assert _classify_regime(2, unavailable=1) == ("RISK-ON", False)

    def test_two_missing_components_forces_risk_off(self):
        """Data blackout fail-safe: with 2 of 3 signals dark, a score of 0 is
        ignorance, not neutrality. Must force RISK-OFF and flag degraded."""
        assert _classify_regime(0, unavailable=2) == ("RISK-OFF", True)

    def test_all_components_missing_forces_risk_off(self):
        """yfinance fully down (e.g. ImportError path) → RISK-OFF, degraded."""
        assert _classify_regime(1, unavailable=3) == ("RISK-OFF", True)


class TestDegradedField:
    """MacroRegimeResult must carry the degraded flag to downstream consumers."""

    def test_result_dataclass_has_degraded_field(self):
        names = {f.name for f in fields(MacroRegimeResult)}
        assert "degraded" in names, (
            "MacroRegimeResult needs a `degraded` field so daily_brief.py can "
            "warn that the regime was forced RISK-OFF by missing data"
        )
