"""
Daily TA sweep across all active portfolio holdings.

Reads portfolio.json for current holdings, runs a batch CDP scan via
tradingview-cdp/cli.js sweep, cross-references DCF projections and
target-portfolio.json for context, then outputs enriched JSON to stdout.

The SKILL.md (ta-daily-sweep) calls this script and formats the report.

Usage:
    python3 plugins/tradingview/scripts/ta_sweep_batch.py [--skip TICKERS]
    python3 plugins/tradingview/scripts/ta_sweep_batch.py --skip HUMN,WYFI

Args:
    --skip: Extra tickers to exclude beyond the default skip list.
    --delay: CDP wait ms per ticker (default 1500, use 1200 for speed).
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
PROJECTIONS_DIR = REPO_ROOT / "investment_screener/backend/data/projections"
TV_CLI          = REPO_ROOT / "tradingview-cdp/cli.js"

# Default output path — served by backend as /api/ta-sweep/results
TA_SWEEP_RESULTS_PATH = REPO_ROOT / "investment_screener/backend/data/ta-sweep-results.json"

# Always skip — cash / non-equity entries
DEFAULT_SKIP: set[str] = {"PSU.U.TO", "PSU-U.TO", "USD_CASH"}


# ── Data loaders ───────────────────────────────────────────────────────────────

def load_portfolio() -> list[dict[str, Any]]:
    """Return holdings list from portfolio.json."""
    with open(PORTFOLIO_PATH) as f:
        return json.load(f).get("holdings", [])


def load_target_portfolio() -> dict[str, dict[str, Any]]:
    """Return target-portfolio holdings keyed by ticker."""
    with open(TARGET_PATH) as f:
        data = json.load(f)
    return {h["ticker"]: h for h in data.get("holdings", [])}


def load_dcf(ticker: str) -> dict[str, Any] | None:
    """Load the most recent DCF projection for ticker, or None if not found."""
    path = PROJECTIONS_DIR / f"{ticker}.json"
    if not path.exists():
        return None
    with open(path) as f:
        raw = json.load(f)
    entry = raw[-1] if isinstance(raw, list) else raw
    thesis    = entry.get("aiThesis", {})
    scenarios = entry.get("scenarios", {})
    return {
        "fairValue": thesis.get("fairValue"),
        "action":    thesis.get("action"),
        "bear":      (scenarios.get("bear") or {}).get("scenarioPrice"),
        "base":      (scenarios.get("base") or {}).get("scenarioPrice"),
        "bull":      (scenarios.get("bull") or {}).get("scenarioPrice"),
    }


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
        "pctToFV":   round((fv - price) / fv * 100, 1),
        "base":      dcf.get("base"),
        "action":    dcf.get("action"),
    }


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


def save_sweep_results(results: list[dict[str, Any]], output_path: Path) -> None:
    """Persist sweep results to a timestamped JSON file for backend/frontend consumption.

    Writes {timestamp, scan_date, count, results} — overwrites any prior file.
    Consumed by the backend /api/ta-sweep/results endpoint and the TA Summary panel.

    Args:
        results:     Enriched per-ticker sweep results from main sweep loop.
        output_path: Destination file path (default: ta-sweep-results.json in backend/data/).
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "scan_date": now.strftime("%Y-%m-%d"),
        "count":     len(results),
        "results":   results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)


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
    args = parser.parse_args()

    extra_skip: set[str] = set(args.skip.upper().split(",")) if args.skip else set()
    skip = DEFAULT_SKIP | extra_skip

    holdings = load_portfolio()
    tickers  = [h["symbol"] for h in holdings if h.get("symbol") and h["symbol"] not in skip]
    delay_ms = int(args.delay)

    print(f"Scanning {len(tickers)} holdings...", file=sys.stderr)

    scan_results = run_sweep(tickers, delay_ms=delay_ms)
    target_map   = load_target_portfolio()

    for res in scan_results:
        ticker = res["ticker"]
        dcf    = load_dcf(ticker)
        target = target_map.get(ticker)
        add_dcf_flags(res, dcf)
        res          = validate_adx(res)
        res["action"]       = derive_action(res, target)
        res["targetAction"] = (target or {}).get("action")
        res["targetWeight"] = (target or {}).get("targetWeight")

    print(json.dumps(scan_results, indent=2))

    # Auto-save to backend/data/ unless suppressed — enables /api/ta-sweep/results endpoint
    if not args.no_save:
        save_path = Path(args.save_results) if args.save_results else TA_SWEEP_RESULTS_PATH
        save_sweep_results(scan_results, save_path)
        print(f"Results saved → {save_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
