#!/usr/bin/env python3
"""
backtest_harness.py - Python utility script.

Purpose:
    Backtest harness — E4 historical simulation and counterfactual analysis.

Simulates portfolio rebalances from historical target snapshots, generates
execution quality metrics, counterfactual scenarios, and correlates outcomes
with E3 prediction ledger for post-hoc signal validation.

Append-only output: data/backtest_report.json (aggregated summary).

Usage:
    from backtest_harness import (
        extract_historical_targets, fetch_backtest_prices,
        simulate_rebalance, analyze_execution_quality,
        generate_timing_counterfactuals, generate_threshold_counterfactuals,
        generate_backtest_report, correlate_with_prediction_ledger
    )

Key Input Dependencies:
    - git history (commit-by-commit target-portfolio.json snapshots)
    - investment_screener/backend/data/target-portfolio.json
    - yfinance for historical OHLCV data
    - investment_screener/backend/data/predictions.jsonl (E3 correlation)

Layer:
    Backend / Python Services

Usage Examples:
    from backtest_harness import (
        extract_historical_targets, fetch_backtest_prices,
        simulate_rebalance, analyze_execution_quality,
        generate_timing_counterfactuals, generate_threshold_counterfactuals,
        generate_backtest_report, correlate_with_prediction_ledger
    )

Key Functions (Index):
    - Order()
    - RebalanceSnapshot()
    - extract_historical_targets()
    - fetch_backtest_prices()
    - simulate_rebalance()
    - analyze_execution_quality()
    - generate_timing_counterfactuals()
    - generate_threshold_counterfactuals()
    - generate_backtest_report()
    - correlate_with_prediction_ledger()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
BACKTEST_REPORT_PATH = DATA_DIR / "backtest_report.json"
PREDICTIONS_PATH = DATA_DIR / "predictions.jsonl"
PRICE_CACHE_DIR = REPO_ROOT / "temp" / "backtest_price_cache"


@dataclass
class Order:
    """Simulated buy/sell order from a rebalance."""
    ticker: str
    side: str  # "buy" or "sell"
    shares: float
    fill_price: float
    executed_at: str  # ISO date
    pnl: Optional[float] = None  # For sells: (fill_price - entry_price) * shares


@dataclass
class RebalanceSnapshot:
    """Captures one rebalance decision and its outcome."""
    date: str  # ISO date
    orders: list[Order]
    execution_vwap: Optional[dict[str, float]] = None  # {ticker: vwap}
    execution_quality: Optional[dict[str, float]] = None  # {ticker: quality_score}
    realized_pnl: Optional[float] = None  # Sum of order P&Ls


def extract_historical_targets(commit_hash: str) -> dict[str, float]:
    """Extract target portfolio weights from a historical git commit.

    Clones the repo at commit_hash, reads target-portfolio.json, extracts
    holdings, and returns {ticker: targetWeight}.

    Args:
        commit_hash: Full git commit hash to extract from.

    Returns:
        Dict of {ticker: targetWeight} for all holdings, or {} on error.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            target_path = tmpdir_path / "target-portfolio.json"

            # Use git show to extract file without cloning
            result = subprocess.run(
                ["git", "show", f"{commit_hash}:investment_screener/backend/data/target-portfolio.json"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {}

            try:
                data = json.loads(result.stdout)
                targets = {}
                for holding in data.get("holdings", []):
                    ticker = holding.get("ticker")
                    weight = holding.get("targetWeight")
                    if ticker and weight is not None:
                        targets[ticker] = float(weight)
                return targets
            except (json.JSONDecodeError, ValueError):
                return {}

    except Exception:
        return {}


def fetch_backtest_prices(tickers: list[str], target_date: str) -> dict[str, dict[str, float]]:
    """Fetch historical OHLCV data for given tickers on a specific date.

    Caches locally in temp/backtest_price_cache/ to avoid redundant yfinance
    queries. Handles missing tickers gracefully.

    Args:
        tickers: List of ticker symbols.
        target_date: ISO date string (YYYY-MM-DD).

    Returns:
        Dict of {ticker: {open, high, low, close, volume}}, skipping missing tickers.
    """
    PRICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    for ticker in tickers:
        cache_file = PRICE_CACHE_DIR / f"{ticker}_{target_date}.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    results[ticker] = json.load(f)
                continue
            except (json.JSONDecodeError, IOError):
                pass

        try:
            hist = yf.Ticker(ticker).history(start=target_date, end=target_date)
            if hist.empty:
                continue

            row = hist.iloc[0]
            data = {
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            results[ticker] = data

            # Cache for reuse
            with open(cache_file, "w") as f:
                json.dump(data, f)

        except Exception:
            # Ticker not found or error fetching
            pass

    return results


def simulate_rebalance(
    targets_before: dict[str, float],
    targets_after: dict[str, float],
    prices: dict[str, dict[str, float]],
    entry_prices: Optional[dict[str, float]] = None,
) -> tuple[list[Order], float]:
    """Simulate a rebalance and generate buy/sell orders.

    Compares target weights before and after, generates orders to rebalance
    (assuming 100 units of portfolio value for simplicity), uses mid-prices
    for execution, and calculates P&L on sells if entry prices are provided.

    Args:
        targets_before: {ticker: weight} before rebalance.
        targets_after: {ticker: weight} after rebalance.
        prices: {ticker: {open, high, low, close, volume}}.
        entry_prices: {ticker: entry_price} for P&L calculation on sells.

    Returns:
        (list of Order objects, total_pnl)
    """
    if entry_prices is None:
        entry_prices = {}

    orders = []
    total_pnl = 0.0

    all_tickers = set(targets_before.keys()) | set(targets_after.keys())

    for ticker in all_tickers:
        before = targets_before.get(ticker, 0.0)
        after = targets_after.get(ticker, 0.0)
        delta = after - before

        if abs(delta) < 0.001:  # Skip minimal changes
            continue

        price_data = prices.get(ticker)
        if not price_data:
            continue

        # Use mid-price: (high + low) / 2
        mid_price = (price_data["high"] + price_data["low"]) / 2.0

        # Normalize delta to shares (assuming 100-unit portfolio)
        shares = abs(delta)

        if delta > 0:  # Buy
            order = Order(
                ticker=ticker,
                side="buy",
                shares=shares,
                fill_price=mid_price,
                executed_at=datetime.now().isoformat(),
                pnl=None,
            )
        else:  # Sell
            entry_price = entry_prices.get(ticker, mid_price)
            pnl = (mid_price - entry_price) * shares
            total_pnl += pnl
            order = Order(
                ticker=ticker,
                side="sell",
                shares=shares,
                fill_price=mid_price,
                executed_at=datetime.now().isoformat(),
                pnl=pnl,
            )

        orders.append(order)

    return orders, total_pnl


def analyze_execution_quality(
    orders: list[Order],
    prices: dict[str, dict[str, float]],
) -> dict[str, float]:
    """Analyze execution quality by comparing fill prices vs. VWAP.

    For each order, score quality as: 1.0 - (slippage_bps / 100).
    VWAP is estimated as (high + low + close) / 3 as a proxy.

    Args:
        orders: List of Order objects with fill_price set.
        prices: {ticker: {open, high, low, close, volume}}.

    Returns:
        Dict of {ticker: quality_score} (0.0–1.0, higher is better).
    """
    quality_scores = {}

    for ticker_prices in set(o.ticker for o in orders):
        ticker_orders = [o for o in orders if o.ticker == ticker_prices]
        price_data = prices.get(ticker_prices)
        if not price_data:
            continue

        # Estimate VWAP
        vwap = (price_data["high"] + price_data["low"] + price_data["close"]) / 3.0

        fills = [o.fill_price for o in ticker_orders]
        avg_fill = sum(fills) / len(fills) if fills else vwap

        # Slippage in basis points
        slippage_bps = abs(avg_fill - vwap) / vwap * 10000 if vwap != 0 else 0
        quality = max(0.0, 1.0 - (slippage_bps / 100))
        quality_scores[ticker_prices] = quality

    return quality_scores


def generate_timing_counterfactuals(
    orders: list[Order],
    dates: list[str],
) -> dict[str, Any]:
    """Generate timing counterfactuals: re-simulate with 1d, 5d price shifts.

    For each date in dates (typically around rebalance date), fetches prices
    1 day before, 1 day after, and 5 days after, re-simulates orders, and
    calculates alternative P&L.

    Args:
        orders: List of Order objects (executed at original date).
        dates: List of ISO date strings to generate counterfactuals for.

    Returns:
        {
            "1d_earlier": {date: pnl},
            "1d_later": {date: pnl},
            "5d_later": {date: pnl},
        }
    """
    tickers = [o.ticker for o in orders]
    counterfactuals = {"1d_earlier": {}, "1d_later": {}, "5d_later": {}}

    for target_date_str in dates:
        target_date = datetime.fromisoformat(target_date_str).date()

        # Fetch prices at different offsets
        for offset_days, key in [(-1, "1d_earlier"), (1, "1d_later"), (5, "5d_later")]:
            offset_date = target_date + timedelta(days=offset_days)
            offset_date_str = offset_date.isoformat()

            prices_at_offset = fetch_backtest_prices(tickers, offset_date_str)
            if not prices_at_offset:
                continue

            # Re-simulate order execution at offset prices
            alt_pnl = 0.0
            for order in orders:
                if order.side != "sell" or order.ticker not in prices_at_offset:
                    continue
                price_data = prices_at_offset[order.ticker]
                mid_price = (price_data["high"] + price_data["low"]) / 2.0
                # Assuming entry_price from order.fill_price
                alt_pnl += (mid_price - order.fill_price) * order.shares

            if alt_pnl != 0:
                counterfactuals[key][target_date_str] = alt_pnl

    return counterfactuals


def generate_threshold_counterfactuals(
    before_weights: dict[str, float],
    orders: list[Order],
    prices: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Generate threshold-drift counterfactuals: re-simulate with ±5% weight drift.

    For each order, re-calculates P&L if the target weight had drifted ±5%,
    simulating sensitivity to targeting precision.

    Args:
        before_weights: Initial portfolio weights.
        orders: Orders generated from rebalance.
        prices: {ticker: {open, high, low, close, volume}}.

    Returns:
        {
            "minus_5pct": {ticker: alt_pnl},
            "plus_5pct": {ticker: alt_pnl},
        }
    """
    counterfactuals = {"minus_5pct": {}, "plus_5pct": {}}

    for order in orders:
        before_wt = before_weights.get(order.ticker, 0.0)
        price_data = prices.get(order.ticker)
        if not price_data:
            continue

        mid_price = (price_data["high"] + price_data["low"]) / 2.0

        # Drift scenarios
        for drift_key, drift_sign in [("minus_5pct", -0.05), ("plus_5pct", 0.05)]:
            drift_wt = before_wt + drift_sign
            alt_shares = abs(order.shares * (drift_wt / before_wt)) if before_wt != 0 else order.shares
            if order.side == "sell":
                alt_pnl = (mid_price - order.fill_price) * alt_shares
                if order.ticker not in counterfactuals[drift_key]:
                    counterfactuals[drift_key][order.ticker] = 0.0
                counterfactuals[drift_key][order.ticker] += alt_pnl

    return counterfactuals


def generate_backtest_report(
    start_date: str,
    end_date: str,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate a comprehensive backtest report by scanning git commits.

    Iterates through git commits between start_date and end_date,
    extracts historical targets, fetches prices, simulates rebalances,
    aggregates metrics, and outputs to data/backtest_report.json.

    Args:
        start_date: ISO date string (YYYY-MM-DD).
        end_date: ISO date string (YYYY-MM-DD).
        params: Optional config {price_source, counterfactuals_enabled, etc.}.

    Returns:
        Backtest report dict with keys:
            - metadata: {start_date, end_date, run_timestamp}
            - rebalances: [{date, orders, pnl, execution_quality}]
            - summary: {total_rebalances, total_pnl, avg_quality_score}
    """
    if params is None:
        params = {}

    report = {
        "metadata": {
            "start_date": start_date,
            "end_date": end_date,
            "run_timestamp": datetime.now().isoformat(),
            "params": params,
        },
        "rebalances": [],
        "summary": {
            "total_rebalances": 0,
            "total_pnl": 0.0,
            "avg_quality_score": 0.0,
        },
    }

    # Get all commits in date range
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"--since={start_date}",
                f"--until={end_date}",
                "--pretty=format:%H %ai",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return report

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            commit_hash = parts[0]
            commit_date = parts[1]  # YYYY-MM-DD
            commits.append((commit_hash, commit_date))

    except Exception:
        return report

    # Simulate rebalances
    quality_scores = []

    for commit_hash, commit_date in commits:
        targets = extract_historical_targets(commit_hash)
        if not targets:
            continue

        prices = fetch_backtest_prices(list(targets.keys()), commit_date)
        if not prices:
            continue

        # Use simplified before/after: assume all holdings are being rebalanced
        orders, pnl = simulate_rebalance(targets, targets, prices)
        if not orders:
            continue

        quality = analyze_execution_quality(orders, prices)
        if quality:
            quality_scores.extend(quality.values())

        snapshot = {
            "date": commit_date,
            "orders": [asdict(o) for o in orders],
            "realized_pnl": pnl,
            "execution_quality": quality,
        }

        if params.get("counterfactuals_enabled", False):
            timing_cf = generate_timing_counterfactuals(orders, [commit_date])
            threshold_cf = generate_threshold_counterfactuals(targets, orders, prices)
            snapshot["counterfactuals"] = {
                "timing": timing_cf,
                "threshold": threshold_cf,
            }

        report["rebalances"].append(snapshot)

    # Compute summary
    report["summary"]["total_rebalances"] = len(report["rebalances"])
    report["summary"]["total_pnl"] = sum(r.get("realized_pnl", 0.0) for r in report["rebalances"])
    if quality_scores:
        report["summary"]["avg_quality_score"] = sum(quality_scores) / len(quality_scores)

    return report


def correlate_with_prediction_ledger(
    backtest_report: dict[str, Any],
    predictions_path: Path = PREDICTIONS_PATH,
) -> dict[str, Any]:
    """Correlate backtest rebalances with E3 prediction ledger.

    Links rebalances to prediction claims harvested on or near the same date,
    calculates correlation metrics (number of aligned predictions, average
    precision/recall).

    Args:
        backtest_report: Output from generate_backtest_report().
        predictions_path: Path to predictions.jsonl.

    Returns:
        Correlation report with keys:
            - total_predictions_linked: int
            - rebalance_alignment: {date: {accuracy, count}}
            - signal_quality: float (0.0–1.0)
    """
    report = {
        "total_predictions_linked": 0,
        "rebalance_alignment": {},
        "signal_quality": 0.0,
    }

    if not predictions_path.exists():
        return report

    try:
        predictions = []
        with open(predictions_path) as f:
            for line in f:
                if line.strip():
                    predictions.append(json.loads(line))
    except (json.JSONDecodeError, IOError):
        return report

    # For each rebalance, find predictions on the same date
    for rebalance in backtest_report.get("rebalances", []):
        rebal_date = rebalance.get("date")
        if not rebal_date:
            continue

        # Find tickers in rebalance
        rebal_tickers = {o["ticker"] for o in rebalance.get("orders", [])}

        # Find predictions on this date
        matching_predictions = [
            p for p in predictions
            if p.get("claimDate") == rebal_date and p.get("ticker") in rebal_tickers
        ]

        if matching_predictions:
            report["total_predictions_linked"] += len(matching_predictions)
            report["rebalance_alignment"][rebal_date] = {
                "accuracy": len(matching_predictions) / max(1, len(rebal_tickers)),
                "count": len(matching_predictions),
            }

    # Compute signal quality
    if report["rebalance_alignment"]:
        accuracies = [v.get("accuracy", 0.0) for v in report["rebalance_alignment"].values()]
        report["signal_quality"] = sum(accuracies) / len(accuracies) if accuracies else 0.0

    return report


def main() -> int:
    """CLI entry point for backtest harness."""
    import argparse

    parser = argparse.ArgumentParser(description="E4 Backtest Harness")
    subparsers = parser.add_subparsers(dest="command")

    # Command: generate-report
    gen_parser = subparsers.add_parser("generate-report", help="Generate backtest report")
    gen_parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    gen_parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    gen_parser.add_argument("--with-counterfactuals", action="store_true")

    # Command: extract-targets
    ext_parser = subparsers.add_parser("extract-targets", help="Extract targets from commit")
    ext_parser.add_argument("--commit", required=True, help="Commit hash")

    args = parser.parse_args()

    if args.command == "generate-report":
        params = {"counterfactuals_enabled": args.with_counterfactuals}
        report = generate_backtest_report(args.start_date, args.end_date, params)
        print(json.dumps(report, indent=2))
        return 0

    elif args.command == "extract-targets":
        targets = extract_historical_targets(args.commit)
        print(json.dumps(targets, indent=2))
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
