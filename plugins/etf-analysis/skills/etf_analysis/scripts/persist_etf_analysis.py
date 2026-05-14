#!/usr/bin/env python3
"""
persist_etf_analysis.py — etf-analysis plugin

Saves or updates an ETF analysis JSON to the data/etf_analysis/ directory.
If a file already exists for this ticker, appends the new analysis as a new
version (list of versions, same pattern as projections/).

Usage:
    python3 persist_etf_analysis.py < /tmp/DXYZ_etf.json
    python3 persist_etf_analysis.py --input /tmp/KOID_etf.json
    python3 persist_etf_analysis.py --input /tmp/HUMN_etf.json --dry-run
"""

import json
import sys
import argparse
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[5] / "investment_screener" / "backend" / "data" / "etf_analysis"


def persist(data: dict, dry_run: bool = False) -> str:
    ticker = data.get("ticker", "UNKNOWN").upper()
    out_path = DATA_DIR / f"{ticker}.json"

    existing = []
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            if not isinstance(existing, list):
                existing = [existing]
        except Exception:
            existing = []

    next_version = max((e.get("version", 0) for e in existing), default=0) + 1
    data["version"] = next_version
    existing.append(data)

    if dry_run:
        print(f"[DRY RUN] Would write {ticker}.json  (version {next_version})")
        return str(out_path)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(existing, indent=2))
    print(f"✅ Written: {out_path}  (version {next_version})")
    return str(out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Input JSON file path (default: stdin)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.input:
        data = json.loads(Path(args.input).read_text())
    else:
        data = json.load(sys.stdin)

    persist(data, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
