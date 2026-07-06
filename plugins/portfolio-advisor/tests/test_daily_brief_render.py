"""Tests for daily_brief.py's render() RISK-block wiring (Phase 3, E1)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))

from daily_brief import render  # noqa: E402


def _base_brief(risk_snapshot: dict | None = None) -> dict:
    return {
        "date": "2026-07-05",
        "macro_regime": {"regime": "NEUTRAL", "score": 0, "details": []},
        "score_deltas": {}, "pillar_deltas": {}, "conviction_scores": [],
        "earnings_flags": [], "pillar_health": [], "yesterday_date": None,
        "overnight_gaps": [],
        "risk_snapshot": risk_snapshot,
    }


def test_render_includes_risk_line_when_snapshot_present():
    risk_snapshot = {
        "portfolioVol": 0.28, "portfolioBeta": 1.4,
        "clusterExposure": [{"pillarId": "ai_infra", "weight": 0.61, "varianceContributionPct": 72.0}],
        "marginalRiskContribution": {"NVDA": 0.18, "PANW": 0.09},
    }
    output = render(_base_brief(risk_snapshot))
    assert "RISK:" in output
    assert "vol 28%" in output
    assert "beta 1.4" in output
    assert "top cluster 61%" in output
    assert "MRC leader: NVDA 18%" in output


def test_render_omits_risk_line_when_snapshot_absent():
    output = render(_base_brief(risk_snapshot=None))
    assert "RISK:" not in output
