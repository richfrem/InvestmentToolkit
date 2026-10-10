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
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "plugins/portfolio-advisor/scripts"))
from risk_reward import refresh_advice  # noqa: E402
from standing_decision_check import decision_condition  # noqa: E402

_ACTIONABLE_BANDS = frozenset({"EXIT", "TRIM", "ACCUMULATE", "INITIATE"})

# Overweight (in percentage points) beyond which a TRIM signal proposes a trim back to target.
_TRIM_BAND_PP = 0.5
# How many of the day's top cards are checked for a stale valuation before acting.
REFRESH_CHECK_TOP_N = 5


def load_standing_decisions(db_path: str | None = None) -> dict[str, Any]:
    """Load the owner's standing decisions keyed by ticker, from domain_model.sqlite.

    The decisions live on ``investment.standing_decision_type`` / ``standing_decision_reason``
    and reach this function through the canonical recommendation records; there is no file.

    Args:
        db_path: domain_model.sqlite to read (default: the real database).

    Returns:
        Dict of ticker -> standing decision (only tickers that have one).
    """
    from recommendation import recommend_all
    return {t: r["standing_decision"] for t, r in recommend_all(db_path).items()
            if r.get("standing_decision")}


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


def _decision_text(check: dict[str, Any] | None, decision: dict[str, Any]) -> str:
    """Why a standing decision holds this card back: the reconciled note when available."""
    reason = str(decision.get("reason") or "").strip()
    if check and check.get("note"):
        return f"{check['note']}{' Your recorded reason: ' + reason if reason else ''}"
    return (f"Standing decision ({decision.get('type', 'USER')}): {reason} "
            "Signal stands but no trade proposed without your direction.")


_VALUATION_WORDS = {"BUY": "a buy", "ACCUMULATE": "a buy", "SELL": "a sell", "TRIM": "a sell",
                    "HOLD": "a hold", "MAINTAIN": "a hold"}


def _valuation_view(s: dict[str, Any]) -> str:
    """The valuation model's opinion as a sentence, for cards whose stance is not the model's action."""
    words = _VALUATION_WORDS.get(str(s.get("dcf_action") or "").upper())
    fv = s.get("pct_to_fv")
    gap = f", {fv:+.1f}% to fair value" if fv is not None else ""
    rated = f"the valuation model rates it {words}{gap}" if words else f"the valuation score is {s['total']:+d}{gap}"
    return f"For reference only, {rated}."


def _held_back_rationale(s: dict[str, Any], check: dict[str, Any] | None, decision: dict[str, Any],
                         condition: dict[str, Any] | None) -> str:
    """Rationale for a card the standing decision holds back.

    When the stance differs from the valuation action the stance leads and the valuation
    is one closing sentence, so the card never reads as two recommendations.
    """
    waits = f" {condition['note']}" if condition else ""
    if check and check.get("effective") != s.get("band"):
        return f"{_decision_text(check, decision)}{waits} {_valuation_view(s)}"
    return f"{_signal_summary(s)}. {_decision_text(check, decision)}{waits}"


_PRIORITY_LABELS = ("Ready to act", "Needs your decision", "No trade proposed", "Waiting for your condition", "Already acted on")


def _priority(card: dict[str, Any]) -> dict[str, Any]:
    """Where a card ranks today and why.

    Tiers: 0 ready to act, 1 the standing decision and valuation disagree, 2 no trade
    proposed, 3 waiting (owner's condition or the macro gate), 4 already acted on. A
    decision condition that is met lifts the card to tier 0.
    """
    relation = (card.get("decisionCheck") or {}).get("relation")
    recent = card.get("recentTrades") or {}
    # A level named in the owner's decision only steers cards that decision governs.
    condition = card.get("condition") if relation in ("AGREES", "CONFIRMED", "WAITS") else None
    label = None
    if (recent.get("context") or {}).get("status") == "ACTED":
        tier = 4
    elif card["executionStatus"] in ("READY", "LIMIT_ONLY"):
        tier = 0
    elif condition and condition["met"]:
        tier, label = 0, "Your condition is met"
    elif relation in ("CONFLICT", "OUTDATED", "UNCLEAR"):
        tier = 1
    elif relation == "WAITS" or card["executionStatus"] == "QUEUED" or condition:
        tier = 3
    else:
        tier = 2
        label = "Holding by your decision" if relation == "CONFIRMED" else None
    if tier == 3 and card["executionStatus"] == "QUEUED":
        label = "Queued by the macro gate"
    return {"tier": tier, "label": label or _PRIORITY_LABELS[tier]}


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
        Recommendation cards in today's priority order: ready to act, needs your
        decision, no trade proposed, waiting, already acted on; within a group sells
        before buys, then the larger valuation gap first. MAINTAIN/WATCHLIST actions
        produce no cards.
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
        # Does the owner's standing decision agree with this action (standing_decision_check.py)?
        check = s.get("decision_check") or None
        if check and check["relation"] == "OUTDATED":
            decision = None   # an entry call cannot govern a position already held
        base: dict[str, Any] = {
            "ticker": s["ticker"],
            "signal": band,
            # One stance per card: the action, or the reconciled stance when a standing decision disagrees.
            "recommendation": check["effective"] if check else band,
            "decisionCheck": check,
            # Is the level named in the standing decision reached (standing_decision_check.py)?
            "condition": decision_condition(decision, s.get("price"), s.get("levels")),
            "refreshFirst": None,
            "pctToFairValue": s.get("pct_to_fv"),
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
                base["rationale"] = f"{_held_back_rationale(s, check, decision, base['condition'])}{_earnings_note(earn)}"
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
            base["rationale"] = _held_back_rationale(s, check, decision, base["condition"])
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

    ranked = sells + buys
    for card in ranked:
        check = card["decisionCheck"]
        if check and check["relation"] in ("OUTDATED", "UNCLEAR"):
            card["rationale"] = f"{card['rationale']} {check['note']}"
        card["priority"] = _priority(card)
    # Daily priority order, not sell-then-buy by score: almost every card shares one score.
    ranked.sort(key=lambda r: (r["priority"]["tier"], 0 if r["signal"] in ("EXIT", "TRIM") else 1,
                               -abs(r["score"]), -abs(r["pctToFairValue"] or 0), r["ticker"]))
    # Every card says what was already traded, so a signal never reads as if nothing happened.
    for card in ranked:
        note = ((card["recentTrades"] or {}).get("context") or {}).get("note")
        if note:
            card["rationale"] = f"{card['rationale']} {note}."
    supports = {s["ticker"]: (s.get("support"), s.get("dcf_action")) for s in scores}
    for i, r in enumerate(ranked, start=1):
        r["urgency"] = i
        # The cards most likely to be acted on today must rest on a current valuation.
        if i <= REFRESH_CHECK_TOP_N:
            r["refreshFirst"] = refresh_advice(r["ticker"], *supports[r["ticker"]])
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
                     price=rec.get("price"), support=rec.get("support"),
                     recent_trades=rec.get("recent_trades"), decision_check=rec.get("decision_check"),
                     actual_weight=actual, target_weight=target,
                     weight_gap=target - actual if target is not None else None)
        scores.append(score)
    standing = {t: r["standing_decision"] for t, r in records.items() if r.get("standing_decision")}
    state = load_portfolio_state(db_path=db_path)
    return {**brief, "conviction_scores": scores,
            "recommendations": build_recommendations(scores, standing, brief.get("earnings_flags", []),
                                                       brief.get("macro_regime", {}), state["total_usd"])}
