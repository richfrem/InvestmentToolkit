# E2 — Rebalancer v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formalize `/rebalance`'s informal drift/capital/account logic into a real engine:
`py_services/rebalancer.py`, producing `data/rebalance_plan.json`. Per-holding drift bands
replace point targets, a risk-budget check cross-references E1's `risk_snapshot.json`
(variance, not weight), B5's `thesis_breaker_state.json` flags (never suppresses) proposed
buys, Canada-aware account/tax placement becomes data + code, and the `rebalance-portfolio`
skill shrinks to: run engine → present plan → HITL per order.

**Architecture:** One new file, `investment_screener/backend/py_services/rebalancer.py`, built
bottom-up as pure, independently-testable functions (bands → candidate orders → account
routing → capital gains → risk-budget warnings → breaker warnings → orchestrator), same shape
as `risk_engine.py`/`market_regime.py`/`thesis_breakers.py`. A small one-off migration script
retires two globalSettings fields that turn out to be a TypeScript-only concern. TypeScript
changes unify the dashboard's health-check band formula with the new engine's. The skill
becomes a thin wrapper.

**Tech Stack:** Python 3, pytest, argparse. No new dependencies. TypeScript changes in the
existing Express backend (Zod, no new deps). Reuses `portfolio_io.py` (weights/totals),
`ticker_aliases.py` (`normalize_ticker`), `update_thesis.py` (`load_thesis`/`save_thesis`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-09-rebalancer-v2-design.md` — read it once before
  starting; every task below implements a piece of it.
- Ticker field is always `ticker`, never `symbol` (CLAUDE.md rule 10).
- `rebalancer.py` never mutates any input file (`target-portfolio.json`, `portfolio.json`,
  `risk_snapshot.json`, `thesis_breaker_state.json`, `account_policy.json`). It owns
  `data/rebalance_plan.json` exclusively.
- Risk-budget and thesis-breaker checks are **warnings only** — nothing in this plan excludes
  an order for breaching a cap or hitting a TRIGGERED breaker. Only three things exclude an
  order entirely: `EXIT`/`SELL`-rated valuation action on a buy, price above
  `targetEntryPrice`, and a conflicting `standingDecision` (spec §4.2).
- `EXIT`/`SELL`-gating reads the ticker's latest AI projection `aiThesis.action` from
  `data/projections/{TICKER}.json` — **not** `derive_action()`'s portfolio-weight ratio label,
  which answers a different question and stays untouched (spec §2).
- All new/changed Python files: file header + Google-style docstrings on every non-trivial
  function, full type hints, snake_case, refactor at 50+ lines or 3+ nesting levels
  (`.agent/rules/coding-conventions.md`).
- TDD: every function gets its failing test written first. No live network calls, no
  wall-clock coupling in tests — inject "now"/"today" as parameters where needed.
- Commit after every task.
- Per `.agent/rules/worktree-subagent-isolation.md`: run `git status --short` in the **main
  checkout** (not the worktree) after every task.

---

## Task 1: `account_policy.json` + `compute_bands()`

**Files:**
- Create: `investment_screener/backend/data/account_policy.json`
- Create: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Produces: `DEFAULT_BAND_CONFIG: dict[str, float]`,
  `compute_bands(current_weights: dict[str, float], target_weights: dict[str, float], band_config: dict[str, float] = DEFAULT_BAND_CONFIG) -> dict[str, dict[str, Any]]`

- [ ] **Step 1: Create `account_policy.json`**

```json
{
  "accountPreferenceRules": [
    { "match": "usDividendPayer", "prefer": "RRSP", "reason": "treaty withholding exemption" },
    { "match": "highGrowthEquity", "prefer": "TFSA", "reason": "tax-free compounding" },
    { "match": "default", "prefer": "TFSA" }
  ],
  "psuFundingRule": {
    "ticker": "PSU-U.TO",
    "sameAccountOnly": true,
    "sharesFormula": "ceil(N * price / 100)"
  },
  "riskBudgetCaps": {
    "maxMarginalRiskContributionPct": 25,
    "maxClusterVarianceContributionPct": 60
  },
  "bandConfig": {
    "relativePct": 20,
    "absolutePct": 1.5,
    "criticalMultiplier": 2.0
  }
}
```

- [ ] **Step 2: Write the failing tests**

```python
"""Tests for rebalancer.py — E2 rebalancer v2 (Phase 3, sub-spec 4)."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from rebalancer import DEFAULT_BAND_CONFIG, compute_bands  # noqa: E402


def test_compute_bands_in_band_when_drift_within_band():
    # target 5.5%, band = max(5.5*0.20, 1.5) = 1.5pp; current 4.5% -> drift -1.0pp, in band
    bands = compute_bands({"NBIS": 4.5}, {"NBIS": 5.5}, DEFAULT_BAND_CONFIG)
    assert bands["NBIS"]["inBand"] is True
    assert bands["NBIS"]["bandPct"] == pytest.approx(1.5)
    assert bands["NBIS"]["driftPct"] == pytest.approx(-1.0)


def test_compute_bands_out_of_band_when_drift_exceeds_band():
    # target 5.5%, band 1.5pp; current 2.1% -> drift -3.4pp, out of band
    bands = compute_bands({"NBIS": 2.1}, {"NBIS": 5.5}, DEFAULT_BAND_CONFIG)
    assert bands["NBIS"]["inBand"] is False


def test_compute_bands_relative_band_dominates_for_large_targets():
    # target 20% -> relative band = 20*0.20 = 4.0pp > 1.5pp absolute floor
    bands = compute_bands({"BIG": 16.5}, {"BIG": 20.0}, DEFAULT_BAND_CONFIG)
    assert bands["BIG"]["bandPct"] == pytest.approx(4.0)
    assert bands["BIG"]["inBand"] is True  # drift -3.5pp within 4.0pp band


def test_compute_bands_boundary_drift_equal_to_band_is_in_band():
    bands = compute_bands({"X": 4.0}, {"X": 5.5}, DEFAULT_BAND_CONFIG)  # drift exactly -1.5pp
    assert bands["X"]["inBand"] is True


def test_compute_bands_ticker_missing_from_one_side_defaults_to_zero():
    bands = compute_bands({"ORPHAN": 2.0}, {}, DEFAULT_BAND_CONFIG)
    assert bands["ORPHAN"]["targetWeight"] == 0.0
    assert bands["ORPHAN"]["bandPct"] == pytest.approx(1.5)  # absolute floor, target*rel=0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rebalancer'`

- [ ] **Step 4: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
rebalancer.py (Python Service)
=====================================

Purpose:
    Formalizes /rebalance + portfolio_action.py's informal drift/capital/
    account logic into a real engine: per-holding drift bands (not point
    targets), a risk-budget check against E1's risk_snapshot.json,
    Canada-aware account/tax placement, and an ordered sells-before-buys
    order-plan output. Never mutates any input file — owns
    data/rebalance_plan.json exclusively. See docs/superpowers/specs/
    2026-07-09-rebalancer-v2-design.md.

Layer: Backend / Python Services / Rebalancer

Usage:
    python3 rebalancer.py --pretty
    python3 rebalancer.py --no-save --pretty
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portfolio_io import load_portfolio_state, compute_weights  # noqa: E402
from ticker_aliases import normalize_ticker  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"
PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
RISK_SNAPSHOT_PATH = DATA_DIR / "risk_snapshot.json"
THESIS_BREAKER_STATE_PATH = DATA_DIR / "thesis_breaker_state.json"
ACCOUNT_POLICY_PATH = DATA_DIR / "account_policy.json"
PROJECTIONS_DIR = DATA_DIR / "projections"
REBALANCE_PLAN_PATH = DATA_DIR / "rebalance_plan.json"

DEFAULT_BAND_CONFIG: dict[str, float] = {"relativePct": 20.0, "absolutePct": 1.5, "criticalMultiplier": 2.0}


def compute_bands(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    band_config: dict[str, float] = DEFAULT_BAND_CONFIG,
) -> dict[str, dict[str, Any]]:
    """Per-holding no-churn band: max(relative %, absolute pp) around targetWeight.

    A holding whose actual drift falls within its band gets no rebalance
    order generated this run — this is what kills churn/small-order noise
    vs. a flat point-target comparison.

    Args:
        current_weights: {ticker: weight_pct} (0-100 scale), actual broker weights.
        target_weights: {ticker: weight_pct} (0-100 scale), from target-portfolio.json.
        band_config: {"relativePct": float, "absolutePct": float} — band =
            max(targetWeight * relativePct/100, absolutePct).

    Returns:
        {ticker: {"currentWeight", "targetWeight", "bandPct", "driftPct", "inBand"}}
        for the union of tickers in either input (a ticker missing from one
        side is treated as 0.0 on that side).
    """
    tickers = set(current_weights) | set(target_weights)
    result: dict[str, dict[str, Any]] = {}
    for t in tickers:
        current = current_weights.get(t, 0.0)
        target = target_weights.get(t, 0.0)
        drift = current - target
        band_pct = max(target * band_config["relativePct"] / 100.0, band_config["absolutePct"])
        result[t] = {
            "currentWeight": round(current, 4),
            "targetWeight": round(target, 4),
            "bandPct": round(band_pct, 4),
            "driftPct": round(drift, 4),
            "inBand": abs(drift) <= band_pct,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebalance order plan")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"status": "scaffold — orchestrator added in Task 8"}, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/data/account_policy.json \
        investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add account_policy.json + rebalancer.py compute_bands() (E2 task 1)"
```

---

## Task 2: Valuation-action gate + `compute_candidate_orders()`

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Consumes: `compute_bands()` (Task 1).
- Produces: `get_latest_valuation_action(ticker: str, projections_dir: Path) -> str | None`,
  `compute_candidate_orders(bands: dict[str, dict[str, Any]], target_data: dict[str, Any], prices: dict[str, float], total_usd: float, projections_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]`
  — returns `(candidate_orders, skipped_restores)`. Each candidate order:
  `{"ticker", "action": "sell"|"buy", "shares", "currentWeight", "targetWeight"}`. Each
  skipped restore: `{"ticker", "reason"}`.

- [ ] **Step 1: Write the failing tests**

```python
from rebalancer import (  # noqa: E402
    get_latest_valuation_action,
    compute_candidate_orders,
)


def _write_projection(path: Path, ticker: str, action: str) -> None:
    (path / f"{ticker}.json").write_text(json.dumps([{
        "source": "AI_AGENT", "savedAt": "2026-07-01T00:00:00Z",
        "aiThesis": {"action": action},
    }]))


def test_get_latest_valuation_action_reads_latest_ai_agent_entry(tmp_path):
    _write_projection(tmp_path, "NBIS", "ACCUMULATE")
    assert get_latest_valuation_action("NBIS", tmp_path) == "ACCUMULATE"


def test_get_latest_valuation_action_missing_file_returns_none(tmp_path):
    assert get_latest_valuation_action("NOPE", tmp_path) is None


def test_candidate_orders_sell_when_overweight(tmp_path):
    bands = {"CRWD": {"currentWeight": 7.8, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": 3.8, "inBand": False}}
    target_data = {"holdings": [{"ticker": "CRWD", "targetWeight": 4.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"CRWD": 100.0}, 10000.0, tmp_path)
    assert skipped == []
    assert candidates[0]["ticker"] == "CRWD"
    assert candidates[0]["action"] == "sell"
    assert candidates[0]["shares"] == math.floor(0.038 * 10000.0 / 100.0)


def test_candidate_orders_buy_when_underweight_and_clean(tmp_path):
    _write_projection(tmp_path, "NBIS", "ACCUMULATE")
    bands = {"NBIS": {"currentWeight": 2.1, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.4, "inBand": False}}
    target_data = {"holdings": [{"ticker": "NBIS", "targetWeight": 5.5}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"NBIS": 20.0}, 10000.0, tmp_path)
    assert skipped == []
    assert candidates[0]["action"] == "buy"


def test_candidate_orders_skips_exit_rated_underweight(tmp_path):
    _write_projection(tmp_path, "INTC", "EXIT")
    bands = {"INTC": {"currentWeight": 1.0, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": -3.0, "inBand": False}}
    target_data = {"holdings": [{"ticker": "INTC", "targetWeight": 4.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"INTC": 30.0}, 10000.0, tmp_path)
    assert candidates == []
    assert skipped[0]["ticker"] == "INTC"
    assert "EXIT" in skipped[0]["reason"]


def test_candidate_orders_skips_above_target_entry_price(tmp_path):
    bands = {"SNDK": {"currentWeight": 4.2, "targetWeight": 6.0, "bandPct": 1.5, "driftPct": -1.8, "inBand": False}}
    target_data = {"holdings": [{"ticker": "SNDK", "targetWeight": 6.0, "targetEntryPrice": 1350.0}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"SNDK": 1741.0}, 10000.0, tmp_path)
    assert candidates == []
    assert "targetEntryPrice" in skipped[0]["reason"]


def test_candidate_orders_skips_when_standing_decision_conflicts(tmp_path):
    bands = {"VST": {"currentWeight": 1.0, "targetWeight": 2.27, "bandPct": 1.5, "driftPct": -1.27, "inBand": False}}
    target_data = {"holdings": [{
        "ticker": "VST", "targetWeight": 2.27,
        "standingDecision": {"type": "SA_LP_EXIT_OVERRIDE", "reason": "DO NOT ADD"},
    }]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"VST": 50.0}, 10000.0, tmp_path)
    assert candidates == []
    assert "Standing decision" in skipped[0]["reason"]


def test_candidate_orders_skips_zero_share_orders(tmp_path):
    # Tiny drift dollar amount rounds down to 0 shares — must not emit a phantom order.
    bands = {"TINY": {"currentWeight": 0.01, "targetWeight": 1.5, "bandPct": 1.5, "driftPct": -1.49, "inBand": False}}
    target_data = {"holdings": [{"ticker": "TINY", "targetWeight": 1.5}]}
    candidates, skipped = compute_candidate_orders(bands, target_data, {"TINY": 5000.0}, 100.0, tmp_path)
    assert candidates == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_latest_valuation_action'`

- [ ] **Step 3: Implement**

Add to `rebalancer.py` (after `compute_bands`):

```python
def get_latest_valuation_action(ticker: str, projections_dir: Path) -> str | None:
    """Latest AI projection's aiThesis.action for a ticker, or None if unavailable.

    Mirrors portfolio_action.py's _load_ai_upside() latest-AI_AGENT-projection
    selection, but returns the raw action string instead of computed upside —
    this is the actual "EXIT/SELL-gated" signal the rebalancer must never buy
    against (not derive_action()'s portfolio-weight ratio label).

    Args:
        ticker: Ticker to look up.
        projections_dir: Path to data/projections/.

    Returns:
        The latest AI_AGENT projection's aiThesis.action, or None if the
        projection file is missing, empty, or malformed.
    """
    path = projections_dir / f"{ticker}.json"
    if not path.exists():
        return None
    try:
        projs = json.loads(path.read_text())
        if isinstance(projs, list):
            if not projs:
                return None
            ai = [p for p in projs if p.get("source") == "AI_AGENT"]
            proj = max(ai, key=lambda x: x.get("savedAt", "")) if ai else projs[0]
        else:
            proj = projs
        return proj.get("aiThesis", {}).get("action")
    except Exception:
        return None


def compute_candidate_orders(
    bands: dict[str, dict[str, Any]],
    target_data: dict[str, Any],
    prices: dict[str, float],
    total_usd: float,
    projections_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Turn out-of-band holdings into raw candidate orders (pre-account-routing).

    Applies the hard-rule exclusions that remove an order entirely (never
    warnings): never buys an EXIT/SELL-rated holding, never buys above
    targetEntryPrice, and downgrades to a no-op when a standingDecision is
    present (same "signal stands but no trade proposed without your
    direction" framing brief_recommendations.py already uses for EXIT/REDUCE).
    Sells are never gated — an overweight EXIT-rated or standing-decision
    holding should still be trimmed toward target.

    Args:
        bands: Output of compute_bands().
        target_data: Parsed target-portfolio.json (targetEntryPrice,
            standingDecision per holding).
        prices: {ticker: current_price}.
        total_usd: Broker-authoritative portfolio total (never shares×price).
        projections_dir: Path to data/projections/.

    Returns:
        (candidate_orders, skipped_restores).
    """
    holdings_by_ticker = {h["ticker"]: h for h in target_data.get("holdings", [])}
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for ticker, band in bands.items():
        if band["inBand"]:
            continue
        price = prices.get(ticker)
        if not price or price <= 0:
            continue
        holding = holdings_by_ticker.get(ticker, {})
        drift_dollars = abs(band["driftPct"]) / 100.0 * total_usd
        shares = math.floor(drift_dollars / price)
        if shares <= 0:
            continue

        if band["driftPct"] > 0:
            candidates.append({
                "ticker": ticker, "action": "sell", "shares": shares,
                "currentWeight": band["currentWeight"], "targetWeight": band["targetWeight"],
            })
            continue

        valuation_action = get_latest_valuation_action(ticker, projections_dir)
        if valuation_action in ("EXIT", "SELL"):
            skipped.append({"ticker": ticker, "reason": f"{valuation_action}-rated — not restoring"})
            continue

        entry_cap = holding.get("targetEntryPrice")
        if entry_cap is not None and price > entry_cap:
            skipped.append({
                "ticker": ticker,
                "reason": f"Price ${price:.2f} above targetEntryPrice ${entry_cap:.2f}",
            })
            continue

        standing = holding.get("standingDecision")
        if standing:
            skipped.append({
                "ticker": ticker,
                "reason": f"Standing decision ({standing.get('type', 'USER')}): "
                          f"{standing.get('reason', '')} Signal stands but no trade "
                          f"proposed without your direction.",
            })
            continue

        candidates.append({
            "ticker": ticker, "action": "buy", "shares": shares,
            "currentWeight": band["currentWeight"], "targetWeight": band["targetWeight"],
        })

    return candidates, skipped
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (13 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add valuation-action gate + compute_candidate_orders() (E2 task 2)"
```

---

## Task 3: `load_account_positions()`

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Produces: `load_account_positions(portfolio_path: Path) -> tuple[dict[str, dict[str, dict[str, float | None]]], dict[str, float], dict[str, str]]`
  — returns `(account_positions, account_cash_usd, account_source)`.
  `account_positions[account][ticker] = {"shares": float, "costBasis": float | None}`.
  `account_cash_usd[account]` is the account's USD cash balance (a separate top-level
  dict, not a reserved key inside `account_positions` — keeping cash out of the
  per-ticker dict avoids a type-hint mismatch: a `dict[str, dict[str, float]]` cannot
  also correctly hold a bare `float` under a magic key). `account_source[account]`
  is `"tvSnapshot"` or `"heuristic_1_3_mirror"`.

- [ ] **Step 1: Write the failing tests**

```python
from rebalancer import load_account_positions  # noqa: E402


def _write_portfolio_with_tvsnapshot(path: Path, accounts: list[dict]) -> None:
    path.write_text(json.dumps({
        "holdings": [], "totals": {"totalUSD": 1000.0},
        "tvSnapshot": {"snapshots": accounts},
    }))


def test_load_account_positions_reads_tvsnapshot_per_account(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    _write_portfolio_with_tvsnapshot(portfolio_path, [
        {
            "accountType": "TFSA",
            "positions": [{"symbol": "NBIS", "quantity": 10, "avgFillPrice": 20.0}],
            "balances": {"cashUSDCombined": 500.0},
        },
        {
            "accountType": "RRSP",
            "positions": [{"symbol": "NBIS", "quantity": 3, "avgFillPrice": 22.0}],
            "balances": {"cashUSDCombined": 100.0},
        },
    ])
    positions, cash, source = load_account_positions(portfolio_path)
    assert positions["TFSA"]["NBIS"] == {"shares": 10.0, "costBasis": 20.0}
    assert positions["RRSP"]["NBIS"] == {"shares": 3.0, "costBasis": 22.0}
    assert cash["TFSA"] == 500.0
    assert cash["RRSP"] == 100.0
    assert source == {"TFSA": "tvSnapshot", "RRSP": "tvSnapshot"}


def test_load_account_positions_falls_back_to_heuristic_when_rrsp_missing(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    _write_portfolio_with_tvsnapshot(portfolio_path, [
        {
            "accountType": "TFSA",
            "positions": [{"symbol": "NBIS", "quantity": 9, "avgFillPrice": 20.0}],
            "balances": {"cashUSDCombined": 500.0},
        },
    ])
    positions, cash, source = load_account_positions(portfolio_path)
    assert positions["RRSP"]["NBIS"]["shares"] == 3.0  # floor(9/3)
    assert cash["RRSP"] == 0.0
    assert source["RRSP"] == "heuristic_1_3_mirror"


def test_load_account_positions_no_tvsnapshot_returns_empty(tmp_path):
    portfolio_path = tmp_path / "portfolio.json"
    portfolio_path.write_text(json.dumps({"holdings": [], "totals": {"totalUSD": 1000.0}}))
    positions, cash, source = load_account_positions(portfolio_path)
    assert positions == {}
    assert cash == {}
    assert source == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL — `ImportError: cannot import name 'load_account_positions'`

- [ ] **Step 3: Implement**

Add to `rebalancer.py`:

```python
def load_account_positions(
    portfolio_path: Path = PORTFOLIO_PATH,
) -> tuple[dict[str, dict[str, dict[str, float | None]]], dict[str, float], dict[str, str]]:
    """Per-account share/cost-basis positions, preferring real tvSnapshot data.

    Reads portfolio.json's tvSnapshot.snapshots[].positions for real
    per-account splits (with avgFillPrice as cost basis) when present. Falls
    back to mirroring TFSA at ~1/3 share count for RRSP (this repo's
    documented account structure) for any account tvSnapshot doesn't cover.

    Args:
        portfolio_path: Path to portfolio.json.

    Returns:
        (account_positions, account_cash_usd, account_source) —
        account_positions[account][ticker] = {"shares", "costBasis"};
        account_cash_usd[account] is that account's USD cash balance (a
        separate dict, not folded into account_positions — see this
        function's Interfaces note on why); account_source[account] is
        "tvSnapshot" or "heuristic_1_3_mirror".
    """
    raw = json.loads(Path(portfolio_path).read_text())
    snapshots = (raw.get("tvSnapshot") or {}).get("snapshots", [])

    positions: dict[str, dict[str, dict[str, float | None]]] = {}
    cash_usd: dict[str, float] = {}
    source: dict[str, str] = {}
    synced_accounts: set[str] = set()

    for snap in snapshots:
        acct = snap.get("accountType")
        if not acct:
            continue
        synced_accounts.add(acct)
        acct_positions: dict[str, dict[str, float | None]] = {}
        for p in snap.get("positions", []):
            sym = normalize_ticker(p.get("symbol", ""))
            if not sym:
                continue
            acct_positions[sym] = {
                "shares": float(p.get("quantity") or 0),
                "costBasis": float(p["avgFillPrice"]) if p.get("avgFillPrice") else None,
            }
        balances = snap.get("balances", {})
        cash_usd[acct] = float(balances.get("cashUSDCombined") or balances.get("cashUSD") or 0)
        positions[acct] = acct_positions
        source[acct] = "tvSnapshot"

    if synced_accounts and "RRSP" not in synced_accounts and "TFSA" in positions:
        rrsp_positions: dict[str, dict[str, float | None]] = {}
        for sym, pos in positions["TFSA"].items():
            mirrored = math.floor(pos["shares"] / 3)
            if mirrored > 0:
                rrsp_positions[sym] = {"shares": float(mirrored), "costBasis": pos["costBasis"]}
        positions["RRSP"] = rrsp_positions
        cash_usd["RRSP"] = 0.0
        source["RRSP"] = "heuristic_1_3_mirror"

    return positions, cash_usd, source
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (16 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add load_account_positions() with tvSnapshot + heuristic fallback (E2 task 3)"
```

---

## Task 4: `compute_account_routing()`

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Consumes: `compute_candidate_orders()` (Task 2), `load_account_positions()` (Task 3) —
  note Task 3's corrected 3-tuple return: `(account_positions, account_cash_usd, account_source)`.
- Produces: `compute_account_routing(candidate_orders: list[dict[str, Any]], account_positions: dict[str, dict[str, dict[str, float | None]]], account_cash_usd: dict[str, float], account_policy: dict[str, Any], target_data: dict[str, Any], prices: dict[str, float]) -> list[dict[str, Any]]`
  — each returned order gains `"account"`; buys needing extra cash get a
  same-account synthetic PSU-U.TO sell order inserted before them.

- [ ] **Step 1: Write the failing tests**

```python
from rebalancer import compute_account_routing  # noqa: E402


def test_routing_sells_go_to_the_account_that_holds_shares():
    candidates = [{"ticker": "CRWD", "action": "sell", "shares": 10, "currentWeight": 7.0, "targetWeight": 4.0}]
    positions = {"TFSA": {"CRWD": {"shares": 15.0, "costBasis": 100.0}}}
    cash = {"TFSA": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"CRWD": 100.0})
    assert routed[0]["account"] == "TFSA"
    assert routed[0]["shares"] == 10


def test_routing_splits_sell_proportionally_across_two_accounts():
    candidates = [{"ticker": "CRWD", "action": "sell", "shares": 12, "currentWeight": 7.0, "targetWeight": 4.0}]
    positions = {
        "TFSA": {"CRWD": {"shares": 9.0, "costBasis": 100.0}},
        "RRSP": {"CRWD": {"shares": 3.0, "costBasis": 100.0}},
    }
    cash = {"TFSA": 0.0, "RRSP": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"CRWD": 100.0})
    tfsa_order = next(o for o in routed if o["account"] == "TFSA")
    rrsp_order = next(o for o in routed if o["account"] == "RRSP")
    assert tfsa_order["shares"] + rrsp_order["shares"] == 12
    assert tfsa_order["shares"] > rrsp_order["shares"]  # TFSA held more


def test_routing_buy_uses_preferred_account_from_policy():
    candidates = [{"ticker": "NBIS", "action": "buy", "shares": 5, "currentWeight": 2.1, "targetWeight": 5.5}]
    positions = {"TFSA": {}}
    cash = {"TFSA": 5000.0}
    policy = {
        "accountPreferenceRules": [{"match": "highGrowthEquity", "prefer": "TFSA"}, {"match": "default", "prefer": "TFSA"}],
        "psuFundingRule": {"ticker": "PSU-U.TO"},
    }
    target_data = {"holdings": [{"ticker": "NBIS", "role": "highGrowthEquity"}]}
    routed = compute_account_routing(candidates, positions, cash, policy, target_data, {"NBIS": 20.0})
    assert routed[-1]["account"] == "TFSA"


def test_routing_psu_funding_rule_triggers_when_cash_insufficient():
    candidates = [{"ticker": "NBIS", "action": "buy", "shares": 100, "currentWeight": 2.1, "targetWeight": 5.5}]
    positions = {"TFSA": {"PSU-U.TO": {"shares": 50.0, "costBasis": 100.0}}}
    cash = {"TFSA": 100.0}
    policy = {
        "accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}],
        "psuFundingRule": {"ticker": "PSU-U.TO", "sameAccountOnly": True, "sharesFormula": "ceil(N * price / 100)"},
    }
    target_data = {"holdings": [{"ticker": "NBIS"}]}
    prices = {"NBIS": 20.0, "PSU-U.TO": 100.0}  # buy costs $2000, only $100 cash -> needs PSU trim
    routed = compute_account_routing(candidates, positions, cash, policy, target_data, prices)
    psu_sell = next(o for o in routed if o["ticker"] == "PSU-U.TO")
    nbis_buy = next(o for o in routed if o["ticker"] == "NBIS")
    assert psu_sell["action"] == "sell"
    assert psu_sell["account"] == "TFSA"  # same account as the buy it's funding
    assert nbis_buy["account"] == "TFSA"


def test_routing_no_shares_held_produces_no_sell_order():
    # Defensive: a candidate sell for a ticker not actually held in any account must not crash.
    candidates = [{"ticker": "GHOST", "action": "sell", "shares": 5, "currentWeight": 3.0, "targetWeight": 1.0}]
    positions = {"TFSA": {}}
    cash = {"TFSA": 0.0}
    policy = {"accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}], "psuFundingRule": {"ticker": "PSU-U.TO"}}
    routed = compute_account_routing(candidates, positions, cash, policy, {"holdings": []}, {"GHOST": 10.0})
    assert routed == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_account_routing'`

- [ ] **Step 3: Implement**

Add to `rebalancer.py`:

```python
def compute_account_routing(
    candidate_orders: list[dict[str, Any]],
    account_positions: dict[str, dict[str, dict[str, float | None]]],
    account_cash_usd: dict[str, float],
    account_policy: dict[str, Any],
    target_data: dict[str, Any],
    prices: dict[str, float],
) -> list[dict[str, Any]]:
    """Assign each candidate order to an account, sequenced sells-before-buys.

    Sells route to whichever account(s) actually hold shares, split
    proportionally to shares held when more than one account holds the
    ticker. Buys route per accountPreferenceRules matched against the
    holding's role/pillarId tags, falling back to "default". A buy needing
    more cash than is available in its target account triggers a
    same-account PSU-U.TO trim sized via ceil(shortfall / psu_price)
    (never cross-account, per psuFundingRule).

    Args:
        candidate_orders: Output of compute_candidate_orders().
        account_positions: Output of load_account_positions() (the positions
            dict — first element of its 3-tuple return).
        account_cash_usd: Output of load_account_positions() (the cash dict —
            second element of its 3-tuple return).
        account_policy: Parsed account_policy.json.
        target_data: Parsed target-portfolio.json (role/pillarId per holding).
        prices: {ticker: current_price}.

    Returns:
        Ordered list of per-account orders — sells first (by ticker), then
        buys (by ticker); each order has an "account" key, and PSU-funded
        buys get a preceding synthetic PSU-U.TO sell order in the same
        account.
    """
    holdings_by_ticker = {h["ticker"]: h for h in target_data.get("holdings", [])}
    rules = account_policy.get("accountPreferenceRules", [])
    psu_rule = account_policy.get("psuFundingRule", {})
    psu_ticker = psu_rule.get("ticker", "PSU-U.TO")

    def preferred_account(ticker: str) -> str:
        holding = holdings_by_ticker.get(ticker, {})
        tags = {holding.get("role"), holding.get("pillarId")}
        for rule in rules:
            if rule.get("match") in tags:
                return rule["prefer"]
        return next((r["prefer"] for r in rules if r.get("match") == "default"), "TFSA")

    sells = [o for o in candidate_orders if o["action"] == "sell"]
    buys = [o for o in candidate_orders if o["action"] == "buy"]
    routed: list[dict[str, Any]] = []

    for order in sorted(sells, key=lambda o: o["ticker"]):
        ticker = order["ticker"]
        held = {
            acct: pos[ticker]["shares"]
            for acct, pos in account_positions.items()
            if ticker in pos and pos[ticker]["shares"] > 0
        }
        if not held:
            continue
        total_held = sum(held.values())
        remaining = order["shares"]
        allocated: list[dict[str, Any]] = []
        for acct, held_shares in sorted(held.items(), key=lambda kv: -kv[1]):
            acct_shares = min(remaining, math.floor(order["shares"] * held_shares / total_held))
            if acct_shares > 0:
                allocated.append({**order, "account": acct, "shares": acct_shares})
                remaining -= acct_shares
        if remaining > 0 and allocated:
            allocated[0]["shares"] += remaining  # rounding remainder to the largest holder
        routed.extend(allocated)

    available_cash: dict[str, float] = dict(account_cash_usd)
    for order in routed:
        price = prices.get(order["ticker"], 0.0)
        available_cash[order["account"]] = available_cash.get(order["account"], 0.0) + order["shares"] * price

    for order in sorted(buys, key=lambda o: o["ticker"]):
        ticker = order["ticker"]
        acct = preferred_account(ticker)
        price = prices.get(ticker, 0.0)
        cost = order["shares"] * price
        cash_here = available_cash.get(acct, 0.0)
        if cost > cash_here and ticker != psu_ticker:
            shortfall = cost - cash_here
            psu_price = prices.get(psu_ticker, 100.0)
            psu_held = account_positions.get(acct, {}).get(psu_ticker, {}).get("shares", 0.0)
            psu_shares = math.ceil(shortfall / psu_price)
            if psu_held >= psu_shares:
                routed.append({
                    "ticker": psu_ticker, "action": "sell", "account": acct,
                    "shares": psu_shares,
                    "rationale": f"Same-account funding for {ticker} buy",
                })
                available_cash[acct] = cash_here + psu_shares * psu_price
        routed.append({**order, "account": acct})
        available_cash[acct] = available_cash.get(acct, 0.0) - cost

    return routed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (21 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add compute_account_routing() with PSU funding rule (E2 task 4)"
```

---

## Task 5: `compute_capital_gains_estimate()`

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Produces: `compute_capital_gains_estimate(ticker: str, account: str, shares_sold: float, sale_price: float, account_positions: dict[str, dict[str, dict[str, float | None]]]) -> float | None`

- [ ] **Step 1: Write the failing tests**

```python
from rebalancer import compute_capital_gains_estimate  # noqa: E402


def test_capital_gains_computed_for_cash_account_with_cost_basis():
    positions = {"Cash": {"AAPL": {"shares": 50.0, "costBasis": 100.0}}}
    gain = compute_capital_gains_estimate("AAPL", "Cash", 10.0, 150.0, positions)
    assert gain == pytest.approx(500.0)  # (150-100)*10


def test_capital_gains_none_for_tfsa_or_rrsp():
    positions = {"TFSA": {"AAPL": {"shares": 50.0, "costBasis": 100.0}}}
    assert compute_capital_gains_estimate("AAPL", "TFSA", 10.0, 150.0, positions) is None


def test_capital_gains_none_when_cost_basis_unavailable():
    positions = {"Cash": {"AAPL": {"shares": 50.0, "costBasis": None}}}
    assert compute_capital_gains_estimate("AAPL", "Cash", 10.0, 150.0, positions) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_capital_gains_estimate'`

- [ ] **Step 3: Implement**

Add to `rebalancer.py`:

```python
def compute_capital_gains_estimate(
    ticker: str,
    account: str,
    shares_sold: float,
    sale_price: float,
    account_positions: dict[str, dict[str, dict[str, float | None]]],
) -> float | None:
    """Estimate capital gains/loss for a Cash-account sell.

    TFSA/RRSP gains are never taxed, so this returns None for any account
    other than "Cash" without even attempting a cost-basis lookup. Forward-
    looking: the user's current accounts are TFSA/RRSP only, so this path is
    fixture-tested but not yet exercised against real data (spec §8).

    Args:
        ticker: Ticker being sold.
        account: Account name the sell is routed to.
        shares_sold: Shares in this sell order.
        sale_price: Current price used for the sell.
        account_positions: Output of load_account_positions() (positions
            only) — used for cost basis in the same account.

    Returns:
        (sale_price - cost_basis) * shares_sold, or None if the account
        isn't "Cash" or cost basis is unavailable.
    """
    if account != "Cash":
        return None
    cost_basis = account_positions.get(account, {}).get(ticker, {}).get("costBasis")
    if not cost_basis:
        return None
    return round((sale_price - cost_basis) * shares_sold, 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (24 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add compute_capital_gains_estimate() for Cash-account sells (E2 task 5)"
```

---

## Task 6: `compute_risk_budget_check()`

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Consumes: `bands` (Task 1's `compute_bands()` output), routed orders (Task 4's
  `compute_account_routing()` output), `risk_snapshot.json`'s shape
  (`marginalRiskContribution: dict[str, float]`, `clusterExposure: list[dict]`).
- Produces: `compute_risk_budget_check(routed_orders: list[dict[str, Any]], bands: dict[str, dict[str, Any]], risk_snapshot: dict[str, Any] | None, account_policy: dict[str, Any], target_data: dict[str, Any]) -> dict[str, list[str]]`

- [ ] **Step 1: Write the failing tests**

```python
from rebalancer import compute_risk_budget_check  # noqa: E402


def test_risk_budget_warns_when_projected_mrc_exceeds_cap():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 50}]
    bands = {"NBIS": {"currentWeight": 2.0, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.5, "inBand": False}}
    risk_snapshot = {"marginalRiskContribution": {"NBIS": 0.10}, "clusterExposure": []}  # 10% MRC today
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NBIS", "pillarId": "ai_infra"}]}
    warnings = compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data)
    # projected = 10% * (5.5/2.0) = 27.5% > 25% cap
    assert "NBIS" in warnings
    assert any("MRC" in w for w in warnings["NBIS"])


def test_risk_budget_no_warning_when_under_cap():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 10}]
    bands = {"NBIS": {"currentWeight": 4.0, "targetWeight": 4.5, "bandPct": 1.5, "driftPct": -0.5, "inBand": False}}
    risk_snapshot = {"marginalRiskContribution": {"NBIS": 0.10}, "clusterExposure": []}
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NBIS", "pillarId": "ai_infra"}]}
    assert compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data) == {}


def test_risk_budget_warns_on_cluster_cap_breach():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 1}]
    bands = {"NBIS": {"currentWeight": 4.0, "targetWeight": 4.1, "bandPct": 1.5, "driftPct": -0.1, "inBand": False}}
    risk_snapshot = {
        "marginalRiskContribution": {"NBIS": 0.05},
        "clusterExposure": [{"pillarId": "ai_infra", "weight": 0.6, "varianceContributionPct": 72.0}],
    }
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60}}
    target_data = {"holdings": [{"ticker": "NBIS", "pillarId": "ai_infra"}]}
    warnings = compute_risk_budget_check(routed, bands, risk_snapshot, policy, target_data)
    assert any("cluster" in w.lower() for w in warnings["NBIS"])


def test_risk_budget_degrades_gracefully_when_snapshot_missing():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 10}]
    bands = {"NBIS": {"currentWeight": 2.0, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.5, "inBand": False}}
    assert compute_risk_budget_check(routed, bands, None, {}, {"holdings": []}) == {}


def test_risk_budget_ignores_sell_orders():
    routed = [{"ticker": "CRWD", "action": "sell", "account": "TFSA", "shares": 10}]
    bands = {"CRWD": {"currentWeight": 7.8, "targetWeight": 4.0, "bandPct": 1.5, "driftPct": 3.8, "inBand": False}}
    risk_snapshot = {"marginalRiskContribution": {"CRWD": 0.99}, "clusterExposure": []}
    policy = {"riskBudgetCaps": {"maxMarginalRiskContributionPct": 1, "maxClusterVarianceContributionPct": 1}}
    assert compute_risk_budget_check(routed, bands, risk_snapshot, policy, {"holdings": []}) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_risk_budget_check'`

- [ ] **Step 3: Implement**

Add to `rebalancer.py`:

```python
def compute_risk_budget_check(
    routed_orders: list[dict[str, Any]],
    bands: dict[str, dict[str, Any]],
    risk_snapshot: dict[str, Any] | None,
    account_policy: dict[str, Any],
    target_data: dict[str, Any],
) -> dict[str, list[str]]:
    """Warn (never exclude) when a proposed buy would push MRC/cluster over cap.

    First-order estimate only: scales the ticker's existing
    marginalRiskContribution by its proposed weight ratio (target/current)
    rather than re-running risk_engine.py against hypothetical post-trade
    weights (out of scope — spec §6.1). Labeled as an estimate in the
    warning text. Degrades to {} when risk_snapshot is None.

    Args:
        routed_orders: Output of compute_account_routing() (only buys matter).
        bands: Output of compute_bands() (for currentWeight/targetWeight).
        risk_snapshot: Parsed risk_snapshot.json, or None if unavailable.
        account_policy: Parsed account_policy.json (riskBudgetCaps).
        target_data: Parsed target-portfolio.json (pillarId per holding).

    Returns:
        {ticker: [warning strings]} — only tickers with at least one warning.
    """
    if not risk_snapshot:
        return {}
    mrc = risk_snapshot.get("marginalRiskContribution", {})
    cluster = {c["pillarId"]: c for c in risk_snapshot.get("clusterExposure", [])}
    caps = account_policy.get("riskBudgetCaps", {})
    mrc_cap = caps.get("maxMarginalRiskContributionPct", 25)
    cluster_cap = caps.get("maxClusterVarianceContributionPct", 60)
    pillar_map = {h["ticker"]: h.get("pillarId", "unassigned") for h in target_data.get("holdings", [])}

    warnings: dict[str, list[str]] = {}
    for order in routed_orders:
        if order["action"] != "buy":
            continue
        ticker = order["ticker"]
        band = bands.get(ticker, {})
        current_w, target_w = band.get("currentWeight", 0.0), band.get("targetWeight", 0.0)
        old_mrc = mrc.get(ticker)
        if old_mrc and current_w > 0:
            projected_mrc_pct = old_mrc * 100 * (target_w / current_w)
            if projected_mrc_pct > mrc_cap:
                warnings.setdefault(ticker, []).append(
                    f"Estimated MRC would reach {projected_mrc_pct:.1f}% (estimate) > {mrc_cap}% cap"
                )
        pillar = pillar_map.get(ticker, "unassigned")
        cluster_entry = cluster.get(pillar)
        if cluster_entry and cluster_entry.get("varianceContributionPct", 0) > cluster_cap:
            warnings.setdefault(ticker, []).append(
                f"Pillar '{pillar}' cluster variance already "
                f"{cluster_entry['varianceContributionPct']:.1f}% > {cluster_cap}% cap"
            )
    return warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (29 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add compute_risk_budget_check() — warn-only MRC/cluster caps (E2 task 6)"
```

---

## Task 7: `compute_breaker_warnings()`

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Produces: `compute_breaker_warnings(routed_orders: list[dict[str, Any]], thesis_breaker_state: dict[str, Any] | None) -> dict[str, list[str]]`

- [ ] **Step 1: Write the failing tests**

```python
from rebalancer import compute_breaker_warnings  # noqa: E402


def test_breaker_warnings_flags_triggered_breaker_on_buy():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 6}]
    state = {"holdings": {"NBIS": {"nbis-rsi-breaker": {
        "status": "TRIGGERED", "currentValue": 78, "currentStreak": 3,
    }}}}
    warnings = compute_breaker_warnings(routed, state)
    assert "NBIS" in warnings
    assert "TRIGGERED" in warnings["NBIS"][0]


def test_breaker_warnings_ignores_ok_and_watching_status():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 6}]
    state = {"holdings": {"NBIS": {"nbis-rsi-breaker": {"status": "WATCHING", "currentStreak": 2}}}}
    assert compute_breaker_warnings(routed, state) == {}


def test_breaker_warnings_ignores_sell_orders():
    routed = [{"ticker": "CRWD", "action": "sell", "account": "TFSA", "shares": 10}]
    state = {"holdings": {"CRWD": {"some-breaker": {"status": "TRIGGERED", "currentStreak": 5}}}}
    assert compute_breaker_warnings(routed, state) == {}


def test_breaker_warnings_degrades_gracefully_when_state_missing():
    routed = [{"ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 6}]
    assert compute_breaker_warnings(routed, None) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_breaker_warnings'`

- [ ] **Step 3: Implement**

Add to `rebalancer.py`:

```python
def compute_breaker_warnings(
    routed_orders: list[dict[str, Any]],
    thesis_breaker_state: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Flag (never suppress) a proposed buy on a ticker with a TRIGGERED breaker.

    Visibility escalation only, matching B5's own posture — this never
    removes a buy order from the plan, only attaches a warning string.

    Args:
        routed_orders: Output of compute_account_routing().
        thesis_breaker_state: Parsed thesis_breaker_state.json, or None.

    Returns:
        {ticker: [warning strings]} for buy orders on tickers with at least
        one TRIGGERED breaker. Degrades to {} if state is missing.
    """
    if not thesis_breaker_state:
        return {}
    holdings_state = thesis_breaker_state.get("holdings", {})
    warnings: dict[str, list[str]] = {}
    for order in routed_orders:
        if order["action"] != "buy":
            continue
        ticker = order["ticker"]
        for breaker_id, entry in holdings_state.get(ticker, {}).items():
            if entry.get("status") == "TRIGGERED":
                warnings.setdefault(ticker, []).append(
                    f"TRIGGERED breaker '{breaker_id}': current value "
                    f"{entry.get('currentValue')!r}, streak {entry.get('currentStreak')}"
                )
    return warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (33 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add compute_breaker_warnings() — B5 flag-only integration (E2 task 7)"
```

---

## Task 8: `compute_rebalance_plan()` orchestrator + CLI

**Files:**
- Modify: `investment_screener/backend/py_services/rebalancer.py`
- Test: `investment_screener/backend/tests/py_services/test_rebalancer.py`

**Interfaces:**
- Consumes: every function from Tasks 1–7.
- Produces: `_check_no_trade_conditions(target_data: dict[str, Any], portfolio_path: Path, projections_dir: Path) -> str | None`,
  `_now_iso() -> str`,
  `compute_rebalance_plan(target_portfolio_path: Path = TARGET_PATH, portfolio_path: Path = PORTFOLIO_PATH, risk_snapshot_path: Path = RISK_SNAPSHOT_PATH, thesis_breaker_state_path: Path = THESIS_BREAKER_STATE_PATH, account_policy_path: Path = ACCOUNT_POLICY_PATH, projections_dir: Path = PROJECTIONS_DIR) -> dict[str, Any]`
  — see spec §3.3 for the full output shape.

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import patch

from rebalancer import compute_rebalance_plan  # noqa: E402


def _write_full_fixture(tmp_path):
    target_path = tmp_path / "target-portfolio.json"
    portfolio_path = tmp_path / "portfolio.json"
    risk_path = tmp_path / "risk_snapshot.json"
    breaker_path = tmp_path / "thesis_breaker_state.json"
    policy_path = tmp_path / "account_policy.json"
    proj_dir = tmp_path / "projections"
    proj_dir.mkdir()

    target_path.write_text(json.dumps({
        "holdings": [
            {"ticker": "CRWD", "targetWeight": 4.0, "pillarId": "cyber"},
            {"ticker": "NBIS", "targetWeight": 5.5, "pillarId": "ai_infra"},
            {"ticker": "PSU-U.TO", "targetWeight": 90.5, "pillarId": "cash"},
        ],
    }))
    portfolio_path.write_text(json.dumps({
        "holdings": [
            {"ticker": "CRWD", "shares": 15.0, "price": 100.0},
            {"ticker": "NBIS", "shares": 1.0, "price": 20.0},
            {"ticker": "PSU-U.TO", "shares": 90.0, "price": 100.0},
        ],
        "totals": {"totalUSD": 10500.0, "timestamp": "2026-07-09T13:00:00Z"},
        "tvSnapshot": {"snapshots": [{
            "accountType": "TFSA",
            "positions": [
                {"symbol": "CRWD", "quantity": 15.0, "avgFillPrice": 90.0},
                {"symbol": "NBIS", "quantity": 1.0, "avgFillPrice": 18.0},
                {"symbol": "PSU-U.TO", "quantity": 90.0, "avgFillPrice": 100.0},
            ],
            "balances": {"cashUSDCombined": 500.0},
        }]},
    }))
    risk_path.write_text(json.dumps({"marginalRiskContribution": {}, "clusterExposure": []}))
    breaker_path.write_text(json.dumps({"holdings": {}}))
    policy_path.write_text(json.dumps({
        "accountPreferenceRules": [{"match": "default", "prefer": "TFSA"}],
        "psuFundingRule": {"ticker": "PSU-U.TO", "sameAccountOnly": True, "sharesFormula": "ceil(N * price / 100)"},
        "riskBudgetCaps": {"maxMarginalRiskContributionPct": 25, "maxClusterVarianceContributionPct": 60},
        "bandConfig": {"relativePct": 20.0, "absolutePct": 1.5, "criticalMultiplier": 2.0},
    }))
    (proj_dir / "NBIS.json").write_text(json.dumps([{
        "source": "AI_AGENT", "savedAt": "2026-07-01T00:00:00Z", "aiThesis": {"action": "ACCUMULATE"},
    }]))
    return target_path, portfolio_path, risk_path, breaker_path, policy_path, proj_dir


def test_compute_rebalance_plan_full_shape(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, proj_dir = _write_full_fixture(tmp_path)
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, projections_dir=proj_dir,
    )
    expected_keys = {"generatedAt", "blockedReason", "bands", "orders", "skippedRestores", "accountDataSource", "warnings"}
    assert expected_keys <= set(plan.keys())
    assert plan["blockedReason"] is None
    tickers_in_orders = {o["ticker"] for o in plan["orders"]}
    assert "CRWD" in tickers_in_orders  # overweight (7.8% actual vs 4.0% target) -> sell
    assert "NBIS" in tickers_in_orders  # underweight (1.9% actual vs 5.5% target) -> buy
    assert plan["accountDataSource"] == {"TFSA": "tvSnapshot", "RRSP": "heuristic_1_3_mirror"}


def test_compute_rebalance_plan_blocked_when_targets_dont_sum_to_100(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, proj_dir = _write_full_fixture(tmp_path)
    target_path.write_text(json.dumps({"holdings": [{"ticker": "CRWD", "targetWeight": 4.0, "pillarId": "cyber"}]}))
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, projections_dir=proj_dir,
    )
    assert plan["blockedReason"] is not None
    assert "TARGETS_INVALID" in plan["blockedReason"]
    assert plan["orders"] == []


def test_compute_rebalance_plan_blocked_when_portfolio_stale(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, proj_dir = _write_full_fixture(tmp_path)
    stale = json.loads(portfolio_path.read_text())
    stale["totals"]["timestamp"] = "2020-01-01T00:00:00Z"
    portfolio_path.write_text(json.dumps(stale))
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, projections_dir=proj_dir,
    )
    assert "DATA_STALE" in plan["blockedReason"]


def test_compute_rebalance_plan_degrades_when_risk_snapshot_missing(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, proj_dir = _write_full_fixture(tmp_path)
    risk_path.unlink()
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, projections_dir=proj_dir,
    )
    assert plan["blockedReason"] is None
    assert any("risk_snapshot" in w for w in plan["warnings"])


def test_compute_rebalance_plan_order_carries_risk_and_breaker_warnings(tmp_path):
    target_path, portfolio_path, risk_path, breaker_path, policy_path, proj_dir = _write_full_fixture(tmp_path)
    risk_path.write_text(json.dumps({
        "marginalRiskContribution": {"NBIS": 0.20},
        "clusterExposure": [{"pillarId": "ai_infra", "weight": 0.3, "varianceContributionPct": 30.0}],
    }))
    breaker_path.write_text(json.dumps({"holdings": {"NBIS": {"b1": {"status": "TRIGGERED", "currentValue": 80, "currentStreak": 4}}}}))
    plan = compute_rebalance_plan(
        target_portfolio_path=target_path, portfolio_path=portfolio_path,
        risk_snapshot_path=risk_path, thesis_breaker_state_path=breaker_path,
        account_policy_path=policy_path, projections_dir=proj_dir,
    )
    nbis_order = next(o for o in plan["orders"] if o["ticker"] == "NBIS")
    assert len(nbis_order["riskGateWarnings"]) >= 1  # cap-breaching, deliberately not vetoed
    assert len(nbis_order["breakerWarnings"]) >= 1
    assert nbis_order in plan["orders"]  # still present, not excluded
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_rebalance_plan'`

- [ ] **Step 3: Implement**

Add to `rebalancer.py`, replacing the scaffold `main()` from Task 1:

```python
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _check_no_trade_conditions(
    target_data: dict[str, Any], portfolio_path: Path, projections_dir: Path,
) -> str | None:
    """Returns a blockedReason string, or None if clear to trade.

    Checks (in order): portfolio.json staleness (>60min), target weights not
    summing to 100%±0.5%, >30% of thesis holdings missing a DCF projection.

    Args:
        target_data: Parsed target-portfolio.json.
        portfolio_path: Path to portfolio.json.
        projections_dir: Path to data/projections/.

    Returns:
        A human-readable blockedReason, or None.
    """
    raw = json.loads(Path(portfolio_path).read_text())
    ts = raw.get("totals", {}).get("timestamp")
    if ts:
        age_minutes = (
            datetime.now(timezone.utc) - datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ).total_seconds() / 60
        if age_minutes > 60:
            return f"DATA_STALE — portfolio.json is {age_minutes:.0f} min old (run /tv-portfolio-sync first)"

    holdings = target_data.get("holdings", [])
    weight_sum = sum(h.get("targetWeight", 0.0) for h in holdings)
    if abs(weight_sum - 100) > 0.5:
        return f"TARGETS_INVALID — target weights sum to {weight_sum:.1f}% (must be 100%)"

    thesis_tickers = [h for h in holdings if h.get("targetWeight", 0) > 0]
    if thesis_tickers:
        missing = sum(1 for h in thesis_tickers if not (projections_dir / f"{h['ticker']}.json").exists())
        if missing / len(thesis_tickers) > 0.3:
            return f"MISSING_VALUATIONS — {missing}/{len(thesis_tickers)} thesis holdings have no DCF projection"

    return None


def compute_rebalance_plan(
    target_portfolio_path: Path = TARGET_PATH,
    portfolio_path: Path = PORTFOLIO_PATH,
    risk_snapshot_path: Path = RISK_SNAPSHOT_PATH,
    thesis_breaker_state_path: Path = THESIS_BREAKER_STATE_PATH,
    account_policy_path: Path = ACCOUNT_POLICY_PATH,
    projections_dir: Path = PROJECTIONS_DIR,
) -> dict[str, Any]:
    """Primary orchestrator — builds the full rebalance order plan.

    Never mutates any input file — owns data/rebalance_plan.json exclusively
    (main()'s --no-save-gated write). Checks no-trade conditions first; if
    any fire, returns early with blockedReason set and orders: [].

    Args:
        target_portfolio_path: Path to target-portfolio.json.
        portfolio_path: Path to portfolio.json.
        risk_snapshot_path: Path to risk_snapshot.json (E1 output).
        thesis_breaker_state_path: Path to thesis_breaker_state.json (B5 output).
        account_policy_path: Path to account_policy.json.
        projections_dir: Path to data/projections/.

    Returns:
        The full rebalance plan dict — see docs/superpowers/specs/
        2026-07-09-rebalancer-v2-design.md §3.3 for the field-by-field shape.
    """
    target_data = json.loads(Path(target_portfolio_path).read_text())
    account_policy = json.loads(Path(account_policy_path).read_text())
    warnings: list[str] = []

    blocked = _check_no_trade_conditions(target_data, Path(portfolio_path), Path(projections_dir))
    if blocked:
        return {
            "generatedAt": _now_iso(), "blockedReason": blocked, "bands": {},
            "orders": [], "skippedRestores": [], "accountDataSource": {}, "warnings": [],
        }

    state = load_portfolio_state(Path(portfolio_path))
    current_weights = compute_weights(state["shares"], state["prices"], state["total_usd"])
    target_weights = {h["ticker"]: h.get("targetWeight", 0.0) for h in target_data.get("holdings", [])}
    band_config = account_policy.get("bandConfig", DEFAULT_BAND_CONFIG)

    bands = compute_bands(current_weights, target_weights, band_config)
    candidates, skipped = compute_candidate_orders(
        bands, target_data, state["prices"], state["total_usd"], Path(projections_dir)
    )

    account_positions, account_cash_usd, account_source = load_account_positions(Path(portfolio_path))
    routed = compute_account_routing(
        candidates, account_positions, account_cash_usd, account_policy, target_data, state["prices"]
    )

    risk_snapshot = None
    if Path(risk_snapshot_path).exists():
        risk_snapshot = json.loads(Path(risk_snapshot_path).read_text())
    else:
        warnings.append("risk_snapshot.json not found — risk-budget check skipped")
    risk_warnings = compute_risk_budget_check(routed, bands, risk_snapshot, account_policy, target_data)

    breaker_state = None
    if Path(thesis_breaker_state_path).exists():
        breaker_state = json.loads(Path(thesis_breaker_state_path).read_text())
    else:
        warnings.append("thesis_breaker_state.json not found — breaker check skipped")
    breaker_warnings = compute_breaker_warnings(routed, breaker_state)

    orders: list[dict[str, Any]] = []
    for order in routed:
        ticker = order["ticker"]
        band = bands.get(ticker, {})
        price = state["prices"].get(ticker, 0.0)
        capital_gains = None
        if order["action"] == "sell":
            capital_gains = compute_capital_gains_estimate(
                ticker, order["account"], order["shares"], price, account_positions
            )
        # Only compute_account_routing's synthetic PSU-funding sell pre-sets
        # "rationale" — every normal candidate-derived order does not, so this
        # (not "driftPct" in band, which PSU-U.TO's own real band entry would
        # also satisfy) is the correct way to tell them apart.
        is_psu_funding_order = "rationale" in order
        gates = ["psu_funding_rule"] if is_psu_funding_order else ["band_check"]
        if order["action"] == "buy":
            gates += ["not_exit_or_sell_rated", "below_target_entry_price"]
        orders.append({
            "ticker": ticker,
            "action": order["action"],
            "account": order["account"],
            "shares": order["shares"],
            "rationale": order.get("rationale") or (
                f"Out of band: {band.get('driftPct', 0):+.1f}pp vs {band.get('bandPct', 0):.1f}pp band"
            ),
            "gatesPassed": gates,
            "riskGateWarnings": risk_warnings.get(ticker, []),
            "breakerWarnings": breaker_warnings.get(ticker, []),
            "capitalGainsEstimate": capital_gains,
        })

    return {
        "generatedAt": _now_iso(),
        "blockedReason": None,
        "bands": bands,
        "orders": orders,
        "skippedRestores": skipped,
        "accountDataSource": account_source,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebalance order plan")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing rebalance_plan.json")
    args = parser.parse_args()

    plan = compute_rebalance_plan()
    if not args.no_save:
        REBALANCE_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REBALANCE_PLAN_PATH, "w") as f:
            json.dump(plan, f, indent=2)

    print(json.dumps(plan, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py -v`
Expected: PASS (38 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/rebalancer.py \
        investment_screener/backend/tests/py_services/test_rebalancer.py
git commit -m "feat: add compute_rebalance_plan() orchestrator + CLI (E2 task 8)"
```

---

## Task 9: Migration — retire `globalSettings.driftThresholdPct`/`criticalDriftPct`

**Files:**
- Create: `investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py`
- Test: `investment_screener/backend/tests/py_services/test_remove_drift_threshold_fields.py`
- Modify (via running the script): `investment_screener/backend/data/theses/target-portfolio.json`

**Interfaces:**
- Consumes: `update_thesis.py`'s `load_thesis()`/`save_thesis()` (already exist, no changes).
- Produces: `strip_drift_threshold_fields(data: dict[str, Any]) -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
"""Test for the E2 globalSettings migration (task 9)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATIONS_DIR = REPO_ROOT / "investment_screener/backend/py_services/migrations"
sys.path.insert(0, str(MIGRATIONS_DIR))

from remove_drift_threshold_fields import strip_drift_threshold_fields  # noqa: E402


def test_strip_removes_both_fields():
    data = {"globalSettings": {"driftThresholdPct": 3.0, "criticalDriftPct": 5.0, "rebalanceFrequency": "quarterly"}}
    removed = strip_drift_threshold_fields(data)
    assert set(removed) == {"driftThresholdPct", "criticalDriftPct"}
    assert "driftThresholdPct" not in data["globalSettings"]
    assert "criticalDriftPct" not in data["globalSettings"]
    assert data["globalSettings"]["rebalanceFrequency"] == "quarterly"  # untouched


def test_strip_is_idempotent():
    data = {"globalSettings": {"rebalanceFrequency": "quarterly"}}
    assert strip_drift_threshold_fields(data) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_remove_drift_threshold_fields.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'remove_drift_threshold_fields'`

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python3
"""
migrations/remove_drift_threshold_fields.py
=====================================

Purpose:
    One-time migration: removes globalSettings.driftThresholdPct and
    globalSettings.criticalDriftPct from target-portfolio.json now that
    account_policy.json's bandConfig is the single source of truth for
    drift-band thresholds, read by both rebalancer.py and ThesisService.ts
    (E2 spec §3.2, §5). Idempotent — safe to run more than once.

Layer: Backend / Python Services / Migrations

Usage:
    python3 investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py
"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from update_thesis import load_thesis, save_thesis  # noqa: E402

RETIRED_FIELDS = ("driftThresholdPct", "criticalDriftPct")


def strip_drift_threshold_fields(data: dict[str, Any]) -> list[str]:
    """Removes the two retired fields from globalSettings, in place.

    Args:
        data: Parsed target-portfolio.json.

    Returns:
        List of field names actually removed (empty if already absent —
        callers use this to skip the save_thesis() call/version bump when
        there's nothing to do).
    """
    settings = data.get("globalSettings", {})
    removed = [k for k in RETIRED_FIELDS if k in settings]
    for key in removed:
        del settings[key]
    return removed


def main() -> None:
    data = load_thesis()
    removed = strip_drift_threshold_fields(data)
    if not removed:
        print("Nothing to migrate — fields already absent.")
        return
    save_thesis(
        data, dry_run=False,
        note=f"E2 migration: removed globalSettings.{', '.join(removed)} — "
             f"drift-band config now lives in account_policy.json's bandConfig.",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest investment_screener/backend/tests/py_services/test_remove_drift_threshold_fields.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the migration against the real data file**

Run: `python3 investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py`
Expected output: `✅  Saved thesis.json  (version {N})`. This bumps `version` (currently the
JSON number `9.8`), not `schemaVersion` (stays `"1.0"`, unaffected). Note:
`save_thesis()`'s bump logic only does the decimal `+0.1` string-parsing path when
`version` is a JSON **string** — since the file currently stores it as a bare
**number** (`9.8`, not `"9.8"`), `isinstance(version, str)` is `False` and the actual
result will be `version + 1` = `10.8`, not `9.9`. This is a pre-existing quirk in
`update_thesis.py`'s versioning logic, not something introduced by this migration —
don't "fix" the jump by hand-editing the output; just confirm the printed version
matches whatever `target-portfolio.json`'s `version` field was immediately before this
step, plus 1.

Verify: `grep -c "driftThresholdPct\|criticalDriftPct" investment_screener/backend/data/theses/target-portfolio.json`
Expected: `0`

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/migrations/remove_drift_threshold_fields.py \
        investment_screener/backend/tests/py_services/test_remove_drift_threshold_fields.py \
        investment_screener/backend/data/theses/target-portfolio.json
git commit -m "chore: migrate globalSettings off driftThresholdPct/criticalDriftPct (E2 task 9)"
```

---

## Task 10: TypeScript — unify `ThesisService.ts`'s band formula with `account_policy.json`

**Files:**
- Modify: `investment_screener/backend/src/utils/zod-schemas.ts:192-197`
- Modify: `investment_screener/backend/src/services/ThesisService.ts:30-56,94,141-144,176-177,202-205`

**Interfaces:**
- Produces (zod-schemas.ts): `AccountPolicySchema`, `type AccountPolicy`.
- Consumes (ThesisService.ts): `AccountPolicySchema`/`AccountPolicy` from `zod-schemas.ts`.

- [ ] **Step 1: Update `zod-schemas.ts`**

Replace (lines 192-197):
```typescript
    globalSettings: z.object({
        driftThresholdPct: z.number().min(0.5).max(20).default(3.0),
        criticalDriftPct: z.number().min(1).max(30).default(5.0),
        rebalanceFrequency: z.enum(['weekly', 'monthly', 'quarterly']).default('quarterly'),
        portfolioValueUSD: z.number().nonnegative().optional(),
    }),
});
```

With:
```typescript
    globalSettings: z.object({
        rebalanceFrequency: z.enum(['weekly', 'monthly', 'quarterly']).default('quarterly'),
        portfolioValueUSD: z.number().nonnegative().optional(),
    }),
});

// === ACCOUNT POLICY SCHEMA (E2 — Rebalancer v2) ===
// account_policy.json — drift-band config, risk-budget caps, account/tax
// placement rules. Read by both rebalancer.py (Python) and this service
// (TypeScript, independently re-implemented, not shelled out to Python).

export const AccountPolicySchema = z.object({
    accountPreferenceRules: z.array(z.object({
        match: z.string(),
        prefer: z.enum(['TFSA', 'RRSP', 'Cash']),
        reason: z.string().optional(),
    })),
    psuFundingRule: z.object({
        ticker: z.string(),
        sameAccountOnly: z.boolean(),
        sharesFormula: z.string(),
    }),
    riskBudgetCaps: z.object({
        maxMarginalRiskContributionPct: z.number().positive(),
        maxClusterVarianceContributionPct: z.number().positive(),
    }),
    bandConfig: z.object({
        relativePct: z.number().positive(),
        absolutePct: z.number().positive(),
        criticalMultiplier: z.number().positive().default(2.0),
    }),
});

export type AccountPolicy = z.infer<typeof AccountPolicySchema>;
```

- [ ] **Step 2: Add `account_policy.json` reading + band-formula helpers to `ThesisService.ts`**

Add import (line 27, extend the existing import block):
```typescript
import {
    Thesis, ThesisSchema,
    HealthCheck, HealthCheckSchema,
    DriftEntry, HoldingHealth, Projection,
    AccountPolicy, AccountPolicySchema
} from '../utils/zod-schemas';
```

Add constant (after line 32, alongside `PORTFOLIO_FILE`):
```typescript
const ACCOUNT_POLICY_FILE = path.resolve(__dirname, '../../data/account_policy.json');
```

Add methods (inside the `ThesisService` class, alongside `getPortfolioItems`):
```typescript
    private getAccountPolicy(): AccountPolicy | null {
        if (!fs.existsSync(ACCOUNT_POLICY_FILE)) return null;
        try {
            const data = JSON.parse(fs.readFileSync(ACCOUNT_POLICY_FILE, 'utf-8'));
            return AccountPolicySchema.parse(data);
        } catch (e) {
            console.error('[ThesisService] Error reading account_policy.json:', e);
            return null;
        }
    }

    private computeBandPct(targetPct: number, bandConfig: AccountPolicy['bandConfig']): number {
        return Math.max(targetPct * bandConfig.relativePct / 100, bandConfig.absolutePct);
    }
```

- [ ] **Step 3: Replace the drift-threshold reads in `computeHealthCheck()`**

Add (right after `const portfolioItems = await this.getPortfolioItems();` at line 98):
```typescript
        const accountPolicy = this.getAccountPolicy();
        const bandConfig = accountPolicy?.bandConfig ?? { relativePct: 20, absolutePct: 1.5, criticalMultiplier: 2.0 };
```

Replace (holding-level block, lines 141-144):
```typescript
            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= thesis.globalSettings.criticalDriftPct) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= thesis.globalSettings.driftThresholdPct) status = 'DRIFT';
```

With:
```typescript
            const bandPct = this.computeBandPct(holding.targetWeight, bandConfig);
            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= bandPct * bandConfig.criticalMultiplier) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= bandPct) status = 'DRIFT';
```

Replace (alert message, line 177):
```typescript
                    message: `${holding.ticker} is drifting ${driftPct.toFixed(1)}% (Threshold: ${thesis.globalSettings.driftThresholdPct}%)`,
```

With:
```typescript
                    message: `${holding.ticker} is drifting ${driftPct.toFixed(1)}% (Band: ${bandPct.toFixed(1)}pp)`,
```

Replace (pillar-level block, lines 202-205):
```typescript
            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= thesis.globalSettings.criticalDriftPct) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= thesis.globalSettings.driftThresholdPct) status = 'DRIFT';
```

With:
```typescript
            const pillarBandPct = this.computeBandPct(pillar.targetWeight, bandConfig);
            let status: 'ON_TARGET' | 'DRIFT' | 'CRITICAL' = 'ON_TARGET';
            if (Math.abs(driftPct) >= pillarBandPct * bandConfig.criticalMultiplier) status = 'CRITICAL';
            else if (Math.abs(driftPct) >= pillarBandPct) status = 'DRIFT';
```

- [ ] **Step 4: Build and verify no type errors**

Run: `npm run build -w backend`
Expected: Build succeeds with no TypeScript errors (no remaining references to
`driftThresholdPct`/`criticalDriftPct` anywhere in the backend).

Verify: `grep -rn "driftThresholdPct\|criticalDriftPct" investment_screener/backend/src/`
Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/src/utils/zod-schemas.ts \
        investment_screener/backend/src/services/ThesisService.ts
git commit -m "feat: unify ThesisService health-check band formula with account_policy.json (E2 task 10)"
```

**Note:** requires `npm run build -w backend` + a backend restart before the dashboard
reflects the new thresholds (pitfall #3) — flag this to the user in the final summary, don't
restart the running dev server yourself without asking.

---

## Task 11: Skill — `rebalance-portfolio` `SKILL.md` becomes a thin wrapper

**Files:**
- Modify: `plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md`

**Interfaces:**
- Consumes: `python3 investment_screener/backend/py_services/rebalancer.py --pretty` (Task 8),
  reading its `data/rebalance_plan.json` output.

- [ ] **Step 1: Replace the "No-Trade Conditions" section**

Replace the `## ⚠️ No-Trade Conditions` section (the block listing `DATA_STALE`,
`TARGETS_INVALID`, `MISSING_VALUATIONS`, `EARNINGS_SEASON`, `THESIS_OUT_OF_SYNC`) with:

```markdown
## ⚠️ No-Trade Conditions

`rebalancer.py`'s `blockedReason` field covers `DATA_STALE`, `TARGETS_INVALID`, and
`MISSING_VALUATIONS` computationally — if `data/rebalance_plan.json`'s `blockedReason` is
non-null, state it verbatim and stop; no orders were generated.

Two conditions stay your judgment call, not a hard block — check before presenting the plan:
- `EARNINGS_SEASON` — 3+ holdings have earnings within 7 days. Surface a list; let the user
  decide whether to proceed.
- `THESIS_OUT_OF_SYNC` — run `verify_thesis_sync.py`; if it fails, tell the user to fix sync
  before rebalancing.
```

- [ ] **Step 2: Replace Steps 1–4 with the engine call**

Replace everything from `## Step 1: Load Current State` through the end of
`## Step 4: Build Trade Payload` (the current in-context drift-classification, capital-
sequencing, and account-heuristic prose) with:

```markdown
## Step 1: Run the Rebalancer Engine

```bash
python3 investment_screener/backend/py_services/rebalancer.py --pretty
```

This computes drift bands, candidate orders (with the EXIT/SELL-rated, targetEntryPrice, and
standingDecision hard-rule exclusions already applied), account routing (real per-account
data when available, heuristic TFSA/RRSP mirror otherwise), capital-gains estimates for any
Cash-account sells, risk-budget warnings against `risk_snapshot.json`, and thesis-breaker
warnings against `thesis_breaker_state.json` — then writes `data/rebalance_plan.json`.

If `blockedReason` is non-null, state it verbatim and stop (see No-Trade Conditions above).

Read `data/rebalance_plan.json` for the rest of this skill's steps — its `orders[]` array is
already sequenced sells-before-buys, per-account.
```

- [ ] **Step 3: Update Step 5 to render warnings inline**

In the `## Step 5: Present Trade Recommendations` table, add a line under any order whose
`riskGateWarnings` or `breakerWarnings` arrays are non-empty:

```markdown
Under any order row with non-empty `riskGateWarnings` or `breakerWarnings`, render:
```
   ⚠️ {warning text}
```
one line per warning string, before moving to the next order row.
```

- [ ] **Step 4: Update Step 6's confirmation prompt to include warnings**

In `## Step 6: Confirm + Log Each Trade`, change the presentation line to:

```markdown
1. Present: *"Trade {N}: {ACTION} {shares} shares of {TICKER} at ~${price} — {rationale}.
   {warning lines, if any}. Confirm?"*
```

- [ ] **Step 5: Remove the now-redundant "Account Selection Heuristics" table**

Replace the `## 🇨🇦 Account Selection Heuristics (TFSA vs RRSP)` section's static markdown
table with a pointer:

```markdown
## 🇨🇦 Account Selection

Account routing (TFSA/RRSP/Cash preference rules, PSU-U.TO same-account funding rule) is now
computed by `rebalancer.py` from `investment_screener/backend/data/account_policy.json` — each
order in the plan already carries its `"account"` field. Edit `account_policy.json` directly
if the routing rules need to change; no skill-side heuristic table to keep in sync anymore.
```

- [ ] **Step 6: Manual verification**

Since this task edits prose, not code, verify the edits landed correctly:

```bash
grep -n "rebalancer.py --pretty" plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md
grep -n "account_policy.json" plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md
grep -c "Drifted DOWN.*SELL" plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md
```
Expected: first two greps find matches; the third finds `0` (the old inline drift-
classification table is gone).

- [ ] **Step 7: Commit**

```bash
git add plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md
git commit -m "docs: rewrite rebalance-portfolio skill as a thin wrapper around rebalancer.py (E2 task 11)"
```

---

## Final step: whole-branch review

After all 11 tasks are committed in the worktree, follow the same pattern as E1/C2/B5: request
a final whole-branch review (opus) before merging to local `main`. Specifically check:

- `rebalancer.py` never mutates `target-portfolio.json`, `portfolio.json`,
  `risk_snapshot.json`, `thesis_breaker_state.json`, or `account_policy.json` — only reads.
  It owns `data/rebalance_plan.json` exclusively.
- The three hard-rule exclusions (EXIT/SELL-rated buy, above `targetEntryPrice`, conflicting
  `standingDecision`) genuinely exclude the order — never appear in `orders[]`, only in
  `skippedRestores[]`. The two soft checks (risk-budget, thesis-breaker) genuinely never
  exclude — every cap-breaching or TRIGGERED-breaker order is still present in `orders[]`
  with its warning field populated. This is the literal Phase 3 acceptance criterion
  (reinterpreted per spec §6.3) — confirm
  `test_compute_rebalance_plan_order_carries_risk_and_breaker_warnings` passes and the order
  is asserted present, not absent.
- `driftThresholdPct`/`criticalDriftPct` are fully gone from
  `investment_screener/backend/data/theses/target-portfolio.json`,
  `investment_screener/backend/src/utils/zod-schemas.ts`, and
  `investment_screener/backend/src/services/ThesisService.ts` (grep all three).
- Run the full new test surface together:
  `python3 -m pytest investment_screener/backend/tests/py_services/test_rebalancer.py investment_screener/backend/tests/py_services/test_remove_drift_threshold_fields.py -v`
  — all green, and no regressions in `test_risk_engine.py`/`test_market_regime.py`/
  `test_thesis_breakers.py`/`test_update_price_levels.py` (run the full `py_services/` test
  directory once more before merge).
- `npm run build -w backend` succeeds cleanly.
- Per `.agent/rules/worktree-subagent-isolation.md`: run `git status --short` in the **main
  checkout** (not the worktree) after every task, confirming no stray writes leaked outside
  the worktree.

After a clean review: merge to local `main`, push `feature/fable5-phase3-e2-rebalancer-v2` to
`origin` as a backup/PR source — **do not merge or open a PR into `origin/main`**, same
standing git policy as every prior Fable5 phase. Report the branch is ready and stop there.
