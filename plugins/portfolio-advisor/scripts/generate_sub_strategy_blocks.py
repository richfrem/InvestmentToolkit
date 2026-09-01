"""
generate_sub_strategy_blocks.py — Regenerate AUTO_UPDATE current_positions blocks
in every sub-strategy .md file.

For each sub-strategy, writes a table showing:
  - Held positions: ticker | shares | actual% | target% | gap | action | entry price
  - Undeployed (initiate): same columns, — for shares/actual/gap
  - Watchlist: ticker | — | — | target% | — | WATCHLIST | entry price if set
  - Avoided positions (target=0, not held): excluded

Called from generate_portfolio_blueprint.py --write and refresh_all.py.
Can also run standalone: python3 generate_sub_strategy_blocks.py

Layer: Plugin / portfolio-advisor / Report Generation
"""

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "investment_screener/backend/py_services"))
from portfolio_io import load_portfolio_state, load_thesis_holdings, compute_weights, replace_block, ROLE_LABEL  # noqa: E402
from portfolio_action import derive_action, ACTION_EMOJI  # noqa: E402

DB_PATH = REPO_ROOT / "investment_screener/backend/data/domain_model.sqlite"
SUB_DIR = REPO_ROOT / "investment_screener/backend/data/theses/sub_strategies"

# sub-strategy filename stem → pillar IDs it covers
PILLAR_MAP: dict[str, list[str]] = {
    "asi_race":            ["compute", "titans", "datainfra"],
    "cybersecurity":       ["security"],
    "sovereign_finance":   ["sovfin"],
    "quality_saas":        ["quality_saas"],
    "space_defense":       ["defense"],
    "critical_materials_magnets": ["defense"],
    "photonics_optical":   ["photonics"],
    "quantum_computing":   ["quantum"],
    "robotics_automation": ["robotics"],
    "strategic_reserve":   ["cash"],
    "power_infrastructure": ["power"],
    "applied_ai":          [],  # ARCHIVED — block will note this
    "metabolic_rewriting": ["biohealth"],
}


def _gap_str(actual: float, target: float) -> str:
    diff = actual - target
    flag = " ⚠" if abs(diff) >= 2.0 else ""
    return f"{'+' if diff >= 0 else ''}{diff:.1f}pp{flag}"


def _entry_str(h: dict) -> str:
    ep = h.get("targetEntryPrice")
    return f"≤${ep:,.0f}" if ep else "—"


def build_current_positions_block(
    sub_id: str,
    holdings_in_pillar: list[dict],
    weights: dict[str, float],
    total_usd: float,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if sub_id == "applied_ai":
        return f"*Auto-updated {now} — this thesis is ARCHIVED; no active positions.*"

    if not holdings_in_pillar:
        return f"*Auto-updated {now} — no holdings mapped to this thesis yet.*"

    held     = [h for h in holdings_in_pillar if h.get("role") in ("accumulate", "trim", "exit")]
    initiate = [h for h in holdings_in_pillar if h.get("role") == "initiate"]
    watchlist = [h for h in holdings_in_pillar
                 if h.get("role") in ("watchlist", "monitor", "avoid")
                 and float(h.get("targetWeight") or 0) > 0]

    lines: list[str] = [f"*Auto-updated {now} by TV sync · Portfolio total: ${total_usd:,.0f} USD*", ""]

    # ── Active positions ──────────────────────────────────────────────────────
    if held:
        lines += [
            "**Active Positions**",
            "",
            "| Ticker | Shares | Actual% | Target% | Gap | Action | Entry Price |",
            "|--------|--------|---------|---------|-----|--------|-------------|",
        ]
        for h in sorted(held, key=lambda x: weights.get(x["ticker"], 0), reverse=True):
            t      = h["ticker"]
            shrs   = h.get("shares") or 0
            act    = weights.get(t, 0)
            tgt    = float(h.get("targetWeight") or 0)
            role   = h.get("role", "")
            action = derive_action(t, act, tgt)
            emoji  = ACTION_EMOJI.get(action, "")
            entry  = _entry_str(h)
            lines.append(
                f"| **{t}** | {shrs} | {act:.1f}% | {tgt:.1f}% "
                f"| {_gap_str(act, tgt)} | {emoji} {action} | {entry} |"
            )
        lines.append("")

    # ── Pending initiation ────────────────────────────────────────────────────
    if initiate:
        lines += [
            "**Pending Initiation**",
            "",
            "| Ticker | Shares | Actual% | Target% | Gap | Action | Entry Price |",
            "|--------|--------|---------|---------|-----|--------|-------------|",
        ]
        for h in sorted(initiate, key=lambda x: float(x.get("targetWeight") or 0), reverse=True):
            t     = h["ticker"]
            tgt   = float(h.get("targetWeight") or 0)
            entry = _entry_str(h)
            lines.append(
                f"| **{t}** | — | — | {tgt:.1f}% | — | 🟢 INITIATE | {entry} |"
            )
        lines.append("")

    # ── Watchlist (target > 0 but no entry yet) ───────────────────────────────
    if watchlist:
        lines += [
            "**Watchlist** *(target set, entry not yet triggered)*",
            "",
            "| Ticker | Target% | Action | Entry Price | Note |",
            "|--------|---------|--------|-------------|------|",
        ]
        for h in sorted(watchlist, key=lambda x: float(x.get("targetWeight") or 0), reverse=True):
            t     = h["ticker"]
            tgt   = float(h.get("targetWeight") or 0)
            role  = h.get("role", "watchlist")
            entry = _entry_str(h)
            note  = (h.get("thesisForInclusion") or "")[:60]
            lines.append(
                f"| {t} | {tgt:.1f}% | {ROLE_LABEL.get(role, role.upper())} | {entry} | {note} |"
            )
        lines.append("")

    # ── Summary ───────────────────────────────────────────────────────────────
    actual_sum = sum(weights.get(h["ticker"], 0) for h in held)
    target_sum = sum(float(h.get("targetWeight") or 0) for h in holdings_in_pillar)
    gap = actual_sum - target_sum
    lines.append(
        f"**Pillar total — Actual: {actual_sum:.1f}% · Target: {target_sum:.1f}% · "
        f"Gap: {'+' if gap >= 0 else ''}{gap:.1f}pp**"
    )

    return "\n".join(lines)


def run(db_path: Path = DB_PATH) -> None:
    state = load_portfolio_state(db_path)
    shares    = state["shares"]
    prices    = state["prices"]
    total_usd = state["total_usd"]
    weights   = compute_weights(shares, prices, total_usd)

    holdings_list = load_thesis_holdings(str(db_path))

    # Group holdings by pillarId
    by_pillar: dict[str, list[dict]] = {}
    for h in holdings_list:
        pid = h.get("pillarId", "")
        by_pillar.setdefault(pid, []).append(h)

    updated = 0
    for md_file in sorted(SUB_DIR.glob("*.md")):
        sub_id  = md_file.stem
        pids    = PILLAR_MAP.get(sub_id)
        if pids is None:
            continue  # unknown sub-strategy, skip

        holdings = []
        for pid in pids:
            holdings.extend(by_pillar.get(pid, []))

        body = build_current_positions_block(sub_id, holdings, weights, total_usd)
        content = md_file.read_text()
        new_content = replace_block(content, "current_positions", body)
        if new_content != content:
            md_file.write_text(new_content)
            print(f"  ✓ {md_file.name}")
            updated += 1
        else:
            print(f"  — {md_file.name} (no change)")

    print(f"✓ Sub-strategy blocks: {updated} updated.")


if __name__ == "__main__":
    run()
