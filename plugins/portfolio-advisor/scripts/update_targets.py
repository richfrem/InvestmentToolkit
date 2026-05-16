#!/usr/bin/env python3
"""
update_targets.py — Precision target-weight editor for target-portfolio.json.

This is the canonical script for updating thesis target weights during conversation.
After any update it auto-normalizes to 100% and prints a clear diff.
Optionally regenerates investment_thesis.md blueprint.

Usage:
  # Set specific weights (can be 0 to EXIT):
  python3 update_targets.py --set NVDA=6.5 META=4.5 CRWD=0

  # Add a brand-new ticker to the thesis:
  python3 update_targets.py --add BTDR=1.25 --name "Bitdeer Technologies" \\
      --pillar compute --strategy sa-asi-race \\
      --note "Proprietary Sealminer ASIC — structural cost moat. SA LP +92%."

  # Remove a ticker entirely from the holdings array:
  python3 update_targets.py --remove CRWD

  # Print current weights sorted by target (no changes):
  python3 update_targets.py --show

  # After setting weights, auto-normalize and regenerate blueprint:
  python3 update_targets.py --set VST=1.0 BE=2.5 --write --blueprint

  # Dry-run (show diff but don't write):
  python3 update_targets.py --set INTC=7.0 --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parents[3]
TARGET_JSON   = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
VALIDATE_PY   = Path(__file__).parent / "validate_weights.py"
BLUEPRINT_PY  = Path(__file__).parent / "generate_portfolio_blueprint.py"


def load() -> dict:
    return json.loads(TARGET_JSON.read_text())


def save(data: dict) -> None:
    tmp = TARGET_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, TARGET_JSON)


def normalize(data: dict) -> dict:
    total = sum(h.get("targetWeight", 0) or 0 for h in data["holdings"])
    if total == 0:
        return data
    factor = 100.0 / total
    for h in data["holdings"]:
        w = h.get("targetWeight", 0) or 0
        if w > 0:
            h["targetWeight"] = round(w * factor, 4)
    return data


def current_total(data: dict) -> float:
    return sum(h.get("targetWeight", 0) or 0 for h in data["holdings"])


def show_weights(data: dict, title: str = "Current targets") -> None:
    holdings = [(h["ticker"], h.get("targetWeight", 0) or 0) for h in data["holdings"]]
    holdings.sort(key=lambda x: -x[1])
    total = sum(w for _, w in holdings)
    print(f"\n{title} (total = {total:.4f}%)")
    print(f"{'Ticker':<12} {'Target%':>10}")
    print("-" * 24)
    for ticker, w in holdings:
        if w > 0:
            print(f"{ticker:<12} {w:>10.4f}%")
    zeros = [t for t, w in holdings if w == 0]
    if zeros:
        print(f"\n  EXIT (0%): {', '.join(zeros)}")


def apply_set(data: dict, pairs: list[str], dry_run: bool) -> dict:
    """Apply TICKER=WEIGHT pairs. Creates entry if ticker missing (bare minimum)."""
    changes = {}
    for pair in pairs:
        if "=" not in pair:
            print(f"ERROR: bad format '{pair}' — use TICKER=WEIGHT", file=sys.stderr)
            sys.exit(1)
        ticker, raw = pair.split("=", 1)
        ticker = ticker.strip().upper()
        try:
            weight = float(raw.strip())
        except ValueError:
            print(f"ERROR: weight must be a number, got '{raw}'", file=sys.stderr)
            sys.exit(1)
        changes[ticker] = weight

    print("\n── Weight changes ──────────────────────────────")
    before = {h["ticker"]: h.get("targetWeight", 0) or 0 for h in data["holdings"]}

    for ticker, new_w in changes.items():
        old_w = before.get(ticker, None)
        found = False
        for h in data["holdings"]:
            if h["ticker"] == ticker:
                h["targetWeight"] = new_w
                found = True
                break
        if not found:
            # Ticker not in holdings yet — add a minimal entry
            data["holdings"].append({
                "ticker": ticker,
                "targetWeight": new_w,
                "role": "speculative" if new_w > 0 else "untracked",
                "subStrategyId": "sa-asi-race",
            })
        direction = "↑" if (old_w is None or new_w > (old_w or 0)) else ("→" if new_w == (old_w or 0) else "↓")
        old_str = f"{old_w:.4f}%" if old_w is not None else "NEW"
        print(f"  {direction} {ticker:<8} {old_str:>10} → {new_w:.4f}%")

    total_before = sum(before.values())
    total_after  = current_total(data)
    print(f"\n  Pre-normalize total: {total_after:.4f}%  (was {total_before:.4f}%)")

    if dry_run:
        print("\n  [DRY RUN — no files written]")
    return data


def apply_add(data: dict, pairs: list[str], name: str, pillar: str,
              strategy: str, note: str, dry_run: bool) -> dict:
    """Add a brand-new ticker to holdings."""
    if len(pairs) != 1:
        print("ERROR: --add requires exactly one TICKER=WEIGHT pair", file=sys.stderr)
        sys.exit(1)
    ticker, raw = pairs[0].split("=", 1)
    ticker = ticker.strip().upper()
    weight = float(raw.strip())

    existing = next((h for h in data["holdings"] if h["ticker"] == ticker), None)
    if existing:
        print(f"INFO: {ticker} already in holdings — use --set to update weight")
        existing["targetWeight"] = weight
        return data

    entry: dict = {
        "ticker": ticker,
        "name": name or ticker,
        "targetWeight": weight,
        "role": "speculative",
        "subStrategyId": strategy or "sa-asi-race",
    }
    if pillar:
        entry["pillarId"] = pillar
    if note:
        entry["thesisForInclusion"] = note

    data["holdings"].append(entry)
    print(f"\n── Added new holding ──────────────────────────")
    print(f"  + {ticker:<8} target={weight:.4f}%  pillar={pillar or '—'}  strategy={strategy or 'sa-asi-race'}")
    if note:
        print(f"    note: {note[:80]}...")
    if dry_run:
        print("  [DRY RUN — no files written]")
    return data


def apply_remove(data: dict, tickers: list[str], dry_run: bool) -> dict:
    """Remove tickers from holdings array entirely."""
    print("\n── Removing holdings ───────────────────────────")
    for ticker in tickers:
        ticker = ticker.upper()
        before_len = len(data["holdings"])
        data["holdings"] = [h for h in data["holdings"] if h["ticker"] != ticker]
        if len(data["holdings"]) < before_len:
            print(f"  ✕ removed {ticker}")
        else:
            print(f"  ! {ticker} not found — skipped")
    if dry_run:
        print("  [DRY RUN — no files written]")
    return data


def run_blueprint() -> None:
    result = subprocess.run(
        [sys.executable, str(BLUEPRINT_PY), "--write"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Blueprint error: {result.stderr}", file=sys.stderr)
    else:
        print(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(
        description="Precision target-weight editor for target-portfolio.json"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--set",    nargs="+", metavar="TICKER=WEIGHT",
                      help="Set target weights: NVDA=6.5 META=4.5 CRWD=0")
    mode.add_argument("--add",    nargs=1,   metavar="TICKER=WEIGHT",
                      help="Add a brand-new ticker to the thesis")
    mode.add_argument("--remove", nargs="+", metavar="TICKER",
                      help="Remove tickers from holdings array entirely")
    mode.add_argument("--show",   action="store_true",
                      help="Print current weights (no changes)")

    # --add metadata
    parser.add_argument("--name",     default="", help="Display name for --add")
    parser.add_argument("--pillar",   default="", help="Pillar ID for --add")
    parser.add_argument("--strategy", default="sa-asi-race", help="SubStrategyId for --add")
    parser.add_argument("--note",     default="", help="thesisForInclusion for --add")

    # Output control
    parser.add_argument("--write",     action="store_true",
                        help="Write changes to target-portfolio.json (auto-normalizes)")
    parser.add_argument("--blueprint", action="store_true",
                        help="After writing, regenerate investment_thesis.md blueprint")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Print diff but don't write anything")

    args = parser.parse_args()

    data = load()

    if args.show:
        show_weights(data)
        return

    if not any([args.set, args.add, args.remove]):
        parser.print_help()
        return

    if args.set:
        data = apply_set(data, args.set, args.dry_run)
    elif args.add:
        data = apply_add(data, args.add, args.name, args.pillar,
                         args.strategy, args.note, args.dry_run)
    elif args.remove:
        data = apply_remove(data, args.remove, args.dry_run)

    if args.dry_run:
        show_weights(normalize(dict(holdings=list(data["holdings"]))), "Projected targets after normalize")
        return

    if args.write:
        data = normalize(data)
        save(data)
        total = current_total(data)
        print(f"\n✅ Wrote target-portfolio.json  (sum={total:.4f}%)")
        show_weights(data, "Updated targets")

        if args.blueprint:
            print("\n── Regenerating investment_thesis.md blueprint ──")
            run_blueprint()
    else:
        print("\nHint: add --write to persist changes, --blueprint to also update thesis.md")
        show_weights(normalize(data), "Projected targets (not written)")


if __name__ == "__main__":
    main()
