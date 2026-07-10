#!/usr/bin/env python3
"""
rebalancer.py (Python Service)
=====================================

Purpose:
    Formalizes /rebalance + portfolio_action.py's informal drift/capital/
    account logic into a real engine: per-holding drift bands (not point
    targets), a risk-budget check against E1's risk_snapshot.json,
    Canada-aware account/tax placement, and an ordered sells-before-buys
    order-plan output. Never mutates any input file — owns
    data/rebalance_plan.json exclusively. See docs/superpowers/specs/
    2026-07-09-rebalancer-v2-design.md.

Layer: Backend / Python Services / Rebalancer

Usage:
    python3 rebalancer.py --pretty
    python3 rebalancer.py --no-save --pretty
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portfolio_io import load_portfolio_state, compute_weights  # noqa: E402
from ticker_aliases import normalize_ticker  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
RISK_SNAPSHOT_PATH = DATA_DIR / "risk_snapshot.json"
THESIS_BREAKER_STATE_PATH = DATA_DIR / "thesis_breaker_state.json"
ACCOUNT_POLICY_PATH = DATA_DIR / "account_policy.json"
PROJECTIONS_DIR = DATA_DIR / "projections"
REBALANCE_PLAN_PATH = DATA_DIR / "rebalance_plan.json"

DEFAULT_BAND_CONFIG: dict[str, float] = {"relativePct": 20.0, "absolutePct": 1.5, "criticalMultiplier": 2.0}


def compute_bands(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    band_config: dict[str, float] = DEFAULT_BAND_CONFIG,
) -> dict[str, dict[str, Any]]:
    """Per-holding no-churn band: max(relative %, absolute pp) around targetWeight.

    A holding whose actual drift falls within its band gets no rebalance
    order generated this run — this is what kills churn/small-order noise
    vs. a flat point-target comparison.

    Args:
        current_weights: {ticker: weight_pct} (0-100 scale), actual broker weights.
        target_weights: {ticker: weight_pct} (0-100 scale), from target-portfolio.json.
        band_config: {"relativePct": float, "absolutePct": float} — band =
            max(targetWeight * relativePct/100, absolutePct).

    Returns:
        {ticker: {"currentWeight", "targetWeight", "bandPct", "driftPct", "inBand"}}
        for the union of tickers in either input (a ticker missing from one
        side is treated as 0.0 on that side).
    """
    tickers = set(current_weights) | set(target_weights)
    result: dict[str, dict[str, Any]] = {}
    for t in tickers:
        current = current_weights.get(t, 0.0)
        target = target_weights.get(t, 0.0)
        drift = current - target
        band_pct = max(target * band_config["relativePct"] / 100.0, band_config["absolutePct"])
        result[t] = {
            "currentWeight": round(current, 4),
            "targetWeight": round(target, 4),
            "bandPct": round(band_pct, 4),
            "driftPct": round(drift, 4),
            "inBand": abs(drift) <= band_pct,
        }
    return result


def get_latest_valuation_action(ticker: str, projections_dir: Path) -> str | None:
    """Latest AI projection's aiThesis.action for a ticker, or None if unavailable.

    Mirrors portfolio_action.py's _load_ai_upside() latest-AI_AGENT-projection
    selection, but returns the raw action string instead of computed upside —
    this is the actual "EXIT/SELL-gated" signal the rebalancer must never buy
    against (not derive_action()'s portfolio-weight ratio label).

    Args:
        ticker: Ticker to look up.
        projections_dir: Path to data/projections/.

    Returns:
        The latest AI_AGENT projection's aiThesis.action, or None if the
        projection file is missing, empty, or malformed.
    """
    path = projections_dir / f"{ticker}.json"
    if not path.exists():
        return None
    try:
        projs = json.loads(path.read_text())
        if isinstance(projs, list):
            if not projs:
                return None
            ai = [p for p in projs if p.get("source") == "AI_AGENT"]
            proj = max(ai, key=lambda x: x.get("savedAt", "")) if ai else projs[0]
        else:
            proj = projs
        return proj.get("aiThesis", {}).get("action")
    except Exception:
        return None


def compute_candidate_orders(
    bands: dict[str, dict[str, Any]],
    target_data: dict[str, Any],
    prices: dict[str, float],
    total_usd: float,
    projections_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Turn out-of-band holdings into raw candidate orders (pre-account-routing).

    Applies the hard-rule exclusions that remove an order entirely (never
    warnings): never buys an EXIT/SELL-rated holding, never buys above
    targetEntryPrice, and downgrades to a no-op when a standingDecision is
    present (same "signal stands but no trade proposed without your
    direction" framing brief_recommendations.py already uses for EXIT/REDUCE).
    Sells are never gated — an overweight EXIT-rated or standing-decision
    holding should still be trimmed toward target.

    Args:
        bands: Output of compute_bands().
        target_data: Parsed target-portfolio.json (targetEntryPrice,
            standingDecision per holding).
        prices: {ticker: current_price}.
        total_usd: Broker-authoritative portfolio total (never shares×price).
        projections_dir: Path to data/projections/.

    Returns:
        (candidate_orders, skipped_restores).
    """
    holdings_by_ticker = {h["ticker"]: h for h in target_data.get("holdings", [])}
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for ticker, band in bands.items():
        if band["inBand"]:
            continue
        price = prices.get(ticker)
        if not price or price <= 0:
            continue
        holding = holdings_by_ticker.get(ticker, {})
        drift_dollars = abs(band["driftPct"]) / 100.0 * total_usd
        shares = math.floor(drift_dollars / price)

        if band["driftPct"] > 0:
            if shares <= 0:
                continue
            candidates.append({
                "ticker": ticker, "action": "sell", "shares": shares,
                "currentWeight": band["currentWeight"], "targetWeight": band["targetWeight"],
            })
            continue

        # Buy-side hard gates are evaluated before the zero-share check so a
        # skip reason is still recorded even when the drift-dollar amount
        # floors to 0 shares at the current price (e.g. high-priced tickers).
        valuation_action = get_latest_valuation_action(ticker, projections_dir)
        if valuation_action in ("EXIT", "SELL"):
            skipped.append({"ticker": ticker, "reason": f"{valuation_action}-rated — not restoring"})
            continue

        entry_cap = holding.get("targetEntryPrice")
        if entry_cap is not None and price > entry_cap:
            skipped.append({
                "ticker": ticker,
                "reason": f"Price ${price:.2f} above targetEntryPrice ${entry_cap:.2f}",
            })
            continue

        standing = holding.get("standingDecision")
        if standing:
            skipped.append({
                "ticker": ticker,
                "reason": f"Standing decision ({standing.get('type', 'USER')}): "
                          f"{standing.get('reason', '')} Signal stands but no trade "
                          f"proposed without your direction.",
            })
            continue

        if shares <= 0:
            continue

        candidates.append({
            "ticker": ticker, "action": "buy", "shares": shares,
            "currentWeight": band["currentWeight"], "targetWeight": band["targetWeight"],
        })

    return candidates, skipped


def load_account_positions(
    portfolio_path: Path = PORTFOLIO_PATH,
) -> tuple[dict[str, dict[str, dict[str, float | None]]], dict[str, float], dict[str, str]]:
    """Per-account share/cost-basis positions, preferring real tvSnapshot data.

    Reads portfolio.json's tvSnapshot.snapshots[].positions for real
    per-account splits (with avgFillPrice as cost basis) when present. Falls
    back to mirroring TFSA at ~1/3 share count for RRSP (this repo's
    documented account structure) for any account tvSnapshot doesn't cover.

    Args:
        portfolio_path: Path to portfolio.json.

    Returns:
        (account_positions, account_cash_usd, account_source) —
        account_positions[account][ticker] = {"shares", "costBasis"};
        account_cash_usd[account] is that account's USD cash balance (a
        separate dict, not folded into account_positions — see this
        function's Interfaces note on why); account_source[account] is
        "tvSnapshot" or "heuristic_1_3_mirror".
    """
    raw = json.loads(Path(portfolio_path).read_text())
    snapshots = (raw.get("tvSnapshot") or {}).get("snapshots", [])

    positions: dict[str, dict[str, dict[str, float | None]]] = {}
    cash_usd: dict[str, float] = {}
    source: dict[str, str] = {}
    synced_accounts: set[str] = set()

    for snap in snapshots:
        acct = snap.get("accountType")
        if not acct:
            continue
        synced_accounts.add(acct)
        acct_positions: dict[str, dict[str, float | None]] = {}
        for p in snap.get("positions", []):
            sym = normalize_ticker(p.get("symbol", ""))
            if not sym:
                continue
            acct_positions[sym] = {
                "shares": float(p.get("quantity") or 0),
                "costBasis": float(p["avgFillPrice"]) if p.get("avgFillPrice") else None,
            }
        balances = snap.get("balances", {})
        cash_usd[acct] = float(balances.get("cashUSDCombined") or balances.get("cashUSD") or 0)
        positions[acct] = acct_positions
        source[acct] = "tvSnapshot"

    if synced_accounts and "RRSP" not in synced_accounts and "TFSA" in positions:
        rrsp_positions: dict[str, dict[str, float | None]] = {}
        for sym, pos in positions["TFSA"].items():
            mirrored = math.floor(pos["shares"] / 3)
            if mirrored > 0:
                rrsp_positions[sym] = {"shares": float(mirrored), "costBasis": pos["costBasis"]}
        positions["RRSP"] = rrsp_positions
        cash_usd["RRSP"] = 0.0
        source["RRSP"] = "heuristic_1_3_mirror"

    return positions, cash_usd, source


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebalance order plan")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"status": "scaffold — orchestrator added in Task 8"}, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
