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

Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Internal state database)
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


def _new_actionable_tickers(
    recommendations: list[dict[str, Any]],
    yesterday: dict[str, Any] | None,
) -> list[str]:
    """Tickers with an actionable recommendation today that were NOT
    actionable in yesterday's brief snapshot.

    "New" is day-over-day (same snapshot-comparison idiom as
    _score_deltas/_pillar_trends), not merely "actionable right now" —
    a ticker that was already actionable yesterday and remains so today
    is not re-flagged every single day.

    Args:
        recommendations: Today's recommendation cards (from
            build_recommendations() — flat list, each with `ticker` and
            `actionable`).
        yesterday: Prior day's full brief snapshot dict, or None on the
            first-ever run.

    Returns:
        Sorted list of ticker symbols. On a first-ever run (yesterday is
        None), every actionable ticker today counts as "new".
    """
    today_actionable = {r["ticker"] for r in recommendations if r.get("actionable")}
    if yesterday is None:
        return sorted(today_actionable)
    yesterday_actionable = {
        r["ticker"] for r in yesterday.get("recommendations", []) if r.get("actionable")
    }
    return sorted(today_actionable - yesterday_actionable)


def _newly_fired_alerts(
    alert_state_start: list[dict[str, Any]],
    alert_state_end: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Alerts that are 'fired' at the end of this /daily run but were
    NOT 'fired' at the start — i.e. genuinely fired during this run,
    not a stale 'fired' state that's been sitting there for weeks.

    Never raises: malformed entries in either list are simply ignored
    (missing 'alert_id' or 'state' keys just don't match).

    Args:
        alert_state_start: sync_alert_state()'s output from the start
            of this run.
        alert_state_end: sync_alert_state()'s output from the end of
            this run.

    Returns:
        The subset of alert_state_end's entries whose state is "fired"
        and whose alert_id was NOT already "fired" at the start.
    """
    fired_at_start = {
        a.get("alert_id") for a in alert_state_start if a.get("state") == "fired"
    }
    return [
        a for a in alert_state_end
        if a.get("state") == "fired" and a.get("alert_id") not in fired_at_start
    ]


def _inject_pine_signals_step(
    recommendations: list[dict[str, Any]],
    yesterday: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Auto-inject 'ai-ta-levels' onto each ticker with a new actionable
    recommendation today (Task 5B-8).

    Real production side effect: physically switches the live
    TradingView chart to each qualifying ticker in turn and injects the
    ai-ta-levels Pine script via pine_script_manager.inject_pine_script().
    Chosen deliberately (user decision, 2026-07-13) over an
    advisory-only or opt-in-flag alternative.

    Graceful error handling: inject_pine_script() itself never raises
    and already logs its own failure reason; this function additionally
    logs a one-line warning per failed ticker and — critically — keeps
    processing the remaining tickers rather than stopping early. Never
    raises.

    Args:
        recommendations: Today's recommendation cards.
        yesterday: Prior day's brief snapshot, or None.

    Returns:
        List of {"ticker": str, "injected": bool} results, one per
        qualifying ticker (empty list if nothing new today).
    """
    tickers = _new_actionable_tickers(recommendations, yesterday)
    if not tickers:
        return []

    sys.path.insert(0, str(PY_SERVICES))
    from pine_script_manager import inject_pine_script

    results = []
    for ticker in tickers:
        ok = inject_pine_script("ai-ta-levels", ticker)
        if not ok:
            print(f"  Pine injection skipped for {ticker} (validation or "
                  f"injection failure — see inject_pine_script's own log)",
                  file=sys.stderr)
        results.append({"ticker": ticker, "injected": ok})
    return results


# ── Core pipeline ─────────────────────────────────────────────────────────────

def _emit_rebalance_events_step(
    recommendations: list[dict[str, Any]],
    scores_raw: list[dict[str, Any]],
) -> None:
    """Emit a G4 rebalance event for each BUY/SELL recommendation card
    (non-blocking — a per-card emission failure is logged nowhere and
    does not stop processing the rest, matching this file's existing
    G4 emission convention for earnings/breaker events).

    Args:
        recommendations: Today's recommendation cards (flat list from
            build_recommendations()).
        scores_raw: Today's conviction score rows, used to look up each
            ticker's current price.
    """
    from evolution_events import emit_rebalance_event
    for rec in recommendations:
        try:
            ticker = rec.get("ticker")
            action = rec.get("recommendation")
            if ticker and action in ("BUY", "SELL"):
                curr_price = next(
                    (s["price"] for s in scores_raw if s["ticker"] == ticker),
                    None,
                )
                emit_rebalance_event(
                    ticker=ticker,
                    order_type="buy" if action == "BUY" else "sell",
                    order_quantity=1,
                    order_price=curr_price or 0.0,
                    rebalance_date=date.today().isoformat(),
                    current_price=curr_price,
                )
        except Exception:
            pass  # Non-blocking


def _harvest_predictions_step() -> int | None:
    """Run the E3 prediction harvest, degrading to None on any failure.

    Isolated into its own function (rather than inlined in run()) so it's
    unit-testable without mocking run()'s other half-dozen dynamically
    imported dependencies.

    Returns:
        Count of newly harvested claims this run, or None if harvesting
        failed — the daily brief must never block on this.
    """
    from harvest_predictions import (
        harvest_action_and_dcf_claims,
        harvest_rebalance_and_breaker_claims,
    )
    try:
        harvested = harvest_action_and_dcf_claims()
        harvested += harvest_rebalance_and_breaker_claims()
        return len(harvested)
    except Exception as exc:
        print(f"  Prediction harvest skipped: {exc}", file=sys.stderr)
        return None


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
    from market_regime import compute_market_regime
    from risk_engine import compute_risk_snapshot
    from earnings_calendar import get_earnings_calendar
    from compute_conviction_scores import compute_all
    from brief_recommendations import build_recommendations, load_standing_decisions
    from overnight_gaps import get_overnight_gaps
    from thesis_breakers import compute_breaker_state
    from alert_manager import sync_alert_state
    from evolution_events import (  # G4 event emission (non-blocking)
        emit_earnings_event,
        emit_breaker_override_event,
        EarningsGrade,
    )

    # ── -1. Alert state sync (start) — 5C-8, advisory only, never raises ─────
    print("▶ Alert state sync (start)...", file=sys.stderr)
    alert_state_start = sync_alert_state()

    # ── 0. Overnight gap scan ─────────────────────────────────────────────────
    print("▶ Overnight gap scan...", file=sys.stderr)
    try:
        gaps = get_overnight_gaps()
    except Exception:
        gaps = []

    # ── 1. Macro regime ───────────────────────────────────────────────────────
    print("▶ Macro regime...", file=sys.stderr)
    macro = get_macro_regime()

    # ── 1a. Market regime (additive — does not feed the RISK-OFF gate above) ──
    print("▶ Market regime...", file=sys.stderr)
    try:
        market_regime = compute_market_regime()
    except Exception as exc:
        print(f"  Market regime skipped: {exc}", file=sys.stderr)
        market_regime = None

    # ── 1b. Portfolio risk snapshot ───────────────────────────────────────────
    print("▶ Risk snapshot...", file=sys.stderr)
    try:
        risk_snapshot = compute_risk_snapshot()
    except Exception as exc:
        print(f"  Risk snapshot skipped: {exc}", file=sys.stderr)
        risk_snapshot = None

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

    # ── 4a. Emit earnings events (G4 — non-blocking) ──────────────────────────
    for e in earnings:
        if e.flag != "UNKNOWN":
            grade_map = {"BEAT": EarningsGrade.BEAT, "MISS": EarningsGrade.MISS, "IN_LINE": EarningsGrade.IN_LINE}
            grade = grade_map.get(e.flag, EarningsGrade.IN_LINE)
            try:
                # Try to get current price from conviction scores
                curr_price = next(
                    (s["price"] for s in scores_raw if s["ticker"] == e.ticker),
                    None,
                )
                emit_earnings_event(
                    ticker=e.ticker,
                    grade=grade,
                    earnings_date=e.earnings_date,
                    current_price=curr_price,
                )
            except Exception:
                pass  # Non-blocking

    # ── 5. Pillar health ──────────────────────────────────────────────────────
    with open(TARGET_PATH) as f:
        target_data = json.load(f)
    pillars = _pillar_summary(scores_raw, target_data)

    # ── 5b. Thesis breaker evaluation (B5 — additive, top-of-triage) ──────────
    print("▶ Thesis breakers...", file=sys.stderr)
    try:
        breaker_state, triggered_breakers = compute_breaker_state(
            conviction_scores=scores_raw,
            market_regime=market_regime,
            pillar_health=pillars,
        )
    except Exception as exc:
        print(f"  Thesis breakers skipped: {exc}", file=sys.stderr)
        breaker_state, triggered_breakers = None, []

    # ── 5c. Emit breaker override events (G4 — non-blocking) ─────────────────
    if breaker_state:
        for ticker, breakers in breaker_state.get("holdings", {}).items():
            for breaker_id, entry in breakers.items():
                if entry.get("status") == "TRIGGERED":
                    try:
                        curr_price = next(
                            (s["price"] for s in scores_raw if s["ticker"] == ticker),
                            None,
                        )
                        emit_breaker_override_event(
                            ticker=ticker,
                            breaker_name=entry.get("metric", breaker_id),
                            override_date=date.today().isoformat(),
                            override_reason=entry.get("note", "Thesis breaker triggered"),
                            breaker_threshold=entry.get("threshold"),
                            current_price=curr_price,
                        )
                    except Exception:
                        pass  # Non-blocking

    # ── 5d. Prediction ledger harvest (E3 — additive, non-blocking) ──────────
    print("▶ Prediction harvest...", file=sys.stderr)
    predictions_harvested = _harvest_predictions_step()

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

    # ── 6a. Emit rebalance events for recommended actions (G4 — non-blocking) ─
    _emit_rebalance_events_step(recommendations, scores_raw)

    # ── 6c. Pine signal injection (5B-8, real TV chart side effect) ──────────
    print("▶ Pine signal injection...", file=sys.stderr)
    pine_injections = _inject_pine_signals_step(recommendations, yesterday)

    # ── 6d. Alert state sync (end) + advisory candidates (5C-8) ──────────────
    # Advisory only: computes which tickers WOULD get a TV alert, but never
    # calls create_price_alert()/dedup_alerts() — real TV alerts can't be
    # individually deleted, so /daily surfaces candidates without creating
    # anything (user decision, 2026-07-14).
    print("▶ Alert state sync (end)...", file=sys.stderr)
    alert_state_end = sync_alert_state()
    newly_fired = _newly_fired_alerts(alert_state_start, alert_state_end)
    advisory_alert_tickers = _new_actionable_tickers(recommendations, yesterday)

    brief: dict[str, Any] = {
        "overnight_gaps": gaps,
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_regime": asdict(macro),
        "market_regime": market_regime,
        "risk_snapshot": risk_snapshot,
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
        "thesis_breakers": breaker_state,
        "thesis_breakers_triggered": triggered_breakers,
        "predictions_harvested": predictions_harvested,
        "pine_injections": pine_injections,
        "alert_sync": {
            "start": alert_state_start,
            "end": alert_state_end,
            "newly_fired": newly_fired,
        },
        "advisory_alert_signals": advisory_alert_tickers,
    }

    # ── 7. Save snapshot ──────────────────────────────────────────────────────
    DAILY_BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    snap = DAILY_BRIEFS_DIR / f"{date.today().isoformat()}.json"
    with open(snap, "w") as f:
        json.dump(brief, f, indent=2)

    return brief


# ── Renderer ──────────────────────────────────────────────────────────────────

def _stale_manual_breakers(
    thesis_breakers: dict[str, Any] | None,
) -> list[tuple[str, str, dict[str, Any]]]:
    """Collect every stale manual breaker across all holdings.

    Args:
        thesis_breakers: The daily brief's thesis_breakers state dict (Task 3's
            compute_breaker_state() output), or None if evaluation failed this run.

    Returns:
        List of (ticker, breaker_id, state_entry) tuples for every manual
        breaker currently flagged stale.
    """
    if not thesis_breakers:
        return []
    return [
        (ticker, bid, entry)
        for ticker, breakers in thesis_breakers.get("holdings", {}).items()
        for bid, entry in breakers.items()
        if entry.get("type") == "manual" and entry.get("stale")
    ]


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

    # ── Thesis breakers (B5 — top of triage, above all TA signals) ────────────
    triggered = brief.get("thesis_breakers_triggered") or []
    if triggered:
        triggered_sorted = sorted(triggered, key=lambda b: -(b.get("targetWeight") or 0))
        lines.append(f"\n🚨  THESIS BREAKER TRIGGERED — {len(triggered_sorted)} holding(s):")
        for b in triggered_sorted:
            thr = b["threshold"]
            thr_str = ",".join(str(t) for t in thr) if isinstance(thr, list) else str(thr)
            if b["type"] == "auto":
                detail = f"(current: {b.get('currentValue')}, {b.get('currentStreak')}/{b.get('horizon')} consecutive runs)"
            else:
                detail = f"(manually flagged TRIGGERED on {b.get('statusSetAt')})"
            lines.append(f"    {b['ticker']:<8} {b['metric']} {b['operator']} {thr_str}  {detail}")
            if b.get("note"):
                lines.append(f"          \"{b['note']}\"")

    # ── Alerts fired since this run started (5C-8, advisory) ───────────────────
    newly_fired = brief.get("alert_sync", {}).get("newly_fired", [])
    if newly_fired:
        lines.append(f"\n🔔  ALERTS FIRED — {len(newly_fired)} since this run started:")
        for a in newly_fired:
            lines.append(f"    {a.get('symbol', '?'):<20} alert_id={a.get('alert_id')}")

    # ── Overnight gaps ────────────────────────────────────────────────────────
    gaps = brief.get("overnight_gaps", [])
    if gaps:
        lines.append(f"\n🌙  OVERNIGHT GAPS — {len(gaps)} mover(s) ≥2%:")
        for g in gaps:
            icon  = "🟢" if g["direction"] == "UP" else "🔴"
            state = g.get("market_state", "")
            lines.append(
                f"    {icon} {g['ticker']:<8}  {g['change_pct']:>+6.1f}%"
                f"  (${g['current']:.2f} vs ${g['prev_close']:.2f})  {state}"
            )

    # ── Macro (unchanged — still feeds the RISK-OFF/NEUTRAL ACCUMULATE gate) ──
    macro_regime_label = macro["regime"]
    if macro_regime_label == "RISK-OFF":
        lines.append("\n⛔  MACRO GATE: RISK-OFF — ACCUMULATE signals blocked today.")
    elif macro_regime_label == "NEUTRAL":
        lines.append("\n⚠️  MACRO GATE: NEUTRAL — only highest-conviction (+4 or above) ACCUMULATE actions.")

    # ── Market regime (new, C2 — additive, informational only) ────────────────
    mr = brief.get("market_regime")
    if mr:
        icon = {"RISK_ON": "✅", "NEUTRAL": "⚠️", "RISK_OFF": "🔴", "STRESS": "🆘"}.get(mr["regime"], "")
        breadth = mr.get("signals", {}).get("breadth", {}).get("value")
        term_slope = mr.get("signals", {}).get("termSlope", {}).get("value")
        breadth_str = f"{breadth:.0f}%" if breadth is not None else "n/a"
        term_str = f"{term_slope:+.2f}" if term_slope is not None else "n/a"
        lines.append(
            f"\n{icon}  REGIME: {mr['regime']} · breadth {breadth_str} · "
            f"term-slope {term_str} · degraded: {'yes' if mr['degraded'] else 'no'}"
        )
    else:
        lines.append("\n⚠️  REGIME: unavailable (market_regime.py failed — see stderr)")

    # ── Portfolio risk snapshot ───────────────────────────────────────────────
    risk = brief.get("risk_snapshot")
    if risk:
        vol = risk.get("portfolioVol")
        beta = risk.get("portfolioBeta")
        cluster = risk.get("clusterExposure") or []
        top_cluster = max(cluster, key=lambda c: c["weight"], default=None)
        mrc = risk.get("marginalRiskContribution") or {}
        mrc_leader = max(mrc.items(), key=lambda kv: kv[1], default=None)

        vol_str = f"{vol * 100:.0f}%" if vol is not None else "—"
        beta_str = f"{beta:.1f}" if beta is not None else "—"
        cluster_str = f"{top_cluster['weight'] * 100:.0f}%" if top_cluster else "—"
        mrc_str = f"{mrc_leader[0]} {mrc_leader[1] * 100:.0f}%" if mrc_leader else "—"

        lines.append(
            f"\n📊  RISK: vol {vol_str} · beta {beta_str} · top cluster {cluster_str} "
            f"· MRC leader: {mrc_str}"
        )

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
        if macro_regime_label == "RISK-OFF":
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

    # ── Advisory alert candidates (5C-8 — advisory only, no real creation) ────
    advisory_tickers = brief.get("advisory_alert_signals", [])
    if advisory_tickers:
        lines.append(
            f"\n💡  Would create TV alerts for: {', '.join(advisory_tickers)} "
            f"(advisory-only — auto-creation disabled)."
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

    # ── Manual breaker staleness (B5) ──────────────────────────────────────────
    stale_manual = _stale_manual_breakers(brief.get("thesis_breakers"))
    if stale_manual:
        lines.append(f"\n🕰   MANUAL BREAKERS NEEDING REVIEW — {len(stale_manual)}:")
        for ticker, bid, entry in stale_manual:
            lines.append(
                f"    {ticker:<8} {bid}  last set {entry['statusSetAt']} "
                f"({entry['daysSinceReview']}d ago, cadence {entry['reviewCadenceDays']}d)"
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
