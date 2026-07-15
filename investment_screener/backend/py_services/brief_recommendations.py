#!/usr/bin/env python3
"""
brief_recommendations.py - Python utility script.

Purpose:
    Actionable recommendation builder for the Daily Brief.

Converts conviction scores + standing decisions + macro gate + earnings flags
into per-ticker recommendation cards: action, plain-language rationale, and a
proposed trade sized from the live broker equity total. Consumed by
daily_brief.py (adds a `recommendations` array to the brief JSON) and rendered
by the Daily Brief page with action buttons.

Standing decisions ANNOTATE — they never mute the underlying signal
(no-sycophancy rule) — but they downgrade the proposed action so the system
never recommends trades against the user's documented calls (e.g. CORZ
allowlisted SA/DCF conflict, OKLO/CEG sell-only-when-green).

Usage (library only — wired into daily_brief.py):
    from brief_recommendations import build_recommendations, load_standing_decisions

Key Input Dependencies:
    - investment_screener/backend/data/daily-briefs/ (Reads conviction data)

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    - load_standing_decisions()
    - _signal_summary()
    - _earnings_note()
    - build_recommendations()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
STANDING_DECISIONS_PATH = (
    REPO_ROOT / "plugins/portfolio-advisor/references/standing-decisions.json"
)

_ACTIONABLE_BANDS = frozenset({"EXIT", "REDUCE", "ACCUMULATE"})


def load_standing_decisions(path: Path = STANDING_DECISIONS_PATH) -> dict[str, Any]:
    """Load the user's standing decisions keyed by ticker.

    Args:
        path: Standing decisions JSON file.

    Returns:
        Dict of ticker → decision dict (empty if file missing).
    """
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f).get("decisions", {})


def _signal_summary(s: dict[str, Any]) -> str:
    """One-line component summary used inside every rationale.

    Args:
        s: Conviction score row.

    Returns:
        Plain-language signal summary string.
    """
    parts = [f"Score {s['total']:+d} ({s['band']})"]
    if s.get("dcf_action"):
        fv = s.get("pct_to_fv")
        fv_str = f" with {fv:+.1f}% to fair value" if fv is not None else ""
        parts.append(f"DCF {s['dcf_action']}{fv_str}")
    if s.get("rsi"):
        parts.append(f"RSI {s['rsi']:.0f}")
    if s.get("flags"):
        parts.append("flags: " + ", ".join(s["flags"][:3]))
    return " · ".join(parts)


def _earnings_note(e: dict[str, Any] | None) -> str:
    """Binary-event warning sentence, or empty string.

    Args:
        e: Earnings flag entry for the ticker, or None.

    Returns:
        Warning sentence when an event is IMMINENT/APPROACHING.
    """
    if not e or e.get("flag") not in ("IMMINENT", "APPROACHING"):
        return ""
    return (f" ⚡ Earnings in {e['days_away']}d ({e['earnings_date']}) — "
            f"binary event, size before acting.")


def build_recommendations(
    scores: list[dict[str, Any]],
    standing: dict[str, Any],
    earnings: list[dict[str, Any]],
    macro: dict[str, Any],
    total_equity: float,
) -> list[dict[str, Any]]:
    """Build ranked recommendation cards from the day's signals.

    Args:
        scores: Conviction score rows (dicts from compute_conviction_scores).
        standing: Standing decisions keyed by ticker.
        earnings: Earnings flag entries (ticker/earnings_date/days_away/flag).
        macro: Macro regime dict (regime/score/degraded).
        total_equity: Live broker total equity USD (totals.totalUSD — never
            computed from shares × price).

    Returns:
        Recommendation cards: sells first (worst score first), then buys
        (best score first). HOLD/WATCH bands produce no cards.
    """
    earn_map = {e["ticker"]: e for e in earnings}
    regime = macro.get("regime", "NEUTRAL")
    sells: list[dict[str, Any]] = []
    buys: list[dict[str, Any]] = []

    for s in scores:
        band = s.get("band")
        if band not in _ACTIONABLE_BANDS:
            continue
        held = (s.get("actual_weight") or 0) > 0
        decision = standing.get(s["ticker"])
        earn = earn_map.get(s["ticker"])
        base: dict[str, Any] = {
            "ticker": s["ticker"],
            "signal": band,
            "score": s["total"],
            "held": held,
            "standingDecision": decision,
            "earnings": earn,
            "proposedTrade": None,
            "actionable": False,
        }

        if band in ("EXIT", "REDUCE"):
            if not held:
                continue   # watchlist noise — nothing to reduce
            if decision:
                base["recommendation"] = "HOLD"
                base["rationale"] = (
                    f"{_signal_summary(s)}. Standing decision "
                    f"({decision.get('type', 'USER')}): {decision.get('reason', '')} "
                    f"Signal stands but no trade proposed without your direction."
                    f"{_earnings_note(earn)}"
                )
                sells.append(base)
                continue
            actual = s.get("actual_weight") or 0.0
            gap = s.get("weight_gap")
            if band == "EXIT":
                trim_pct = actual
                base["recommendation"] = "SELL"
                verb = f"selling the full {actual:.1f}% position"
            else:
                trim_pct = -gap if (gap is not None and gap < -0.5) else actual / 2
                base["recommendation"] = "TRIM"
                verb = f"trimming {trim_pct:.1f}% of portfolio back toward target"
            value = round(trim_pct / 100 * total_equity, 2)
            base["proposedTrade"] = {
                "side": "sell", "ticker": s["ticker"], "approxValueUSD": value,
            }
            base["actionable"] = True
            base["rationale"] = (
                f"{_signal_summary(s)}. Recommend {verb} (~${value:,.0f})."
                f"{_earnings_note(earn)}"
            )
            sells.append(base)
            continue

        # ── ACCUMULATE ────────────────────────────────────────────────────────
        if decision and decision.get("maxEntryPrice"):
            limit = decision["maxEntryPrice"]
            base["recommendation"] = "BUY_LIMIT"
            base["actionable"] = True
            base["rationale"] = (
                f"{_signal_summary(s)}. Standing decision: never add above "
                f"${limit:,.0f} — accumulate via GTC limit at or below that price "
                f"only. {decision.get('reason', '')}{_earnings_note(earn)}"
            )
            buys.append(base)
            continue

        gated = (
            regime == "RISK-OFF"
            or (regime == "NEUTRAL" and s["total"] < 4)
            or macro.get("degraded")
        )
        if gated:
            reason = ("Macro is RISK-OFF — no new buys today; signal queued for "
                      "when the regime improves."
                      if regime == "RISK-OFF" or macro.get("degraded")
                      else "NEUTRAL macro requires score ≥ +4 — signal queued.")
            base["recommendation"] = "QUEUED"
            base["rationale"] = f"{_signal_summary(s)}. {reason}{_earnings_note(earn)}"
            buys.append(base)
            continue

        gap = s.get("weight_gap") or 0.0
        value = round(max(gap, 0.0) / 100 * total_equity, 2)
        base["recommendation"] = "BUY"
        base["actionable"] = True
        base["proposedTrade"] = {
            "side": "buy", "ticker": s["ticker"], "approxValueUSD": value,
        }
        base["rationale"] = (
            f"{_signal_summary(s)}. Underweight {gap:+.1f}pp vs target — "
            f"recommend buying ~${value:,.0f} to close the gap."
            f"{_earnings_note(earn)}"
        )
        buys.append(base)

    sells.sort(key=lambda r: r["score"])
    buys.sort(key=lambda r: -r["score"])
    ranked = sells + buys
    for i, r in enumerate(ranked, start=1):
        r["urgency"] = i
    return ranked
