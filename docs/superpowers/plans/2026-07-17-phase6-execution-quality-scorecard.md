# Execution Quality Scorecard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, no worktree — small single-script addition, docs-adjacent risk level, same posture as this session's other Phase 6 work). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `execution_quality_scorecard.py` — a deterministic script joining
`orders_executed.jsonl` (Phase 5E-8's audit trail, never read until now) with `trade-log.json` to
surface decision breakdowns, per-gate fail rates, and an overridden-order worklist.

**Architecture:** Single new `py_services/` script following `generate_track_record_report.py`'s
exact shape (pure functions, `Path` params for test injection, `--json` CLI flag, graceful
degradation on missing/empty input). One doc edit to wire it into `/weekly-review`.

**Tech Stack:** Python 3.11, pytest (via the existing `tests/py_services/` suite).

## Global Constraints

- Full spec: `docs/superpowers/specs/2026-07-17-phase6-execution-quality-scorecard-design.md`.
- Never touch the real gitignored `data/orders_executed.jsonl` from a test — every test injects a
  `tmp_path` file, following `test_generate_track_record_report.py`'s exact pattern (this repo has
  a known, logged map-debt bug from an earlier test polluting a real `data/*.jsonl` file — do not
  repeat it).
- No return/P&L computation — this pass is decision-breakdown and gate-fail-rate only.
- No change to `aiThesis.action`, `standingDecision`, or any gating behavior — output is
  informational only, consumed by `/weekly-review` as an advisory section.
- The 6 gate names to track (from `check_risk_gates()`'s output): `mrc`, `cluster_variance`,
  `breaker_veto`, `size`, `balance`, `data_readiness`.
- `decision` field values: `EXECUTED`, `BLOCKED`, `OVERRIDDEN` (per `log_order_execution()`'s
  docstring in `order_risk_gates.py`).

---

### Task 1: `execution_quality_scorecard.py` — core functions + tests

**Files:**
- Create: `investment_screener/backend/py_services/execution_quality_scorecard.py`
- Create: `investment_screener/backend/tests/py_services/test_execution_quality_scorecard.py`
- Read (reference only, no changes): `investment_screener/backend/py_services/generate_track_record_report.py`,
  `investment_screener/backend/py_services/order_risk_gates.py` (for the real `orders_executed.jsonl`
  record shape), `investment_screener/backend/tests/py_services/test_generate_track_record_report.py`
  (test-style reference)

**Interfaces:**
- Produces: `load_orders_executed(path: Path) -> list[dict]`,
  `compute_decision_breakdown(orders: list[dict]) -> dict[str, int]`,
  `compute_gate_fail_rates(orders: list[dict]) -> dict[str, dict]`,
  `compute_overridden_registry(orders: list[dict]) -> list[dict]`,
  `build_report(orders_path: Path = ORDERS_EXECUTED_PATH) -> dict`. Task 2 (the `/weekly-review`
  doc wiring) only calls the script's CLI (`--json`), not these functions directly, so this is
  the complete public interface.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for execution_quality_scorecard.py — Phase 6 execution-quality groundwork."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from execution_quality_scorecard import (  # noqa: E402
    build_report,
    compute_decision_breakdown,
    compute_gate_fail_rates,
    compute_overridden_registry,
    load_orders_executed,
)


def _order(decision, gates, ticker="AAPL", side="BUY"):
    return {
        "timestamp": "2026-07-15T15:32:35.094016+00:00",
        "order": {"ticker": ticker, "side": side, "shares": 1.0, "price": 150.0},
        "decision": decision,
        "gate_result": {
            "passed": all(g["passed"] for g in gates),
            "gates": gates,
            "reasons": [g["reason"] for g in gates if not g["passed"]],
        },
        "trade_execution_result": None,
    }


class TestLoadOrdersExecuted:
    def test_missing_file_returns_empty_list(self, tmp_path):
        assert load_orders_executed(tmp_path / "nonexistent.jsonl") == []

    def test_loads_real_jsonl_records(self, tmp_path):
        path = tmp_path / "orders_executed.jsonl"
        rec = _order("BLOCKED", [{"name": "balance", "passed": False, "reason": "Insufficient cash"}])
        path.write_text(json.dumps(rec) + "\n")
        loaded = load_orders_executed(path)
        assert len(loaded) == 1
        assert loaded[0]["decision"] == "BLOCKED"


class TestComputeDecisionBreakdown:
    def test_counts_each_decision_type(self):
        orders = [
            _order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}]),
            _order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}]),
            _order("BLOCKED", [{"name": "balance", "passed": False, "reason": "no cash"}]),
            _order("OVERRIDDEN", [{"name": "mrc", "passed": False, "reason": "MRC over cap"}]),
        ]
        result = compute_decision_breakdown(orders)
        assert result == {"EXECUTED": 2, "BLOCKED": 1, "OVERRIDDEN": 1}

    def test_empty_input_yields_all_zero_counts(self):
        result = compute_decision_breakdown([])
        assert result == {"EXECUTED": 0, "BLOCKED": 0, "OVERRIDDEN": 0}


class TestComputeGateFailRates:
    def test_computes_fail_rate_per_gate(self):
        orders = [
            _order("EXECUTED", [
                {"name": "balance", "passed": True, "reason": "ok"},
                {"name": "mrc", "passed": True, "reason": "ok"},
            ]),
            _order("BLOCKED", [
                {"name": "balance", "passed": False, "reason": "no cash"},
                {"name": "mrc", "passed": True, "reason": "ok"},
            ]),
        ]
        result = compute_gate_fail_rates(orders)
        assert result["balance"] == {"failCount": 1, "totalSeen": 2, "failRate": 0.5}
        assert result["mrc"] == {"failCount": 0, "totalSeen": 2, "failRate": 0.0}

    def test_gate_never_seen_is_absent_not_zero(self):
        orders = [_order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}])]
        result = compute_gate_fail_rates(orders)
        assert "cluster_variance" not in result

    def test_empty_input_yields_empty_dict(self):
        assert compute_gate_fail_rates([]) == {}


class TestComputeOverriddenRegistry:
    def test_lists_only_overridden_orders_with_failed_gate_detail(self):
        orders = [
            _order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}]),
            _order("OVERRIDDEN", [
                {"name": "mrc", "passed": False, "reason": "MRC over cap"},
                {"name": "balance", "passed": True, "reason": "ok"},
            ], ticker="NVDA", side="BUY"),
        ]
        registry = compute_overridden_registry(orders)
        assert len(registry) == 1
        assert registry[0]["ticker"] == "NVDA"
        assert registry[0]["overriddenGates"] == ["mrc"]
        assert registry[0]["reasons"] == ["MRC over cap"]

    def test_no_overridden_orders_yields_empty_list(self):
        orders = [_order("EXECUTED", [{"name": "balance", "passed": True, "reason": "ok"}])]
        assert compute_overridden_registry(orders) == []


class TestBuildReport:
    def test_report_has_expected_shape(self, tmp_path):
        path = tmp_path / "orders_executed.jsonl"
        rec = _order("BLOCKED", [{"name": "balance", "passed": False, "reason": "no cash"}])
        path.write_text(json.dumps(rec) + "\n")

        report = build_report(path)
        assert report["totalOrdersLogged"] == 1
        assert report["decisionBreakdown"]["BLOCKED"] == 1
        assert "balance" in report["gateFailRates"]
        assert report["overriddenRegistry"] == []

    def test_report_on_missing_file_degrades_gracefully(self, tmp_path):
        report = build_report(tmp_path / "no_such_file.jsonl")
        assert report["totalOrdersLogged"] == 0
        assert report["decisionBreakdown"] == {"EXECUTED": 0, "BLOCKED": 0, "OVERRIDDEN": 0}
        assert report["gateFailRates"] == {}
        assert report["overriddenRegistry"] == []
```

Save this to `investment_screener/backend/tests/py_services/test_execution_quality_scorecard.py`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_execution_quality_scorecard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'execution_quality_scorecard'` (the
module doesn't exist yet).

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""
execution_quality_scorecard.py - Python utility script.

Purpose:
    Phase 6 execution-quality groundwork. Reads Phase 5E-8's
    orders_executed.jsonl audit trail (logged by order_risk_gates.py's
    log_order_execution(), never read by any script until now) and
    computes a decision breakdown, per-gate fail rate, and an
    overridden-order worklist. Deterministic — no ML, no return/P&L
    correlation (that needs price-history joining out of scope here).

Layer:
    Backend / Python Services

Usage:
    python3 execution_quality_scorecard.py [--json]

Key Functions (Index):
    - load_orders_executed()
    - compute_decision_breakdown()
    - compute_gate_fail_rates()
    - compute_overridden_registry()
    - build_report()
    - main()

Key Input Dependencies:
    - investment_screener/backend/data/orders_executed.jsonl (gitignored, may not exist yet)

Key Output Dependencies:
    None
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ORDERS_EXECUTED_PATH = DATA_DIR / "orders_executed.jsonl"

_DECISIONS = ("EXECUTED", "BLOCKED", "OVERRIDDEN")


def load_orders_executed(path: Path = ORDERS_EXECUTED_PATH) -> list[dict[str, Any]]:
    """Load orders_executed.jsonl. Missing file degrades to an empty list, never raises."""
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def compute_decision_breakdown(orders: list[dict[str, Any]]) -> dict[str, int]:
    """Count logged order attempts by decision (EXECUTED/BLOCKED/OVERRIDDEN)."""
    counts = {d: 0 for d in _DECISIONS}
    for order in orders:
        decision = order.get("decision")
        if decision in counts:
            counts[decision] += 1
    return counts


def compute_gate_fail_rates(orders: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-gate fail rate across every logged attempt that included that gate.

    A gate never seen in any record is absent from the result, not reported as 0% fail
    (0% fail and "never evaluated" are different facts).
    """
    seen: dict[str, dict[str, int]] = {}
    for order in orders:
        for gate in order.get("gate_result", {}).get("gates", []):
            name = gate["name"]
            bucket = seen.setdefault(name, {"failCount": 0, "totalSeen": 0})
            bucket["totalSeen"] += 1
            if not gate["passed"]:
                bucket["failCount"] += 1
    return {
        name: {**stats, "failRate": round(stats["failCount"] / stats["totalSeen"], 4)}
        for name, stats in seen.items()
    }


def compute_overridden_registry(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flat worklist of every OVERRIDDEN order: ticker, which gate(s) it overrode, reasons.

    Manual-review worklist, not an automated verdict — no outcome/return computation.
    """
    registry = []
    for order in orders:
        if order.get("decision") != "OVERRIDDEN":
            continue
        gates = order.get("gate_result", {}).get("gates", [])
        failed_gates = [g["name"] for g in gates if not g["passed"]]
        reasons = [g["reason"] for g in gates if not g["passed"]]
        registry.append({
            "ticker": order.get("order", {}).get("ticker"),
            "side": order.get("order", {}).get("side"),
            "timestamp": order.get("timestamp"),
            "overriddenGates": failed_gates,
            "reasons": reasons,
        })
    return registry


def build_report(orders_path: Path = ORDERS_EXECUTED_PATH) -> dict[str, Any]:
    """Build the full execution-quality scorecard dict."""
    orders = load_orders_executed(orders_path)
    return {
        "totalOrdersLogged": len(orders),
        "decisionBreakdown": compute_decision_breakdown(orders),
        "gateFailRates": compute_gate_fail_rates(orders),
        "overriddenRegistry": compute_overridden_registry(orders),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Phase 6 execution-quality scorecard")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"Execution quality — {report['totalOrdersLogged']} order attempt(s) logged")
    if report["totalOrdersLogged"] == 0:
        print("  No orders_executed.jsonl data yet — this is expected early on, not a bug.")
        return
    breakdown = report["decisionBreakdown"]
    print(f"  Decisions: {breakdown['EXECUTED']} executed / {breakdown['BLOCKED']} blocked / "
          f"{breakdown['OVERRIDDEN']} overridden")
    for gate, stats in report["gateFailRates"].items():
        print(f"  Gate {gate:<18} fail rate {stats['failRate']:.0%} "
              f"({stats['failCount']}/{stats['totalSeen']})")
    if report["overriddenRegistry"]:
        print("  Overridden orders (manual review worklist):")
        for entry in report["overriddenRegistry"]:
            print(f"    {entry['ticker']} {entry['side']} — overrode {entry['overriddenGates']}: "
                  f"{'; '.join(entry['reasons'])}")


if __name__ == "__main__":
    main()
```

Save this to `investment_screener/backend/py_services/execution_quality_scorecard.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_execution_quality_scorecard.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Manual smoke test against the real (gitignored) data file**

```bash
cd investment_screener/backend
python3 py_services/execution_quality_scorecard.py --json
```
Expected: runs without error against the real `data/orders_executed.jsonl` (currently 5 sandbox
BLOCKED entries), producing a real report — confirms the script works end-to-end, not just
against synthetic fixtures.

- [ ] **Step 6: Commit**

```bash
git add investment_screener/backend/py_services/execution_quality_scorecard.py \
        investment_screener/backend/tests/py_services/test_execution_quality_scorecard.py
git commit -m "feat: add execution quality scorecard (Phase 6 reward-modeling groundwork)"
```

---

### Task 2: Wire into `/weekly-review`

**Files:**
- Modify: `plugins/portfolio-advisor/agents/weekly-review-agent.md`

**Interfaces:**
- Consumes: Task 1's script via its `--json` CLI output only (no direct function import — the
  agent shells out, same as the existing track-record line).

- [ ] **Step 1: Add the new section immediately after Phase 1b**

In `plugins/portfolio-advisor/agents/weekly-review-agent.md`, after the existing Phase 1b block
(the `generate_track_record_report.py --json` section and its "sparse for a while" note), add:

```markdown
### Phase 1c: Execution Quality Scorecard (Phase 6 — additive, sparse initially)
Surface risk-gate audit-trail stats from live order attempts this week:
```bash
python3 investment_screener/backend/py_services/execution_quality_scorecard.py --json
```
Present the decision breakdown (executed/blocked/overridden) and per-gate fail rates alongside
the track-record hit-rate table. If any orders were `OVERRIDDEN`, list them as a manual-review
worklist — this is informational only, never a verdict on whether the override was correct (no
return/P&L computation happens here). **This will likely be empty or sparse for a while** — real
order flow through the risk gates needs to accumulate first. That's expected, not a bug.
```

- [ ] **Step 2: Verify the file still reads coherently**

Read the full `weekly-review-agent.md` file after the edit to confirm the new Phase 1c section
flows naturally between Phase 1b and Phase 2, with consistent heading level and tone.

- [ ] **Step 3: Commit and push**

```bash
git add plugins/portfolio-advisor/agents/weekly-review-agent.md
git commit -m "docs: wire execution quality scorecard into /weekly-review Phase 1c"
git push origin main
```
