"""
Task 5D-8: Integration into Order Execution

Tests for three new, standalone functions added to data_window_validator.py:
  - compute_liquidity_score(candle)
  - check_overbought_veto(indicators, threshold=80.0)
  - check_order_data_readiness(ticker, timeframe="1D", rsi_veto_threshold=80.0)

These are self-contained, importable functions ready for a FUTURE
order_risk_gates.py (Task 5E's own scope to create) to import and call — this
task does NOT create that file (see this task's brief).

compute_liquidity_score() substitutes Volume + intraday range for "bid/ask
spread analysis" since extract_data_window()'s real output (Task 5D-1,
confirmed live) has no bid/ask fields at all — documented as an honest
approximation, not a true liquidity metric.

check_order_data_readiness()'s tests genuinely mock get_validated_data_window
(Task 5D-7) at the data_window_validator module's own reference — no real CDP
calls are made.

Key documented asymmetry under test (see this task's brief): a missing volume
degrades compute_liquidity_score() to score 0.0 (conservative — unconfirmed
liquidity is a real risk), while a missing RSI does NOT trigger
check_overbought_veto() (permissive — absence of data is not evidence of an
overbought condition). Tests 4 and 10 lock in this asymmetry; it must not be
"fixed" into symmetric treatment.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import data_window_validator  # noqa: E402
from data_window_validator import (  # noqa: E402
    check_order_data_readiness,
    check_overbought_veto,
    compute_liquidity_score,
)


# --- compute_liquidity_score() ---

def test_compute_liquidity_score_high_volume():
    result = compute_liquidity_score({"volume": 2_000_000, "high": 105, "low": 100})
    assert result["score"] == 1.0


def test_compute_liquidity_score_moderate_volume():
    result = compute_liquidity_score({"volume": 500_000, "high": 105, "low": 100})
    assert result["score"] == 0.5


def test_compute_liquidity_score_low_volume():
    result = compute_liquidity_score({"volume": 50_000, "high": 105, "low": 100})
    assert result["score"] == 0.2


def test_compute_liquidity_score_missing_volume_returns_zero():
    result_missing_key = compute_liquidity_score({"high": 105, "low": 100})
    result_none_volume = compute_liquidity_score({"volume": None, "high": 105, "low": 100})

    assert result_missing_key["score"] == 0.0
    assert result_missing_key["volume"] is None
    assert result_none_volume["score"] == 0.0
    assert result_none_volume["volume"] is None


def test_compute_liquidity_score_computes_range_pct():
    result = compute_liquidity_score({"volume": 1_000_000, "high": 103, "low": 100})
    assert result["range_pct"] == 3.0


def test_compute_liquidity_score_never_raises_on_malformed_candle():
    for malformed in (None, [1, 2, 3], {}):
        result = compute_liquidity_score(malformed)
        assert result["score"] == 0.0
        assert result["volume"] is None
        assert result["range_pct"] is None


# --- check_overbought_veto() ---

def test_check_overbought_veto_triggers_above_threshold():
    result = check_overbought_veto({"rsi": 85.0})
    assert result["vetoed"] is True
    assert "overbought" in result["reason"].lower() or "RSI" in result["reason"]


def test_check_overbought_veto_triggers_at_exact_threshold():
    result = check_overbought_veto({"rsi": 80.0})
    assert result["vetoed"] is True


def test_check_overbought_veto_does_not_trigger_below_threshold():
    result = check_overbought_veto({"rsi": 75.0})
    assert result["vetoed"] is False
    assert result["reason"] is None


def test_check_overbought_veto_missing_rsi_does_not_trigger():
    result_missing_key = check_overbought_veto({})
    result_none_rsi = check_overbought_veto({"rsi": None})

    assert result_missing_key["vetoed"] is False
    assert result_missing_key["rsi"] is None
    assert result_none_rsi["vetoed"] is False
    assert result_none_rsi["rsi"] is None


def test_check_overbought_veto_respects_custom_threshold():
    result = check_overbought_veto({"rsi": 65.0}, threshold=60.0)
    assert result["vetoed"] is True


# --- check_order_data_readiness() ---

_VALID_CANDLE = {
    "open": 217.04,
    "high": 222.75,
    "low": 215.28,
    "close": 216.10,
    "volume": 1_640_000,
    "timestamp": "2026-07-14T00:00:00+00:00",
}

_INDICATORS_OVERBOUGHT = {
    "rsi": 85.0,
    "macd": 1.23,
    "bb_upper": 230.0,
    "bb_lower": 210.0,
    "adx": 25.0,
    "atr": 3.5,
}

_EMPTY_INDICATORS = {
    "rsi": None,
    "macd": None,
    "bb_upper": None,
    "bb_lower": None,
    "adx": None,
    "atr": None,
}


def test_check_order_data_readiness_composes_all_three(monkeypatch):
    fixture = {
        "valid": True,
        "candle": dict(_VALID_CANDLE),
        "indicators": dict(_INDICATORS_OVERBOUGHT),
        "warnings": [],
    }
    monkeypatch.setattr(
        data_window_validator, "get_validated_data_window", lambda ticker, timeframe: fixture
    )

    result = check_order_data_readiness("NVDA")

    assert result["valid"] is True
    assert result["candle"] == _VALID_CANDLE
    assert result["indicators"] == _INDICATORS_OVERBOUGHT
    assert result["warnings"] == []
    assert result["liquidity"]["score"] == 1.0
    assert result["rsi_veto"]["vetoed"] is True


def test_check_order_data_readiness_handles_none_candle_gracefully(monkeypatch):
    fixture = {
        "valid": False,
        "candle": None,
        "indicators": dict(_EMPTY_INDICATORS),
        "warnings": ["extraction failed after all retries"],
    }
    monkeypatch.setattr(
        data_window_validator, "get_validated_data_window", lambda ticker, timeframe: fixture
    )

    result = check_order_data_readiness("NVDA")

    assert result["liquidity"]["score"] == 0.0
    assert result["rsi_veto"]["vetoed"] is False


def test_check_order_data_readiness_calls_get_validated_data_window_with_correct_args(monkeypatch):
    calls = []

    def fake_get_validated_data_window(ticker, timeframe):
        calls.append((ticker, timeframe))
        return {
            "valid": True,
            "candle": dict(_VALID_CANDLE),
            "indicators": dict(_EMPTY_INDICATORS),
            "warnings": [],
        }

    monkeypatch.setattr(
        data_window_validator, "get_validated_data_window", fake_get_validated_data_window
    )

    check_order_data_readiness("AAPL", timeframe="60")

    assert calls == [("AAPL", "60")]
