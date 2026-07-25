#!/usr/bin/env python3
"""
update_targets.py — Precision target-weight editor for domain_model.sqlite.

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
import subprocess
import sys
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parents[3]
DB_PATH       = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
VALIDATE_PY   = Path(__file__).parent / "validate_weights.py"
BLUEPRINT_PY  = Path(__file__).parent / "generate_portfolio_blueprint.py"
REFRESH_ALL   = Path(__file__).parent / "refresh_all.py"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from portfolio_io import load_thesis_holdings  # noqa: E402


def load() -> dict:
    return {"holdings": load_thesis_holdings(str(DB_PATH))}


def save(data: dict) -> None:
    """Writes every holding's thesis fields into investment.* (Wave 8),
    writing directly to the domain model. Pillars are resolved
    (auto-created if missing) since investment.pillar_id is a real FK against
    strategy_pillar."""
    from domain_model.db_client import initialize_db
    from domain_model.investment_repository import resolve_investment, update_investment_fields
    from domain_model.pillar_repository import resolve_pillar, resolve_sub_strategy

    conn = initialize_db(str(DB_PATH))
    try:
        for h in data["holdings"]:
            pillar_id = h.get("pillarId")
            if pillar_id:
                # Idempotent: preserves existing name/target_weight if the
                # pillar already exists (resolve_pillar only updates fields
                # actually passed).
                existing = conn.execute(
                    "SELECT name FROM strategy_pillar WHERE pillar_id = ?;", (pillar_id,)
                ).fetchone()
                if not existing:
                    resolve_pillar(conn, pillar_id, pillar_id.replace("_", " ").title())

            sub_strategy_id = h.get("subStrategyId")
            if sub_strategy_id:
                # sub_strategy.pillar_id is itself a real FK -- auto-create
                # against this holding's pillar (or "other" if unset) the same
                # way pillars are auto-created above.
                existing_sub = conn.execute(
                    "SELECT sub_strategy_id FROM sub_strategy WHERE sub_strategy_id = ?;", (sub_strategy_id,)
                ).fetchone()
                if not existing_sub:
                    fallback_pillar = pillar_id or "other"
                    if not conn.execute(
                        "SELECT pillar_id FROM strategy_pillar WHERE pillar_id = ?;", (fallback_pillar,)
                    ).fetchone():
                        resolve_pillar(conn, fallback_pillar, fallback_pillar.replace("_", " ").title())
                    resolve_sub_strategy(conn, sub_strategy_id, fallback_pillar, sub_strategy_id.replace("-", " ").title())
            # name only takes effect for a brand-new investment row --
            # update_investment_fields() has no `name` column (not in
            # _UPDATABLE_FIELDS); renaming an existing investment is out of
            # this script's scope.
            investment_id = resolve_investment(conn, h["ticker"], asset_class="EQUITY", currency="USD", name=h.get("name"))
            update_investment_fields(
                conn, investment_id,
                pillar_id=pillar_id,
                sub_strategy_id=h.get("subStrategyId"), target_weight=h.get("targetWeight"),
                thesis_for_inclusion=h.get("thesisForInclusion"),
                agent_rationale=h.get("agentRationale"), lifecycle_status=h.get("role"),
            )
    finally:
        conn.close()

    # KNOWN LIMITATION: --set-entry TICKER=null (clear) pops the key from the
    # in-memory dict, which is indistinguishable here from "never had one" --
    # this only propagates newly-SET entry prices to SQLite, not explicit
    # clears. Acceptable for this wave (clearing an entry price is rare;
    # flagged rather than silently wrong).
    if any(h.get("targetEntryPrice") is not None for h in data["holdings"]):
        _save_entry_prices(data["holdings"])


def _save_entry_prices(holdings: list[dict]) -> None:
    from domain_model.db_client import initialize_db
    from domain_model.price_level_repository import replace_price_levels, get_price_levels

    conn = initialize_db(str(DB_PATH))
    try:
        for h in holdings:
            if h.get("targetEntryPrice") is None:
                continue
            existing = get_price_levels(conn, h["ticker"]) or {}
            replace_price_levels(
                conn, h["ticker"],
                (existing.get("price_level_set") or {}).get("schema_version"),
                (existing.get("price_level_set") or {}).get("last_updated"),
                (existing.get("price_level_set") or {}).get("last_updated_by"),
                (existing.get("price_level_set") or {}).get("note"),
                existing.get("buy_tiers") or [], existing.get("sell_tiers") or [],
                existing.get("stop_loss"), h["targetEntryPrice"],
            )
    finally:
        conn.close()


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
    """Run the full refresh pipeline (roles + blueprint) after any target change."""
    script = REFRESH_ALL if REFRESH_ALL.exists() else BLUEPRINT_PY
    extra  = [] if REFRESH_ALL.exists() else ["--write"]
    result = subprocess.run(
        [sys.executable, str(script)] + extra,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Refresh error: {result.stderr}", file=sys.stderr)
    else:
        print(result.stdout.strip())


def apply_entry_prices(data: dict, pairs: list[str], dry_run: bool) -> dict:
    """Set targetEntryPrice on holdings. Format: TICKER=PRICE or TICKER=null to clear."""
    holdings = {h["ticker"]: h for h in data["holdings"]}
    for pair in pairs:
        if "=" not in pair:
            print(f"⚠  Skipping malformed entry: {pair}", file=sys.stderr)
            continue
        ticker, raw = pair.split("=", 1)
        ticker = ticker.strip().upper()
        if ticker not in holdings:
            print(f"⚠  {ticker} not in thesis — skipping", file=sys.stderr)
            continue
        if raw.strip().lower() == "null":
            holdings[ticker].pop("targetEntryPrice", None)
            label = "cleared"
        else:
            try:
                price = float(raw.strip())
            except ValueError:
                print(f"⚠  Invalid price for {ticker}: {raw}", file=sys.stderr)
                continue
            holdings[ticker]["targetEntryPrice"] = price
            label = f"${price:,.2f}"
        if not dry_run:
            print(f"  {ticker}: targetEntryPrice → {label}")
    data["holdings"] = list(holdings.values())
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Precision target-weight editor for domain_model.sqlite"
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

    # Entry price (GTC limit target)
    parser.add_argument("--set-entry", nargs="+", metavar="TICKER=PRICE",
                        help="Set GTC target entry price: SNDK=1350 NBIS=210. "
                             "Use TICKER=null to clear.")

    # Output control
    parser.add_argument("--write",     action="store_true",
                        help="Write changes to domain_model.sqlite (auto-normalizes)")
    parser.add_argument("--blueprint", action="store_true",
                        help="After writing, regenerate investment_thesis.md blueprint")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Print diff but don't write anything")

    args = parser.parse_args()

    data = load()

    if args.show:
        show_weights(data)
        return

    if not any([args.set, args.add, args.remove, args.set_entry]):
        parser.print_help()
        return

    if args.set:
        data = apply_set(data, args.set, args.dry_run)
    elif args.add:
        data = apply_add(data, args.add, args.name, args.pillar,
                         args.strategy, args.note, args.dry_run)
    elif args.remove:
        data = apply_remove(data, args.remove, args.dry_run)

    if args.set_entry:
        data = apply_entry_prices(data, args.set_entry, args.dry_run)

    if args.dry_run:
        show_weights(normalize(dict(holdings=list(data["holdings"]))), "Projected targets after normalize")
        return

    if args.write:
        data = normalize(data)
        save(data)
        total = current_total(data)
        print(f"\n✅ Wrote domain_model.sqlite  (sum={total:.4f}%)")
        show_weights(data, "Updated targets")

        if args.blueprint:
            print("\n── Regenerating investment_thesis.md blueprint ──")
            run_blueprint()
    else:
        print("\nHint: add --write to persist changes, --blueprint to also update thesis.md")
        show_weights(normalize(data), "Projected targets (not written)")


if __name__ == "__main__":
    main()
