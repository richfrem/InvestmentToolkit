"""Unified conviction scorer for portfolio holdings.

Combines DCF projections, TA sweep signals, and thesis weight gap into a
single per-holding score (range −6 to +6). Drives the daily brief's ranked
action list.

Score = dcf_pts + ta_pts + weight_gap_pts + momentum_pts

Bands:
    ≥ +3 : ACCUMULATE  — consider adding to position
    +1–+2: HOLD        — no action required
     0   : WATCH       — borderline; monitor closely
    −1–−2: REDUCE      — trim toward target or below
    ≤ −3 : EXIT        — thesis broken; full exit

Usage:
    python3 compute_conviction_scores.py
    python3 compute_conviction_scores.py --json
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT        = Path(__file__).resolve().parents[3]
TA_SWEEP_PATH    = REPO_ROOT / "investment_screener/backend/data/ta-sweep-results.json"
PROJECTIONS_DIR  = REPO_ROOT / "investment_screener/backend/data/projections"
TARGET_PATH      = REPO_ROOT / "investment_screener/backend/data/theses/target-portfolio.json"
PORTFOLIO_PATH   = REPO_ROOT / "investment_screener/backend/data/portfolio.json"
SKIP_TICKERS     = frozenset({"PSU-U.TO", "PSU.U.TO", "USD_CASH", "USD_CASH_TFSA"})


@dataclass
class ConvictionScore:
    """Per-holding conviction score with component breakdown."""

    ticker: str
    total: int
    band: str               # ACCUMULATE | HOLD | WATCH | REDUCE | EXIT
    dcf_pts: int            # −2 to +2: from DCF action signal
    ta_pts: int             # −2 to +1: from RSI/Vol Bias/flags
    weight_gap_pts: int     # −1 to +1: underweight BUY or overweight SELL
    momentum_pts: int       # −1 to +1: ADX trend quality
    dcf_action: str | None
    pct_to_fv: float | None
    rsi: float | None
    adx: float | None
    vol_bias: float | None
    actual_weight: float | None
    target_weight: float | None
    weight_gap: float | None    # positive = underweight vs target
    flags: list[str]
    ta_staleness_days: int | None


# ── DCF scoring ────────────────────────────────────────────────────────────────

_DCF_MAP: dict[str, int] = {
    "BUY":        +2,
    "ACCUMULATE": +2,
    "MAINTAIN":   +1,
    "HOLD":       +1,
    "TRIM":       -1,
    "SELL":       -2,
}


def _score_dcf(action: str | None) -> int:
    """Score DCF action signal.

    Args:
        action: DCF recommendation string from projection.

    Returns:
        Score contribution in range −2 to +2.
    """
    return _DCF_MAP.get((action or "").upper(), 0)


# ── TA scoring ─────────────────────────────────────────────────────────────────

def _score_ta(
    rsi: float | None,
    vol_bias: float | None,
    flags: list[str],
) -> int:
    """Score technical analysis signals.

    Oversold RSI is bullish for long-term accumulation.
    Overbought + cooling RSI signals fading momentum.
    Heavy distribution (vol_bias deeply negative) is bearish.

    Args:
        rsi: Current RSI value (0–100).
        vol_bias: Volume bias percentage from AI TA Levels indicator.
        flags: TA flag list from sweep result.

    Returns:
        Score contribution clamped to −2 to +1.
    """
    if rsi is None:
        return 0
    pts = 0

    if rsi < 35:
        pts += 1         # oversold — strong long-term entry zone
    elif rsi > 70:
        pts -= 1         # overbought — elevated add risk

    if "RSI_COOLING" in flags:
        pts -= 1         # momentum fading from peak

    if vol_bias is not None and vol_bias < -25:
        pts -= 1         # heavy sustained distribution

    return max(-2, min(1, pts))


# ── Weight gap scoring ─────────────────────────────────────────────────────────

def _score_weight_gap(gap: float | None, dcf_action: str | None) -> int:
    """Score position sizing vs. thesis target.

    Only applies the bonus/penalty when DCF and positioning agree:
    underweight + BUY = add urgency; overweight + SELL = reduce urgency.

    Args:
        gap: target_weight − actual_weight (positive = underweight).
        dcf_action: Current DCF recommendation.

    Returns:
        Score contribution in range −1 to +1.
    """
    if gap is None:
        return 0
    bullish = (dcf_action or "").upper() in ("BUY", "ACCUMULATE")
    bearish = (dcf_action or "").upper() in ("SELL", "TRIM")

    if gap > 1.0 and bullish:
        return +1
    if gap < -1.0 and bearish:
        return -1
    return 0


# ── Momentum scoring ───────────────────────────────────────────────────────────

def _score_momentum(adx: float | None, flags: list[str]) -> int:
    """Score trend quality via ADX and momentum flags.

    Strong trend without cooling = conviction intact.
    Strong ADX + RSI cooling = trend fading — reduces conviction to add.
    Weak ADX = no directional evidence.

    Args:
        adx: Average Directional Index value.
        flags: TA flag list from sweep result.

    Returns:
        Score contribution in range −1 to +1.
    """
    if adx is None:
        return 0
    strong = adx >= 30
    cooling = "RSI_COOLING" in flags

    if strong and not cooling:
        return +1    # strong trend, momentum intact
    if strong and cooling:
        return -1    # fading strong trend — often marks a top
    return 0


# ── Band classification ────────────────────────────────────────────────────────

def _band(total: int) -> str:
    """Map numeric score to action band.

    Args:
        total: Summed conviction score.

    Returns:
        Action band string.
    """
    if total >= 3:
        return "ACCUMULATE"
    if total >= 1:
        return "HOLD"
    if total == 0:
        return "WATCH"
    if total >= -2:
        return "REDUCE"
    return "EXIT"


# ── Data loaders ───────────────────────────────────────────────────────────────

def _load_ta() -> tuple[dict[str, dict[str, Any]], int | None]:
    """Load TA sweep results keyed by ticker and compute staleness.

    Returns:
        Tuple of (ticker_map, staleness_days).
    """
    if not TA_SWEEP_PATH.exists():
        return {}, None
    with open(TA_SWEEP_PATH) as f:
        raw = json.load(f)
    results: list[dict[str, Any]] = raw.get("results", [])
    ts = raw.get("timestamp")
    stale: int | None = None
    if ts:
        scanned = datetime.fromisoformat(ts)
        stale = (datetime.now(timezone.utc) - scanned).days
    return {r["ticker"]: r for r in results}, stale


def _load_dcf(ticker: str) -> dict[str, Any]:
    """Load latest AI_AGENT DCF projection for ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Dict with action, fairValue, pctToFV keys (empty if missing).
    """
    path = PROJECTIONS_DIR / f"{ticker}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        raw = json.load(f)
    entries: list[dict[str, Any]] = raw if isinstance(raw, list) else [raw]
    ai = [e for e in entries if e.get("source") == "AI_AGENT"]
    entry = (ai[-1] if ai else entries[-1]) if entries else {}
    thesis = entry.get("aiThesis", {})
    snap = entry.get("snapshot", {})
    price = snap.get("price") or 0
    fv = thesis.get("fairValue")
    pct = round((fv - price) / price * 100, 1) if fv and price else None
    return {"action": thesis.get("action"), "fairValue": fv, "pctToFV": pct}


def _load_actual_weights() -> dict[str, float]:
    """Load actual portfolio weight per ticker from portfolio.json.

    Returns:
        Dict of ticker → weight percentage.
    """
    if not PORTFOLIO_PATH.exists():
        return {}
    with open(PORTFOLIO_PATH) as f:
        data = json.load(f)
    holdings = data.get("holdings", data) if isinstance(data, dict) else data
    # Support both currentValue and market_value field names
    def val(h: dict[str, Any]) -> float:
        return h.get("currentValue") or h.get("market_value") or 0.0
    total = sum(val(h) for h in holdings)
    if not total:
        return {}
    return {
        h["symbol"]: round(val(h) / total * 100, 2)
        for h in holdings
        if h.get("symbol")
    }


def _load_target_weights() -> dict[str, float]:
    """Load target weight per ticker from target-portfolio.json.

    Returns:
        Dict of ticker → target weight percentage.
    """
    with open(TARGET_PATH) as f:
        data = json.load(f)
    return {h["ticker"]: h.get("targetWeight", 0)
            for h in data.get("holdings", [])}


# ── Main compute ───────────────────────────────────────────────────────────────

def compute_all() -> list[ConvictionScore]:
    """Compute conviction scores for all active portfolio holdings.

    Returns:
        List of ConvictionScore sorted by total score descending.
    """
    ta_map, stale_days = _load_ta()
    actual   = _load_actual_weights()
    targets  = _load_target_weights()

    all_tickers = (set(targets) | set(ta_map) | set(actual)) - SKIP_TICKERS

    scores: list[ConvictionScore] = []
    for ticker in sorted(all_tickers):
        ta     = ta_map.get(ticker, {})
        dcf    = _load_dcf(ticker)
        act_w  = actual.get(ticker)
        tgt_w  = targets.get(ticker)

        # Skip watchlist tickers with no actual position and no TA data
        if act_w is None and not ta and not dcf:
            continue

        gap = round(tgt_w - act_w, 2) if tgt_w is not None and act_w is not None else None
        flags      = ta.get("flags", [])

        # Prefer TA sweep's enriched DCF over raw projection file when available
        dcf_action = ta.get("dcf", {}).get("action") or dcf.get("action")
        pct_to_fv  = ta.get("dcf", {}).get("pctToFV") or dcf.get("pctToFV")
        rsi        = ta.get("rsi")
        adx        = ta.get("adx")
        vol_bias   = ta.get("volBias")

        dcf_pts  = _score_dcf(dcf_action)
        ta_pts   = _score_ta(rsi, vol_bias, flags)
        gap_pts  = _score_weight_gap(gap, dcf_action)
        mom_pts  = _score_momentum(adx, flags)
        total    = dcf_pts + ta_pts + gap_pts + mom_pts

        scores.append(ConvictionScore(
            ticker=ticker,
            total=total,
            band=_band(total),
            dcf_pts=dcf_pts,
            ta_pts=ta_pts,
            weight_gap_pts=gap_pts,
            momentum_pts=mom_pts,
            dcf_action=dcf_action,
            pct_to_fv=pct_to_fv,
            rsi=rsi,
            adx=adx,
            vol_bias=vol_bias,
            actual_weight=act_w,
            target_weight=tgt_w,
            weight_gap=gap,
            flags=flags,
            ta_staleness_days=stale_days,
        ))

    return sorted(scores, key=lambda s: s.total, reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute unified conviction scores")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    scores = compute_all()

    if args.json:
        print(json.dumps([asdict(s) for s in scores], indent=2))
        return

    print(f"\n{'TICKER':<8} {'SCORE':>5}  {'BAND':<12}  "
          f"{'DCF':>3} {'TA':>3} {'GAP':>3} {'MOM':>3}  "
          f"{'DCF_ACTION':<12}  {'RSI':>5}  {'ADX':>5}  {'WGT_GAP':>8}")
    print("─" * 88)
    band_icon = {"ACCUMULATE": "▲", "HOLD": "◆", "WATCH": "○", "REDUCE": "▼", "EXIT": "✗"}
    for s in scores:
        icon = band_icon.get(s.band, " ")
        print(
            f"{s.ticker:<8} {s.total:>+5d}  {icon}{s.band:<11}  "
            f"{s.dcf_pts:>+3d} {s.ta_pts:>+3d} {s.weight_gap_pts:>+3d} {s.momentum_pts:>+3d}  "
            f"{(s.dcf_action or 'n/a'):<12}  "
            f"{s.rsi or 0:>5.1f}  {s.adx or 0:>5.1f}  "
            f"{s.weight_gap or 0:>+7.1f}%"
        )


if __name__ == "__main__":
    main()
