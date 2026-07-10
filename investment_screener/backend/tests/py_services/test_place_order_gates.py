"""
Tests for place_order.py input validation and safety gates.
All tests run via subprocess — no TradingView required for gates 1–7.
Tests 8–9 require TV on port 9222 and are skipped automatically when absent.

Exit code contract:
  1  — generic error (Node/CDP failure, missing required arg)
  2  — argparse error (missing required argument)
  3  — order exceeds max-order-value cap
  4  — portfolio.json stale (DATA_STALE_BLOCKED, before any CDP call)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PLACE_ORDER = REPO_ROOT / "investment_screener/backend/py_services/place_order.py"

# A known-in-hours weekday timestamp (Wed 2024-06-12, 11:00 ET / 15:00 UTC — no US market
# holiday that week) for PLACE_ORDER_NOW_OVERRIDE, so gate-order tests below assert the
# gate they name regardless of what day/time this suite actually runs (map-debt: these 3
# tests used to fail with MARKET_CLOSED_BLOCKED on weekends/after-hours since the market-
# hours gate fires before the gate under test).
IN_HOURS_NOW = "2024-06-12T15:00:00+00:00"


def _run(*extra_args: str, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(PLACE_ORDER), *extra_args],
        capture_output=True, text=True, cwd=str(REPO_ROOT), env=env,
    )


def _tv_reachable() -> bool:
    import socket
    try:
        s = socket.create_connection(("localhost", 9222), timeout=0.5)
        s.close()
        return True
    except OSError:
        return False


TV_AVAILABLE = _tv_reachable()


# ── Argument validation tests (no TV, no portfolio needed) ────────────────────

def test_preflight_missing_ticker():
    """--preflight without --ticker must exit non-zero."""
    r = _run("--action", "buy", "--shares", "1", "--order-type", "market",
             "--account", "tfsa", "--preflight")
    assert r.returncode != 0, "Expected non-zero exit when --ticker is missing"


def test_execute_missing_account():
    """--execute without --account must exit non-zero."""
    r = _run("--ticker", "AAPL", "--action", "buy", "--shares", "1",
             "--order-type", "market", "--execute")
    assert r.returncode != 0, "Expected non-zero exit when --account is missing"


def test_cancel_missing_order_id():
    """--cancel without --order-id must exit non-zero."""
    r = _run("--cancel")
    assert r.returncode != 0, "Expected non-zero exit when --order-id is missing for --cancel"


def test_modify_missing_new_price():
    """--modify with --order-id but without --new-price must exit non-zero."""
    r = _run("--modify", "--order-id", "fake-uuid-1234")
    assert r.returncode != 0, "Expected non-zero exit when --new-price is missing for --modify"


def test_limit_order_missing_limit_price():
    """--order-type limit without --limit-price must exit non-zero."""
    r = _run("--ticker", "AAPL", "--action", "buy", "--shares", "1",
             "--order-type", "limit", "--account", "tfsa", "--preflight")
    assert r.returncode != 0, "Expected non-zero exit for limit order without --limit-price"


# ── Freshness gate tests (no TV required) ─────────────────────────────────────

def _make_portfolio(tmp_path: Path, age_minutes: float) -> Path:
    """Create a minimal portfolio.json with an mtime offset in minutes."""
    p = tmp_path / "portfolio.json"
    p.write_text(json.dumps([{"symbol": "AAPL", "shares": 10, "price": 150}]))
    if age_minutes > 0:
        old_time = time.time() - age_minutes * 60
        os.utime(str(p), (old_time, old_time))
    return p


def test_stale_portfolio_exits_4(tmp_path):
    """A portfolio.json older than 60 minutes must exit 4 BEFORE any CDP call.
    TV is NOT required — this gate fires before any Node.js invocation."""
    portfolio = _make_portfolio(tmp_path, age_minutes=120)
    r = _run(
        "--ticker", "AAPL", "--action", "buy", "--shares", "1",
        "--order-type", "market", "--account", "tfsa", "--preflight",
        env_overrides={
            "PLACE_ORDER_PORTFOLIO_PATH": str(portfolio),
            "PLACE_ORDER_NOW_OVERRIDE": IN_HOURS_NOW,
        },
    )
    assert r.returncode == 4, (
        f"Expected exit 4 for stale portfolio, got {r.returncode}.\n"
        f"stdout: {r.stdout[:300]}\nstderr: {r.stderr[:300]}"
    )
    combined = r.stdout + r.stderr
    assert "stale" in combined.lower() or "DATA_STALE" in combined, (
        "Expected stale/DATA_STALE message in output"
    )


def test_stale_with_ack_stale_proceeds(tmp_path):
    """--ack-stale must bypass the stale gate (not exit 4).
    May still exit non-zero if TV is absent, but must not exit 4."""
    portfolio = _make_portfolio(tmp_path, age_minutes=120)
    r = _run(
        "--ticker", "AAPL", "--action", "buy", "--shares", "1",
        "--order-type", "market", "--account", "tfsa", "--preflight",
        "--ack-stale",
        env_overrides={"PLACE_ORDER_PORTFOLIO_PATH": str(portfolio)},
    )
    assert r.returncode != 4, (
        f"Expected --ack-stale to bypass stale gate (not exit 4), got {r.returncode}.\n"
        f"stdout: {r.stdout[:300]}\nstderr: {r.stderr[:300]}"
    )


def test_market_closed_exits_5_and_ack_closed_bypasses(tmp_path):
    """PLACE_ORDER_NOW_OVERRIDE lets this gate be asserted directly, independent of
    wall-clock/weekday state — a Saturday timestamp must exit 5 (MARKET_CLOSED_BLOCKED)
    before any Node.js invocation, and --ack-closed must bypass it (not exit 5)."""
    portfolio = _make_portfolio(tmp_path, age_minutes=0)
    saturday_utc = "2024-06-15T15:00:00+00:00"  # confirmed Saturday

    r = _run(
        "--ticker", "AAPL", "--action", "buy", "--shares", "1",
        "--order-type", "market", "--account", "tfsa", "--preflight",
        env_overrides={
            "PLACE_ORDER_PORTFOLIO_PATH": str(portfolio),
            "PLACE_ORDER_NOW_OVERRIDE": saturday_utc,
        },
    )
    assert r.returncode == 5, (
        f"Expected exit 5 for market-closed weekend, got {r.returncode}.\n"
        f"stdout: {r.stdout[:300]}\nstderr: {r.stderr[:300]}"
    )
    combined = r.stdout + r.stderr
    assert "MARKET_CLOSED_BLOCKED" in combined or "closed" in combined.lower(), (
        "Expected a market-closed message in output"
    )

    r_ack = _run(
        "--ticker", "AAPL", "--action", "buy", "--shares", "1",
        "--order-type", "market", "--account", "tfsa", "--preflight",
        "--ack-closed",
        env_overrides={
            "PLACE_ORDER_PORTFOLIO_PATH": str(portfolio),
            "PLACE_ORDER_NOW_OVERRIDE": saturday_utc,
        },
    )
    assert r_ack.returncode != 5, (
        f"Expected --ack-closed to bypass market-closed gate (not exit 5), got {r_ack.returncode}.\n"
        f"stdout: {r_ack.stdout[:300]}\nstderr: {r_ack.stderr[:300]}"
    )


@pytest.mark.skipif(not TV_AVAILABLE, reason="TradingView not reachable on port 9222")
def test_tradingview_connection_and_broker_login(tmp_path):
    """Verify that TradingView Desktop is running and a broker connection is active.
    This is the primary sanity check for live brokerage automation."""
    # 1. TradingView is open (since TV_AVAILABLE is True, otherwise this test is skipped)
    assert TV_AVAILABLE, "TradingView Desktop must be open and running with remote debugging on port 9222."

    # 2. Check if broker is logged in by executing a dry-run preflight check
    portfolio = _make_portfolio(tmp_path, age_minutes=0)
    r = _run(
        "--ticker", "AAPL", "--action", "buy", "--shares", "1",
        "--order-type", "market", "--account", "tfsa", "--preflight",
        env_overrides={"PLACE_ORDER_PORTFOLIO_PATH": str(portfolio)},
    )
    combined = r.stdout + r.stderr
    assert "No broker connected" not in combined, (
        "Broker panel not connected! Please open TradingView, connect your broker panel "
        "(e.g., Questrade), and log in first before running live integration tests."
    )


@pytest.mark.skipif(not TV_AVAILABLE, reason="TradingView not reachable on port 9222")
def test_fresh_portfolio_exits_0(tmp_path):
    """A fresh portfolio.json (under 60 min old) must produce exit 0."""
    portfolio = _make_portfolio(tmp_path, age_minutes=0)
    r = _run(
        "--ticker", "AAPL", "--action", "buy", "--shares", "1",
        "--order-type", "market", "--account", "tfsa", "--preflight",
        env_overrides={
            "PLACE_ORDER_PORTFOLIO_PATH": str(portfolio),
            "PLACE_ORDER_NOW_OVERRIDE": IN_HOURS_NOW,
        },
    )
    combined = r.stdout + r.stderr
    if r.returncode == 1 and "No broker connected" in combined:
        pytest.skip("Skipping because TradingView is reachable but no broker is connected.")
    assert r.returncode == 0, (
        f"Expected exit 0 for fresh portfolio, got {r.returncode}.\n"
        f"stdout: {r.stdout[:300]}\nstderr: {r.stderr[:300]}"
    )
    assert "freshnessWarning" not in combined, "Should not have freshness warning for fresh portfolio"


@pytest.mark.skipif(not TV_AVAILABLE, reason="TradingView not reachable on port 9222")
def test_size_cap_exits_3(tmp_path):
    """A limit order whose cost (limitPrice × shares) exceeds --max-order-value must exit 3.
    Must use a limit order — market orders have costEstimate=null and cannot trigger the cap."""
    portfolio = _make_portfolio(tmp_path, age_minutes=0)
    r = _run(
        "--ticker", "AAPL", "--action", "buy", "--shares", "100",
        "--order-type", "limit", "--limit-price", "100.00",  # cost = $10,000
        "--account", "tfsa", "--preflight",
        "--max-order-value", "100",   # $100 cap — $10,000 order will exceed it
        env_overrides={
            "PLACE_ORDER_PORTFOLIO_PATH": str(portfolio),
            "PLACE_ORDER_NOW_OVERRIDE": IN_HOURS_NOW,
        },
    )
    combined = r.stdout + r.stderr
    if r.returncode == 1 and "No broker connected" in combined:
        pytest.skip("Skipping because TradingView is reachable but no broker is connected.")
    assert r.returncode == 3, (
        f"Expected exit 3 for oversized order, got {r.returncode}.\n"
        f"stdout: {r.stdout[:300]}\nstderr: {r.stderr[:300]}"
    )
    assert "_sizeWarning" in r.stdout or "sizeWarning" in r.stdout.lower(), (
        "Expected _sizeWarning in card output"
    )

