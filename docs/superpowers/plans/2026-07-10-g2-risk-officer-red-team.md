# G2 — Risk Officer + Red Team + Data Quality Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close Phase 3's final gap — give E2's warn-only risk/breaker signals real veto
power, make the "Adversarial Objectivity Constraint" a reusable mandatory agent instead of
prose, and wire `market_data.py`'s currently-unreachable `dataQuality` signal into a real
degrade/halt decision.

**Architecture:** A new deterministic engine (`risk_officer.py`) mirrors E1/C2/B5/E2's
established split — pure, independently-testable classification functions, a thin CLI, an
append-only override ledger — wrapped by a thin LLM agent (`risk-officer-agent.md`) that both
`/rebalance` and `/daily` dispatch via the Agent tool. `red-team-agent.md` and
`data-quality-agent.md` are purely conversational (no new engine for red-team; a small
additive `dataQuality` passthrough wiring for data-quality). Three existing, already-shipped
SKILL.md files (`rebalance-portfolio`, `stock_valuation`) and one agent
(`daily-loop-agent.md`) gain new steps that dispatch these agents — no existing step is
removed or restructured.

**Tech Stack:** Python 3, pytest, argparse, `unittest.mock.patch`. No new dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-10-g2-risk-officer-red-team-design.md` — read it once
  before starting; every task below implements a piece of it.
- Ticker field is always `ticker`, never `symbol` (CLAUDE.md rule 10).
- `risk_officer.py` never mutates `rebalance_plan.json`, `risk_snapshot.json`, or
  `thesis_breaker_state.json` — read-only on all three. It owns
  `data/risk_officer_review.json` and `data/risk_officer_overrides.jsonl` exclusively.
- `risk_officer.py`'s veto rule reuses E2's existing thresholds exactly: an order is vetoed
  iff `riskGateWarnings` or `breakerWarnings` is non-empty. No new numeric caps, no new
  `account_policy.json` config surface.
- All new/changed Python files: file header + Google-style docstrings on every non-trivial
  function, full type hints, snake_case, refactor at 50+ lines or 3+ nesting levels
  (`.agent/rules/coding-conventions.md`).
- TDD: every function gets its failing test written first (repo's non-negotiable rule 1). No
  live network calls in tests — `get_fundamentals`/`get_prices`/`get_estimates` are always
  mocked via `unittest.mock.patch`, matching `test_wacc.py`'s existing pattern.
- CLI validation errors use `sys.exit(f"ERROR: ...")`, never a raw uncaught exception —
  matches `thesis_breakers.py`'s existing convention (repo-wide, not just that file).
- Commit after every task.

---

## Task 1: `risk_officer.py` — classification + review-artifact computation

**Files:**
- Create: `investment_screener/backend/py_services/risk_officer.py`
- Test: `investment_screener/backend/tests/py_services/test_risk_officer.py`

**Interfaces:**
- Produces: `classify_orders(orders: list[dict]) -> tuple[list[dict], list[dict]]`,
  `compute_risk_officer_review(rebalance_plan_path: Path = REBALANCE_PLAN_PATH, output_path: Path = REVIEW_PATH, save: bool = True) -> dict`,
  module constants `REPO_ROOT`, `DATA_DIR`, `REBALANCE_PLAN_PATH`, `REVIEW_PATH`,
  `OVERRIDES_PATH`, private `_now_iso() -> str`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for risk_officer.py — G2 risk-officer veto classification (Phase 3, sub-spec 5)."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from risk_officer import classify_orders, compute_risk_officer_review  # noqa: E402


def _order(ticker, risk_warnings=None, breaker_warnings=None, **extra):
    return {
        "ticker": ticker, "action": "buy", "account": "TFSA", "shares": 10,
        "rationale": "Out of band: -3.1pp vs 1.5pp band",
        "gatesPassed": ["band_check"],
        "riskGateWarnings": risk_warnings or [],
        "breakerWarnings": breaker_warnings or [],
        "capitalGainsEstimate": None,
        **extra,
    }


def test_classify_orders_vetoes_on_risk_gate_warning_only():
    orders = [_order("CORZ", risk_warnings=["Estimated MRC would reach 31.2% (estimate) > 25% cap"])]
    vetoed, approved = classify_orders(orders)
    assert len(vetoed) == 1
    assert approved == []
    assert vetoed[0]["vetoReasons"] == ["Estimated MRC would reach 31.2% (estimate) > 25% cap"]


def test_classify_orders_vetoes_on_breaker_warning_only():
    orders = [_order("NBIS", breaker_warnings=["TRIGGERED breaker 'nbis-trend': current value 'DOWNTREND', streak 5"])]
    vetoed, approved = classify_orders(orders)
    assert len(vetoed) == 1
    assert vetoed[0]["vetoReasons"] == ["TRIGGERED breaker 'nbis-trend': current value 'DOWNTREND', streak 5"]


def test_classify_orders_approves_when_both_empty():
    orders = [_order("MSFT")]
    vetoed, approved = classify_orders(orders)
    assert vetoed == []
    assert len(approved) == 1
    assert "vetoReasons" not in approved[0]


def test_classify_orders_concatenates_both_reason_lists_risk_first():
    orders = [_order(
        "CORZ",
        risk_warnings=["MRC breach"],
        breaker_warnings=["TRIGGERED breaker 'corz-margin'"],
    )]
    vetoed, _ = classify_orders(orders)
    assert vetoed[0]["vetoReasons"] == ["MRC breach", "TRIGGERED breaker 'corz-margin'"]


def test_classify_orders_preserves_order_and_handles_mixed_batch():
    orders = [_order("A"), _order("B", risk_warnings=["breach"]), _order("C")]
    vetoed, approved = classify_orders(orders)
    assert [o["ticker"] for o in vetoed] == ["B"]
    assert [o["ticker"] for o in approved] == ["A", "C"]


def test_compute_risk_officer_review_no_plan_file_returns_no_plan_status(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    output_path = tmp_path / "risk_officer_review.json"
    result = compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path)
    assert result["status"] == "no_plan"
    assert result["vetoedOrders"] == []
    assert result["approvedOrders"] == []
    assert not output_path.exists()


def test_compute_risk_officer_review_blocked_plan_returns_plan_blocked_status(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    plan_path.write_text(json.dumps({
        "generatedAt": "2026-07-10T13:00:00Z", "blockedReason": "DATA_STALE — ...",
        "orders": [], "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    }))
    output_path = tmp_path / "risk_officer_review.json"
    result = compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path)
    assert result["status"] == "plan_blocked"
    assert not output_path.exists()


def test_compute_risk_officer_review_writes_file_and_round_trips(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    plan_path.write_text(json.dumps({
        "generatedAt": "2026-07-10T13:58:00Z", "blockedReason": None,
        "orders": [
            _order("CORZ", risk_warnings=["MRC breach"]),
            _order("MSFT"),
        ],
        "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    }))
    output_path = tmp_path / "risk_officer_review.json"

    result = compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path)

    assert result["status"] == "ok"
    assert result["sourceRebalancePlanGeneratedAt"] == "2026-07-10T13:58:00Z"
    assert "generatedAt" in result
    assert [o["ticker"] for o in result["vetoedOrders"]] == ["CORZ"]
    assert [o["ticker"] for o in result["approvedOrders"]] == ["MSFT"]

    assert output_path.exists()
    on_disk = json.loads(output_path.read_text())
    assert on_disk == result


def test_compute_risk_officer_review_no_save_skips_write(tmp_path):
    plan_path = tmp_path / "rebalance_plan.json"
    plan_path.write_text(json.dumps({
        "generatedAt": "x", "blockedReason": None, "orders": [_order("MSFT")],
        "bands": {}, "skippedRestores": [], "accountDataSource": {}, "warnings": [],
    }))
    output_path = tmp_path / "risk_officer_review.json"
    compute_risk_officer_review(rebalance_plan_path=plan_path, output_path=output_path, save=False)
    assert not output_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_officer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'risk_officer'`

- [ ] **Step 3: Write the minimal implementation**

```python
#!/usr/bin/env python3
"""
risk_officer.py (Python Service)
=====================================

Purpose:
    Turns E2's warn-only riskGateWarnings/breakerWarnings (rebalance_plan.json)
    into real veto power. Reuses E2's exact thresholds — an order is vetoed
    iff either warning list is non-empty; no new numeric caps are introduced.
    Never mutates rebalance_plan.json, risk_snapshot.json, or
    thesis_breaker_state.json — read-only on all three. Owns
    data/risk_officer_review.json and data/risk_officer_overrides.jsonl
    exclusively. See docs/superpowers/specs/
    2026-07-10-g2-risk-officer-red-team-design.md.

Layer: Backend / Python Services / Risk

Usage:
    python3 risk_officer.py --pretty
    python3 risk_officer.py --log-override --ticker CORZ --action buy \
        --account TFSA --rationale "Conviction unchanged, MRC estimate is first-order only"

Key Functions:
    - classify_orders() - Splits rebalance_plan.json's orders into (vetoed, approved)
    - compute_risk_officer_review() - Primary orchestrator: plan -> risk_officer_review.json
    - log_risk_officer_override() - Appends one accountability-trail record for an override
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
REBALANCE_PLAN_PATH = DATA_DIR / "rebalance_plan.json"
REVIEW_PATH = DATA_DIR / "risk_officer_review.json"
OVERRIDES_PATH = DATA_DIR / "risk_officer_overrides.jsonl"


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a literal 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def classify_orders(orders: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split rebalance_plan.json's orders into (vetoed, approved).

    An order is vetoed iff its riskGateWarnings or breakerWarnings list is
    non-empty — E2's existing warn-only signals, now enforced rather than
    merely displayed. No new numeric thresholds are introduced here.

    Args:
        orders: The "orders" list from rebalance_plan.json.

    Returns:
        (vetoed, approved). Vetoed entries are the input order dict plus a
        "vetoReasons" key (riskGateWarnings entries first, then
        breakerWarnings entries). Approved entries are returned unchanged
        (no "vetoReasons" key added).
    """
    vetoed: list[dict[str, Any]] = []
    approved: list[dict[str, Any]] = []
    for order in orders:
        risk_warnings = order.get("riskGateWarnings", [])
        breaker_warnings = order.get("breakerWarnings", [])
        if risk_warnings or breaker_warnings:
            vetoed.append({**order, "vetoReasons": risk_warnings + breaker_warnings})
        else:
            approved.append(order)
    return vetoed, approved


def compute_risk_officer_review(
    rebalance_plan_path: Path = REBALANCE_PLAN_PATH,
    output_path: Path = REVIEW_PATH,
    save: bool = True,
) -> dict[str, Any]:
    """Load rebalance_plan.json, classify its orders, write risk_officer_review.json.

    Args:
        rebalance_plan_path: Path to rebalance_plan.json.
        output_path: Where to write risk_officer_review.json.
        save: If False, compute and return without writing the file (mirrors
            rebalancer.py's --no-save pattern).

    Returns:
        {"status": "ok"|"no_plan"|"plan_blocked", "generatedAt",
         "sourceRebalancePlanGeneratedAt", "vetoedOrders", "approvedOrders"}.
        "no_plan" (rebalance_plan_path doesn't exist) and "plan_blocked"
        (the plan's blockedReason is non-null) both return empty order
        lists and write no file — there is nothing to review yet.
    """
    if not Path(rebalance_plan_path).exists():
        return {"status": "no_plan", "vetoedOrders": [], "approvedOrders": []}

    plan = json.loads(Path(rebalance_plan_path).read_text())
    if plan.get("blockedReason"):
        return {"status": "plan_blocked", "vetoedOrders": [], "approvedOrders": []}

    vetoed, approved = classify_orders(plan.get("orders", []))
    result = {
        "status": "ok",
        "generatedAt": _now_iso(),
        "sourceRebalancePlanGeneratedAt": plan.get("generatedAt"),
        "vetoedOrders": vetoed,
        "approvedOrders": approved,
    }
    if save:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result, indent=2))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_officer.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/risk_officer.py investment_screener/backend/tests/py_services/test_risk_officer.py
git commit -m "feat(risk-officer): add order veto classification + review-artifact engine"
```

---

## Task 2: `risk_officer.py` — override logging + CLI

**Files:**
- Modify: `investment_screener/backend/py_services/risk_officer.py`
- Test: `investment_screener/backend/tests/py_services/test_risk_officer.py`

**Interfaces:**
- Consumes (from Task 1): `REVIEW_PATH`, `OVERRIDES_PATH`, `_now_iso()`.
- Produces: `log_risk_officer_override(ticker: str, action: str, account: str, shares: float | None, veto_reasons: list[str], rationale: str, overridden_by: str = "user", path: Path = OVERRIDES_PATH) -> None`,
  `_cli_log_override(ticker: str, action: str, account: str, rationale: str, overridden_by: str = "user", review_path: Path = REVIEW_PATH, overrides_path: Path = OVERRIDES_PATH) -> None`
  (raises `ValueError` if `review_path` is missing or no matching vetoed order is found),
  CLI flags `--pretty`, `--no-save`, `--log-override`, `--ticker`, `--action`, `--account`,
  `--rationale`, `--overridden-by`.

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_risk_officer.py`:

```python
import pytest

from risk_officer import log_risk_officer_override, _cli_log_override  # noqa: E402


class TestLogRiskOfficerOverride:
    def test_appends_one_jsonl_line(self, tmp_path):
        path = tmp_path / "risk_officer_overrides.jsonl"
        log_risk_officer_override(
            ticker="CORZ", action="buy", account="TFSA", shares=10.0,
            veto_reasons=["MRC breach"],
            rationale="Conviction unchanged, MRC estimate is first-order only",
            path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["ticker"] == "CORZ"
        assert entry["action"] == "buy"
        assert entry["account"] == "TFSA"
        assert entry["shares"] == 10.0
        assert entry["vetoReasons"] == ["MRC breach"]
        assert entry["overriddenBy"] == "user"
        assert "date" in entry

    def test_second_call_appends_not_overwrites(self, tmp_path):
        path = tmp_path / "risk_officer_overrides.jsonl"
        log_risk_officer_override(
            ticker="CORZ", action="buy", account="TFSA", shares=10.0,
            veto_reasons=["a"], rationale="first", path=path,
        )
        log_risk_officer_override(
            ticker="NBIS", action="buy", account="RRSP", shares=3.0,
            veto_reasons=["b"], rationale="second", path=path,
        )
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2


class TestCliLogOverride:
    def test_resolves_vetoed_order_then_logs(self, tmp_path):
        review_path = tmp_path / "risk_officer_review.json"
        overrides_path = tmp_path / "risk_officer_overrides.jsonl"
        review_path.write_text(json.dumps({
            "status": "ok", "generatedAt": "x", "sourceRebalancePlanGeneratedAt": "y",
            "vetoedOrders": [{
                "ticker": "CORZ", "action": "buy", "account": "TFSA", "shares": 10,
                "vetoReasons": ["MRC breach"],
            }],
            "approvedOrders": [],
        }))
        _cli_log_override(
            ticker="CORZ", action="buy", account="TFSA",
            rationale="Conviction unchanged",
            review_path=review_path, overrides_path=overrides_path,
        )
        entry = json.loads(overrides_path.read_text().strip())
        assert entry["shares"] == 10
        assert entry["vetoReasons"] == ["MRC breach"]

    def test_missing_review_file_raises(self, tmp_path):
        review_path = tmp_path / "does_not_exist.json"
        overrides_path = tmp_path / "risk_officer_overrides.jsonl"
        with pytest.raises(ValueError, match="not found"):
            _cli_log_override(
                ticker="CORZ", action="buy", account="TFSA", rationale="x",
                review_path=review_path, overrides_path=overrides_path,
            )

    def test_no_matching_vetoed_order_raises(self, tmp_path):
        review_path = tmp_path / "risk_officer_review.json"
        overrides_path = tmp_path / "risk_officer_overrides.jsonl"
        review_path.write_text(json.dumps({
            "status": "ok", "generatedAt": "x", "sourceRebalancePlanGeneratedAt": "y",
            "vetoedOrders": [], "approvedOrders": [],
        }))
        with pytest.raises(ValueError, match="no vetoed order"):
            _cli_log_override(
                ticker="CORZ", action="buy", account="TFSA", rationale="x",
                review_path=review_path, overrides_path=overrides_path,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_officer.py -v`
Expected: FAIL with `ImportError: cannot import name 'log_risk_officer_override'`

- [ ] **Step 3: Write the minimal implementation**

Append to `investment_screener/backend/py_services/risk_officer.py` (before the final
`if __name__ == "__main__":` block):

```python
def log_risk_officer_override(
    ticker: str,
    action: str,
    account: str,
    shares: float | None,
    veto_reasons: list[str],
    rationale: str,
    overridden_by: str = "user",
    path: Path = OVERRIDES_PATH,
) -> None:
    """Append one accountability-trail record for a vetoed-order override.

    Called by risk-officer-agent.md — only a human decision to proceed with
    a vetoed order constitutes an "override." Mirrors thesis_breakers.py's
    log_breaker_override() exactly: append-only, one JSON object per line.

    Args:
        ticker: Order's ticker.
        action: "buy" or "sell".
        account: Order's account (e.g. "TFSA").
        shares: Order's share count, or None if unknown.
        veto_reasons: The order's vetoReasons at time of override.
        rationale: The user's stated reason for proceeding anyway.
        overridden_by: Who made the call — defaults to "user".
        path: Target JSONL file.
    """
    entry = {
        "date": date.today().isoformat(),
        "ticker": ticker,
        "action": action,
        "account": account,
        "shares": shares,
        "vetoReasons": veto_reasons,
        "rationale": rationale,
        "overriddenBy": overridden_by,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _cli_log_override(
    ticker: str,
    action: str,
    account: str,
    rationale: str,
    overridden_by: str = "user",
    review_path: Path = REVIEW_PATH,
    overrides_path: Path = OVERRIDES_PATH,
) -> None:
    """Resolve a vetoed order's shares/vetoReasons from risk_officer_review.json, then log.

    Thin wrapper so a caller (risk-officer-agent.md, via --log-override) only
    needs a ticker/action/account/rationale — not risk_officer_review.json's
    internal shape.

    Args:
        ticker: Order's ticker.
        action: "buy" or "sell".
        account: Order's account.
        rationale: The user's stated reason for proceeding anyway.
        overridden_by: Who made the call — defaults to "user".
        review_path: Path to risk_officer_review.json.
        overrides_path: Target JSONL file.

    Raises:
        ValueError: If review_path doesn't exist, or no vetoed order matches
            (ticker, action, account).
    """
    if not Path(review_path).exists():
        raise ValueError(f"{review_path} not found — run risk_officer.py --pretty first")
    review = json.loads(Path(review_path).read_text())
    match = next(
        (
            o for o in review.get("vetoedOrders", [])
            if o["ticker"] == ticker and o["action"] == action and o["account"] == account
        ),
        None,
    )
    if match is None:
        raise ValueError(f"no vetoed order found for {ticker}/{action}/{account} in {review_path}")
    log_risk_officer_override(
        ticker=ticker, action=action, account=account, shares=match.get("shares"),
        veto_reasons=match.get("vetoReasons", []), rationale=rationale,
        overridden_by=overridden_by, path=overrides_path,
    )


def main() -> None:
    """CLI entry point — compute the risk-officer review, or log an override.

    --log-override lets risk-officer-agent.md record a vetoed-order override
    without importing this module directly.
    """
    parser = argparse.ArgumentParser(description="Risk officer veto classification / override logging")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-save", action="store_true", help="Print only, skip writing risk_officer_review.json")
    parser.add_argument("--log-override", action="store_true", help="Log an override instead of reviewing")
    parser.add_argument("--ticker", help="Ticker (required with --log-override)")
    parser.add_argument("--action", choices=["buy", "sell"], help="Order action (required with --log-override)")
    parser.add_argument("--account", help="Account (required with --log-override)")
    parser.add_argument("--rationale", help="Override rationale (required with --log-override)")
    parser.add_argument("--overridden-by", default="user", help="Who made the override call")
    args = parser.parse_args()

    if args.log_override:
        if not (args.ticker and args.action and args.account and args.rationale):
            sys.exit("ERROR: --log-override requires --ticker, --action, --account, and --rationale")
        _cli_log_override(args.ticker, args.action, args.account, args.rationale, args.overridden_by)
        print(f"✅  Logged override for {args.ticker} {args.action} ({args.account})")
        return

    result = compute_risk_officer_review(save=not args.no_save)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_risk_officer.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/risk_officer.py investment_screener/backend/tests/py_services/test_risk_officer.py
git commit -m "feat(risk-officer): add override logging + CLI"
```

---

## Task 3: `market_data.get_prices()` — staleness passthrough

**Files:**
- Modify: `investment_screener/backend/py_services/market_data.py:44-109`
- Test: `investment_screener/backend/tests/py_services/test_market_data.py` (create if it
  doesn't already exist; if it exists, append to it)

**Interfaces:**
- Consumes: `check_staleness(as_of_date: str, max_age_days: int = 120) -> bool` (existing,
  from `data_quality.py`, already imported in `market_data.py`).
- Produces: `_price_staleness(rows: list[dict], max_age_days: int = 5) -> bool`. Every
  ticker entry `get_prices()` returns gains a `"dataQuality": {"staleness": bool}` key.

- [ ] **Step 1: Check for an existing test file, then write the failing test**

```bash
ls investment_screener/backend/tests/py_services/test_market_data.py 2>/dev/null && echo EXISTS || echo NEW_FILE
```

If `NEW_FILE`, create `investment_screener/backend/tests/py_services/test_market_data.py`
with this content (the header + imports). If `EXISTS`, append only the two test functions
below to the existing file, adding `_price_staleness, get_prices` to its existing `from
market_data import ...` line.

```python
"""Tests for market_data.py's dataQuality wiring (G2, Phase 3 sub-spec 5)."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from market_data import _price_staleness, get_prices  # noqa: E402


def test_price_staleness_false_for_empty_rows():
    assert _price_staleness([]) is False


def test_price_staleness_boundary_is_inclusive_not_stale():
    from datetime import date, timedelta
    boundary_date = (date.today() - timedelta(days=5)).isoformat()
    assert _price_staleness([{"date": boundary_date, "close": 1.0}], max_age_days=5) is False


def test_price_staleness_true_past_boundary():
    from datetime import date, timedelta
    old_date = (date.today() - timedelta(days=10)).isoformat()
    assert _price_staleness([{"date": old_date, "close": 1.0}], max_age_days=5) is True


def test_get_prices_attaches_data_quality_on_fresh_fetch():
    with patch("market_data.cache_get", return_value=None), \
         patch("market_data.cache_set"), \
         patch("market_data.yf.download") as mock_download:
        import pandas as pd
        from datetime import date
        idx = pd.to_datetime([date.today().isoformat()])
        mock_download.return_value = pd.DataFrame({
            "Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5], "Volume": [1000],
        }, index=idx)
        result = get_prices(["NVDA"], period="5d")
    assert "dataQuality" in result["NVDA"]
    assert result["NVDA"]["dataQuality"]["staleness"] is False


def test_get_prices_attaches_data_quality_on_cache_hit():
    from datetime import date, timedelta
    stale_date = (date.today() - timedelta(days=30)).isoformat()
    cached_entry = {"data": [{"date": stale_date, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}], "asOf": "x"}
    with patch("market_data.cache_get", return_value=cached_entry):
        result = get_prices(["NVDA"], period="5d")
    assert result["NVDA"]["dataQuality"]["staleness"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_market_data.py -v`
Expected: FAIL with `ImportError: cannot import name '_price_staleness'`

- [ ] **Step 3: Write the minimal implementation**

In `investment_screener/backend/py_services/market_data.py`, add this helper directly above
`get_prices()` (after `_now_iso()`, before line 44):

```python
def _price_staleness(rows: list[dict], max_age_days: int = 5) -> bool:
    """True if the last row's date is more than max_age_days old.

    OHLCV has no second source to cross-check for conflicts (unlike
    get_fundamentals()'s EDGAR-vs-yfinance check) — this is a staleness-only
    signal, reusing check_staleness() from data_quality.py.

    Args:
        rows: OHLCV row dicts (get_prices()'s "data" list), oldest first —
            the last element is the most recent bar.
        max_age_days: Staleness threshold in days, default 5 (a trading
            week) — looser than get_fundamentals()'s 120-day threshold since
            daily price data is expected to be much fresher.

    Returns:
        False if rows is empty (nothing to judge staleness on), or the last
        date is within max_age_days (inclusive boundary). True otherwise.
    """
    if not rows:
        return False
    return check_staleness(rows[-1]["date"], max_age_days=max_age_days)


def _with_data_quality(result: dict[str, dict]) -> dict[str, dict]:
    """Attach a {"staleness": bool} dataQuality dict to every entry in result, in place.

    Args:
        result: get_prices()'s per-ticker result dict, built so far.

    Returns:
        The same dict, mutated in place and returned for convenience at call sites.
    """
    for entry in result.values():
        entry["dataQuality"] = {"staleness": _price_staleness(entry.get("data", []))}
    return result
```

Then modify `get_prices()`'s two return points. Change:
```python
    if not to_fetch:
        return result
```
to:
```python
    if not to_fetch:
        return _with_data_quality(result)
```
And change the final line of the function from:
```python
    return result
```
to:
```python
    return _with_data_quality(result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_market_data.py -v`
Expected: PASS (5 tests)

Also run the full existing suite to confirm nothing else broke (several scripts call
`get_prices()` and destructure its return dict — adding a key is additive/non-breaking, but
verify):

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -v -k "wacc or technicals or market_data"`
Expected: PASS, no regressions

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/market_data.py investment_screener/backend/tests/py_services/test_market_data.py
git commit -m "feat(data-quality): add staleness passthrough to market_data.get_prices()"
```

---

## Task 4: `wacc.py` — dataQuality passthrough

**Files:**
- Modify: `investment_screener/backend/py_services/wacc.py:127-212`
- Test: `investment_screener/backend/tests/py_services/test_wacc.py`

**Interfaces:**
- Consumes: `get_fundamentals()`'s existing `"dataQuality"` key (already present since Phase
  1 — this task surfaces it, doesn't create it).
- Produces: `compute_wacc()`'s return dict gains a `"dataQuality"` key
  (`{"staleness": bool, "dataConflicts": list, "flags": list}`).

- [ ] **Step 1: Write the failing test**

Append to `investment_screener/backend/tests/py_services/test_wacc.py`:

```python
def test_compute_wacc_surfaces_data_quality_from_fundamentals():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={
             "totalDebt": {"value": 200_000_000.0, "source": "yfinance", "asOf": "x"},
             "dataQuality": {"staleness": True, "dataConflicts": [], "flags": []},
         }):
        result = compute_wacc(
            ticker="TESTCO", market_cap=800_000_000.0,
            beta_override=1.0, cost_of_debt_override=0.05,
        )
    assert result["dataQuality"] == {"staleness": True, "dataConflicts": [], "flags": []}


def test_compute_wacc_defaults_data_quality_when_fundamentals_omit_it():
    with patch("wacc.compute_risk_free_rate", return_value={"riskFreeRate": 0.04, "usedFallback": False}), \
         patch("wacc.get_fundamentals", return_value={}):
        result = compute_wacc(
            ticker="TESTCO", market_cap=1_000_000_000.0,
            beta_override=1.0, cost_of_debt_override=0.05,
        )
    assert result["dataQuality"] == {"staleness": False, "dataConflicts": [], "flags": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_wacc.py -v -k data_quality`
Expected: FAIL with `KeyError: 'dataQuality'`

- [ ] **Step 3: Write the minimal implementation**

In `investment_screener/backend/py_services/wacc.py`, in `compute_wacc()`'s return dict
(currently ending at `"source": {...}`), add one key:

```python
    return {
        "wacc": round(final_wacc, 4),
        "riskFreeRate": rf["riskFreeRate"],
        "beta": beta,
        "erp": erp,
        "costOfDebt": cod_result["costOfDebt"],
        "capApplied": cap_applied,
        "floorApplied": floor_applied,
        "betaWarning": beta_warning,
        "dataQuality": fundamentals.get(
            "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
        ),
        "source": {
            "riskFree": "fallback" if rf["usedFallback"] else "market_data:^TNX",
            "beta": "override" if beta_override is not None else (
                "fallback_sector_average" if beta_result["usedFallback"] else "local_ols_2y"
            ),
            "costOfDebt": "override" if cost_of_debt_override is not None else (
                "fallback" if cod_result["usedFallback"] else "market_data:get_fundamentals"
            ),
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_wacc.py -v`
Expected: PASS (all tests, including the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/wacc.py investment_screener/backend/tests/py_services/test_wacc.py
git commit -m "feat(data-quality): surface dataQuality in wacc.py output"
```

---

## Task 5: `comps_valuation.py` — dataQuality passthrough

**Files:**
- Modify: `investment_screener/backend/py_services/comps_valuation.py:86-138`
- Test: `investment_screener/backend/tests/py_services/test_comps_valuation.py`

**Interfaces:**
- Consumes: `get_fundamentals()`'s existing `"dataQuality"` key.
- Produces: `comps_implied_range()`'s return dict gains a `"dataQuality"` key,
  `{ticker: {"staleness": bool, "dataConflicts": list, "flags": list}}`, keyed by every
  ticker actually used (target + `peersUsed`) — both on the `"ok"` and
  `"insufficient_peer_data"` paths where a target dataQuality is available.

- [ ] **Step 1: Write the failing test**

Read `investment_screener/backend/tests/py_services/test_comps_valuation.py` first to see its
existing `_write_projection`-style fixture helper, then append (adapting to match whatever
fixture helper that file already defines — if it defines a helper named differently, use that
name instead of inventing a new one):

```python
def test_comps_implied_range_includes_data_quality_per_ticker_used(tmp_path, monkeypatch):
    import comps_valuation

    (tmp_path / "NVDA.json").write_text(json.dumps([{
        "source": "AI_AGENT", "savedAt": "2026-07-01",
        "snapshot": {"price": 100.0, "shares": 1000.0, "revenue": 5000.0},
    }]))
    (tmp_path / "AMD.json").write_text(json.dumps([{
        "source": "AI_AGENT", "savedAt": "2026-07-01",
        "snapshot": {"price": 50.0, "shares": 2000.0, "revenue": 3000.0},
    }]))
    (tmp_path / "AVGO.json").write_text(json.dumps([{
        "source": "AI_AGENT", "savedAt": "2026-07-01",
        "snapshot": {"price": 200.0, "shares": 500.0, "revenue": 4000.0},
    }]))

    quality_by_ticker = {
        "NVDA": {"staleness": True, "dataConflicts": [], "flags": []},
        "AMD": {"staleness": False, "dataConflicts": [], "flags": []},
        "AVGO": {"staleness": False, "dataConflicts": [], "flags": []},
    }

    def fake_get_fundamentals(ticker, cik=None):
        return {
            "totalDebt": {"value": 0.0}, "cashAndEquivalents": {"value": 0.0},
            "dataQuality": quality_by_ticker[ticker],
        }

    monkeypatch.setattr(comps_valuation, "get_fundamentals", fake_get_fundamentals)

    result = comps_valuation.comps_implied_range("NVDA", ["AMD", "AVGO"], str(tmp_path))

    assert result["status"] == "ok"
    assert result["dataQuality"]["NVDA"]["staleness"] is True
    assert result["dataQuality"]["AMD"]["staleness"] is False
    assert result["dataQuality"]["AVGO"]["staleness"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_comps_valuation.py -v -k data_quality`
Expected: FAIL with `KeyError: 'dataQuality'`

- [ ] **Step 3: Write the minimal implementation**

In `investment_screener/backend/py_services/comps_valuation.py`, modify `comps_implied_range()`:

```python
def comps_implied_range(ticker: str, peer_tickers: list[str], projections_dir: str) -> dict:
    """Peer-median EV/Sales applied to the target's own revenue -> implied price range.

    Args:
        ticker: Target ticker.
        peer_tickers: Curated peer ticker list (from projections/{TICKER}.json's `peers` field).
        projections_dir: Path to the projections directory.

    Returns:
        {"status": "ok", "impliedPriceRange": {"low": float, "high": float},
         "peersUsed": [...], "evSalesMedian": float,
         "dataQuality": {ticker: {"staleness","dataConflicts","flags"}, ...peers...}}
        or {"status": "insufficient_peer_data", "peersUsed": [...]} when fewer
        than 2 peers have usable data. dataQuality is keyed by every ticker
        whose get_fundamentals() was actually consulted (target + peersUsed).
    """
    target_proj = load_latest_projection(ticker, projections_dir)
    if target_proj is None:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    snapshot = target_proj.get("snapshot", {})
    target_shares = snapshot.get("shares")
    target_revenue = snapshot.get("revenue")
    if not target_shares or not target_revenue:
        return {"status": "insufficient_peer_data", "peersUsed": []}

    peer_multiples = {}
    for peer in peer_tickers:
        multiple = _peer_ev_sales(peer, projections_dir)
        if multiple is not None:
            peer_multiples[peer] = multiple

    if len(peer_multiples) < 2:
        return {"status": "insufficient_peer_data", "peersUsed": list(peer_multiples)}

    ev_sales_median = statistics.median(peer_multiples.values())

    fundamentals = get_fundamentals(ticker)
    target_debt = fundamentals.get("totalDebt", {}).get("value") or 0.0
    target_cash = fundamentals.get("cashAndEquivalents", {}).get("value") or 0.0

    implied_ev = ev_sales_median * target_revenue
    implied_price = (implied_ev - target_debt + target_cash) / target_shares

    data_quality = {ticker: fundamentals.get(
        "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
    )}
    for peer in peer_multiples:
        peer_fundamentals = get_fundamentals(peer)
        data_quality[peer] = peer_fundamentals.get(
            "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
        )

    # +/-10% band around the point estimate — a single multiple from a small
    # peer set is not precise enough to present as one number.
    return {
        "status": "ok",
        "impliedPriceRange": {
            "low": round(implied_price * 0.9, 2),
            "high": round(implied_price * 1.1, 2),
        },
        "peersUsed": list(peer_multiples),
        "evSalesMedian": round(ev_sales_median, 3),
        "dataQuality": data_quality,
    }
```

Note: the second `get_fundamentals(peer)` call per used peer is a cache hit
(`market_data.py`'s `get_fundamentals()` caches by ticker) since `_peer_ev_sales()` already
called it once for the same peer earlier in this same function — cheap, not a real re-fetch.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_comps_valuation.py -v`
Expected: PASS (all tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/comps_valuation.py investment_screener/backend/tests/py_services/test_comps_valuation.py
git commit -m "feat(data-quality): surface dataQuality in comps_valuation.py output"
```

---

## Task 6: `peer_bench.py` — dataQuality passthrough

**Files:**
- Modify: `investment_screener/backend/py_services/peer_bench.py`
- Test: `investment_screener/backend/tests/py_services/test_peer_bench.py`

**Interfaces:**
- Consumes: `market_data.get_fundamentals()` (new direct import into `peer_bench.py`).
- Produces: `compute_peer_benchmark()`'s `"ok"` return dict gains a `"dataQuality"` key,
  `{ticker: {"staleness","dataConflicts","flags"}}`, keyed by target + `peersUsed`.

- [ ] **Step 1: Write the failing test**

Read `investment_screener/backend/tests/py_services/test_peer_bench.py` first to see its
existing fixture/monkeypatch pattern for `compute_raw_metrics`, then append (using that same
pattern — the file already mocks `peer_bench.compute_raw_metrics`, add a mock for
`peer_bench.get_fundamentals` alongside it):

```python
def test_compute_peer_benchmark_includes_data_quality_per_ticker_used(monkeypatch):
    import peer_bench

    def fake_raw_metrics(ticker, sector, projections_dir, cik=None):
        return {"revenueGrowth": {"NVDA": 0.5, "AMD": 0.3, "AVGO": 0.4}[ticker]}

    def fake_get_fundamentals(ticker, cik=None):
        return {"dataQuality": {
            "NVDA": {"staleness": True, "dataConflicts": [], "flags": []},
            "AMD": {"staleness": False, "dataConflicts": [], "flags": []},
            "AVGO": {"staleness": False, "dataConflicts": [], "flags": []},
        }[ticker]}

    monkeypatch.setattr(peer_bench, "compute_raw_metrics", fake_raw_metrics)
    monkeypatch.setattr(peer_bench, "get_fundamentals", fake_get_fundamentals)

    result = peer_bench.compute_peer_benchmark("NVDA", ["AMD", "AVGO"], "chips_ai", "/tmp/unused")

    assert result["status"] == "ok"
    assert result["dataQuality"]["NVDA"]["staleness"] is True
    assert result["dataQuality"]["AMD"]["staleness"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_peer_bench.py -v -k data_quality`
Expected: FAIL with `AttributeError: module 'peer_bench' has no attribute 'get_fundamentals'`

- [ ] **Step 3: Write the minimal implementation**

In `investment_screener/backend/py_services/peer_bench.py`, add the import:

```python
from market_data import get_fundamentals  # noqa: E402
```
directly below the existing `from framework_score import compute_raw_metrics  # noqa: E402`
line.

Then modify `compute_peer_benchmark()`'s return to include `dataQuality`:

```python
    table = []
    for metric_name, target_value in target_metrics.items():
        if target_value is None or not isinstance(target_value, (int, float)):
            continue
        peer_values = [
            peer_metrics[p][metric_name] for p in peers_used
            if isinstance(peer_metrics[p].get(metric_name), (int, float))
        ]
        if len(peer_values) < MIN_USABLE_PEERS:
            continue

        peer_median = statistics.median(peer_values)
        all_values = peer_values + [target_value]
        peer_mean = statistics.mean(peer_values)
        peer_stdev = statistics.pstdev(peer_values)
        z_score = (target_value - peer_mean) / peer_stdev if peer_stdev > 0 else 0.0
        rank = sorted(all_values).index(target_value) + 1
        percentile = round(rank / len(all_values) * 100)

        table.append({
            "metric": metric_name,
            "ticker": target_value,
            "peerMedian": round(peer_median, 4),
            "zScore": round(z_score, 3),
            "percentile": percentile,
        })

    data_quality = {}
    for t in [ticker, *peers_used]:
        fundamentals = get_fundamentals(t)
        data_quality[t] = fundamentals.get(
            "dataQuality", {"staleness": False, "dataConflicts": [], "flags": []}
        )

    return {"status": "ok", "peersUsed": peers_used, "table": table, "dataQuality": data_quality}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_peer_bench.py -v`
Expected: PASS (all tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/peer_bench.py investment_screener/backend/tests/py_services/test_peer_bench.py
git commit -m "feat(data-quality): surface dataQuality in peer_bench.py output"
```

---

## Task 7: `technicals.py` — dataQuality passthrough

**Files:**
- Modify: `investment_screener/backend/py_services/technicals.py:287-363`
- Test: `investment_screener/backend/tests/py_services/test_technicals.py`

**Interfaces:**
- Consumes (from Task 3): `get_prices()`'s per-ticker `"dataQuality": {"staleness": bool}`.
- Produces: `compute_technical_snapshot()`'s return dict gains a `"dataQuality"` key,
  `{"staleness": bool}`, taken from the target ticker's own price-fetch result (not the
  benchmark's).

- [ ] **Step 1: Write the failing test**

Append to `investment_screener/backend/tests/py_services/test_technicals.py`:

```python
def test_compute_technical_snapshot_surfaces_data_quality_staleness():
    rows = [{"date": f"2026-01-{i:02d}", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000} for i in range(1, 25)]
    with patch("technicals.get_prices", return_value={
        "NVDA": {"data": rows, "source": "yfinance", "asOf": "x", "dataQuality": {"staleness": True}},
        "SPY": {"data": rows, "source": "yfinance", "asOf": "x", "dataQuality": {"staleness": False}},
    }):
        result = compute_technical_snapshot("NVDA", "D", "1y", "SPY", None)
    assert result["dataQuality"] == {"staleness": True}


def test_compute_technical_snapshot_empty_data_defaults_data_quality_not_stale():
    with patch("technicals.get_prices", return_value={}):
        result = compute_technical_snapshot("NVDA", "D", "1y", "SPY", None)
    assert result["dataQuality"] == {"staleness": False}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_technicals.py -v -k data_quality`
Expected: FAIL with `KeyError: 'dataQuality'`

- [ ] **Step 3: Write the minimal implementation**

In `investment_screener/backend/py_services/technicals.py`, in `compute_technical_snapshot()`:
the empty-`df` early-return dict gains one key, and the main return dict gains one key sourced
from `prices.get(ticker, {})`:

```python
    if df.empty:
        return {
            "ticker": ticker, "timeframe": timeframe, "asOf": None,
            "rsi14": None, "ema21": None, "ema50": None, "ema200": None,
            "macd": None, "adx14": None, "plusDI": None, "minusDI": None,
            "atr14": None, "bollinger": None, "keltner": None, "squeeze": None,
            "anchoredVwap": None, "volumeRatio20d": None,
            "relativeStrength": {"ratio": None, "slope63d": None},
            "dataQuality": {"staleness": False},
        }
```

and, in the final return statement, add:

```python
        "volumeRatio20d": compute_volume_ratio(df["volume"]),
        "relativeStrength": relative_strength,
        "dataQuality": prices.get(ticker, {}).get("dataQuality", {"staleness": False}),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_technicals.py -v`
Expected: PASS (all tests, including the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/technicals.py investment_screener/backend/tests/py_services/test_technicals.py
git commit -m "feat(data-quality): surface dataQuality in technicals.py output"
```

---

## Task 8: Three agent definitions + `plugin.json` registration

**Files:**
- Create: `plugins/portfolio-advisor/agents/risk-officer-agent.md`
- Create: `plugins/portfolio-advisor/agents/red-team-agent.md`
- Create: `plugins/portfolio-advisor/agents/data-quality-agent.md`
- Modify: `plugins/portfolio-advisor/plugin.json:80-105`

**Interfaces:**
- Consumes (from Tasks 1-2): `risk_officer.py --pretty`, `risk_officer.py --log-override
  --ticker --action --account --rationale`.
- Consumes (spec-only, no code dependency): `rebalance_plan.json`'s `orders[]` shape (E2),
  projection JSON shape (`stock_valuation` skill), `data/risk_officer_review.json` (Task 1).
- No test file — these are markdown agent definitions (conversational judgment + tool
  orchestration), matching how `daily-loop-agent.md` and `thesis-review-agent.md` have no
  test files today (spec §7).

This task has no TDD cycle (no code, no tests) — it is scaffolding + documentation, matching
the plan's "fold setup/scaffolding into the task whose deliverable needs it" guidance. Its
deliverable (three registered, dispatchable agents) is independently verifiable by dispatching
each one via the Agent tool against a hand-built fixture and checking its output matches the
contract below — do this manually as this task's verification step, not via pytest.

- [ ] **Step 1: Create `risk-officer-agent.md`**

```markdown
---
name: risk-officer-agent
description: >
  Consumes data/rebalance_plan.json (E2) and classifies its orders into vetoed
  vs approved via risk_officer.py — reusing E2's exact riskGateWarnings/
  breakerWarnings thresholds (25% MRC / 60% cluster variance, TRIGGERED thesis
  breakers). Presents vetoed orders with rationale, handles the override
  conversation one order at a time, logs any override to
  data/risk_officer_overrides.jsonl. Dispatched by rebalance-portfolio/SKILL.md
  (Step 1b, real enforcement) and daily-loop-agent.md (Step 1.5, read-only
  banner) — never dispatches itself.
dependencies:
  - skill:rebalance-portfolio
tools: ["Bash", "Read", "Write"]
---

# Risk Officer Agent

You are the **Risk Officer**. Your job is to enforce E2's already-computed risk-gate and
thesis-breaker warnings as real vetoes, not just displayed text. You never invent new
numeric thresholds — you only ever act on `riskGateWarnings`/`breakerWarnings` that
`rebalancer.py` already computed onto each order in `data/rebalance_plan.json`.

## Mode 1: Real enforcement (dispatched from `/rebalance`)

1. Run:
   ```bash
   python3 investment_screener/backend/py_services/risk_officer.py --pretty
   ```
2. If the result's `"status"` is `"no_plan"` or `"plan_blocked"`, report that plainly and
   stop — there is nothing to review.
3. Present `vetoedOrders` in a table, one row per order, each row's `vetoReasons` printed as
   sub-bullets underneath (mirror the "Skipped Restores" table style already used in
   `rebalance-portfolio/SKILL.md`).
4. Present `approvedOrders` as the trade plan that proceeds to the rest of `/rebalance`'s flow
   unchanged.
5. For each vetoed order, ask the user: proceed anyway (override), or accept the veto?
   - **Accept the veto**: the order is dropped from the plan. Nothing to log — this is the
     default outcome, not an exception.
   - **Override**: ask for a one-sentence rationale, then run:
     ```bash
     python3 investment_screener/backend/py_services/risk_officer.py --log-override \
       --ticker {TICKER} --action {buy|sell} --account {ACCOUNT} --rationale "{stated reason}"
     ```
     The order then rejoins the trade plan exactly as if it had been approved. Never batch
     multiple overrides on one confirmation — one order, one explicit decision, every time.

## Mode 2: Read-only banner (dispatched from `/daily`)

1. Check if `data/rebalance_plan.json` exists and its `generatedAt` is within the last 24h.
   If not, say nothing — `/daily` never generates a rebalance plan itself, so an old or
   missing plan is the normal case, not an error.
2. If fresh, run the same `risk_officer.py --pretty` command as Mode 1.
3. If `vetoedOrders` is non-empty, return exactly one line to the caller:
   `⛔ RISK OFFICER: {N} order(s) in the last /rebalance plan were vetoed — run /rebalance to review.`
   Do not present the vetoed orders' detail here, do not offer to override here — this mode
   is visibility only, per the spec's explicit `/daily` scope boundary (§3.3).
```

- [ ] **Step 2: Create `red-team-agent.md`**

```markdown
---
name: red-team-agent
description: >
  Adversarial reviewer for a completed analysis artifact (a stock_valuation
  projection, or an E2 rebalance_plan.json). Produces at least 3 specific,
  falsifiable objections plus a "what would change my mind" list. Explicitly
  forbidden from proposing trades. Dispatched mandatorily by
  stock_valuation/SKILL.md (after Step 4) and rebalance-portfolio/SKILL.md
  (after Step 1b) before either skill presents its final recommendation to
  the user. Output is conversational only — never persisted to disk.
tools: ["Read"]
---

# Red Team Agent

You are the **Red Team**. Your only job is to attack the artifact you're given — a DCF
projection or a rebalance plan — using nothing but the data already present in that artifact
plus any files you read yourself. You are **forbidden from proposing a trade, a share count,
or an account** in your output; that is not your role, and doing so would blur the line this
agent exists to keep clean (Standing Constraint: decision support, not advice).

## Contract

Given the artifact, produce exactly two sections:

**Objections** — at least 3, each one:
- Names a specific, concrete claim in the artifact (a DCF growth assumption, a comps peer
  choice, a rebalance order's rationale, an "approved" classification from the risk officer).
- States the specific evidence, data point, or scenario that would contradict that claim.
- Never generic risk-off boilerplate ("markets can go down") — every objection must be
  falsifiable against something concrete in the artifact itself or a fact you can point to.

**What would change my mind** — one entry per objection above, stating the observable
event/data that would resolve it either direction (confirm the objection was right, or
resolve it in the artifact's favor).

Print both sections to the user, above whatever recommendation the calling skill was about to
present. Do not write these objections to any file — this is a presentation-time check, read
fresh every time you're dispatched, not a data contract any other engine consumes.
```

- [ ] **Step 3: Create `data-quality-agent.md`**

```markdown
---
name: data-quality-agent
description: >
  Decides degrade-gracefully vs halt when a Step 3.5/3.6 valuation-committee
  script (wacc.py, comps_valuation.py, peer_bench.py, technicals.py) flags
  staleness or a cross-source conflict via its dataQuality output. Dispatched
  by stock_valuation/SKILL.md whenever a flag fires — not dispatched on every
  run, only when triggered. Read-only: decides, never edits analyticsLog
  itself (the calling skill does the append).
tools: ["Read"]
---

# Data Quality Agent

You are dispatched only when `stock_valuation/SKILL.md` detects a `dataQuality.staleness ==
true` or a non-empty `dataQuality.dataConflicts` entry from one of Step 3.5/3.6's scripts for
the ticker currently being evaluated. You decide **DEGRADE** or **HALT** — nothing else. You
never edit `analyticsLog` yourself; the calling skill appends your decision + detail to
`analyticsLog.dataQualityFlags` (an existing field, no schema change).

## Decision tree

You are given: which script flagged it (`wacc` / `comps` / `peerBench` / `technicals`), the
specific staleness or conflict detail, and whether that script's output feeds
`aiThesis.action`'s 2-of-3 gate (`wacc`/`comps` do — `dcf_scenarios.py --wacc-file` consumes
`wacc.py`'s discount rate directly; `framework`/`peerBench`/`technicals` are informational-only
and never gate).

1. Staleness only (no `dataConflicts` entries), on an informational-only lens (`peerBench` or
   `technicals`) → **DEGRADE**.
2. Staleness only, on a gate-feeding lens (`wacc` or `comps`) → **DEGRADE**, but your note
   must say the fair value may be stale-input-affected.
3. A `dataConflicts` entry with `diffPct` under 15% → **DEGRADE** (same materiality bar
   CLAUDE.md rule 8 already uses for DCF fair-value deltas — a difference this small isn't
   worth stopping the pipeline over).
4. A `dataConflicts` entry with `diffPct` >= 15% on a gate-feeding lens (`wacc` or `comps`) →
   **HALT**.
5. A `dataConflicts` entry with `diffPct` >= 15% on an informational-only lens → **DEGRADE**
   with a prominent flag — never halt a pipeline over data that doesn't feed the actual
   valuation number.

## Output

Return exactly one of:
- `DEGRADE: {one-sentence note for analyticsLog.dataQualityFlags}`
- `HALT: {one-sentence reason to tell the user, naming the specific ticker/metric/script}`

Nothing else. The calling skill handles the rest (append-and-continue, or stop-and-report).
```

- [ ] **Step 4: Register all three in `plugin.json`**

In `plugins/portfolio-advisor/plugin.json`, the `"agents"` array's last entry currently ends
like this (no trailing comma, since it's the last element):

```json
        {
            "name": "weekly_review_agent",
            "path": "agents/weekly-review-agent.md",
            "trigger": "/weekly-review"
        }
    ],
```

Add a comma after that entry's closing `}` and insert three new entries before the array's
closing `]`:

```json
        {
            "name": "weekly_review_agent",
            "path": "agents/weekly-review-agent.md",
            "trigger": "/weekly-review"
        },
        {
            "name": "risk_officer_agent",
            "path": "agents/risk-officer-agent.md",
            "trigger": "/rebalance"
        },
        {
            "name": "red_team_agent",
            "path": "agents/red-team-agent.md",
            "trigger": "red-team"
        },
        {
            "name": "data_quality_agent",
            "path": "agents/data-quality-agent.md",
            "trigger": "data-quality"
        }
```

- [ ] **Step 5: Validate `plugin.json` is still well-formed JSON**

Run: `python3 -m json.tool plugins/portfolio-advisor/plugin.json > /dev/null && echo VALID`
Expected: `VALID`

- [ ] **Step 6: Commit**

```bash
git add plugins/portfolio-advisor/agents/risk-officer-agent.md plugins/portfolio-advisor/agents/red-team-agent.md plugins/portfolio-advisor/agents/data-quality-agent.md plugins/portfolio-advisor/plugin.json
git commit -m "feat(g2): add risk-officer, red-team, and data-quality agent definitions"
```

---

## Task 9: `rebalance-portfolio/SKILL.md` — Risk Officer + Red Team integration

**Files:**
- Modify: `plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md`

**Interfaces:**
- Consumes (from Task 8): `risk-officer-agent.md`, `red-team-agent.md` (dispatched via the
  Agent tool, not imported as code).
- No test file — this is a skill-instruction change, verified by manual walkthrough (Step 5
  below), matching how E2's own Step 5/5b/6 additions were verified.

- [ ] **Step 1: Insert "Step 1b: Risk Officer Review" after Step 1**

In `plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md`, immediately after the
existing `## Step 1: Run the Rebalancer Engine` section (currently ending right before `##
Step 5: Present Trade Recommendations`), insert:

```markdown
---

## Step 1b: Risk Officer Review

Dispatch `risk-officer-agent` (Mode 1: real enforcement) via the Agent tool. It runs
`risk_officer.py --pretty` and returns vetoed vs approved orders.

- Any order in `vetoedOrders` is **removed** from the trade plan presented in Step 5 and
  instead rendered in a new "⛔ Vetoed by Risk Officer" section (same table style as the
  existing "Skipped Restores" section in Step 5), each row listing its `vetoReasons`.
- If the user chooses to override a veto, that override is handled entirely inside
  `risk-officer-agent`'s own conversation (one order at a time, logged via
  `risk_officer.py --log-override`) — once overridden, the order rejoins the set of orders
  this skill treats as approved for the rest of the flow (Step 5 table, Step 5b posting,
  Step 6 confirm+log).
- If `risk_officer.py` reports `"status": "no_plan"` or `"plan_blocked"`, or fails outright,
  degrade gracefully: show a one-line warning and proceed with the unreviewed plan — same
  degrade pattern E1/C2 already use in `daily_brief.py` when their own engines are
  unavailable.

---

## Step 1c: Red Team Review

Dispatch `red-team-agent` via the Agent tool, passing the post-veto-filtering order set (what
will actually be proposed in Step 5, after Step 1b's exclusions and any overrides). Print its
"Objections" and "What would change my mind" sections to the user, directly above Step 5's
trade table. This step is **mandatory, every `/rebalance` run** — never skipped, never made
conditional on plan size or user request.
```

- [ ] **Step 2: Verify the file is still well-formed markdown with correct step ordering**

Run: `grep -n "^## Step" plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md`
Expected output (order matters):
```
116:## Step 1: Run the Rebalancer Engine
XXX:## Step 1b: Risk Officer Review
XXX:## Step 1c: Red Team Review
XXX:## Step 5: Present Trade Recommendations
XXX:## Step 5b: Post Suggestions to Trade Log
XXX:## Step 6: Confirm + Log Each Trade
```

- [ ] **Step 3: Manual walkthrough verification**

With a hand-built fixture `data/rebalance_plan.json` containing at least one order with a
non-empty `riskGateWarnings`, manually invoke the `/rebalance` skill and confirm: the vetoed
order appears in a distinct "⛔ Vetoed by Risk Officer" section, not in the main trade table;
declining to override leaves it out of Step 5b's posted suggestions; overriding it produces
one new line in `data/risk_officer_overrides.jsonl`. This is the acceptance-test scenario from
spec §7 exercised end-to-end through the skill, not just through `risk_officer.py` directly.

- [ ] **Step 4: Commit**

```bash
git add plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md
git commit -m "feat(rebalance): add mandatory Risk Officer + Red Team review steps"
```

---

## Task 10: `daily-loop-agent.md` — Step 1.5 read-only risk banner

**Files:**
- Modify: `plugins/portfolio-advisor/agents/daily-loop-agent.md`

**Interfaces:**
- Consumes (from Task 8): `risk-officer-agent` (Mode 2: read-only banner).
- No test file — agent-instruction change, verified by manual walkthrough.

- [ ] **Step 1: Insert "Step 1.5 — Risk Officer Banner (Automatic, Read-Only)" between Step 1
  and Step 2**

In `plugins/portfolio-advisor/agents/daily-loop-agent.md`, immediately after the `### Step 1 —
Morning Brief (Automatic, Then Presented)` section and before `### Step 2 — Triage (Agent
Proposes, User Confirms)`, insert:

```markdown
---

### Step 1.5 — Risk Officer Banner (Automatic, Read-Only)

Dispatch `risk-officer-agent` (Mode 2: read-only banner) via the Agent tool. This never
generates a new rebalance plan and never blocks anything in this loop — it only checks
whether the *last* `/rebalance` run (if any, and if fresh) left any vetoed orders on file.

If it returns a banner line, print it immediately below the Morning Brief block, before the
triage queue:

```
⛔ RISK OFFICER: 2 order(s) in the last /rebalance plan were vetoed — run /rebalance to review.
```

If it returns nothing (no fresh plan, or a fresh plan with zero vetoes), print nothing — this
step is silent by default, exactly like Step 0's readiness check.

---
```

- [ ] **Step 2: Verify the step is correctly positioned**

Run: `grep -n "^### Step" plugins/portfolio-advisor/agents/daily-loop-agent.md | head -5`
Expected: `Step 0`, `Step 1`, `Step 1.5`, `Step 2`, `Step 3` in that order.

- [ ] **Step 3: Manual walkthrough verification**

With a hand-built fixture `data/rebalance_plan.json` (fresh `generatedAt`, one vetoed order
per Task 1's fixture shape) and its matching `data/risk_officer_review.json` already computed,
manually walk `/daily` through Step 0/Step 1/Step 1.5 and confirm the banner line appears
exactly once, before the triage queue, and that Step 2/3 proceed completely unchanged
afterward.

- [ ] **Step 4: Commit**

```bash
git add plugins/portfolio-advisor/agents/daily-loop-agent.md
git commit -m "feat(daily): add read-only Risk Officer banner (Step 1.5)"
```

---

## Task 11: `stock_valuation/SKILL.md` — Data Quality + Red Team integration

**Files:**
- Modify: `plugins/stock-valuation/skills/stock_valuation/SKILL.md`

**Interfaces:**
- Consumes (from Tasks 4-7): each Step 3.5/3.6 script's new `"dataQuality"` output key.
- Consumes (from Task 8): `data-quality-agent`, `red-team-agent` (dispatched via the Agent
  tool).
- No test file — skill-instruction change, verified by manual walkthrough.

- [ ] **Step 1: Add the data-quality check to the end of Step 3.5**

In `plugins/stock-valuation/skills/stock_valuation/SKILL.md`, immediately after the existing
Step 3.5 paragraph that begins "Merge all six outputs (`dcf`, `wacc`, `reverseDcf`,
`sensitivity`, `monteCarlo`, `comps`) into the projection's `analyticsLog` object before Step
4...", append:

```markdown
**Data-quality check (mandatory, after merging):** For `wacc` (single-ticker `dataQuality`
dict) and `comps` (per-ticker `dataQuality` dict, check the target ticker's own entry), if
`dataQuality.staleness` is `true` or `dataQuality.dataConflicts` is non-empty, dispatch
`data-quality-agent` via the Agent tool with: which script flagged it (`wacc` or `comps`), the
specific detail, and the fact that both feed `aiThesis.action`'s 2-of-3 gate. Its response is
one of:
- `DEGRADE: {note}` — append `{note}` to `analyticsLog.dataQualityFlags` and continue to Step 4.
- `HALT: {reason}` — stop before Step 4. Report `{reason}` to the user. Leave whatever is
  currently in `temp/evaluations/{TICKER}_projection.json` as-is (don't delete it, don't
  persist it to `data/projections/`) so the user can inspect what was gathered before the halt.
```

- [ ] **Step 2: Add the data-quality check to the end of Step 3.6**

Immediately after the existing Step 3.6 paragraph that begins "Merge all three outputs
(`framework`, `peerBench`, `technicals`) into the projection's `analyticsLog` object before
Step 4...", append:

```markdown
**Data-quality check (mandatory, after merging):** For `peerBench` (per-ticker `dataQuality`
dict, check the target ticker's own entry) and `technicals` (single `dataQuality` dict), if
`dataQuality.staleness` is `true` or `dataQuality.dataConflicts` is non-empty, dispatch
`data-quality-agent` via the Agent tool with: which script flagged it (`peerBench` or
`technicals`), the specific detail, and the fact that neither feeds `aiThesis.action`'s gate
(informational-only, per the framework doc's own Step 3.6 boundary). Per the agent's decision
tree, this always resolves to `DEGRADE` for an informational-only lens — append the note to
`analyticsLog.dataQualityFlags` and continue. `framework_score.py` doesn't call
`get_fundamentals()`/`get_prices()` directly (it reads persisted projection snapshots), so it
has no `dataQuality` output to check here.
```

- [ ] **Step 3: Add the mandatory Red Team step after Step 4**

Immediately after the existing `## Step 4: Validate & Repair` section's closing line ("Fix all
reported errors before proceeding. If math inconsistency detected → invoke **FB-05** from
`references/fallback-tree.md`."), insert a new section (before whatever numbered step
currently follows, e.g. weight normalization / Step 5):

```markdown
---

## Step 4.5: Red Team Review

Dispatch `red-team-agent` via the Agent tool, passing the validated projection JSON (post-Step
4, pre-persistence). Print its "Objections" and "What would change my mind" sections to the
user, directly above whatever conversational summary this skill was about to present. This
step is **mandatory, every `/evaluate-stock` run** — never skipped, never made conditional on
conviction level or user request.

---
```

- [ ] **Step 4: Verify the file structure**

Run: `grep -n "^## Step" plugins/stock-valuation/skills/stock_valuation/SKILL.md`
Expected: `Step 3.5`, `Step 3.6`, `Step 4`, `Step 4.5`, then whatever step numbering already
followed Step 4 before this task, unchanged.

- [ ] **Step 5: Manual walkthrough verification**

With a hand-built fixture where `wacc.py`'s mocked output carries
`dataQuality.dataConflicts` with a `diffPct` of 20 (>= 15%), manually walk a `/evaluate-stock`
run through Step 3.5 and confirm it halts before Step 4 with a reason naming `wacc` and the
conflict detail, and that `data/projections/{TICKER}.json` is not modified. With a second
fixture where `technicals.py`'s mocked output carries `dataQuality.staleness == true`, confirm
Step 3.6 degrades (appends to `analyticsLog.dataQualityFlags`) and the pipeline continues
through Step 4 and the new Step 4.5 normally.

- [ ] **Step 6: Commit**

```bash
git add plugins/stock-valuation/skills/stock_valuation/SKILL.md
git commit -m "feat(evaluate-stock): add mandatory Data Quality + Red Team review steps"
```

---

## Final Verification

- [ ] Run the full backend test suite to confirm zero regressions from the `market_data.py`,
  `wacc.py`, `comps_valuation.py`, `peer_bench.py`, and `technicals.py` changes:

  Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/ -v`
  Expected: all tests pass (prior baseline count + the new tests added across Tasks 1-7)

- [ ] Confirm the Phase 3 acceptance criterion end-to-end: a fixture `rebalance_plan.json`
  with a deliberately cap-breaching order produces a `risk_officer_review.json` with that
  order in `vetoedOrders` (already covered by Task 1's
  `test_compute_risk_officer_review_writes_file_and_round_trips`, re-confirm here as the
  literal spec §9 acceptance test, not just a unit test).

- [ ] Confirm `plugin.json` still validates: `python3 -m json.tool plugins/portfolio-advisor/plugin.json > /dev/null && echo VALID`

- [ ] Per `.agent/rules/worktree-subagent-isolation.md`: run `git status --short` in the
  **main checkout** (not the worktree) after every task's implementer/fix subagent, before
  generating that task's review package.

- [ ] Update `start_here.md`: mark G2 complete, note Phase 3 (E1/C2/B5/E2/G2) is now fully
  closed out, and record whatever branch name this work shipped on
  (`feature/fable5-phase3-g2-risk-officer-red-team`, matching the naming convention every
  prior sub-spec used) — following the "Git policy going forward" section already documented
  there (push to `origin` as a backup/PR source, do not merge/PR into `origin/main`).
