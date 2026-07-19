#!/usr/bin/env python3
"""
compute_conviction_scores.py - Python utility script.

Purpose:
    Unified conviction scorer for portfolio holdings.

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

Key Input Dependencies:
    - investment_screener/backend/data/theses/target-portfolio.json (Reads targets)

Layer:
    Backend / Python Services

Usage Examples:
    python3 compute_conviction_scores.py
    python3 compute_conviction_scores.py --json

Key Functions (Index):
    - ConvictionScore()
    - _score_dcf()
    - _score_ta()
    - _score_weight_gap()
    - _score_momentum()
    - _resolve_pct_to_fv()
    - _band()
    - _load_ta()
    - _load_dcf()
    - _load_actual_weights()
    - val()
    - _load_target_weights()
    - compute_all()
    - main()

Key Input Dependencies:
    None

Key Output Dependencies:
    None
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

def _score_momentum(
    adx: float | None,
    flags: list[str],
    rsi: float | None = None,
) -> int:
    """Score trend quality via ADX, trend direction, and momentum flags.

    ADX measures trend STRENGTH only — it is identical for a strong rally and
    a free-fall. The +1 bonus therefore requires directional evidence that the
    trend is up (RSI > 55). A strong trend that is fading (RSI_COOLING) or
    pointing down (RSI < 45) reduces conviction to add. Ambiguous direction
    (RSI 45–55, or RSI missing) earns no bonus.

    Args:
        adx: Average Directional Index value.
        flags: TA flag list from sweep result.
        rsi: Current RSI — used as the trend-direction proxy.

    Returns:
        Score contribution in range −1 to +1.
    """
    if adx is None or adx < 30:
        return 0
    if "RSI_COOLING" in flags:
        return -1    # fading strong trend — often marks a top
    if rsi is None:
        return 0     # strong trend but direction unknowable — no bonus
    if rsi < 45:
        return -1    # strong DOWNTREND — never reward a falling knife
    if rsi > 55:
        return +1    # strong uptrend, momentum intact
    return 0         # direction ambiguous


# ── % to fair value resolution ─────────────────────────────────────────────────

def _resolve_pct_to_fv(
    ta: dict[str, Any],
    dcf: dict[str, Any],
) -> float | None:
    """Resolve % distance from current price to DCF fair value.

    Always recomputes from the sweep's live close and fair value when both are
    present — the enriched pctToFV stored in older sweep files was
    FV-denominated (wrong) and must not be trusted. Falls back to the
    projection-file value (price-denominated at save time) otherwise.

    Args:
        ta: Per-ticker TA sweep row (may contain close + dcf.fairValue).
        dcf: Projection-derived dict (may contain pctToFV).

    Returns:
        Percentage gap (positive = upside to fair value), or None.
    """
    close = ta.get("close")
    fv = ta.get("dcf", {}).get("fairValue")
    if close and fv:
        return round((fv - close) / close * 100, 1)
    pct = dcf.get("pctToFV")
    return pct if pct is not None else None


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

def _load_ta(
    db_path: str | None = None,
    ta_json_path: Path | None = None
) -> tuple[dict[str, dict[str, Any]], int | None]:
    """Load TA sweep results keyed by ticker and compute staleness from SQLite ledger,
    falling back to legacy flat-file JSON if the database is missing or empty.

    Returns:
        Tuple of (ticker_map, staleness_days).
    """
    import os
    import sqlite3

    resolved_db_path = db_path or str(REPO_ROOT / "investment_screener/backend/data/intelligence.sqlite")
    resolved_json_path = ta_json_path or TA_SWEEP_PATH

    # Try database first
    if os.path.exists(resolved_db_path):
        try:
            conn = sqlite3.connect(resolved_db_path)
            # Fetch latest sweep per ticker using window partition
            cursor = conn.execute("""
                SELECT ticker, payload_json, effective_at, ingested_at FROM (
                    SELECT i.ticker, ie.payload_json, ie.effective_at, ie.ingested_at,
                           ROW_NUMBER() OVER (PARTITION BY i.ticker ORDER BY ie.effective_at DESC, ie.ingested_at DESC) as rn
                    FROM intelligence_event ie
                    JOIN instrument i ON i.instrument_id = ie.instrument_id
                    WHERE ie.event_type = 'TECHNICAL_SWEEP' AND ie.status = 'ACTIVE'
                ) WHERE rn = 1;
            """)
            rows = cursor.fetchall()
            conn.close()

            if rows:
                ticker_map = {}
                latest_ts = None
                for ticker, payload_json, effective_at, ingested_at in rows:
                    if payload_json:
                        ticker_map[ticker] = json.loads(payload_json)
                    # Track latest ingested_at to calculate staleness
                    ts = ingested_at or effective_at
                    if ts:
                        if latest_ts is None or ts > latest_ts:
                            latest_ts = ts

                stale: int | None = None
                if latest_ts:
                    ts_str = latest_ts.replace("Z", "+00:00")
                    if len(ts_str) == 10:  # YYYY-MM-DD
                        ts_str += "T00:00:00+00:00"
                    try:
                        scanned = datetime.fromisoformat(ts_str)
                        stale = (datetime.now(timezone.utc) - scanned).days
                    except ValueError:
                        pass
                return ticker_map, stale
        except Exception:
            pass

    # Fall back to legacy flat-file JSON
    if not resolved_json_path.exists():
        return {}, None
    with open(resolved_json_path) as f:
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

def compute_all(
    db_path: str | None = None,
    ta_json_path: Path | None = None
) -> list[ConvictionScore]:
    """Compute conviction scores for all active portfolio holdings.

    Returns:
        List of ConvictionScore sorted by total score descending.
    """
    ta_map, stale_days = _load_ta(db_path=db_path, ta_json_path=ta_json_path)
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
        pct_to_fv  = _resolve_pct_to_fv(ta, dcf)
        rsi        = ta.get("rsi")
        adx        = ta.get("adx")
        vol_bias   = ta.get("volBias")

        dcf_pts  = _score_dcf(dcf_action)
        ta_pts   = _score_ta(rsi, vol_bias, flags)
        gap_pts  = _score_weight_gap(gap, dcf_action)
        mom_pts  = _score_momentum(adx, flags, rsi)
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
