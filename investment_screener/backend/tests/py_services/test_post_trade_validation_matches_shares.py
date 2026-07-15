"""Tests for order_risk_gates.py — Post-Trade Validation (Task 5E-7).

Covers three functions:
- get_trade_log_entries(): reads the real trade log (investment_screener/
  backend/data/trade-log.json — always a tmp_path fixture here, never the
  real gitignored file).
- find_matching_trade_log_entry(): finds the newest trade log entry
  matching an order's ticker/side/(account), restricted to entries in a
  real executed state (excludes "suggested"/"cancelled"/"inactive"/
  "submitted" — a real-data-verified correction, see the task brief).
- wait_for_trade_log_entry(): polls get_trade_log_entries() +
  find_matching_trade_log_entry() until a match appears or timeout
  elapses. time.sleep/time.monotonic are always monkeypatched here so no
  test sleeps anywhere near the real 60s default timeout.
- validate_trade_execution(): pure comparison (no I/O) between an order
  and its already-matched trade log entry — exact shares reconciliation,
  percentage-tolerance price slippage check (> not >=).
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import order_risk_gates  # noqa: E402
from order_risk_gates import (  # noqa: E402
    find_matching_trade_log_entry,
    get_trade_log_entries,
    validate_trade_execution,
    wait_for_trade_log_entry,
)


def _order(side="BUY", ticker="CORZ", shares=10.0, price=100.0):
    return {"ticker": ticker, "side": side, "shares": shares, "price": price}


def _log_entry(ticker="CORZ", action="buy", shares=10.0, price=100.0,
                account="TFSA", status="logged", logged_at="2026-07-13T12:00:00.000Z"):
    return {
        "id": "abc123",
        "ticker": ticker,
        "action": action,
        "shares": shares,
        "price": price,
        "totalCost": shares * price,
        "account": account,
        "orderType": "market",
        "limitPrice": None,
        "date": "2026-07-13",
        "notes": "",
        "status": status,
        "source": "cdp_execution",
        "tvOrderId": None,
        "loggedAt": logged_at,
    }


# --- validate_trade_execution() ------------------------------------------


def test_validate_trade_execution_matched_no_slippage():
    order = _order(shares=10.0, price=100.0)
    entry = _log_entry(shares=10.0, price=100.0)

    result = validate_trade_execution(order, entry)

    assert result["matched"] is True
    assert result["shares_delta"] == 0.0
    assert result["slippage_flagged"] is False


def test_validate_trade_execution_shares_mismatch():
    order = _order(shares=10.0, price=100.0)
    entry = _log_entry(shares=8.0, price=100.0)

    result = validate_trade_execution(order, entry)

    assert result["matched"] is False
    assert result["shares_delta"] == -2.0


def test_validate_trade_execution_price_slippage_flagged():
    order = _order(shares=10.0, price=100.0)
    entry = _log_entry(shares=10.0, price=103.0)  # 3% slippage

    result = validate_trade_execution(order, entry)

    assert result["matched"] is True
    assert result["slippage_flagged"] is True
    assert round(result["price_slippage_pct"], 2) == 3.0


def test_validate_trade_execution_price_slippage_within_cap_not_flagged():
    order = _order(shares=10.0, price=100.0)
    entry = _log_entry(shares=10.0, price=101.0)  # 1% slippage

    result = validate_trade_execution(order, entry)

    assert result["slippage_flagged"] is False


def test_validate_trade_execution_boundary_exact_slippage_cap_not_flagged():
    order = _order(shares=10.0, price=100.0)
    entry = _log_entry(shares=10.0, price=102.0)  # exactly 2%

    result = validate_trade_execution(order, entry, slippage_cap_pct=2.0)

    assert result["slippage_flagged"] is False


def test_validate_trade_execution_no_matching_entry():
    order = _order(shares=10.0, price=100.0)

    result = validate_trade_execution(order, None)

    assert result["matched"] is False
    assert result["shares_delta"] is None


def test_validate_trade_execution_zero_order_price_skips_slippage():
    order = _order(shares=10.0, price=0.0)
    entry = _log_entry(shares=10.0, price=100.0)

    result = validate_trade_execution(order, entry)

    assert result["price_slippage_pct"] is None
    assert result["slippage_flagged"] is False


# --- find_matching_trade_log_entry() --------------------------------------


def test_find_matching_trade_log_entry_excludes_cancelled():
    order = _order(ticker="CORZ", side="BUY")
    older_logged = _log_entry(status="logged", logged_at="2026-07-10T10:00:00.000Z", price=100.0)
    newer_cancelled = _log_entry(status="cancelled", price=0.0, logged_at="2026-07-13T10:00:00.000Z")
    entries = [older_logged, newer_cancelled]

    result = find_matching_trade_log_entry(order, entries)

    assert result is older_logged


def test_find_matching_trade_log_entry_excludes_suggested_and_working_statuses():
    order = _order(ticker="CORZ", side="BUY")
    entries = [
        _log_entry(status="suggested"),
        _log_entry(status="inactive"),
        _log_entry(status="submitted"),
    ]

    result = find_matching_trade_log_entry(order, entries)

    assert result is None


def test_find_matching_trade_log_entry_returns_newest_match():
    order = _order(ticker="CORZ", side="BUY")
    older = _log_entry(status="logged", logged_at="2026-07-10T10:00:00.000Z")
    newer = _log_entry(status="logged", logged_at="2026-07-13T10:00:00.000Z")
    entries = [older, newer]

    result = find_matching_trade_log_entry(order, entries)

    assert result is newer


def test_find_matching_trade_log_entry_filters_by_account():
    order = _order(ticker="CORZ", side="BUY")
    tfsa_entry = _log_entry(account="TFSA", logged_at="2026-07-13T10:00:00.000Z")
    rrsp_entry = _log_entry(account="RRSP", logged_at="2026-07-13T11:00:00.000Z")
    entries = [tfsa_entry, rrsp_entry]

    result = find_matching_trade_log_entry(order, entries, account="TFSA")

    assert result is tfsa_entry


def test_find_matching_trade_log_entry_filters_by_after_timestamp():
    order = _order(ticker="CORZ", side="BUY")
    stale_entry = _log_entry(logged_at="2026-07-10T10:00:00.000Z")
    entries = [stale_entry]

    result = find_matching_trade_log_entry(order, entries, after_timestamp="2026-07-12T00:00:00.000Z")

    assert result is None


def test_find_matching_trade_log_entry_returns_none_when_no_match():
    order = _order(ticker="ZZZZ", side="BUY")
    entries = [_log_entry(ticker="CORZ")]

    result = find_matching_trade_log_entry(order, entries)

    assert result is None


# --- get_trade_log_entries() ----------------------------------------------


def test_get_trade_log_entries_returns_none_when_file_missing(tmp_path):
    missing_path = tmp_path / "trade-log.json"

    result = get_trade_log_entries(trade_log_path=missing_path)

    assert result == []


def test_get_trade_log_entries_returns_empty_on_malformed_json(tmp_path):
    trade_log_file = tmp_path / "trade-log.json"
    trade_log_file.write_text("{not valid json")

    result = get_trade_log_entries(trade_log_path=trade_log_file)

    assert result == []


def test_get_trade_log_entries_reads_real_entries(tmp_path):
    trade_log_file = tmp_path / "trade-log.json"
    entries = [_log_entry(), _log_entry(ticker="NVDA")]
    trade_log_file.write_text(json.dumps(entries))

    result = get_trade_log_entries(trade_log_path=trade_log_file)

    assert result == entries


# --- wait_for_trade_log_entry() -------------------------------------------


def test_wait_for_trade_log_entry_returns_immediately_on_first_match(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr(order_risk_gates.time, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(order_risk_gates, "get_trade_log_entries", lambda path=None: [_log_entry()])

    order = _order(ticker="CORZ", side="BUY")
    result = wait_for_trade_log_entry(order)

    assert result is not None
    assert sleep_calls == []


def test_wait_for_trade_log_entry_polls_until_match_appears(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr(order_risk_gates.time, "sleep", lambda s: sleep_calls.append(s))

    # Fake monotonic clock that advances a small amount each call (never
    # anywhere near a real 60s wait).
    clock = {"t": 0.0}

    def fake_monotonic():
        return clock["t"]

    monkeypatch.setattr(order_risk_gates.time, "monotonic", fake_monotonic)

    call_count = {"n": 0}

    def fake_get_entries(path=None):
        call_count["n"] += 1
        clock["t"] += 2.0  # simulate poll_interval elapsing
        if call_count["n"] < 3:
            return []
        return [_log_entry()]

    monkeypatch.setattr(order_risk_gates, "get_trade_log_entries", fake_get_entries)

    order = _order(ticker="CORZ", side="BUY")
    result = wait_for_trade_log_entry(order, timeout=60.0, poll_interval=2.0)

    assert result is not None
    assert call_count["n"] == 3
    assert len(sleep_calls) == 2


def test_wait_for_trade_log_entry_times_out_returns_none(monkeypatch):
    sleep_calls = []
    monkeypatch.setattr(order_risk_gates.time, "sleep", lambda s: sleep_calls.append(s))

    clock = {"t": 0.0}

    def fake_monotonic():
        return clock["t"]

    monkeypatch.setattr(order_risk_gates.time, "monotonic", fake_monotonic)

    def fake_get_entries(path=None):
        clock["t"] += 10.0  # advance clock past timeout quickly
        return []

    monkeypatch.setattr(order_risk_gates, "get_trade_log_entries", fake_get_entries)

    order = _order(ticker="CORZ", side="BUY")
    result = wait_for_trade_log_entry(order, timeout=60.0, poll_interval=2.0)

    assert result is None
