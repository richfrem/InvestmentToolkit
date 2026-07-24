import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import backtest_harness  # noqa: E402


def test_extract_historical_targets_tries_both_pre_and_post_move_paths():
    """extract_historical_targets() reads target-portfolio.json out of historical git
    blobs. The file moved from data/target-portfolio.json to data/theses/
    target-portfolio.json partway through this repo's history (Wave 2 investigation
    finding). A commit-SHA-agnostic historical reader must try both paths, since it
    has no way to know a priori whether a given historical commit predates the move.
    Silently trying only one path means every commit on the other side of the move
    returns empty/wrong data with no error -- the exact failure mode this test guards.
    """
    candidate_paths = backtest_harness.candidate_target_portfolio_paths()
    assert "investment_screener/backend/data/target-portfolio.json" in candidate_paths
    assert (
        "investment_screener/backend/data/theses/target-portfolio.json"
        in candidate_paths
    )


class TestCorrelateWithPredictionLedger:
    """Wave 5D Task 3: correlate_with_prediction_ledger() must read
    PREDICTION_CLAIM events from intelligence.sqlite, not predictions.jsonl."""

    def _seed_claim(self, tmp_path, db_path, claim_date="2026-07-10", ticker="CORZ"):
        from intelligence.db_client import initialize_db
        from intelligence.event_store import append_event
        from intelligence.replay_ledger import replay_events_to_db

        ledger_path = tmp_path / "observations.jsonl"
        conn = initialize_db(str(db_path))
        append_event(
            str(ledger_path), event_type="PREDICTION_CLAIM", effective_at=claim_date,
            status="ACTIVE", title=f"Prediction claim: {ticker} action_rating ({claim_date})",
            body_markdown="Direction: bullish, horizon: 90 days.", ticker=ticker,
            payload={"ticker": ticker, "type": "action_rating", "date": claim_date,
                     "id": f"{ticker}:action_rating:{claim_date}"},
            idempotency_key=f"prediction-claim-{ticker}:action_rating:{claim_date}",
        )
        replay_events_to_db(str(ledger_path), conn)

    def test_links_predictions_matching_rebalance_date_and_ticker(self, tmp_path):
        db_path = tmp_path / "intelligence.sqlite"
        self._seed_claim(tmp_path, db_path, claim_date="2026-07-10", ticker="CORZ")

        backtest_report = {
            "rebalances": [
                {"date": "2026-07-10", "orders": [{"ticker": "CORZ", "side": "buy"}]},
            ]
        }
        result = backtest_harness.correlate_with_prediction_ledger(backtest_report, str(db_path))
        assert result["total_predictions_linked"] == 1
        assert result["rebalance_alignment"]["2026-07-10"]["count"] == 1

    def test_empty_ledger_yields_zero_correlation(self, tmp_path):
        from intelligence.db_client import initialize_db

        db_path = tmp_path / "empty_intelligence.sqlite"
        initialize_db(str(db_path))
        backtest_report = {"rebalances": [{"date": "2026-07-10", "orders": []}]}
        result = backtest_harness.correlate_with_prediction_ledger(backtest_report, str(db_path))
        assert result["total_predictions_linked"] == 0
        assert result["signal_quality"] == 0.0

    def test_missing_db_path_degrades_gracefully(self, tmp_path):
        backtest_report = {"rebalances": [{"date": "2026-07-10", "orders": []}]}
        result = backtest_harness.correlate_with_prediction_ledger(
            backtest_report, str(tmp_path / "no_such_db.sqlite")
        )
        assert result["total_predictions_linked"] == 0
