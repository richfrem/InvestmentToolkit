#!/usr/bin/env python3
"""
apply_catalyst.py — Adjust DCF scenario probability weights for a material catalyst.

Shifts bear/bull weights, recomputes the weighted fair value from existing
per-scenario prices, then updates the projection JSON + optionally agentRationale.

Usage (run from repo root):
    python3 plugins/portfolio-advisor/scripts/apply_catalyst.py \\
        --ticker CRWV \\
        --type major_contract \\
        --note "Meta $21B deal expansion + $8.5B IG financing" \\
        --write

Catalyst type presets (bull shift / bear shift in percentage points):
    design_win        +10pp bull / -5pp bear
    major_contract    +8pp bull  / -5pp bear
    funding_secured   +7pp bull  / -4pp bear
    partnership       +5pp bull  / -3pp bear
    earnings_beat     +5pp bull  / -3pp bear
    thesis_breaker   -10pp bull  / +15pp bear
    custom            requires --shift-bull and --shift-bear
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
PROJ_DIR    = REPO_ROOT / "investment_screener/backend/data/projections"
THESIS_JSON = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"

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
    return round(sum(new_weights[n] * s["scenarioPrice"] for n, s in scenarios.items()), 2)


def _find_latest_ai_agent(data: list) -> tuple[int, dict]:
    ai = [(i, p) for i, p in enumerate(data) if p.get("source") == "AI_AGENT"]
    if not ai:
        raise ValueError("No AI_AGENT entries found in projection JSON")
    return max(ai, key=lambda x: x[1].get("savedAt", ""))


def _get_fv_action(entry: dict) -> tuple[float, str]:
    if "fairValue" in entry:
        return entry["fairValue"], entry.get("action", "")
    th = entry.get("aiThesis", {})
    return th.get("fairValue", 0.0), th.get("action", "")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply catalyst weight shift to a DCF projection JSON."
    )
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g. CRWV)")
    parser.add_argument("--type", dest="catalyst_type", choices=list(PRESETS), required=True,
                        help="Catalyst type preset or 'custom'")
    parser.add_argument("--shift-bull", type=float, default=None,
                        help="Bull weight shift in pp (overrides preset; required for custom)")
    parser.add_argument("--shift-bear", type=float, default=None,
                        help="Bear weight shift in pp (overrides preset; required for custom)")
    parser.add_argument("--note", required=True, help="One-line catalyst description")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="Catalyst date YYYY-MM-DD (default: today)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing")
    parser.add_argument("--write", action="store_true",
                        help="Persist changes to projection JSON")
    parser.add_argument("--update-thesis", action="store_true",
                        help="Append catalyst note to agentRationale in target-portfolio.json")
    args = parser.parse_args()

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

    proj_path = PROJ_DIR / f"{args.ticker}.json"
    if not proj_path.exists():
        print(f"✗ No projection file: {proj_path}", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(proj_path.read_text())
    data: list = raw if isinstance(raw, list) else [raw]
    idx, entry = _find_latest_ai_agent(data)

    old_fv, old_action = _get_fv_action(entry)
    price = entry.get("snapshot", {}).get("price", 0.0)

    if "scenarios" not in entry:
        print(f"⚠  {args.ticker}: no 'scenarios' block — cannot shift weights (legacy format).")
        print("   Only a catalystUpdate note will be appended.")
        new_fv, new_action, new_weights = old_fv, old_action, None
    else:
        scenarios = entry["scenarios"]
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

    # Update fairValue / action
    if "fairValue" in entry:
        entry["fairValue"] = new_fv
        entry["action"] = new_action
        entry["updatedAt"] = now
    else:
        th = entry.setdefault("aiThesis", {})
        th["fairValue"] = new_fv
        th["action"] = new_action
        th["analyzedAt"] = now

    # Update scenario weights
    if new_weights and "scenarios" in entry:
        for name, w in new_weights.items():
            entry["scenarios"][name]["weight"] = w

    # Append to catalystUpdates log
    entry.setdefault("catalystUpdates", []).append(catalyst_block)
    data[idx] = entry

    out = data if isinstance(raw, list) else data[0]
    proj_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n✅ {proj_path.name} updated  FV ${old_fv:.2f}→${new_fv:.2f}  action {old_action}→{new_action}")

    if args.update_thesis:
        thesis = json.loads(THESIS_JSON.read_text())
        for h in thesis.get("holdings", []):
            if h["ticker"] == args.ticker:
                old_rat = h.get("agentRationale", "").rstrip(". ")
                suffix = f" {args.date}: {args.note}."
                if args.note not in old_rat:
                    h["agentRationale"] = old_rat + "." + suffix
                break
        THESIS_JSON.write_text(json.dumps(thesis, indent=2) + "\n")
        print(f"✅ agentRationale updated in target-portfolio.json for {args.ticker}")


if __name__ == "__main__":
    main()
