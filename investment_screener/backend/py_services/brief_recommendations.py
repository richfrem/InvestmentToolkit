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

Standing decisions block trade proposals while preserving the canonical recommendation
(no-sycophancy rule) — but they gate trade readiness so the system
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

_ACTIONABLE_BANDS = frozenset({"EXIT", "TRIM", "ACCUMULATE", "INITIATE"})

# Overweight (in percentage points) beyond which a TRIM signal proposes a trim back to target.
_TRIM_BAND_PP = 0.5


def load_standing_decisions(path: Path | None = None, db_path: str | None = None) -> dict[str, Any]:
    """Load the user's standing decisions keyed by ticker.

    Args:
        path: Standing decisions JSON file.

    Returns:
        Dict of ticker → decision dict (empty if file missing).
    """
    if path is None:
        from recommendation import recommend_all
        return {t: r["standing_decision"] for t, r in recommend_all(db_path).items()
                if r.get("standing_decision")}
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
        (best score first). MAINTAIN/WATCHLIST actions produce no cards.
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
        # What the owner actually traded lately (recent_trades.py, via recommendation.py).
        recent = s.get("recent_trades") if (s.get("recent_trades") or {}).get("count") else None
        acted = bool(recent) and recent["context"]["status"] == "ACTED"
        further = " a further" if acted else ""
        base: dict[str, Any] = {
            "ticker": s["ticker"],
            "signal": band,
            "recommendation": band,
            "executionStatus": "REVIEW",
            "score": s["total"],
            "held": held,
            "standingDecision": decision,
            "earnings": earn,
            "recentTrades": recent,
            "proposedTrade": None,
            "actionable": False,
        }

        if band in ("EXIT", "TRIM"):
            if not held:
                continue   # watchlist noise — nothing to reduce
            if decision:
                base["executionStatus"] = "BLOCKED"
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
                base["executionStatus"] = "READY"
                verb = f"selling the {'remaining' if acted else 'full'} {actual:.1f}% position"
            elif gap is not None and gap < -_TRIM_BAND_PP:
                trim_pct = -gap
                base["executionStatus"] = "READY"
                verb = f"trimming{further} {trim_pct:.1f}% of portfolio back toward target"
            else:
                # TRIM comes from the DCF score; with no material overweight there is no
                # basis to size a sell (AGENTS rule 9: DCF never silently overrides targets).
                # This used to fall through to `actual / 2` and propose selling half of a
                # position that was at or under target (RIOT, MU on 2026-10-01).
                target = s.get("target_weight")
                where = (f"{actual:.1f}% vs a {target:.1f}% target"
                         if target is not None else f"{actual:.1f}% with no target weight")
                base["executionStatus"] = "BLOCKED"
                base["rationale"] = (
                    f"{_signal_summary(s)}. Weight is within {_TRIM_BAND_PP:.1f}pp of target "
                    f"({where}), so no trade is proposed; the TRIM signal alone does not "
                    f"size a sale. Review the thesis if you want to cut it."
                    f"{_earnings_note(earn)}"
                )
                sells.append(base)
                continue
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
        if decision and not decision.get("maxEntryPrice"):
            base["executionStatus"] = "BLOCKED"
            base["rationale"] = f"{_signal_summary(s)}. Standing decision: {decision.get('reason', '')}. Review before trading."
            buys.append(base)
            continue
        if decision and decision.get("maxEntryPrice"):
            limit = decision["maxEntryPrice"]
            base["executionStatus"] = "LIMIT_ONLY"
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
            base["executionStatus"] = "QUEUED"
            base["rationale"] = f"{_signal_summary(s)}. {reason}{_earnings_note(earn)}"
            buys.append(base)
            continue

        gap = s.get("weight_gap") or 0.0
        if gap <= 0:
            base["rationale"] = f"{_signal_summary(s)}. Set or review the target allocation before sizing a trade."
            buys.append(base)
            continue
        value = round(gap / 100 * total_equity, 2)
        base["executionStatus"] = "READY"
        base["actionable"] = True
        base["proposedTrade"] = {
            "side": "buy", "ticker": s["ticker"], "approxValueUSD": value,
        }
        base["rationale"] = (
            f"{_signal_summary(s)}. Underweight {gap:+.1f}pp vs target — "
            f"recommend buying{further} ~${value:,.0f} to close the gap."
            f"{_earnings_note(earn)}"
        )
        buys.append(base)

    sells.sort(key=lambda r: r["score"])
    buys.sort(key=lambda r: -r["score"])
    ranked = sells + buys
    # Every card says what was already traded, so a signal never reads as if nothing happened.
    for card in ranked:
        note = ((card["recentTrades"] or {}).get("context") or {}).get("note")
        if note:
            card["rationale"] = f"{card['rationale']} {note}."
    for i, r in enumerate(ranked, start=1):
        r["urgency"] = i
    return ranked


def align_current_brief(brief: dict[str, Any], db_path: str | None = None) -> dict[str, Any]:
    """Overlay current canonical actions and rebuild trade cards without rewriting history.

    Numeric scores and macro context retain their snapshot dates; holdings, valuation,
    and recommendations are read from the current domain database.
    """
    from recommendation import recommend_all
    from portfolio_io import load_portfolio_state, load_target_weights

    records = recommend_all(db_path)
    targets = load_target_weights(db_path)
    scores = []
    for original in brief.get("conviction_scores", []):
        rec = records.get(original["ticker"])
        if rec is None:
            continue
        score = dict(original)
        actual = rec["current_weight_pct"]
        target = targets.get(original["ticker"])
        score.update(band=rec["action"], dcf_action=rec["valuation"], pct_to_fv=rec["upside_pct"],
                     recent_trades=rec.get("recent_trades"),
                     actual_weight=actual, target_weight=target,
                     weight_gap=target - actual if target is not None else None)
        scores.append(score)
    standing = {t: r["standing_decision"] for t, r in records.items() if r.get("standing_decision")}
    state = load_portfolio_state(None, db_path=db_path)
    return {**brief, "conviction_scores": scores,
            "recommendations": build_recommendations(scores, standing, brief.get("earnings_flags", []),
                                                       brief.get("macro_regime", {}), state["total_usd"])}
