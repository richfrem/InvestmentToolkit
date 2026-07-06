#!/usr/bin/env python3
"""
peer_bench.py (Python Service)
=====================================

Purpose:
    Automates the framework doc's Phase-2 "Peer Benchmarking" table: for
    each raw metric compute_raw_metrics() produces, computes the target
    ticker's value alongside the peer-set median, Z-score, and percentile
    rank. Reuses framework_score.compute_raw_metrics() as the single source
    of truth for every metric formula — never re-derives them.

Layer: Backend / Python Services / Valuation Math

Usage:
    python3 peer_bench.py --ticker NVDA --peers AMD,AVGO,QCOM --sector chips_ai \
        --projections-dir investment_screener/backend/data/projections --pretty

Key Functions:
    - compute_peer_benchmark() - Primary orchestrator: target + peer raw metrics -> benchmarking table
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from framework_score import compute_raw_metrics  # noqa: E402

MIN_USABLE_PEERS = 2


def compute_peer_benchmark(
    ticker: str, peers: list[str], sector: str, projections_dir: str
) -> dict:
    """Build the peer benchmarking table: target value + peer median/Z-score/percentile.

    A metric is included in the table only if the target ticker has a value
    for it AND at least MIN_USABLE_PEERS peers also have a value — never
    fabricated from a smaller set. A percentile of 0 std-dev peer sets
    (all peers identical) reports zScore 0.0 rather than dividing by zero.

    Args:
        ticker: Target ticker.
        peers: Curated peer ticker list (from projections/{TICKER}.json's `peers` field).
        sector: One of "saas_cyber", "chips_ai", "energy_infra".
        projections_dir: Path to the projections directory.

    Returns:
        {"status": "ok", "peersUsed": [...], "table": [{"metric", "ticker",
         "peerMedian", "zScore", "percentile"}, ...]} or
        {"status": "insufficient_peer_data", "peersUsed": []} when fewer
        than MIN_USABLE_PEERS peers have any usable metric at all.
    """
    target_metrics = compute_raw_metrics(ticker, sector, projections_dir)
    peer_metrics = {p: compute_raw_metrics(p, sector, projections_dir) for p in peers}

    peers_used = sorted({
        p for p, m in peer_metrics.items() if any(isinstance(v, (int, float)) for v in m.values())
    })
    if len(peers_used) < MIN_USABLE_PEERS:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    table = []
    for metric_name, target_value in target_metrics.items():
        if target_value is None or not isinstance(target_value, (int, float)):
            continue
        peer_values = [
            peer_metrics[p][metric_name] for p in peers_used
            if isinstance(peer_metrics[p].get(metric_name), (int, float))
        ]
        if len(peer_values) < MIN_USABLE_PEERS:
            continue

        peer_median = statistics.median(peer_values)
        all_values = peer_values + [target_value]
        mean = statistics.mean(all_values)
        stdev = statistics.pstdev(all_values)
        z_score = (target_value - mean) / stdev if stdev > 0 else 0.0
        rank = sorted(all_values).index(target_value) + 1
        percentile = round(rank / len(all_values) * 100)

        table.append({
            "metric": metric_name,
            "ticker": target_value,
            "peerMedian": round(peer_median, 4),
            "zScore": round(z_score, 3),
            "percentile": percentile,
        })

    return {"status": "ok", "peersUsed": peers_used, "table": table}


def main() -> None:
    parser = argparse.ArgumentParser(description="Peer benchmarking table (Z-scores/percentiles)")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--peers", required=True, help="Comma-separated peer tickers")
    parser.add_argument("--sector", required=True, choices=["saas_cyber", "chips_ai", "energy_infra"])
    parser.add_argument("--projections-dir", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    peer_tickers = [p.strip() for p in args.peers.split(",") if p.strip()]
    result = compute_peer_benchmark(args.ticker, peer_tickers, args.sector, args.projections_dir)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
