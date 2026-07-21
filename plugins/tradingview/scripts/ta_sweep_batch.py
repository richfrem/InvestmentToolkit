#!/usr/bin/env python3
"""
ta_sweep_batch.py — Daily TA sweep across all active portfolio holdings.
=========================================================================

Purpose:
    Reads portfolio.json for current holdings, runs a batch CDP scan via
    tradingview-cdp/cli.js sweep, cross-references DCF projections and
    target-portfolio.json for context, then outputs enriched JSON to stdout.

Layer:
    Plugins / TradingView

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Reads holdings)
    - investment_screener/backend/data/theses/target-portfolio.json (Reads target weights)
    - investment_screener/backend/data/domain_model.sqlite (Reads DCF valuations, ADR-029)

Usage:
    python3 plugins/tradingview/scripts/ta_sweep_batch.py [--skip TICKERS]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT       = Path(__file__).resolve().parents[3]
PORTFOLIO_PATH  = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
TARGET_PATH     = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
DB_PATH         = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
TV_CLI          = REPO_ROOT / "tradingview-cdp/cli.js"

# Default output path — served by backend as /api/ta-sweep/results
TA_SWEEP_RESULTS_PATH = REPO_ROOT / "investment_screener/backend/data/ta-sweep-results.json"

# Always skip — cash / non-equity entries. "CASH_USD" is the domain_model.sqlite
# symbol for the cash position (Wave 3 cutover); "USD_CASH" was the legacy
# portfolio.json symbol — both kept so neither source can leak a cash "ticker".
DEFAULT_SKIP: set[str] = {"PSU.U.TO", "PSU-U.TO", "USD_CASH", "CASH_USD"}

# --validate mode: local (technicals.py) vs. TV Data Window cross-check
DIVERGENCE_THRESHOLD_PTS = 2.0

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from technicals import compute_technical_snapshot  # noqa: E402
from portfolio_io import load_portfolio_state  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection,
    get_projection_scenarios,
)


# ── Data loaders ───────────────────────────────────────────────────────────────

def load_portfolio() -> list[dict[str, Any]]:
    """Return current holdings as ``[{"symbol": ...}, ...]`` from domain_model.sqlite.

    Wave 3 cutover: the holdings universe is read from SQLite via
    ``portfolio_io.load_portfolio_state()`` (whose ``shares`` dict is keyed by
    the aggregated-across-accounts symbol), not the plain ``holdings`` array in
    portfolio.json. The only field this consumer needs is ``symbol`` (see
    main()'s ticker-filtering loop), so each holding is projected down to that
    single key rather than reconstructing the full JSON holding shape.
    """
    state = load_portfolio_state(PORTFOLIO_PATH)
    return [{"symbol": symbol} for symbol in state["shares"]]


def load_target_portfolio() -> dict[str, dict[str, Any]]:
    """Return target-portfolio holdings keyed by ticker."""
    with open(TARGET_PATH) as f:
        data = json.load(f)
    return {h["ticker"]: h for h in data.get("holdings", [])}


def load_dcf(ticker: str, db_path: Path | None = None) -> dict[str, Any] | None:
    """Load the most recent DCF projection for ticker, or None if not found.

    Storage backend (Wave 1 Task 7B): reads `projection_version`/
    `projection_scenario` via `domain_model.projection_repository`, not
    `projections/{TICKER}.json` directly (ADR-029). The original code took
    `raw[-1]` (the last array element, i.e. highest MAX(version) for an
    append-only file) with no `source` filter, so this uses plain
    `get_latest_projection` — no AI_AGENT preference, matching the original's
    lack of source filtering.
    """
    conn = initialize_db(str(db_path or DB_PATH))
    try:
        row = conn.execute(
            "SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,)
        ).fetchone()
        if row is None:
            return None
        investment_id = row[0]
        entry = get_latest_projection(conn, investment_id)
        if entry is None:
            return None
        scenario_rows = get_projection_scenarios(conn, entry["projection_id"])
        scenarios = {r["scenario_name"]: r for r in scenario_rows}
        return {
            "fairValue": entry.get("fair_value"),
            "action":    entry.get("action"),
            "bear":      (scenarios.get("bear") or {}).get("scenario_price"),
            "base":      (scenarios.get("base") or {}).get("scenario_price"),
            "bull":      (scenarios.get("bull") or {}).get("scenario_price"),
        }
    finally:
        conn.close()


# ── CDP sweep ──────────────────────────────────────────────────────────────────

def run_sweep(tickers: list[str], delay_ms: int = 1500) -> list[dict[str, Any]]:
    """Invoke cli.js sweep and return parsed JSON results.

    Args:
        tickers:  List of ticker symbols to scan.
        delay_ms: CDP wait between symbol switch and data window read.

    Returns:
        List of per-ticker scan dicts from sweep.js.

    Raises:
        RuntimeError: If cli.js sweep exits non-zero.
    """
    cmd = [
        "node", str(TV_CLI),
        "sweep",
        "--tickers", ",".join(tickers),
        "--delay",   str(delay_ms),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"sweep failed (exit {result.returncode}):\n{result.stderr[:600]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON parse error: {exc}\nOutput: {result.stdout[:400]}") from exc


# ── Enrichment ─────────────────────────────────────────────────────────────────

def add_dcf_flags(result: dict[str, Any], dcf: dict[str, Any] | None) -> None:
    """Append DCF-relative flags and attach dcf context to result in-place.

    Args:
        result: Per-ticker sweep result dict (mutated in-place).
        dcf:    DCF projection dict, or None if unavailable.
    """
    if not dcf:
        return
    fv    = dcf.get("fairValue")
    price = result.get("close")
    if not fv or not price:
        result["dcf"] = dcf
        return

    ratio = price / fv
    flags = result.setdefault("flags", [])
    if ratio > 0.95:
        flags.append("NEAR_FV")
    if ratio > 1.0:
        flags.append("ABOVE_FV")
    if ratio < 0.75:
        flags.append("DEEP_VALUE")

    result["dcf"] = {
        "fairValue": round(fv, 2),
        # % move from current price to fair value — denominator must be price.
        # (fv − price) / fv understates upside and can print impossible values
        # like −742% on deep-SELL names (a price-relative gap floors at −100%).
        "pctToFV":   round((fv - price) / price * 100, 1),
        "base":      dcf.get("base"),
        "action":    dcf.get("action"),
    }


def add_local_validation(result: dict[str, Any], snapshot_fn: Any = compute_technical_snapshot) -> dict[str, Any]:
    """Cross-check TV Data Window rsi/adx against technicals.py's local computation.

    Args:
        result: Per-ticker sweep result dict (must have "ticker"; "rsi"/"adx"
            keys are the TV-scraped values, absent or None if the scrape
            didn't produce them).
        snapshot_fn: Injectable — defaults to the real technicals.py call;
            tests pass a stub instead of hitting the network.

    Returns:
        A new dict (result plus a "localValidation" block) — does not mutate
        the input, matching validate_adx()'s existing copy-on-write pattern.
    """
    snapshot = snapshot_fn(result["ticker"], "D", "3mo", "SPY", None)
    result = {**result}
    result["localValidation"] = {}
    for tv_key, local_key in (("rsi", "rsi14"), ("adx", "adx14")):
        tv_value = result.get(tv_key)
        local_value = snapshot.get(local_key)
        divergence = abs(local_value - tv_value) if (local_value is not None and tv_value is not None) else None
        result["localValidation"][tv_key] = {
            "local": local_value,
            "tv": tv_value,
            "divergencePts": round(divergence, 2) if divergence is not None else None,
            "flag": bool(divergence is not None and divergence > DIVERGENCE_THRESHOLD_PTS),
        }
    return result


def derive_action(result: dict[str, Any], _target: dict[str, Any] | None) -> str:
    """Derive an action suggestion from flags and thesis context.

    Args:
        result: Enriched sweep result.
        target: Matching target-portfolio holding, or None.

    Returns:
        One of: ACCUMULATE, REDUCE, MONITOR, HOLD.
    """
    flags = set(result.get("flags", []))

    # Oversold + accumulation signal → strong buy
    if "RSI_OS" in flags:
        return "ACCUMULATE"
    if "ACCUM_SIGNAL" in flags and "DEEP_VALUE" in flags:
        return "ACCUMULATE"

    # Overbought at or above fair value → reduce
    if "ABOVE_FV" in flags:
        return "REDUCE"
    if "RSI_OB" in flags and ("NEAR_FV" in flags or "ABOVE_FV" in flags or "DIST_SIGNAL" in flags):
        return "REDUCE"

    # Distribution + weak volume on move → monitor closely
    if "DIST_SIGNAL" in flags and "VOLUME_DRY" in flags:
        return "MONITOR"
    if "VOLUME_SPIKE" in flags:
        return "MONITOR"
    if "BIG_DAY" in flags:
        return "MONITOR"
    if "SQUEEZE_ON" in flags:
        return "MONITOR"

    return "HOLD"


# ── Post-processing ────────────────────────────────────────────────────────────

def validate_adx(result: dict[str, Any]) -> dict[str, Any]:
    """Null out ADX values outside the valid 0–100 range and remove stale ADX flags.

    ADX from ta.dmi() is always 0–100. Negative or >100 values indicate a Data Window
    field collision (another indicator using the same 'ADX' key). Until the Pine Script
    is updated to use a unique key ('AI-ADX'), this guards against false ADX_WEAK /
    ADX_STRONG flags.

    Args:
        result: Per-ticker sweep result dict (mutated in-place copy).

    Returns:
        Result dict with adx=None and ADX flags removed when value is out of range.
    """
    adx = result.get("adx")
    if adx is not None and not (0 <= adx <= 100):
        result = {**result}  # shallow copy — don't mutate caller's dict
        result["adx"] = None
        result["flags"] = [f for f in result.get("flags", []) if not f.startswith("ADX_")]
    return result


def enrich_results(
    scan_results: list[dict[str, Any]],
    target_map: dict[str, dict[str, Any]],
    dcf_loader: Any = None,
) -> list[dict[str, Any]]:
    """Apply DCF flags, ADX validation, and action derivation to sweep rows.

    validate_adx returns a shallow copy when it nulls an out-of-range ADX —
    all enrichment must be applied to (and returned from) that copy, otherwise
    the persisted output silently keeps the invalid ADX and loses the derived
    action/target fields.

    Args:
        scan_results: Raw per-ticker rows from sweep.js.
        target_map:   target-portfolio holdings keyed by ticker.
        dcf_loader:   Callable ticker → DCF dict or None (defaults to load_dcf).

    Returns:
        New list of fully enriched rows.
    """
    if dcf_loader is None:
        dcf_loader = load_dcf
    enriched: list[dict[str, Any]] = []
    for res in scan_results:
        ticker = res["ticker"]
        target = target_map.get(ticker)
        add_dcf_flags(res, dcf_loader(ticker))
        res = validate_adx(res)
        res["action"]       = derive_action(res, target)
        res["targetAction"] = (target or {}).get("action")
        res["targetWeight"] = (target or {}).get("targetWeight")
        enriched.append(res)
    return enriched


def save_sweep_results(
    results: list[dict[str, Any]],
    output_path: Path,
    jsonl_path: Path | None = None,
    db_path: Path | None = None,
) -> None:
    """Persist sweep results to a timestamped JSON file for backend/frontend consumption
    AND write TECHNICAL_SWEEP events to the ledger and SQLite read-model (dual-write).

    Writes {timestamp, scan_date, count, results} — overwrites any prior file.
    Consumed by the backend /api/ta-sweep/results endpoint and the TA Summary panel.

    Args:
        results:     Enriched per-ticker sweep results from main sweep loop.
        output_path: Destination file path (default: ta-sweep-results.json in backend/data/).
        jsonl_path:  Optional path to observations.jsonl ledger.
        db_path:     Optional path to intelligence.sqlite database.
    """
    now = datetime.now(timezone.utc)
    scan_date = now.strftime("%Y-%m-%d")
    payload: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "scan_date": scan_date,
        "count":     len(results),
        "results":   results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)

    # 2. Append TECHNICAL_SWEEP events to observations.jsonl ledger
    from intelligence.event_store import append_event, _default_jsonl_path
    from intelligence.replay_ledger import replay_events_to_db
    from intelligence.db_client import initialize_db
    import sqlite3
    import sys

    # Testing guardrail: bypass writing to real ledger during generic tests that do not configure mock paths
    if "pytest" in sys.modules and jsonl_path is None and db_path is None:
        return

    resolved_jsonl_path = jsonl_path or _default_jsonl_path()
    resolved_db_path = db_path or (REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite")


    for res in results:
        ticker = res["ticker"]
        # Convert any negative or invalid ADX/RSI values to string or omit if not matching bounds,
        # but the payload_json will contain the full dict cleanly.
        append_event(
            str(resolved_jsonl_path),
            event_type="TECHNICAL_SWEEP",
            effective_at=scan_date,
            status="ACTIVE",
            title=f"TA Sweep for {ticker}",
            body_markdown=f"Batch technical indicators for {ticker}.",
            ticker=ticker,
            source_id="tradingview-cdp",
            payload=res,
            idempotency_key=f"ta-sweep-{ticker}-{scan_date}",
        )

    # 3. Replay to SQLite read-model
    conn = initialize_db(str(resolved_db_path))
    try:
        replay_events_to_db(str(resolved_jsonl_path), conn)
    finally:
        conn.close()



# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point — run sweep, enrich results, print JSON to stdout, and optionally persist."""
    parser = argparse.ArgumentParser(description="Daily TA sweep across portfolio holdings")
    parser.add_argument("--skip",  default="", help="Extra comma-separated tickers to skip")
    parser.add_argument("--delay", default="1500", help="CDP wait ms per ticker (default 1500)")
    parser.add_argument(
        "--save-results",
        nargs="?",
        const=str(TA_SWEEP_RESULTS_PATH),
        metavar="PATH",
        help="Save results to ta-sweep-results.json (default path) or a custom PATH",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Suppress auto-save (overrides default auto-save behaviour)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Cross-check TV rsi/adx against technicals.py's local computation, flag >2pt divergence",
    )
    args = parser.parse_args()

    extra_skip: set[str] = set(args.skip.upper().split(",")) if args.skip else set()
    skip = DEFAULT_SKIP | extra_skip

    holdings = load_portfolio()
    tickers  = [h["symbol"] for h in holdings if h.get("symbol") and h["symbol"] not in skip]
    delay_ms = int(args.delay)

    print(f"Scanning {len(tickers)} holdings...", file=sys.stderr)

    scan_results = run_sweep(tickers, delay_ms=delay_ms)
    target_map   = load_target_portfolio()
    scan_results = enrich_results(scan_results, target_map)

    if args.validate:
        scan_results = [add_local_validation(r) for r in scan_results]

    print(json.dumps(scan_results, indent=2))

    # Auto-save to backend/data/ unless suppressed — enables /api/ta-sweep/results endpoint
    if not args.no_save:
        save_path = Path(args.save_results) if args.save_results else TA_SWEEP_RESULTS_PATH
        save_sweep_results(scan_results, save_path)
        print(f"Results saved → {save_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
