"""Daily portfolio brief — the one command that runs everything.

Continuous improvement loop:
  1. Macro regime check (VIX, SPY 200D, credit)
  2. TA sweep — auto-runs if stale >4 hours (skips if TradingView not running)
  3. Unified conviction scores (DCF + TA + thesis gap + momentum)
  4. Earnings calendar (binary event flags for next 30 days)
  5. Delta vs yesterday (which holdings improved or deteriorated)
  6. Pillar health aggregation (sub-strategy level conviction)
  7. Saves JSON snapshot → data/daily-briefs/YYYY-MM-DD.json

Each day's run builds on the last. After 5+ days the brief surfaces
conviction trends that single-session analysis cannot see.

Usage:
    python3 plugins/portfolio-advisor/scripts/daily_brief.py
    python3 plugins/portfolio-advisor/scripts/daily_brief.py --skip-ta
    python3 plugins/portfolio-advisor/scripts/daily_brief.py --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT        = Path(__file__).resolve().parents[3]
PY_SERVICES      = REPO_ROOT / "investment_screener/backend/py_services"
TA_SWEEP_SCRIPT  = REPO_ROOT / "plugins/tradingview/scripts/ta_sweep_batch.py"
TA_SWEEP_PATH    = REPO_ROOT / "investment_screener/backend/data/ta-sweep-results.json"
TARGET_PATH      = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
DAILY_BRIEFS_DIR = REPO_ROOT / "investment_screener/backend/data/daily-briefs"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ta_age_hours() -> float | None:
    """Return hours since last TA sweep, or None if no file."""
    if not TA_SWEEP_PATH.exists():
        return None
    with open(TA_SWEEP_PATH) as f:
        data = json.load(f)
    ts = data.get("timestamp")
    if not ts:
        return None
    scanned = datetime.fromisoformat(ts)
    return (datetime.now(timezone.utc) - scanned).total_seconds() / 3600


def _tv_running() -> bool:
    """Return True if TradingView CDP is accessible on port 9222."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:9222/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _load_yesterday() -> dict[str, Any] | None:
    """Load the most recent prior daily brief snapshot."""
    DAILY_BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    for snap in sorted(DAILY_BRIEFS_DIR.glob("*.json"), reverse=True):
        if snap.stem != today_str:
            with open(snap) as f:
                return json.load(f)
    return None


def _score_deltas(
    today: list[dict[str, Any]],
    yesterday: dict[str, Any] | None,
) -> dict[str, int]:
    """Compute conviction score change vs. yesterday.

    Args:
        today: Today's conviction score list (dicts with ticker/total).
        yesterday: Prior day brief snapshot (or None).

    Returns:
        Dict of ticker → delta (positive = improving).
    """
    if not yesterday:
        return {}
    prev = {s["ticker"]: s["total"] for s in yesterday.get("conviction_scores", [])}
    return {
        s["ticker"]: s["total"] - prev[s["ticker"]]
        for s in today
        if s["ticker"] in prev
    }


def _pillar_summary(
    scores: list[dict[str, Any]],
    target_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Aggregate conviction scores by sub-strategy pillar.

    Args:
        scores: Conviction score dicts.
        target_data: Parsed target-portfolio.json.

    Returns:
        Pillar summary list sorted by avg_score descending.
    """
    ticker_pillar = {
        h["ticker"]: h.get("subStrategyId", "unknown")
        for h in target_data.get("holdings", [])
    }
    pillars: dict[str, list[int]] = {}
    for s in scores:
        p = ticker_pillar.get(s["ticker"], "unknown")
        pillars.setdefault(p, []).append(s["total"])

    return sorted(
        [
            {
                "pillar": p,
                "avg_score": round(sum(pts) / len(pts), 2),
                "count": len(pts),
                "min": min(pts),
                "max": max(pts),
            }
            for p, pts in pillars.items()
            if p not in ("unknown", "cash")
        ],
        key=lambda x: x["avg_score"],
        reverse=True,
    )


def _pillar_trends(
    today_pillars: list[dict[str, Any]],
    yesterday: dict[str, Any] | None,
) -> dict[str, float]:
    """Compare today's pillar avg scores vs. yesterday.

    Args:
        today_pillars: Today's pillar health list.
        yesterday: Prior day brief snapshot.

    Returns:
        Dict of pillar → delta (positive = improving).
    """
    if not yesterday:
        return {}
    prev = {p["pillar"]: p["avg_score"] for p in yesterday.get("pillar_health", [])}
    return {
        p["pillar"]: round(p["avg_score"] - prev[p["pillar"]], 2)
        for p in today_pillars
        if p["pillar"] in prev
    }


# ── Core pipeline ─────────────────────────────────────────────────────────────

def run(skip_ta: bool = False) -> dict[str, Any]:
    """Execute the full daily brief pipeline.

    Args:
        skip_ta: Skip TA sweep refresh even when stale.

    Returns:
        Full brief dict ready for JSON serialisation and terminal rendering.
    """
    # Dynamically import py_services modules
    sys.path.insert(0, str(PY_SERVICES))
    from macro_regime import get_macro_regime
    from earnings_calendar import get_earnings_calendar
    from compute_conviction_scores import compute_all
    from brief_recommendations import build_recommendations, load_standing_decisions
    from overnight_gaps import get_overnight_gaps

    # ── 0. Overnight gap scan ─────────────────────────────────────────────────
    print("▶ Overnight gap scan...", file=sys.stderr)
    try:
        gaps = get_overnight_gaps()
    except Exception:
        gaps = []

    # ── 1. Macro regime ───────────────────────────────────────────────────────
    print("▶ Macro regime...", file=sys.stderr)
    macro = get_macro_regime()

    # ── 2. TA sweep (auto-refresh if stale) ───────────────────────────────────
    age = _ta_age_hours()
    ran_ta = False
    ta_skip_reason = ""
    if not skip_ta and (age is None or age > 4):
        if _tv_running():
            age_str = "never" if age is None else f"{age:.1f}h ago"
            print(f"▶ TA sweep (last: {age_str})...", file=sys.stderr)
            result = subprocess.run(
                [sys.executable, str(TA_SWEEP_SCRIPT), "--no-save"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                try:
                    scan = json.loads(result.stdout)
                    payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "scan_date": date.today().isoformat(),
                        "count": len(scan),
                        "results": scan,
                    }
                    with open(TA_SWEEP_PATH, "w") as f:
                        json.dump(payload, f, indent=2)
                    ran_ta = True
                    print(f"  Scanned {len(scan)} holdings.", file=sys.stderr)
                except json.JSONDecodeError:
                    ta_skip_reason = "TA sweep output could not be parsed"
            else:
                ta_skip_reason = "TA sweep exited with error"
        else:
            ta_skip_reason = "TradingView not running (port 9222)"
            age_str = "never" if age is None else f"{age:.1f}h ago"
            print(f"▶ TA sweep skipped — {ta_skip_reason} (using data from {age_str})",
                  file=sys.stderr)
    else:
        if age is not None and age <= 4:
            print(f"▶ TA sweep fresh ({age:.1f}h ago) — skipping rescan.", file=sys.stderr)

    # ── 3. Conviction scores ──────────────────────────────────────────────────
    print("▶ Conviction scores...", file=sys.stderr)
    scores = compute_all()
    scores_raw = [asdict(s) for s in scores]

    # ── 4. Earnings calendar ──────────────────────────────────────────────────
    print("▶ Earnings calendar...", file=sys.stderr)
    earnings = get_earnings_calendar(days_threshold=30)
    earnings_raw = [
        {"ticker": e.ticker, "earnings_date": e.earnings_date,
         "days_away": e.days_away, "flag": e.flag}
        for e in earnings
        if e.flag != "UNKNOWN"
    ]

    # ── 5. Pillar health ──────────────────────────────────────────────────────
    with open(TARGET_PATH) as f:
        target_data = json.load(f)
    pillars = _pillar_summary(scores_raw, target_data)

    # ── 6. Deltas vs yesterday ────────────────────────────────────────────────
    yesterday = _load_yesterday()
    deltas = _score_deltas(scores_raw, yesterday)
    pillar_deltas = _pillar_trends(pillars, yesterday)

    # ── 6b. Actionable recommendations (standing-decision aware) ─────────────
    print("▶ Recommendations...", file=sys.stderr)
    portfolio_path = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
    total_equity = 0.0
    if portfolio_path.exists():
        with open(portfolio_path) as f:
            # Live broker total — never computed from shares × price
            total_equity = json.load(f).get("totals", {}).get("totalUSD", 0.0)
    recommendations = build_recommendations(
        scores=scores_raw,
        standing=load_standing_decisions(),
        earnings=earnings_raw,
        macro=asdict(macro),
        total_equity=total_equity,
    )

    brief: dict[str, Any] = {
        "overnight_gaps": gaps,
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_regime": asdict(macro),
        "ta_refreshed": ran_ta,
        "ta_skip_reason": ta_skip_reason,
        "conviction_scores": scores_raw,
        "recommendations": recommendations,
        "total_equity": total_equity,
        "score_deltas": deltas,
        "pillar_health": pillars,
        "pillar_deltas": pillar_deltas,
        "earnings_flags": earnings_raw,
        "yesterday_date": yesterday.get("date") if yesterday else None,
    }

    # ── 7. Save snapshot ──────────────────────────────────────────────────────
    DAILY_BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    snap = DAILY_BRIEFS_DIR / f"{date.today().isoformat()}.json"
    with open(snap, "w") as f:
        json.dump(brief, f, indent=2)

    return brief


# ── Renderer ──────────────────────────────────────────────────────────────────

def render(brief: dict[str, Any]) -> str:
    """Render the daily brief as a human-readable report.

    Args:
        brief: Full brief dict from run().

    Returns:
        Formatted multi-line string for terminal output.
    """
    lines: list[str] = []
    today      = brief["date"]
    macro      = brief["macro_regime"]
    deltas     = brief.get("score_deltas", {})
    p_deltas   = brief.get("pillar_deltas", {})
    scores     = brief.get("conviction_scores", [])
    earnings   = brief.get("earnings_flags", [])
    pillars    = brief.get("pillar_health", [])
    yesterday  = brief.get("yesterday_date", "—")

    W = 72
    lines += [f"\n{'═' * W}", f"  DAILY PORTFOLIO BRIEF — {today}  (prev: {yesterday})", f"{'═' * W}"]

    # ── Macro ─────────────────────────────────────────────────────────────────
    regime = macro["regime"]
    icon   = {"RISK-ON": "✅", "NEUTRAL": "⚠️", "RISK-OFF": "🔴"}.get(regime, "")
    lines.append(f"\n{icon}  MACRO REGIME: {regime}  (score={macro['score']})")
    for d in macro["details"]:
        lines.append(f"    {d}")
    if regime == "RISK-OFF":
        lines.append("    ⛔  Gate all ACCUMULATE signals. Execute only REDUCE / EXIT today.")
    elif regime == "NEUTRAL":
        lines.append("    ⚠️  Only highest-conviction (+4 or above) ACCUMULATE actions.")

    # ── Earnings / binary events ──────────────────────────────────────────────
    urgent = [e for e in earnings if e["flag"] in ("IMMINENT", "APPROACHING")]
    if urgent:
        lines.append(f"\n⚡  BINARY EVENTS — {len(urgent)} earnings approaching:")
        for e in urgent:
            flag_icon = "🔴" if e["flag"] == "IMMINENT" else "🟡"
            lines.append(f"    {flag_icon} {e['ticker']:<8} reports {e['earnings_date']}  "
                         f"({e['days_away']}d)  → consider pre-event size reduction")

    # ── REDUCE / EXIT list ────────────────────────────────────────────────────
    reduce = [s for s in scores if s["band"] in ("EXIT", "REDUCE")]
    if reduce:
        lines.append(f"\n▼  REDUCE / EXIT — {len(reduce)} holdings:")
        lines.append(f"   {'TICKER':<8} {'SCORE':>5}  {'BAND':<10}  "
                     f"{'DCF_ACTION':<12}  {'RSI':>5}  {'Δ':>4}  FLAGS")
        lines.append(f"   {'─' * 65}")
        for s in reduce:
            d_str = f"{deltas[s['ticker']]:+d}" if s["ticker"] in deltas else " —"
            flags = ",".join(s["flags"][:2]) if s["flags"] else ""
            lines.append(
                f"   {s['ticker']:<8} {s['total']:>+5d}  {s['band']:<10}  "
                f"{(s['dcf_action'] or 'n/a'):<12}  {s['rsi'] or 0:>5.1f}  "
                f"{d_str:>4}  {flags}"
            )

    # ── ACCUMULATE list (gated by macro) ──────────────────────────────────────
    accum = [s for s in scores if s["band"] == "ACCUMULATE"]
    if accum:
        if regime == "RISK-OFF":
            lines.append(f"\n  (ACCUMULATE signals muted — RISK-OFF macro. "
                         f"{len(accum)} candidates queued.)")
        else:
            lines.append(f"\n▲  ACCUMULATE — {len(accum)} holdings:")
            lines.append(f"   {'TICKER':<8} {'SCORE':>5}  {'DCF%FV':>7}  "
                         f"{'RSI':>5}  {'WGT_GAP':>7}  {'Δ':>4}  FLAGS")
            lines.append(f"   {'─' * 65}")
            for s in accum:
                d_str  = f"{deltas[s['ticker']]:+d}" if s["ticker"] in deltas else " —"
                fv_str = f"{s['pct_to_fv']:>+7.1f}" if s["pct_to_fv"] is not None else "    n/a"
                gap_str = f"{s['weight_gap']:>+6.1f}%" if s["weight_gap"] is not None else "     —"
                flags  = ",".join(s["flags"][:2]) if s["flags"] else ""
                lines.append(
                    f"   {s['ticker']:<8} {s['total']:>+5d}  {fv_str}  "
                    f"{s['rsi'] or 0:>5.1f}  {gap_str}  {d_str:>4}  {flags}"
                )

    # ── Score deltas ──────────────────────────────────────────────────────────
    if deltas:
        dn = sorted([(t, d) for t, d in deltas.items() if d < 0], key=lambda x: x[1])
        up = sorted([(t, d) for t, d in deltas.items() if d > 0], key=lambda x: -x[1])
        if dn:
            lines.append(f"\n📉  DETERIORATING vs {yesterday}:")
            for t, d in dn[:5]:
                lines.append(f"    {t:<8}  {d:+d} pts")
        if up:
            lines.append(f"\n📈  IMPROVING vs {yesterday}:")
            for t, d in up[:5]:
                lines.append(f"    {t:<8}  {d:+d} pts")

    # ── Pillar health ─────────────────────────────────────────────────────────
    if pillars:
        lines.append(f"\n🏛   PILLAR HEALTH:")
        lines.append(f"   {'PILLAR':<20}  {'AVG':>5}  {'RANGE':>8}  TREND  HOLDINGS")
        lines.append(f"   {'─' * 60}")
        for p in pillars:
            pname = p["pillar"]
            pd_str = ""
            if pname in p_deltas:
                d = p_deltas[pname]
                pd_str = f"{'▲' if d > 0 else '▼' if d < 0 else '━'} {d:+.2f}"
            bar = "▓" * max(0, int(p["avg_score"]) + 3) + "░" * max(0, 3 - int(p["avg_score"]))
            lines.append(
                f"   {pname:<20}  {p['avg_score']:>+5.2f}  "
                f"[{p['min']:+d}→{p['max']:+d}]  {pd_str:<8}  "
                f"n={p['count']}  {bar}"
            )

    # ── Footer ────────────────────────────────────────────────────────────────
    snap = DAILY_BRIEFS_DIR / f"{today}.json"
    lines += [f"\n  Snapshot saved → {snap}", f"{'─' * W}\n"]
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Daily portfolio brief")
    parser.add_argument("--skip-ta", action="store_true",
                        help="Skip TA sweep even if stale")
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")
    args = parser.parse_args()

    brief = run(skip_ta=args.skip_ta)

    if args.json:
        print(json.dumps(brief, indent=2))
    else:
        print(render(brief))


if __name__ == "__main__":
    main()
