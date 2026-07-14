"""Bugfix regression tests for daily_brief.py's G4 rebalance-event emission.

`run()` previously referenced the module-level `recommendations` name ~36
lines before it was ever assigned, crashing every invocation with
`UnboundLocalError`, and additionally assumed the wrong data shape (a dict
with an "actions" key) for `build_recommendations()`'s real flat-list-of-
cards return value. This block has been extracted into
`_emit_rebalance_events_step()` (matching the `_harvest_predictions_step`/
`_score_deltas` convention of testable private helpers) and corrected to
match the real recommendation-card shape.

`evolution_events.emit_rebalance_event` is mocked at the module-level
attribute (same technique as test_pine_daily_workflow_injects_signals.py
uses for pine_script_manager.inject_pine_script) — the helper's local
`from evolution_events import emit_rebalance_event` re-reads the module
attribute at call time, so no test here reaches the real event log.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from daily_brief import _emit_rebalance_events_step  # noqa: E402
import evolution_events  # noqa: E402


def _card(ticker: str, recommendation: str) -> dict:
    return {"ticker": ticker, "recommendation": recommendation}


def _score(ticker: str, price: float) -> dict:
    return {"ticker": ticker, "price": price}


def _never_call(*args, **kwargs):
    """An emit_rebalance_event stand-in that fails the test loudly if invoked."""
    raise AssertionError(f"emit_rebalance_event must not be invoked, but was called with args={args}, kwargs={kwargs}")


class TestEmitRebalanceEventsStep:
    def test_emits_for_buy_and_sell_cards(self, monkeypatch):
        recommendations = [
            _card("AAPL", "BUY"),
            _card("NBIS", "SELL"),
        ]
        scores_raw = [_score("AAPL", 200.0), _score("NBIS", 30.0)]

        calls = []

        def fake_emit(**kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(evolution_events, "emit_rebalance_event", fake_emit)

        _emit_rebalance_events_step(recommendations, scores_raw)

        assert len(calls) == 2
        order_types = {c["ticker"]: c["order_type"] for c in calls}
        assert order_types == {"AAPL": "buy", "NBIS": "sell"}

    def test_skips_non_buy_sell_recommendations(self, monkeypatch):
        recommendations = [
            _card("AAPL", "HOLD"),
            _card("NBIS", "TRIM"),
            _card("PANW", "BUY_LIMIT"),
            _card("CRWD", "QUEUED"),
        ]
        scores_raw = []

        monkeypatch.setattr(evolution_events, "emit_rebalance_event", _never_call)

        _emit_rebalance_events_step(recommendations, scores_raw)

    def test_looks_up_current_price_from_scores(self, monkeypatch):
        recommendations = [_card("NVDA", "BUY")]
        scores_raw = [_score("NVDA", 123.45)]

        calls = []

        def fake_emit(**kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(evolution_events, "emit_rebalance_event", fake_emit)

        _emit_rebalance_events_step(recommendations, scores_raw)

        assert len(calls) == 1
        assert calls[0]["order_price"] == 123.45
        assert calls[0]["current_price"] == 123.45

    def test_defaults_price_to_zero_when_ticker_not_in_scores(self, monkeypatch):
        recommendations = [_card("MSTR", "BUY")]
        scores_raw = [_score("NVDA", 123.45)]  # MSTR not present

        calls = []

        def fake_emit(**kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(evolution_events, "emit_rebalance_event", fake_emit)

        _emit_rebalance_events_step(recommendations, scores_raw)

        assert len(calls) == 1
        assert calls[0]["order_price"] == 0.0
        assert calls[0]["current_price"] is None

    def test_continues_after_one_emission_failure(self, monkeypatch):
        recommendations = [
            _card("AAPL", "BUY"),
            _card("NBIS", "BUY"),
        ]
        scores_raw = [_score("AAPL", 200.0), _score("NBIS", 30.0)]

        calls = []

        def fake_emit(**kwargs):
            calls.append(kwargs)
            if kwargs["ticker"] == "AAPL":
                raise RuntimeError("boom")

        monkeypatch.setattr(evolution_events, "emit_rebalance_event", fake_emit)

        # Must not raise, and both tickers must have been attempted.
        _emit_rebalance_events_step(recommendations, scores_raw)

        assert [c["ticker"] for c in calls] == ["AAPL", "NBIS"]

    def test_handles_empty_recommendations_list(self, monkeypatch):
        monkeypatch.setattr(evolution_events, "emit_rebalance_event", _never_call)

        _emit_rebalance_events_step([], [])
