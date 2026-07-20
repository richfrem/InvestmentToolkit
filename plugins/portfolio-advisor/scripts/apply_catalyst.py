#!/usr/bin/env python3
"""
apply_catalyst.py (Python Service)
=====================================

Purpose:
    Adjusts DCF scenario probability weights based on material market catalysts (e.g., contract wins, earnings beats).
    Recalculates weighted fair values and updates projection records and thesis rationale.

Layer: Backend / Python Services / Valuation Adjustment

Storage backend (Wave 1 Task 6):
    Reads/writes the `projection_version`/`projection_scenario` tables in
    `investment_screener/backend/data/domain_model.sqlite` via
    `domain_model.projection_repository`, not `projections/{TICKER}.json` directly
    (ADR-029). A real-data investigation found `_find_latest_ai_agent`'s
    source-filtered-then-latest-by-savedAt selection has no SQL equivalent in
    `get_latest_projection` (which is `MAX(version)` only, ignoring source) — 8/82 real
    tickers have zero `AI_AGENT`-sourced projections (only `ETF_ANALYSIS`), and 3 more
    (`BW`, `CLSK`, `LITE`) have non-chronological version numbers where the highest
    version is not the most recently saved `AI_AGENT` entry. `db_client.py`'s
    `projection_version` table gained `source`/`last_grok_sweep`/`catalyst_updates_json`
    columns to close this gap; `get_latest_projection_by_source` is the new lookup this
    module uses in place of `_find_latest_ai_agent`. See `db_client.py`'s DDL-drift-check
    header for the full writeup.

Usage Examples:
    # Major contract win (shifts Bull +8pp, Bear -5pp)
    python3 apply_catalyst.py --ticker MSFT --type major_contract --note "Cloud expansion deal" --write

    # Earnings beat (shifts Bull +5pp, Bear -3pp)
    python3 apply_catalyst.py --ticker NVDA --type earnings_beat --note "H100 demand acceleration" --write

    # Thesis breaker (shifts Bull -10pp, Bear +15pp)
    python3 apply_catalyst.py --ticker INTC --type thesis_breaker --note "GAA node delay to 2027" --write

    # Stamp sweep date only (no catalyst found)
    python3 apply_catalyst.py --ticker AAPL --record-sweep

Key Functions:
    - _shift_weights() - Implements the weight shift logic (Bull/Bear shifts with Base absorption)
    - _compute_fv() - Calculates the new weighted fair value from scenario prices
    - main() - CLI orchestrator for applying catalysts and persisting changes to data storage

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (projection_version / projection_scenario)
    - investment_screener/backend/data/theses/target-portfolio.json (only for --update-thesis)
"""

import argparse
import datetime
import json
import sys
from pathlib import Path


REPO_ROOT   = Path(__file__).resolve().parents[3]
DB_PATH     = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
THESIS_JSON = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"

sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from file_lock import locked_write_json  # noqa: E402
from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.projection_repository import (  # noqa: E402
    get_latest_projection_by_source,
    save_projection_version,
    get_projection_scenarios,
    add_projection_scenario,
)

PRESETS: dict[str, dict[str, float] | None] = {
    "design_win":      {"bull": +10, "bear": -5},
    "major_contract":  {"bull": +8,  "bear": -5},
    "funding_secured": {"bull": +7,  "bear": -4},
    "partnership":     {"bull": +5,  "bear": -3},
    "earnings_beat":   {"bull": +5,  "bear": -3},
    "thesis_breaker":  {"bull": -10, "bear": +15},
    "custom":          None,
}

# Upside → action mapping (lower bound inclusive, upper exclusive)
_ACTION_BANDS = [
    (20,          float("inf"), "BUY"),
    (5,           20,           "ACCUMULATE"),
    (-5,          5,            "MAINTAIN"),
    (-15,         -5,           "TRIM"),
    (float("-inf"), -15,        "SELL"),
]


def _derive_action(upside_pct: float) -> str:
    for lo, hi, action in _ACTION_BANDS:
        if lo <= upside_pct < hi:
            return action
    return "SELL"


def _shift_weights(scenarios: dict, bull_delta_pp: float, bear_delta_pp: float) -> dict[str, float]:
    """Shift bear/bull weights; base absorbs remainder. Clamps each to [0.01, 0.97]."""
    w = {k: s["weight"] for k, s in scenarios.items()}
    w["bull"] = max(0.01, min(0.97, w["bull"] + bull_delta_pp / 100))
    w["bear"] = max(0.01, min(0.97, w["bear"] + bear_delta_pp / 100))
    w["base"] = max(0.01, round(1.0 - w["bull"] - w["bear"], 6))
    total = sum(w.values())
    if abs(total - 1.0) > 0.001:
        for k in w:
            w[k] = round(w[k] / total, 6)
    return w


def _compute_fv(scenarios: dict, new_weights: dict[str, float]) -> float:
    return round(sum(new_weights[n] * (s.get("scenarioPrice") or s.get("presentValue") or 0.0) for n, s in scenarios.items()), 2)


def _resolve_investment_id_readonly(conn, ticker: str) -> str | None:
    """Look up an existing investment's id by symbol without creating one.

    Deliberately does NOT use `investment_repository.resolve_investment` (which
    inserts a new row for an unknown symbol) — the original file-based tool treated a
    missing `projections/{TICKER}.json` as a hard error, not something to silently
    create, and this preserves that read-only-lookup behavior against SQLite.
    """
    cursor = conn.execute("SELECT investment_id FROM investment WHERE symbol = ?;", (ticker,))
    row = cursor.fetchone()
    return row[0] if row else None


def _find_latest_ai_agent(conn, investment_id: str) -> dict:
    """Return the latest `AI_AGENT`-sourced projection_version row for an investment.

    SQL equivalent of the original array-scanning `_find_latest_ai_agent(data)` —
    filters by `source == "AI_AGENT"`, picks the newest by `saved_at`. Raises
    `ValueError` (uncaught, matching original behavior) if no such row exists — this is
    the real, expected outcome for the 8 real tickers whose only projection rows are
    `ETF_ANALYSIS`-sourced (see module docstring).
    """
    row = get_latest_projection_by_source(conn, investment_id, "AI_AGENT")
    if row is None:
        raise ValueError("No AI_AGENT entries found in projection_version for this investment")
    return row


def _load_scenarios(conn, projection_id: str) -> dict:
    """Reconstruct the `{name: {"weight": ..., "scenarioPrice": ...}}` shape
    `_shift_weights`/`_compute_fv` expect from `projection_scenario` rows. Empty dict
    for legacy rows with no scenario rows (mirrors the original 'scenarios' key
    missing-from-JSON legacy-format case)."""
    rows = get_projection_scenarios(conn, projection_id)
    return {
        r["scenario_name"]: {"weight": r["weight"], "scenarioPrice": r["scenario_price"]}
        for r in rows
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply catalyst weight shift to a DCF projection JSON."
    )
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g. CRWV)")
    parser.add_argument("--type", dest="catalyst_type", choices=list(PRESETS), default=None,
                        help="Catalyst type preset or 'custom'. Omit with --record-sweep.")
    parser.add_argument("--shift-bull", type=float, default=None,
                        help="Bull weight shift in pp (overrides preset; required for custom)")
    parser.add_argument("--shift-bear", type=float, default=None,
                        help="Bear weight shift in pp (overrides preset; required for custom)")
    parser.add_argument("--note", default=None, help="One-line catalyst description")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="Catalyst date YYYY-MM-DD (default: today)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    parser.add_argument("--write", action="store_true",
                        help="Persist changes to projection JSON")
    parser.add_argument("--update-thesis", action="store_true",
                        help="Append catalyst note to agentRationale in target-portfolio.json")
    parser.add_argument("--record-sweep", action="store_true",
                        help="Stamp lastGrokSweep date only — no weight shifts (use when sweep "
                             "finds no material catalyst)")
    args = parser.parse_args()

    conn = initialize_db(str(DB_PATH))
    try:
        if args.record_sweep:
            _run_record_sweep(conn, args)
            return

        if args.catalyst_type is None:
            parser.error("--type is required unless using --record-sweep")
        if args.note is None:
            parser.error("--note is required unless using --record-sweep")

        if args.catalyst_type == "custom":
            if args.shift_bull is None or args.shift_bear is None:
                parser.error("--shift-bull and --shift-bear are required for --type custom")
            bull_delta = args.shift_bull
            bear_delta = args.shift_bear
        else:
            preset = PRESETS[args.catalyst_type]
            assert preset is not None
            bull_delta = args.shift_bull if args.shift_bull is not None else preset["bull"]
            bear_delta = args.shift_bear if args.shift_bear is not None else preset["bear"]

        _run_apply_catalyst(conn, args, bull_delta, bear_delta)
    finally:
        conn.close()


def _run_record_sweep(conn, args) -> None:
    """`--record-sweep` mode: stamp `last_grok_sweep` only, no catalyst required."""
    investment_id = _resolve_investment_id_readonly(conn, args.ticker)
    if investment_id is None:
        print(f"✗ No projection record for ticker: {args.ticker}", file=sys.stderr)
        sys.exit(1)

    row = _find_latest_ai_agent(conn, investment_id)
    save_projection_version(
        conn, investment_id, version=row["version"], saved_at=row["saved_at"],
        analyzed_at=row["analyzed_at"], model=row["model"], fair_value=row["fair_value"],
        action=row["action"], rationale=row["rationale"],
        research_event_id=row["research_event_id"], snapshot_json=row["snapshot_json"],
        analytics_log_json=row["analytics_log_json"], source=row["source"],
        last_grok_sweep=args.date, catalyst_updates_json=row["catalyst_updates_json"],
    )
    print(f"✅ {args.ticker}: lastGrokSweep stamped {args.date} (no catalyst applied)")


def _run_apply_catalyst(conn, args, bull_delta: float, bear_delta: float) -> None:
    investment_id = _resolve_investment_id_readonly(conn, args.ticker)
    if investment_id is None:
        print(f"✗ No projection record for ticker: {args.ticker}", file=sys.stderr)
        sys.exit(1)

    row = _find_latest_ai_agent(conn, investment_id)

    old_fv = row["fair_value"] or 0.0
    old_action = row["action"] or ""
    snapshot = json.loads(row["snapshot_json"]) if row["snapshot_json"] else {}
    price = snapshot.get("price", 0.0)

    scenarios = _load_scenarios(conn, row["projection_id"])

    if not scenarios:
        print(f"⚠  {args.ticker}: no 'scenarios' block — cannot shift weights (legacy format).")
        print("   Only a catalystUpdate note will be appended.")
        new_fv, new_action, new_weights = old_fv, old_action, None
        old_upside = new_upside = (old_fv - price) / price * 100 if price else 0.0
    else:
        new_weights = _shift_weights(scenarios, bull_delta, bear_delta)
        new_fv = _compute_fv(scenarios, new_weights)
        old_upside = (old_fv - price) / price * 100 if price else 0.0
        new_upside = (new_fv - price) / price * 100 if price else 0.0
        new_action = _derive_action(new_upside)

        bear_old = scenarios["bear"]["weight"]
        base_old = scenarios["base"]["weight"]
        bull_old = scenarios["bull"]["weight"]

        print(f"\n── {args.ticker} catalyst: {args.catalyst_type} ──────────────────────────────")
        print(f"   Note    : {args.note}")
        print(f"   Shifts  : bull {bull_delta:+.0f}pp / bear {bear_delta:+.0f}pp")
        print(f"\n   Weights before : bear={bear_old:.2f}  base={base_old:.2f}  bull={bull_old:.2f}")
        print(f"   Weights after  : bear={new_weights['bear']:.2f}  "
              f"base={new_weights['base']:.2f}  bull={new_weights['bull']:.2f}")
        print(f"\n   FV     : ${old_fv:.2f} → ${new_fv:.2f}")
        print(f"   Upside : {old_upside:+.1f}% → {new_upside:+.1f}%  (price ${price:.2f})")
        print(f"   Action : {old_action} → {new_action}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return

    if not args.write:
        print("\nUse --write to persist, or --dry-run to preview only.")
        return

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalyst_block = {
        "date": args.date,
        "source": "apply_catalyst.py",
        "type": args.catalyst_type,
        "events": [args.note],
        "weightShifts": {"bull": bull_delta, "bear": bear_delta},
        "thesisImpact": (
            f"Bull probability {bull_delta:+.0f}pp; bear {bear_delta:+.0f}pp. "
            f"FV ${old_fv:.2f}→${new_fv:.2f}. Action: {old_action}→{new_action}."
        ),
    }
    existing_updates = (
        json.loads(row["catalyst_updates_json"]) if row["catalyst_updates_json"] else []
    )
    existing_updates.append(catalyst_block)

    save_projection_version(
        conn, investment_id, version=row["version"], saved_at=row["saved_at"],
        analyzed_at=now, model=row["model"], fair_value=new_fv, action=new_action,
        rationale=row["rationale"], research_event_id=row["research_event_id"],
        snapshot_json=row["snapshot_json"], analytics_log_json=row["analytics_log_json"],
        source=row["source"], last_grok_sweep=args.date,
        catalyst_updates_json=json.dumps(existing_updates),
    )

    if new_weights:
        existing_scenarios = {
            s["scenario_name"]: s for s in get_projection_scenarios(conn, row["projection_id"])
        }
        for name, weight in new_weights.items():
            existing = existing_scenarios.get(name, {})
            add_projection_scenario(
                conn, row["projection_id"], name, weight=weight,
                growth_rate=existing.get("growth_rate"), net_margin=existing.get("net_margin"),
                exit_pe=existing.get("exit_pe"),
                quality_multiplier=existing.get("quality_multiplier"),
                share_change=existing.get("share_change"), rationale=existing.get("rationale"),
                moat_score=existing.get("moat_score"),
                management_score=existing.get("management_score"),
                year5_revenue=existing.get("year5_revenue"),
                year5_net_income=existing.get("year5_net_income"),
                year5_eps=existing.get("year5_eps"), scenario_price=existing.get("scenario_price"),
                risks_json=existing.get("risks_json"),
            )

    print(f"\n✅ {args.ticker} updated  FV ${old_fv:.2f}→${new_fv:.2f}  action {old_action}→{new_action}")

    if args.update_thesis:
        thesis = json.loads(THESIS_JSON.read_text())
        for h in thesis.get("holdings", []):
            if h["ticker"] == args.ticker:
                old_rat = h.get("agentRationale", "").rstrip(". ")
                suffix = f" {args.date}: {args.note}."
                if args.note not in old_rat:
                    h["agentRationale"] = old_rat + "." + suffix
                break
        locked_write_json(THESIS_JSON, thesis)
        print(f"✅ agentRationale updated in target-portfolio.json for {args.ticker}")


if __name__ == "__main__":
    main()
