#!/usr/bin/env python3
"""
ta_sweep_single.py — Single-ticker Technical Analysis sweep with canonical intelligence ledger persistence.
========================================================================================================

Purpose:
    Performs a real-time Technical Analysis sweep for a single ticker via TradingView CDP
    (or local fallback), enriches with DCF fair value from domain_model.sqlite, and commits
    a canonical TECHNICAL_SWEEP event into intelligence.sqlite and the JSONL event store.

Layer:
    Plugins / TradingView / Scripts

Key Input Dependencies:
    - tradingview-cdp/cli.js (TV chart telemetry)
    - investment_screener/backend/data/domain_model.sqlite (Projections & target weights)

Key Output Dependencies:
    - investment_screener/backend/data/intelligence.sqlite (TECHNICAL_SWEEP event)
    - investment_screener/backend/data/intelligence_events.jsonl (Canonical event ledger)

Usage:
    python3 plugins/tradingview/scripts/ta_sweep_single.py {TICKER} [--persist]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ── Path Resolution ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
TV_CLI = REPO_ROOT / "tradingview-cdp/cli.js"
DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
INTEL_DB_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite"
INTEL_JSONL_PATH = REPO_ROOT / "investment_screener/backend/data/intelligence_events.jsonl"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from intelligence.event_store import append_event  # noqa: E402
from intelligence.replay_ledger import replay_events_to_db  # noqa: E402
from intelligence.db_client import initialize_db as init_intel_db  # noqa: E402
from domain_model.projection_repository import get_latest_projection, get_projection_scenarios  # noqa: E402
from domain_model.db_client import initialize_db as init_domain_db  # noqa: E402


def fetch_tv_data(ticker: str) -> Dict[str, Any]:
    """Reads real-time indicators from TradingView Data Window via CDP."""
    clean_sym = ticker.upper()
    try:
        subprocess.run(["node", str(TV_CLI), "chart", "symbol", clean_sym], check=True, capture_output=True, text=True)
        subprocess.run(["node", str(TV_CLI), "chart", "openDataWindow"], check=True, capture_output=True, text=True)
        res = subprocess.run(["node", str(TV_CLI), "chart", "read"], check=True, capture_output=True, text=True)
        out = json.loads(res.stdout)
        if out.get("success") and "data" in out:
            data = out["data"]
            return {
                "ticker": clean_sym,
                "close": float(data.get("Close", 0.0) or 0.0),
                "emaFast": float(data.get("EMA Fast", 0.0) or 0.0),
                "emaMid": float(data.get("EMA Mid", 0.0) or 0.0),
                "emaSlow": float(data.get("EMA Slow", 0.0) or 0.0),
                "adx": float(data.get("ADX", 20.0) or 20.0),
                "volBias": float(data.get("Vol Bias %", "0.0").replace("−", "-") or 0.0),
                "atr": float(data.get("ATR", 0.0) or 0.0),
                "squeezeOn": float(data.get("Squeeze", 0.0) or 0.0) != 0.0,
                "rsi": 50.0,
            }
    except Exception as err:
        print(f"[WARN] TV CDP extraction failed for {clean_sym}: {err}", file=sys.stderr)

    return {
        "ticker": clean_sym,
        "close": 0.0,
        "emaFast": 0.0,
        "emaMid": 0.0,
        "emaSlow": 0.0,
        "adx": 20.0,
        "volBias": 0.0,
        "atr": 0.0,
        "squeezeOn": False,
        "rsi": 50.0,
    }


def enrich_with_dcf(telemetry: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    """Enriches technical telemetry with latest DCF scenario targets from SQLite."""
    if not DB_PATH.exists():
        return telemetry

    conn = init_domain_db(str(DB_PATH))
    try:
        latest = get_latest_projection(conn, ticker.upper())
        if latest:
            fv = latest.get("fair_value")
            scenarios = get_projection_scenarios(conn, latest["projection_id"])
            base_p = next((s["scenario_price"] for s in scenarios if s.get("scenario_name") == "base"), None)
            bear_p = next((s["scenario_price"] for s in scenarios if s.get("scenario_name") == "bear"), None)
            bull_p = next((s["scenario_price"] for s in scenarios if s.get("scenario_name") == "bull"), None)
            telemetry["dcf"] = {
                "fairValue": fv,
                "base": base_p,
                "bear": bear_p,
                "bull": bull_p,
            }
    except Exception as e:
        print(f"[WARN] DCF lookup failed for {ticker}: {e}", file=sys.stderr)
    finally:
        conn.close()

    return telemetry


def persist_sweep(payload: Dict[str, Any]) -> None:
    """Appends to the canonical event ledger and materializes to intelligence.sqlite."""
    scan_date = datetime.now(timezone.utc).date().isoformat()
    ticker = payload["ticker"]

    append_event(
        str(INTEL_JSONL_PATH),
        event_type="TECHNICAL_SWEEP",
        effective_at=scan_date,
        status="ACTIVE",
        title=f"TA Sweep for {ticker}",
        body_markdown=f"Single-ticker technical indicators for {ticker}.",
        ticker=ticker,
        source_id="tradingview-cdp",
        payload=payload,
        idempotency_key=f"ta-sweep-{ticker}-{scan_date}",
    )

    conn = init_intel_db(str(INTEL_DB_PATH))
    try:
        replay_events_to_db(str(INTEL_JSONL_PATH), conn)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Single-ticker TA sweep with canonical persistence")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. STM, IREN, AAPL)")
    parser.add_argument("--persist", action="store_true", default=True, help="Persist to intelligence.sqlite")
    parser.add_argument("--json", action="store_true", help="Print JSON result to stdout")
    args = parser.parse_args()

    clean_sym = args.ticker.upper()
    telemetry = fetch_tv_data(clean_sym)
    enriched = enrich_with_dcf(telemetry, clean_sym)

    if args.persist:
        persist_sweep(enriched)
        print(f"✓ Canonical TECHNICAL_SWEEP event persisted for {clean_sym}", file=sys.stderr)

    if args.json or not sys.stdout.isatty():
        print(json.dumps(enriched, indent=2))


if __name__ == "__main__":
    main()
