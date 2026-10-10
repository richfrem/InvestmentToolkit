"""Task 8: Prediction ledger correlation tests.

correlate_with_prediction_ledger() reads PREDICTION_CLAIM events from intelligence.sqlite
(via db_path). Every test here seeds a tmp_path-scoped sqlite file via the real
intelligence.event_store machinery -- never the default db_path, which would otherwise
silently read the real investment_screener/backend/data/intelligence.sqlite.
"""
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from backtest_harness import correlate_with_prediction_ledger  # noqa: E402


def _seed_prediction_claim(tmp_path, db_path, ticker, claim_date, prediction_id):
    """Seed one real PREDICTION_CLAIM event via the real ledger path.

    Mirrors test_backtest_harness_historical_path.py's _seed_claim helper; the claim date key
    is "date" (per the prediction schema), not "claimDate".
    """
    from intelligence.db_client import initialize_db
    from intelligence.event_store import append_event

    conn = initialize_db(str(db_path))
    append_event(
        conn, event_type="PREDICTION_CLAIM", effective_at=claim_date,
        status="ACTIVE", title=f"Prediction claim: {ticker} action_rating ({claim_date})",
        body_markdown="Direction: bullish, horizon: 90 days.", ticker=ticker,
        payload={"id": prediction_id, "ticker": ticker, "type": "action_rating",
                 "date": claim_date, "direction": "bullish", "confidence": 0.8},
        idempotency_key=f"prediction-claim-{prediction_id}",
    )
    conn.close()


def test_backtest_correlates_with_prediction_ledger(tmp_path):
    """Correlate backtest with E3 prediction ledger (real sqlite, tmp_path-scoped)."""
    today = datetime.now().date().isoformat()
    report = {
        "metadata": {
            "start_date": today,
            "end_date": today,
            "run_timestamp": datetime.now().isoformat(),
        },
        "rebalances": [
            {
                "date": today,
                "orders": [
                    {
                        "ticker": "AAPL",
                        "side": "buy",
                        "shares": 10.0,
                        "fill_price": 150.0,
                        "executed_at": datetime.now().isoformat(),
                        "pnl": None,
                    },
                ],
                "realized_pnl": 0.0,
                "execution_quality": {"AAPL": 0.95},
            },
        ],
        "summary": {"total_rebalances": 1, "total_pnl": 0.0, "avg_quality_score": 0.95},
    }

    db_path = tmp_path / "intelligence.sqlite"
    _seed_prediction_claim(tmp_path, db_path, "AAPL", today, "AAPL:action_rating:2026-01-15")

    correlation = correlate_with_prediction_ledger(report, db_path=str(db_path))

    assert isinstance(correlation, dict)
    assert "total_predictions_linked" in correlation
    assert "rebalance_alignment" in correlation
    assert "signal_quality" in correlation

    # A real prediction on the same date/ticker must actually be linked --
    # this is the assertion the pre-cutover version of this test never made
    # (it only checked `>= 0`, which silently passes even with zero real
    # matches -- exactly the "date" vs "claimDate" bug this task fixed).
    assert correlation["total_predictions_linked"] == 1
    assert today in correlation["rebalance_alignment"]


def test_backtest_prediction_ledger_handles_missing_db(tmp_path):
    """Correlation handles a missing/never-synced sqlite file gracefully."""
    report = {
        "metadata": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "rebalances": [],
        "summary": {"total_rebalances": 0, "total_pnl": 0.0, "avg_quality_score": 0.0},
    }

    missing_db_path = tmp_path / "does-not-exist.sqlite"
    correlation = correlate_with_prediction_ledger(report, db_path=str(missing_db_path))

    assert isinstance(correlation, dict)
    assert correlation["total_predictions_linked"] == 0
    assert correlation["signal_quality"] == 0.0


def test_backtest_prediction_ledger_returns_required_structure(tmp_path):
    """Correlation report has required fields (tmp_path-scoped, empty db)."""
    report = {
        "metadata": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "rebalances": [
            {
                "date": "2026-01-15",
                "orders": [
                    {
                        "ticker": "AAPL",
                        "side": "buy",
                        "shares": 10.0,
                        "fill_price": 150.0,
                        "executed_at": "2026-01-15T10:00:00",
                        "pnl": None,
                    },
                ],
                "realized_pnl": 0.0,
                "execution_quality": {"AAPL": 0.95},
            },
        ],
        "summary": {"total_rebalances": 1, "total_pnl": 0.0, "avg_quality_score": 0.95},
    }

    empty_db_path = tmp_path / "empty.sqlite"
    correlation = correlate_with_prediction_ledger(report, db_path=str(empty_db_path))

    assert "total_predictions_linked" in correlation
    assert "rebalance_alignment" in correlation
    assert "signal_quality" in correlation

    # Signal quality should be 0.0-1.0
    assert 0.0 <= correlation["signal_quality"] <= 1.0


def test_backtest_prediction_ledger_signal_quality_is_numeric(tmp_path):
    """Signal quality is numeric and in valid range (tmp_path-scoped, empty db)."""
    report = {
        "metadata": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "rebalances": [],
        "summary": {"total_rebalances": 0, "total_pnl": 0.0, "avg_quality_score": 0.0},
    }

    empty_db_path = tmp_path / "empty.sqlite"
    correlation = correlate_with_prediction_ledger(report, db_path=str(empty_db_path))

    assert isinstance(correlation["signal_quality"], (int, float))
    assert 0.0 <= correlation["signal_quality"] <= 1.0
