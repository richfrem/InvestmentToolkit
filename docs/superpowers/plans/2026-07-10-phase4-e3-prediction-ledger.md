# Phase 4, Sub-Spec 1 — E3 Prediction Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an append-only prediction ledger that harvests graded claims (action ratings, DCF fair values, rebalance orders, thesis-breaker forecasts) from already-persisted artifacts, grades them against price performance once matured, and reports rolling hit rates — wired non-invasively into `/daily` and `/weekly-review`.

**Architecture:** Two append-only JSONL stores (`data/predictions.jsonl`, `data/predictions_graded.jsonl`), never rewritten in place. A harvester reads existing output artifacts (`projections/*.json`, `rebalance_plan.json`, `thesis_breaker_state.json`) — it never modifies the scripts that produce them. A grader computes one unified directional-return verdict per claim type. A report joins both files into rolling hit-rate stats.

**Tech Stack:** Python 3.13, `jsonschema` (already in `requirements.txt`), `pytest`, the existing `market_data.py` provider abstraction (Phase 1).

## Global Constraints

- Design doc: `docs/superpowers/specs/2026-07-10-phase4-e3-prediction-ledger-design.md` — read it before starting; this plan implements it verbatim.
- No silent schema breaks — every new record carries `"v": 1` from its first write.
- Reproducibility over cleverness — every graded number traces to a stored `basePrice`/`baseSpyPrice` plus a `market_data.get_prices()`/`get_quote()` call at grading time; nothing is estimated.
- Never mutate `projections/*.json`, `rebalance_plan.json`, `thesis_breaker_state.json`, or `target-portfolio.json` — this sub-spec only reads them.
- HITL is not applicable — this sub-spec has no order-touching code path.
- **Worktree isolation (mandatory, see `.agent/rules/worktree-subagent-isolation.md`):** this project has hit repeat worktree-leak incidents in Phase 2b, C2, and G2 — in every case a subagent's edit landed on the main checkout instead of the worktree despite an explicit `cd`/`pwd` instruction. `haiku`-tier dispatches have leaked twice; `sonnet`-tier dispatches have not leaked once. Every task dispatch below MUST: (1) state the exact worktree path as the first instruction, (2) have the subagent confirm `pwd && git branch --show-current` before its first edit, (3) use `sonnet` tier, not `haiku`. After every task, the controller (not the subagent) must run `git status --short` **in the main checkout** (not the worktree) to catch any stray leaked file before generating that task's review package.
- Worktree: `.worktrees/feature-fable5-phase4-e3-prediction-ledger`, branch `feature/fable5-phase4-e3-prediction-ledger`.

---

### Task 1: Prediction ledger core — schema, append/load, grade_claim()

**Files:**
- Create: `investment_screener/backend/py_services/prediction_ledger.py`
- Test: `investment_screener/backend/tests/py_services/test_prediction_ledger.py`

**Interfaces:**
- Produces: `make_prediction_id(ticker: str, claim_type: str, claim_date: str) -> str`, `append_prediction(record: dict, path: Path = PREDICTIONS_PATH) -> None`, `append_grade(record: dict, path: Path = GRADED_PATH) -> None`, `load_predictions(path: Path = PREDICTIONS_PATH) -> list[dict]`, `load_graded(path: Path = GRADED_PATH) -> list[dict]`, `latest_prediction_for(ticker: str, claim_type: str, predictions: list[dict]) -> dict | None`, `grade_claim(direction: str, relative_return: float, band: float = 0.02) -> str`, module constants `PREDICTIONS_PATH`, `GRADED_PATH`, `HORIZON_DAYS: dict[str, int]`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for prediction_ledger.py — E3 append-only prediction ledger core."""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from prediction_ledger import (  # noqa: E402
    append_grade,
    append_prediction,
    grade_claim,
    latest_prediction_for,
    load_graded,
    load_predictions,
    make_prediction_id,
)


class TestMakePredictionId:
    def test_format(self):
        assert make_prediction_id("CORZ", "action_rating", "2026-05-02") == \
            "CORZ:action_rating:2026-05-02"


class TestAppendAndLoadPredictions:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "predictions.jsonl"
        record = {"id": "AAPL:action_rating:2026-01-01", "ticker": "AAPL"}
        append_prediction(record, path)
        loaded = load_predictions(path)
        assert loaded == [record]

    def test_appends_without_truncating(self, tmp_path):
        path = tmp_path / "predictions.jsonl"
        append_prediction({"id": "A"}, path)
        append_prediction({"id": "B"}, path)
        loaded = load_predictions(path)
        assert [r["id"] for r in loaded] == ["A", "B"]

    def test_load_missing_file_returns_empty_list(self, tmp_path):
        assert load_predictions(tmp_path / "does_not_exist.jsonl") == []


class TestAppendAndLoadGraded:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "graded.jsonl"
        record = {"predictionId": "AAPL:action_rating:2026-01-01", "verdict": "correct"}
        append_grade(record, path)
        assert load_graded(path) == [record]

    def test_load_missing_file_returns_empty_list(self, tmp_path):
        assert load_graded(tmp_path / "does_not_exist.jsonl") == []


class TestLatestPredictionFor:
    def test_returns_most_recent_match(self):
        predictions = [
            {"ticker": "CORZ", "type": "action_rating", "date": "2026-01-01", "claim": {"action": "ACCUMULATE"}},
            {"ticker": "CORZ", "type": "dcf_fair_value", "date": "2026-01-01", "claim": {"fairValue": 10}},
            {"ticker": "CORZ", "type": "action_rating", "date": "2026-03-01", "claim": {"action": "TRIM"}},
        ]
        result = latest_prediction_for("CORZ", "action_rating", predictions)
        assert result["date"] == "2026-03-01"

    def test_returns_none_when_no_match(self):
        assert latest_prediction_for("NVDA", "action_rating", []) is None


class TestGradeClaim:
    def test_bullish_correct(self):
        assert grade_claim("bullish", 0.05) == "correct"

    def test_bullish_incorrect(self):
        assert grade_claim("bullish", -0.05) == "incorrect"

    def test_bullish_inconclusive_within_band(self):
        assert grade_claim("bullish", 0.01) == "inconclusive"

    def test_bearish_correct(self):
        assert grade_claim("bearish", -0.05) == "correct"

    def test_bearish_incorrect(self):
        assert grade_claim("bearish", 0.05) == "incorrect"

    def test_bearish_inconclusive_within_band(self):
        assert grade_claim("bearish", -0.01) == "inconclusive"

    def test_boundary_exactly_at_band_is_inconclusive(self):
        assert grade_claim("bullish", 0.02) == "inconclusive"
        assert grade_claim("bearish", -0.02) == "inconclusive"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_prediction_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prediction_ledger'`

- [ ] **Step 3: Write the implementation**

```python
"""Prediction ledger — E3 append-only claim/grade store and grading primitive.

Two append-only JSONL files, never rewritten in place:
  - data/predictions.jsonl        one record per harvested claim
  - data/predictions_graded.jsonl one record per graded outcome, referencing
                                   a prediction's id

See docs/superpowers/specs/2026-07-10-phase4-e3-prediction-ledger-design.md
for the full schema and grading rationale.

Usage:
    python3 prediction_ledger.py --validate
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
PREDICTIONS_PATH = DATA_DIR / "predictions.jsonl"
GRADED_PATH = DATA_DIR / "predictions_graded.jsonl"
SCHEMA_PATH = REPO_ROOT / "schemas/prediction.schema.json"

HORIZON_DAYS: dict[str, int] = {
    "action_rating": 90,
    "dcf_fair_value": 180,
    "rebalance_order": 90,
    "breaker_forecast": 90,
    "earnings_expectation": 90,
}

INCONCLUSIVE_BAND = 0.02


def make_prediction_id(ticker: str, claim_type: str, claim_date: str) -> str:
    """Build the stable, reconstructible id for one prediction record."""
    return f"{ticker}:{claim_type}:{claim_date}"


def _append_jsonl(record: dict[str, Any], path: Path) -> None:
    """Append one JSON record as a line, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load every record from a JSONL file, or [] if it doesn't exist."""
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_prediction(record: dict[str, Any], path: Path = PREDICTIONS_PATH) -> None:
    """Append one prediction record to predictions.jsonl."""
    _append_jsonl(record, path)


def append_grade(record: dict[str, Any], path: Path = GRADED_PATH) -> None:
    """Append one grade record to predictions_graded.jsonl."""
    _append_jsonl(record, path)


def load_predictions(path: Path = PREDICTIONS_PATH) -> list[dict[str, Any]]:
    """Load every prediction record on disk."""
    return _load_jsonl(path)


def load_graded(path: Path = GRADED_PATH) -> list[dict[str, Any]]:
    """Load every grade record on disk."""
    return _load_jsonl(path)


def latest_prediction_for(
    ticker: str, claim_type: str, predictions: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Return the most recently harvested prediction matching ticker+type, or None.

    Args:
        ticker: Ticker symbol.
        claim_type: One of HORIZON_DAYS's keys.
        predictions: Prediction records, in the order they were harvested
            (oldest first) — the same order load_predictions() returns.

    Returns:
        The last matching record, or None if no match exists.
    """
    matches = [p for p in predictions if p["ticker"] == ticker and p["type"] == claim_type]
    return matches[-1] if matches else None


def grade_claim(direction: str, relative_return: float, band: float = INCONCLUSIVE_BAND) -> str:
    """Grade a claim's outcome from its stated direction and realized relative return.

    Args:
        direction: "bullish" or "bearish".
        relative_return: Ticker return minus SPY return over the claim's horizon.
        band: Absolute relative-return threshold below which the outcome is
            "inconclusive" rather than decisively correct/incorrect.

    Returns:
        "correct", "incorrect", or "inconclusive".
    """
    if abs(relative_return) <= band:
        return "inconclusive"
    if direction == "bullish":
        return "correct" if relative_return > band else "incorrect"
    return "correct" if relative_return < -band else "incorrect"


def _validate_all() -> int:
    """Schema-validate every record in both JSONL files. Returns exit code.

    Passes PREDICTIONS_PATH/GRADED_PATH explicitly (not relying on
    load_predictions()/load_graded()'s own default parameter values) so that
    tests can monkeypatch the module-level globals and have this function
    pick up the new value — default parameter values are bound once at def
    time, not at call time, so relying on them here would silently ignore
    a monkeypatched global.
    """
    import jsonschema

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    errors = 0
    for record in load_predictions(PREDICTIONS_PATH):
        try:
            jsonschema.validate(record, schema["definitions"]["prediction"])
        except jsonschema.ValidationError as exc:
            print(f"INVALID prediction {record.get('id')}: {exc.message}")
            errors += 1
    for record in load_graded(GRADED_PATH):
        try:
            jsonschema.validate(record, schema["definitions"]["grade"])
        except jsonschema.ValidationError as exc:
            print(f"INVALID grade {record.get('predictionId')}: {exc.message}")
            errors += 1

    if errors:
        print(f"{errors} invalid record(s).")
        return 1
    print("All prediction/grade records valid.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Prediction ledger utilities")
    parser.add_argument("--validate", action="store_true", help="Schema-validate the ledger")
    args = parser.parse_args()

    if args.validate:
        raise SystemExit(_validate_all())
    parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_prediction_ledger.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/prediction_ledger.py investment_screener/backend/tests/py_services/test_prediction_ledger.py
git commit -m "feat: add prediction_ledger.py core — append-only JSONL store + grade_claim()"
```

---

### Task 2: Harvester — action_rating + dcf_fair_value claims from projections

**Files:**
- Create: `investment_screener/backend/py_services/harvest_predictions.py`
- Test: `investment_screener/backend/tests/py_services/test_harvest_predictions.py`

**Interfaces:**
- Consumes (Task 1): `make_prediction_id`, `append_prediction`, `latest_prediction_for`, `load_predictions`, `HORIZON_DAYS`, `PREDICTIONS_PATH`.
- Produces: `build_action_rating_claim(ticker: str, projection: dict) -> dict | None`, `build_dcf_fair_value_claim(ticker: str, projection: dict) -> dict | None`, `_append_if_new(claim: dict, existing: list[dict], predictions_path: Path) -> list[dict]` (shared helper, reused by Task 3), `harvest_action_and_dcf_claims(projections_dir: Path = PROJECTIONS_DIR, predictions_path: Path = PREDICTIONS_PATH) -> list[dict]`, module constant `PROJECTIONS_DIR`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for harvest_predictions.py — E3 claim harvesting from projections/*.json."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from harvest_predictions import (  # noqa: E402
    _append_if_new,
    build_action_rating_claim,
    build_dcf_fair_value_claim,
    harvest_action_and_dcf_claims,
)


class TestBuildActionRatingClaim:
    def test_accumulate_is_bullish(self):
        projection = {"aiThesis": {"action": "ACCUMULATE", "analyzedAt": "2026-05-02T15:35:09Z"}}
        claim = build_action_rating_claim("CORZ", projection)
        assert claim == {
            "ticker": "CORZ", "type": "action_rating", "date": "2026-05-02",
            "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
        }

    def test_trim_is_bearish(self):
        projection = {"aiThesis": {"action": "TRIM", "analyzedAt": "2026-05-02T15:35:09Z"}}
        claim = build_action_rating_claim("CORZ", projection)
        assert claim["direction"] == "bearish"

    def test_maintain_is_not_harvested(self):
        projection = {"aiThesis": {"action": "MAINTAIN", "analyzedAt": "2026-05-02T15:35:09Z"}}
        assert build_action_rating_claim("CORZ", projection) is None

    def test_watchlist_is_not_harvested(self):
        projection = {"aiThesis": {"action": "WATCHLIST", "analyzedAt": "2026-05-02T15:35:09Z"}}
        assert build_action_rating_claim("CORZ", projection) is None

    def test_missing_action_returns_none(self):
        assert build_action_rating_claim("CORZ", {"aiThesis": {}}) is None


class TestBuildDcfFairValueClaim:
    def test_uses_analytics_log_dcf_when_present(self):
        projection = {
            "aiThesis": {"analyzedAt": "2026-05-02T15:35:09Z"},
            "analyticsLog": {"dcf": {"weightedFairValue": 16.23, "upsidePct": -73}},
        }
        claim = build_dcf_fair_value_claim("CRSP", projection)
        assert claim["claim"] == {"fairValue": 16.23, "upsidePct": -73, "source": "analyticsLog.dcf"}
        assert claim["direction"] == "bearish"

    def test_falls_back_to_ai_thesis_when_no_analytics_dcf(self):
        projection = {
            "aiThesis": {"fairValue": 347.78, "analyzedAt": "2026-05-02T15:35:09Z"},
            "analyticsLog": {"dcf": None},
            "snapshot": {"price": 329.50},
        }
        claim = build_dcf_fair_value_claim("COHR", projection)
        assert claim["claim"]["fairValue"] == 347.78
        assert claim["claim"]["source"] == "aiThesis"
        assert claim["direction"] == "bullish"
        assert claim["claim"]["upsidePct"] == pytest.approx(5.54, abs=0.01)

    def test_missing_fair_value_and_no_snapshot_price_returns_none(self):
        projection = {"aiThesis": {"analyzedAt": "2026-05-02T15:35:09Z"}, "analyticsLog": {}}
        assert build_dcf_fair_value_claim("XYZ", projection) is None

    def test_missing_analyzed_at_returns_none(self):
        projection = {
            "aiThesis": {"fairValue": 100.0},
            "analyticsLog": {"dcf": {"weightedFairValue": 100.0, "upsidePct": 10}},
        }
        assert build_dcf_fair_value_claim("XYZ", projection) is None


class TestAppendIfNew:
    def _claim(self, date="2026-05-02"):
        return {
            "ticker": "CORZ", "type": "action_rating", "date": date,
            "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
        }

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_appends_new_claim(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        result = _append_if_new(self._claim(), [], path)
        assert len(result) == 1
        assert result[0]["basePrice"] == 5.32
        assert result[0]["baseSpyPrice"] == 612.40
        assert result[0]["v"] == 1

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_skips_unchanged_claim(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        existing = _append_if_new(self._claim(), [], path)
        result = _append_if_new(self._claim(date="2026-06-01"), existing, path)
        assert result == []

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_logs_new_claim_when_value_changed(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        existing = _append_if_new(self._claim(), [], path)
        changed = {**self._claim(date="2026-06-01"), "claim": {"action": "TRIM"}, "direction": "bearish"}
        result = _append_if_new(changed, existing, path)
        assert len(result) == 1
        assert result[0]["claim"] == {"action": "TRIM"}

    @patch("harvest_predictions._fetch_base_prices", return_value=None)
    def test_skips_when_price_unavailable(self, _mock_prices, tmp_path):
        path = tmp_path / "predictions.jsonl"
        result = _append_if_new(self._claim(), [], path)
        assert result == []


class TestHarvestActionAndDcfClaims:
    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_harvests_both_claim_types_from_one_projection(self, _mock_prices, tmp_path):
        projections_dir = tmp_path / "projections"
        projections_dir.mkdir()
        (projections_dir / "CORZ.json").write_text(json.dumps([{
            "aiThesis": {"action": "TRIM", "fairValue": 10.64,
                          "analyzedAt": "2026-05-02T15:35:09Z"},
            "analyticsLog": {"dcf": None},
            "snapshot": {"price": 15.0},
        }]))
        predictions_path = tmp_path / "predictions.jsonl"
        result = harvest_action_and_dcf_claims(projections_dir, predictions_path)
        types = {r["type"] for r in result}
        assert types == {"action_rating", "dcf_fair_value"}

    def test_handles_empty_projections_dir(self, tmp_path):
        projections_dir = tmp_path / "projections"
        projections_dir.mkdir()
        result = harvest_action_and_dcf_claims(projections_dir, tmp_path / "predictions.jsonl")
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_harvest_predictions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'harvest_predictions'`

- [ ] **Step 3: Write the implementation**

```python
"""Harvest predictions — E3 claim harvester, reads persisted artifacts only.

Never modifies projections/*.json, rebalance_plan.json, or
thesis_breaker_state.json — purely additive, reads them and appends new
claims to data/predictions.jsonl. Dedup is done by comparing against the
most recently harvested claim of the same (ticker, type) already on the
ledger — no separate state file.

Usage:
    python3 harvest_predictions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prediction_ledger import (  # noqa: E402
    HORIZON_DAYS,
    PREDICTIONS_PATH,
    append_prediction,
    latest_prediction_for,
    load_predictions,
    make_prediction_id,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "investment_screener/backend/data"
PROJECTIONS_DIR = DATA_DIR / "projections"

_BULLISH_ACTIONS = {"INITIATE", "ACCUMULATE"}
_BEARISH_ACTIONS = {"TRIM", "EXIT"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_claim(claim: dict[str, Any]) -> str:
    """Stable hash of a claim payload for traceability (not used for dedup)."""
    canonical = json.dumps(claim, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _load_projection(path: Path) -> dict[str, Any] | None:
    """Load a projection file, unwrapping its list-wrapper if present."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data[0] if data else None
    return data


def build_action_rating_claim(ticker: str, projection: dict[str, Any]) -> dict[str, Any] | None:
    """Extract an action_rating claim from a projection, or None if not gradable.

    MAINTAIN/WATCHLIST carry no directional prediction and are not harvested.
    """
    ai_thesis = projection.get("aiThesis", {}) or {}
    action = ai_thesis.get("action")
    if action not in (_BULLISH_ACTIONS | _BEARISH_ACTIONS):
        return None
    date_str = (ai_thesis.get("analyzedAt") or "")[:10]
    if not date_str:
        return None
    direction = "bullish" if action in _BULLISH_ACTIONS else "bearish"
    return {
        "ticker": ticker, "type": "action_rating", "date": date_str,
        "claim": {"action": action}, "direction": direction,
    }


def build_dcf_fair_value_claim(ticker: str, projection: dict[str, Any]) -> dict[str, Any] | None:
    """Extract a dcf_fair_value claim, preferring analyticsLog.dcf over aiThesis.

    Falls back to aiThesis.fairValue + snapshot.price (deriving upsidePct)
    when analyticsLog.dcf is absent — true for 78/80 current projections,
    since most predate the Phase 2a valuation-committee gate.
    """
    ai_thesis = projection.get("aiThesis", {}) or {}
    dcf = (projection.get("analyticsLog") or {}).get("dcf")
    date_str = (ai_thesis.get("analyzedAt") or "")[:10]
    if not date_str:
        return None

    if dcf and dcf.get("weightedFairValue") is not None and dcf.get("upsidePct") is not None:
        fair_value = dcf["weightedFairValue"]
        upside_pct = dcf["upsidePct"]
        source = "analyticsLog.dcf"
    else:
        fair_value = ai_thesis.get("fairValue")
        current_price = (projection.get("snapshot") or {}).get("price")
        if fair_value is None or not current_price:
            return None
        upside_pct = round((fair_value - current_price) / current_price * 100, 2)
        source = "aiThesis"

    direction = "bullish" if upside_pct > 0 else "bearish"
    return {
        "ticker": ticker, "type": "dcf_fair_value", "date": date_str,
        "claim": {"fairValue": fair_value, "upsidePct": upside_pct, "source": source},
        "direction": direction,
    }


def _price_on_or_after(rows: list[dict[str, Any]], target_date: str) -> float | None:
    """First close price on or after target_date; rows must be date-ascending."""
    for row in rows:
        if row["date"] >= target_date:
            return row["close"]
    return None


def _fetch_base_prices(ticker: str, claim_date: str) -> tuple[float, float] | None:
    """Fetch (ticker close, SPY close) on/after claim_date via market_data.get_prices()."""
    from market_data import get_prices
    result = get_prices([ticker, "SPY"], period="2y", interval="1d")
    t_rows = result.get(ticker, {}).get("data", [])
    spy_rows = result.get("SPY", {}).get("data", [])
    t_price = _price_on_or_after(t_rows, claim_date)
    spy_price = _price_on_or_after(spy_rows, claim_date)
    if t_price is None or spy_price is None:
        return None
    return t_price, spy_price


def _append_if_new(
    claim: dict[str, Any], existing: list[dict[str, Any]], predictions_path: Path
) -> list[dict[str, Any]]:
    """Append claim as a new prediction record unless it's an unchanged dup.

    Dedup rule: skip if the most recently logged claim of this (ticker, type)
    has an identical claim payload. Defends against id collision (same
    ticker+type+date logged twice with a different value) by skipping with a
    stderr warning rather than silently overwriting.

    Returns:
        A list containing the new record, or [] if nothing was appended.
    """
    new_id = make_prediction_id(claim["ticker"], claim["type"], claim["date"])
    prior = latest_prediction_for(claim["ticker"], claim["type"], existing)
    if prior is not None and prior["claim"] == claim["claim"]:
        return []
    if any(r["id"] == new_id for r in existing):
        print(f"  WARNING: id collision, skipping: {new_id}", file=sys.stderr)
        return []

    prices = _fetch_base_prices(claim["ticker"], claim["date"])
    if prices is None:
        return []
    base_price, base_spy_price = prices

    record = {
        "v": 1,
        "id": new_id,
        "date": claim["date"],
        "ticker": claim["ticker"],
        "type": claim["type"],
        "claim": claim["claim"],
        "direction": claim["direction"],
        "horizonDays": HORIZON_DAYS[claim["type"]],
        "basePrice": base_price,
        "baseSpyPrice": base_spy_price,
        "confidence": None,
        "inputsHash": _hash_claim(claim["claim"]),
        "harvestedAt": _now_iso(),
    }
    append_prediction(record, predictions_path)
    existing.append(record)
    return [record]


def harvest_action_and_dcf_claims(
    projections_dir: Path = PROJECTIONS_DIR,
    predictions_path: Path = PREDICTIONS_PATH,
) -> list[dict[str, Any]]:
    """Harvest action_rating and dcf_fair_value claims from every projection file.

    Args:
        projections_dir: Directory of per-ticker projection JSON files.
        predictions_path: Ledger path to read existing state from and append to.

    Returns:
        Every newly appended prediction record this run.
    """
    existing = load_predictions(predictions_path)
    new_records: list[dict[str, Any]] = []
    for proj_file in sorted(projections_dir.glob("*.json")):
        ticker = proj_file.stem
        projection = _load_projection(proj_file)
        if projection is None:
            continue
        for builder in (build_action_rating_claim, build_dcf_fair_value_claim):
            claim = builder(ticker, projection)
            if claim is None:
                continue
            new_records += _append_if_new(claim, existing, predictions_path)
    return new_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest graded claims into the prediction ledger")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be harvested, don't write")
    args = parser.parse_args()

    if args.dry_run:
        existing = load_predictions(PREDICTIONS_PATH)
        print(f"{len(existing)} existing predictions on ledger. Dry-run: no writes performed.")
        return

    new_records = harvest_action_and_dcf_claims()
    print(f"Harvested {len(new_records)} new claim(s).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_harvest_predictions.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/harvest_predictions.py investment_screener/backend/tests/py_services/test_harvest_predictions.py
git commit -m "feat: harvest action_rating + dcf_fair_value claims from projections"
```

---

### Task 3: Harvester extension — rebalance_order + breaker_forecast claims

**Files:**
- Modify: `investment_screener/backend/py_services/harvest_predictions.py`
- Modify: `investment_screener/backend/tests/py_services/test_harvest_predictions.py`

**Interfaces:**
- Consumes (Task 2): `_append_if_new`, `HORIZON_DAYS`, `PREDICTIONS_PATH`.
- Produces: `build_rebalance_order_claims(rebalance_plan: dict, claim_date: str) -> list[dict]`, `build_breaker_forecast_claims(breaker_state: dict, target_data: dict, claim_date: str) -> list[dict]`, `harvest_rebalance_and_breaker_claims(rebalance_plan_path: Path = REBALANCE_PLAN_PATH, thesis_breaker_state_path: Path = THESIS_BREAKER_STATE_PATH, target_portfolio_path: Path = TARGET_PATH, predictions_path: Path = PREDICTIONS_PATH) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

Append to `investment_screener/backend/tests/py_services/test_harvest_predictions.py`:

```python
from harvest_predictions import (  # noqa: E402
    build_breaker_forecast_claims,
    build_rebalance_order_claims,
    harvest_rebalance_and_breaker_claims,
)


class TestBuildRebalanceOrderClaims:
    def test_buy_is_bullish(self):
        plan = {"orders": [{"ticker": "CORZ", "action": "buy", "riskGateWarnings": [], "breakerWarnings": []}]}
        claims = build_rebalance_order_claims(plan, "2026-07-10")
        assert claims == [{
            "ticker": "CORZ", "type": "rebalance_order", "date": "2026-07-10",
            "claim": {"action": "buy", "gateWarningsPresent": False}, "direction": "bullish",
        }]

    def test_sell_is_bearish(self):
        plan = {"orders": [{"ticker": "PSU-U.TO", "action": "sell", "riskGateWarnings": [], "breakerWarnings": []}]}
        claims = build_rebalance_order_claims(plan, "2026-07-10")
        assert claims[0]["direction"] == "bearish"

    def test_gate_warnings_present_flag(self):
        plan = {"orders": [{"ticker": "NBIS", "action": "buy", "riskGateWarnings": ["cluster cap"], "breakerWarnings": []}]}
        claims = build_rebalance_order_claims(plan, "2026-07-10")
        assert claims[0]["claim"]["gateWarningsPresent"] is True

    def test_empty_orders_returns_empty_list(self):
        assert build_rebalance_order_claims({"orders": []}, "2026-07-10") == []

    def test_missing_ticker_or_action_skipped(self):
        plan = {"orders": [{"ticker": None, "action": "buy"}, {"ticker": "X", "action": "hold"}]}
        assert build_rebalance_order_claims(plan, "2026-07-10") == []


class TestBuildBreakerForecastClaims:
    def test_triggered_breaker_is_harvested_as_bearish(self):
        breaker_state = {"holdings": {"NBIS": {"rsi_breach": {"status": "TRIGGERED"}}}}
        target_data = {"holdings": [{"ticker": "NBIS", "thesisBreakers": [
            {"id": "rsi_breach", "metric": "rsi"}
        ]}]}
        claims = build_breaker_forecast_claims(breaker_state, target_data, "2026-07-10")
        assert claims == [{
            "ticker": "NBIS", "type": "breaker_forecast", "date": "2026-07-10",
            "claim": {"breakerId": "rsi_breach", "metric": "rsi", "status": "TRIGGERED"},
            "direction": "bearish",
        }]

    def test_non_triggered_breaker_is_not_harvested(self):
        breaker_state = {"holdings": {"NBIS": {"rsi_breach": {"status": "OK"}}}}
        target_data = {"holdings": [{"ticker": "NBIS", "thesisBreakers": [{"id": "rsi_breach", "metric": "rsi"}]}]}
        assert build_breaker_forecast_claims(breaker_state, target_data, "2026-07-10") == []

    def test_empty_holdings_returns_empty_list(self):
        assert build_breaker_forecast_claims({"holdings": {}}, {"holdings": []}, "2026-07-10") == []


class TestHarvestRebalanceAndBreakerClaims:
    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_missing_rebalance_plan_file_is_not_an_error(self, _mock_prices, tmp_path):
        result = harvest_rebalance_and_breaker_claims(
            rebalance_plan_path=tmp_path / "no_such_plan.json",
            thesis_breaker_state_path=tmp_path / "no_such_state.json",
            target_portfolio_path=tmp_path / "no_such_target.json",
            predictions_path=tmp_path / "predictions.jsonl",
        )
        assert result == []

    @patch("harvest_predictions._fetch_base_prices", return_value=(5.32, 612.40))
    def test_harvests_from_both_artifacts_when_present(self, _mock_prices, tmp_path):
        plan_path = tmp_path / "rebalance_plan.json"
        plan_path.write_text(json.dumps({
            "generatedAt": "2026-07-10T14:00:00Z",
            "orders": [{"ticker": "CORZ", "action": "buy", "riskGateWarnings": [], "breakerWarnings": []}],
        }))
        state_path = tmp_path / "thesis_breaker_state.json"
        state_path.write_text(json.dumps({
            "generatedAt": "2026-07-10T14:00:00Z",
            "holdings": {"NBIS": {"rsi_breach": {"status": "TRIGGERED"}}},
        }))
        target_path = tmp_path / "target-portfolio.json"
        target_path.write_text(json.dumps({
            "holdings": [{"ticker": "NBIS", "thesisBreakers": [{"id": "rsi_breach", "metric": "rsi"}]}]
        }))
        result = harvest_rebalance_and_breaker_claims(
            rebalance_plan_path=plan_path,
            thesis_breaker_state_path=state_path,
            target_portfolio_path=target_path,
            predictions_path=tmp_path / "predictions.jsonl",
        )
        types = {r["type"] for r in result}
        assert types == {"rebalance_order", "breaker_forecast"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_harvest_predictions.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_rebalance_order_claims'`

- [ ] **Step 3: Write the implementation**

Add to `investment_screener/backend/py_services/harvest_predictions.py` (after `build_dcf_fair_value_claim`, before `_price_on_or_after`):

```python
REBALANCE_PLAN_PATH = DATA_DIR / "rebalance_plan.json"
THESIS_BREAKER_STATE_PATH = DATA_DIR / "thesis_breaker_state.json"
TARGET_PATH = DATA_DIR / "theses/target-portfolio.json"


def build_rebalance_order_claims(rebalance_plan: dict[str, Any], claim_date: str) -> list[dict[str, Any]]:
    """Extract rebalance_order claims from a rebalance_plan.json dict.

    buy -> bullish, sell -> bearish. gateWarningsPresent is recorded but not
    itself gradable — it's traceability only, matching the design's
    read-only posture toward risk_officer/thesis-breaker warn flags.
    """
    claims = []
    for order in rebalance_plan.get("orders", []):
        ticker = order.get("ticker")
        action = order.get("action")
        if not ticker or action not in ("buy", "sell"):
            continue
        direction = "bullish" if action == "buy" else "bearish"
        gate_warnings_present = bool(order.get("riskGateWarnings") or order.get("breakerWarnings"))
        claims.append({
            "ticker": ticker, "type": "rebalance_order", "date": claim_date,
            "claim": {"action": action, "gateWarningsPresent": gate_warnings_present},
            "direction": direction,
        })
    return claims


def build_breaker_forecast_claims(
    breaker_state: dict[str, Any], target_data: dict[str, Any], claim_date: str
) -> list[dict[str, Any]]:
    """Extract breaker_forecast claims — only TRIGGERED breakers are claims.

    A breaker at OK status is the absence of a prediction, not one.
    """
    definitions = {
        (h["ticker"], b["id"]): b
        for h in target_data.get("holdings", [])
        for b in h.get("thesisBreakers", [])
    }
    claims = []
    for ticker, breakers in (breaker_state.get("holdings") or {}).items():
        for breaker_id, entry in breakers.items():
            if entry.get("status") != "TRIGGERED":
                continue
            definition = definitions.get((ticker, breaker_id), {})
            claims.append({
                "ticker": ticker, "type": "breaker_forecast", "date": claim_date,
                "claim": {"breakerId": breaker_id, "metric": definition.get("metric"), "status": "TRIGGERED"},
                "direction": "bearish",
            })
    return claims


def harvest_rebalance_and_breaker_claims(
    rebalance_plan_path: Path = REBALANCE_PLAN_PATH,
    thesis_breaker_state_path: Path = THESIS_BREAKER_STATE_PATH,
    target_portfolio_path: Path = TARGET_PATH,
    predictions_path: Path = PREDICTIONS_PATH,
) -> list[dict[str, Any]]:
    """Harvest rebalance_order and breaker_forecast claims, if their artifacts exist.

    Neither artifact existing yet (rebalance_plan.json is only written after
    a /rebalance run; thesis_breaker_state.json may have zero holdings
    populated) is a normal, expected state — not an error.
    """
    existing = load_predictions(predictions_path)
    new_records: list[dict[str, Any]] = []

    if rebalance_plan_path.exists():
        with open(rebalance_plan_path) as f:
            rebalance_plan = json.load(f)
        claim_date = (rebalance_plan.get("generatedAt") or "")[:10]
        if claim_date:
            for claim in build_rebalance_order_claims(rebalance_plan, claim_date):
                new_records += _append_if_new(claim, existing, predictions_path)

    if thesis_breaker_state_path.exists() and target_portfolio_path.exists():
        with open(thesis_breaker_state_path) as f:
            breaker_state = json.load(f)
        with open(target_portfolio_path) as f:
            target_data = json.load(f)
        claim_date = (breaker_state.get("generatedAt") or "")[:10]
        if claim_date:
            for claim in build_breaker_forecast_claims(breaker_state, target_data, claim_date):
                new_records += _append_if_new(claim, existing, predictions_path)

    return new_records
```

Update `main()` to also call the new harvester:

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest graded claims into the prediction ledger")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be harvested, don't write")
    args = parser.parse_args()

    if args.dry_run:
        existing = load_predictions(PREDICTIONS_PATH)
        print(f"{len(existing)} existing predictions on ledger. Dry-run: no writes performed.")
        return

    new_records = harvest_action_and_dcf_claims()
    new_records += harvest_rebalance_and_breaker_claims()
    print(f"Harvested {len(new_records)} new claim(s).")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_harvest_predictions.py -v`
Expected: PASS (20 tests total)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/harvest_predictions.py investment_screener/backend/tests/py_services/test_harvest_predictions.py
git commit -m "feat: harvest rebalance_order + breaker_forecast claims"
```

---

### Task 4: Grading job

**Files:**
- Create: `investment_screener/backend/py_services/grade_predictions.py`
- Test: `investment_screener/backend/tests/py_services/test_grade_predictions.py`

**Interfaces:**
- Consumes (Task 1): `grade_claim`, `append_grade`, `load_predictions`, `load_graded`, `PREDICTIONS_PATH`, `GRADED_PATH`.
- Produces: `find_maturable_predictions(predictions: list[dict], graded_ids: set[str], today: date) -> list[dict]`, `grade_prediction(prediction: dict, ticker_price_now: float, spy_price_now: float, graded_at: str) -> dict`, `run_grading(predictions_path: Path = PREDICTIONS_PATH, graded_path: Path = GRADED_PATH) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for grade_predictions.py — E3 weekly grading job."""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from grade_predictions import (  # noqa: E402
    find_maturable_predictions,
    grade_prediction,
    run_grading,
)


def _prediction(**overrides):
    base = {
        "id": "CORZ:action_rating:2026-01-01", "date": "2026-01-01", "ticker": "CORZ",
        "type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
        "horizonDays": 90, "basePrice": 5.0, "baseSpyPrice": 500.0,
    }
    base.update(overrides)
    return base


class TestFindMaturablePredictions:
    def test_matured_ungraded_is_included(self):
        predictions = [_prediction(date="2026-01-01", horizonDays=90)]
        result = find_maturable_predictions(predictions, graded_ids=set(), today=date(2026, 4, 2))
        assert len(result) == 1

    def test_not_yet_matured_is_excluded(self):
        predictions = [_prediction(date="2026-01-01", horizonDays=90)]
        result = find_maturable_predictions(predictions, graded_ids=set(), today=date(2026, 2, 1))
        assert result == []

    def test_already_graded_is_excluded(self):
        predictions = [_prediction(id="CORZ:action_rating:2026-01-01", date="2026-01-01", horizonDays=90)]
        result = find_maturable_predictions(
            predictions, graded_ids={"CORZ:action_rating:2026-01-01"}, today=date(2026, 4, 2),
        )
        assert result == []


class TestGradePrediction:
    def test_bullish_correct_outperformance(self):
        prediction = _prediction(basePrice=5.0, baseSpyPrice=500.0, direction="bullish")
        grade = grade_prediction(prediction, ticker_price_now=6.0, spy_price_now=505.0, graded_at="2026-04-02")
        assert grade["verdict"] == "correct"
        assert grade["predictionId"] == prediction["id"]
        assert grade["v"] == 1

    def test_bearish_correct_underperformance(self):
        prediction = _prediction(basePrice=5.0, baseSpyPrice=500.0, direction="bearish")
        grade = grade_prediction(prediction, ticker_price_now=4.0, spy_price_now=505.0, graded_at="2026-04-02")
        assert grade["verdict"] == "correct"

    def test_returns_are_rounded_and_present(self):
        prediction = _prediction(basePrice=5.0, baseSpyPrice=500.0, direction="bullish")
        grade = grade_prediction(prediction, ticker_price_now=6.0, spy_price_now=505.0, graded_at="2026-04-02")
        assert "tickerReturn" in grade and "spyReturn" in grade and "relativeReturn" in grade


class TestRunGrading:
    @patch("grade_predictions._fetch_current_prices", return_value=(6.0, 505.0))
    @patch("grade_predictions.date")
    def test_grades_matured_predictions_and_appends(self, mock_date, _mock_prices, tmp_path):
        mock_date.today.return_value = date(2026, 4, 2)
        mock_date.fromisoformat = date.fromisoformat
        predictions_path = tmp_path / "predictions.jsonl"
        predictions_path.write_text(
            '{"id": "CORZ:action_rating:2026-01-01", "date": "2026-01-01", "ticker": "CORZ", '
            '"type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish", '
            '"horizonDays": 90, "basePrice": 5.0, "baseSpyPrice": 500.0}\n'
        )
        graded_path = tmp_path / "graded.jsonl"
        result = run_grading(predictions_path, graded_path)
        assert len(result) == 1
        assert result[0]["predictionId"] == "CORZ:action_rating:2026-01-01"

    @patch("grade_predictions._fetch_current_prices", return_value=(6.0, 505.0))
    @patch("grade_predictions.date")
    def test_does_not_regrade_same_prediction_twice(self, mock_date, _mock_prices, tmp_path):
        mock_date.today.return_value = date(2026, 4, 2)
        mock_date.fromisoformat = date.fromisoformat
        predictions_path = tmp_path / "predictions.jsonl"
        predictions_path.write_text(
            '{"id": "CORZ:action_rating:2026-01-01", "date": "2026-01-01", "ticker": "CORZ", '
            '"type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish", '
            '"horizonDays": 90, "basePrice": 5.0, "baseSpyPrice": 500.0}\n'
        )
        graded_path = tmp_path / "graded.jsonl"
        run_grading(predictions_path, graded_path)
        second_run = run_grading(predictions_path, graded_path)
        assert second_run == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_grade_predictions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'grade_predictions'`

- [ ] **Step 3: Write the implementation**

```python
"""Grade predictions — E3 weekly grading job.

Finds every matured, ungraded prediction and appends a grade record based on
realized ticker return vs. SPY return since the claim's basePrice. Never
mutates predictions.jsonl — grading only appends to predictions_graded.jsonl.

Usage:
    python3 grade_predictions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from prediction_ledger import (  # noqa: E402
    GRADED_PATH,
    PREDICTIONS_PATH,
    append_grade,
    grade_claim,
    load_graded,
    load_predictions,
)


def find_maturable_predictions(
    predictions: list[dict[str, Any]], graded_ids: set[str], today: date
) -> list[dict[str, Any]]:
    """Return predictions whose horizon has elapsed and that aren't graded yet."""
    result = []
    for p in predictions:
        if p["id"] in graded_ids:
            continue
        claim_date = date.fromisoformat(p["date"])
        matures_on = claim_date + timedelta(days=p["horizonDays"])
        if today >= matures_on:
            result.append(p)
    return result


def grade_prediction(
    prediction: dict[str, Any], ticker_price_now: float, spy_price_now: float, graded_at: str
) -> dict[str, Any]:
    """Compute a grade record for one matured prediction from current prices."""
    ticker_return = (ticker_price_now - prediction["basePrice"]) / prediction["basePrice"]
    spy_return = (spy_price_now - prediction["baseSpyPrice"]) / prediction["baseSpyPrice"]
    relative_return = ticker_return - spy_return
    verdict = grade_claim(prediction["direction"], relative_return)
    return {
        "v": 1,
        "predictionId": prediction["id"],
        "gradedAt": graded_at,
        "tickerReturn": round(ticker_return, 4),
        "spyReturn": round(spy_return, 4),
        "relativeReturn": round(relative_return, 4),
        "verdict": verdict,
    }


def _fetch_current_prices(ticker: str) -> tuple[float, float] | None:
    """Fetch (ticker, SPY) current quote prices via market_data.get_quote()."""
    from market_data import get_quote
    result = get_quote([ticker, "SPY"])
    t = result.get(ticker, {}).get("price")
    s = result.get("SPY", {}).get("price")
    if t is None or s is None:
        return None
    return t, s


def run_grading(
    predictions_path: Path = PREDICTIONS_PATH, graded_path: Path = GRADED_PATH
) -> list[dict[str, Any]]:
    """Find matured, ungraded predictions and append a grade record for each."""
    predictions = load_predictions(predictions_path)
    graded_ids = {g["predictionId"] for g in load_graded(graded_path)}
    today = date.today()

    new_grades: list[dict[str, Any]] = []
    for prediction in find_maturable_predictions(predictions, graded_ids, today):
        prices = _fetch_current_prices(prediction["ticker"])
        if prices is None:
            continue
        ticker_price_now, spy_price_now = prices
        grade = grade_prediction(prediction, ticker_price_now, spy_price_now, today.isoformat())
        append_grade(grade, graded_path)
        new_grades.append(grade)
    return new_grades


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade matured predictions")
    parser.add_argument("--dry-run", action="store_true", help="Report matured count, don't write")
    args = parser.parse_args()

    if args.dry_run:
        predictions = load_predictions(PREDICTIONS_PATH)
        graded_ids = {g["predictionId"] for g in load_graded(GRADED_PATH)}
        matured = find_maturable_predictions(predictions, graded_ids, date.today())
        print(f"{len(matured)} prediction(s) ready to grade. Dry-run: no writes performed.")
        return

    new_grades = run_grading()
    print(f"Graded {len(new_grades)} prediction(s).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_grade_predictions.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/grade_predictions.py investment_screener/backend/tests/py_services/test_grade_predictions.py
git commit -m "feat: add grade_predictions.py — weekly matured-claim grading job"
```

---

### Task 5: Track record report generator

**Files:**
- Create: `investment_screener/backend/py_services/generate_track_record_report.py`
- Test: `investment_screener/backend/tests/py_services/test_generate_track_record_report.py`

**Interfaces:**
- Consumes (Task 1): `load_predictions`, `load_graded`, `PREDICTIONS_PATH`, `GRADED_PATH`.
- Produces: `compute_hit_rates(predictions: list[dict], graded: list[dict]) -> dict`, `build_report(predictions_path: Path = PREDICTIONS_PATH, graded_path: Path = GRADED_PATH) -> dict`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for generate_track_record_report.py — E3 rolling hit-rate report."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(PY_SERVICES))

from generate_track_record_report import build_report, compute_hit_rates  # noqa: E402


class TestComputeHitRates:
    def test_hit_rate_excludes_inconclusive_from_denominator(self):
        predictions = [
            {"id": "A", "type": "action_rating"},
            {"id": "B", "type": "action_rating"},
            {"id": "C", "type": "action_rating"},
        ]
        graded = [
            {"predictionId": "A", "verdict": "correct"},
            {"predictionId": "B", "verdict": "incorrect"},
            {"predictionId": "C", "verdict": "inconclusive"},
        ]
        result = compute_hit_rates(predictions, graded)
        assert result["action_rating"]["hitRate"] == 0.5
        assert result["action_rating"]["gradedTotal"] == 3

    def test_ungraded_predictions_are_excluded(self):
        predictions = [{"id": "A", "type": "action_rating"}, {"id": "B", "type": "action_rating"}]
        graded = [{"predictionId": "A", "verdict": "correct"}]
        result = compute_hit_rates(predictions, graded)
        assert result["action_rating"]["gradedTotal"] == 1

    def test_no_decisive_verdicts_yields_null_hit_rate(self):
        predictions = [{"id": "A", "type": "dcf_fair_value"}]
        graded = [{"predictionId": "A", "verdict": "inconclusive"}]
        result = compute_hit_rates(predictions, graded)
        assert result["dcf_fair_value"]["hitRate"] is None

    def test_empty_input_yields_empty_report(self):
        assert compute_hit_rates([], []) == {}


class TestBuildReport:
    def test_report_has_expected_shape(self, tmp_path):
        predictions_path = tmp_path / "predictions.jsonl"
        predictions_path.write_text(json.dumps({"id": "A", "type": "action_rating"}) + "\n")
        graded_path = tmp_path / "graded.jsonl"
        graded_path.write_text(json.dumps({"predictionId": "A", "verdict": "correct"}) + "\n")

        report = build_report(predictions_path, graded_path)
        assert report["totalPredictions"] == 1
        assert report["totalGraded"] == 1
        assert report["totalUngraded"] == 0
        assert report["byClaimType"]["action_rating"]["correct"] == 1

    def test_report_on_empty_ledger(self, tmp_path):
        report = build_report(tmp_path / "no_predictions.jsonl", tmp_path / "no_graded.jsonl")
        assert report["totalPredictions"] == 0
        assert report["byClaimType"] == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_generate_track_record_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'generate_track_record_report'`

- [ ] **Step 3: Write the implementation**

```python
"""Generate track record report — E3 rolling hit-rate stats.

Joins predictions.jsonl and predictions_graded.jsonl into per-claim-type hit
rates. This is the "graded-predictions section" /weekly-review surfaces —
expected to be sparse for a while after this ships, which is fine.

Usage:
    python3 generate_track_record_report.py [--json]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prediction_ledger import GRADED_PATH, PREDICTIONS_PATH, load_graded, load_predictions

_VERDICTS = ("correct", "incorrect", "inconclusive")


def compute_hit_rates(predictions: list[dict[str, Any]], graded: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-claim-type hit rate from graded predictions only.

    hitRate excludes "inconclusive" verdicts from its denominator — a claim
    type with only inconclusive grades so far has a null (not 0.0) hit rate.
    """
    graded_by_id = {g["predictionId"]: g for g in graded}
    predictions_by_id = {p["id"]: p for p in predictions}

    by_type: dict[str, dict[str, int]] = {}
    for prediction_id, grade in graded_by_id.items():
        prediction = predictions_by_id.get(prediction_id)
        if prediction is None:
            continue
        claim_type = prediction["type"]
        bucket = by_type.setdefault(claim_type, {v: 0 for v in _VERDICTS})
        bucket[grade["verdict"]] += 1

    report: dict[str, Any] = {}
    for claim_type, counts in by_type.items():
        graded_total = sum(counts.values())
        decisive = counts["correct"] + counts["incorrect"]
        hit_rate = round(counts["correct"] / decisive, 4) if decisive else None
        report[claim_type] = {**counts, "gradedTotal": graded_total, "hitRate": hit_rate}
    return report


def build_report(
    predictions_path: Path = PREDICTIONS_PATH, graded_path: Path = GRADED_PATH
) -> dict[str, Any]:
    """Build the full track-record report dict."""
    predictions = load_predictions(predictions_path)
    graded = load_graded(graded_path)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "totalPredictions": len(predictions),
        "totalGraded": len(graded),
        "totalUngraded": len(predictions) - len(graded),
        "byClaimType": compute_hit_rates(predictions, graded),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the E3 track-record report")
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"Track record — {report['totalGraded']}/{report['totalPredictions']} graded "
          f"({report['totalUngraded']} pending maturity)")
    if not report["byClaimType"]:
        print("  No graded predictions yet.")
        return
    for claim_type, stats in report["byClaimType"].items():
        rate = f"{stats['hitRate']:.0%}" if stats["hitRate"] is not None else "n/a"
        print(f"  {claim_type:<20} hit rate {rate:>5}  "
              f"({stats['correct']} correct / {stats['incorrect']} incorrect / {stats['inconclusive']} inconclusive)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_generate_track_record_report.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add investment_screener/backend/py_services/generate_track_record_report.py investment_screener/backend/tests/py_services/test_generate_track_record_report.py
git commit -m "feat: add generate_track_record_report.py — rolling hit-rate stats"
```

---

### Task 6: Prediction schema + ledger --validate wiring

**Files:**
- Create: `schemas/prediction.schema.json`
- Test: `investment_screener/backend/tests/py_services/test_prediction_ledger_validate.py`

**Interfaces:**
- Consumes (Task 1): `prediction_ledger.py`'s `SCHEMA_PATH` constant, `load_predictions`, `load_graded`.
- Produces: the schema file itself, consumed by `prediction_ledger.py`'s existing `_validate_all()` (already written in Task 1, referencing `SCHEMA_PATH`).

- [ ] **Step 1: Write the failing test**

```python
"""Tests for prediction_ledger.py's --validate mode (schema wiring)."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"


def _run_validate(predictions_content: str, graded_content: str, tmp_path, monkeypatch) -> subprocess.CompletedProcess:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(predictions_content)
    graded_path = tmp_path / "graded.jsonl"
    graded_path.write_text(graded_content)

    script = f'''
import sys
from pathlib import Path
sys.path.insert(0, "{PY_SERVICES}")
import prediction_ledger
prediction_ledger.PREDICTIONS_PATH = Path("{predictions_path}")
prediction_ledger.GRADED_PATH = Path("{graded_path}")
prediction_ledger.main()
'''
    return subprocess.run(
        [sys.executable, "-c", script, "--validate"], capture_output=True, text=True,
    )


class TestValidate:
    def test_valid_records_pass(self, tmp_path, monkeypatch):
        valid_prediction = json.dumps({
            "v": 1, "id": "CORZ:action_rating:2026-01-01", "date": "2026-01-01", "ticker": "CORZ",
            "type": "action_rating", "claim": {"action": "ACCUMULATE"}, "direction": "bullish",
            "horizonDays": 90, "basePrice": 5.0, "baseSpyPrice": 500.0, "confidence": None,
            "inputsHash": "abc123", "harvestedAt": "2026-01-01T00:00:00Z",
        })
        valid_grade = json.dumps({
            "v": 1, "predictionId": "CORZ:action_rating:2026-01-01", "gradedAt": "2026-04-02",
            "tickerReturn": 0.1, "spyReturn": 0.02, "relativeReturn": 0.08, "verdict": "correct",
        })
        result = _run_validate(valid_prediction + "\n", valid_grade + "\n", tmp_path, monkeypatch)
        assert result.returncode == 0
        assert "All prediction/grade records valid" in result.stdout

    def test_invalid_prediction_fails(self, tmp_path, monkeypatch):
        invalid_prediction = json.dumps({"id": "missing-required-fields"})
        result = _run_validate(invalid_prediction + "\n", "", tmp_path, monkeypatch)
        assert result.returncode == 1
        assert "INVALID prediction" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_prediction_ledger_validate.py -v`
Expected: FAIL with `FileNotFoundError` (schemas/prediction.schema.json doesn't exist yet) surfacing as a non-zero, non-matching returncode, or the subprocess erroring before printing the expected string.

- [ ] **Step 3: Write the schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Prediction",
  "description": "E3 prediction ledger records — see docs/superpowers/specs/2026-07-10-phase4-e3-prediction-ledger-design.md",
  "definitions": {
    "prediction": {
      "type": "object",
      "required": [
        "v", "id", "date", "ticker", "type", "claim", "direction",
        "horizonDays", "basePrice", "baseSpyPrice", "inputsHash", "harvestedAt"
      ],
      "properties": {
        "v": {"type": "integer", "const": 1},
        "id": {"type": "string"},
        "date": {"type": "string"},
        "ticker": {"type": "string"},
        "type": {
          "type": "string",
          "enum": ["action_rating", "dcf_fair_value", "rebalance_order", "breaker_forecast", "earnings_expectation"]
        },
        "claim": {"type": "object"},
        "direction": {"type": "string", "enum": ["bullish", "bearish"]},
        "horizonDays": {"type": "integer"},
        "basePrice": {"type": "number"},
        "baseSpyPrice": {"type": "number"},
        "confidence": {"type": ["number", "null"]},
        "inputsHash": {"type": "string"},
        "harvestedAt": {"type": "string"}
      }
    },
    "grade": {
      "type": "object",
      "required": ["v", "predictionId", "gradedAt", "tickerReturn", "spyReturn", "relativeReturn", "verdict"],
      "properties": {
        "v": {"type": "integer", "const": 1},
        "predictionId": {"type": "string"},
        "gradedAt": {"type": "string"},
        "tickerReturn": {"type": "number"},
        "spyReturn": {"type": "number"},
        "relativeReturn": {"type": "number"},
        "verdict": {"type": "string", "enum": ["correct", "incorrect", "inconclusive"]}
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_prediction_ledger_validate.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add schemas/prediction.schema.json investment_screener/backend/tests/py_services/test_prediction_ledger_validate.py
git commit -m "feat: add schemas/prediction.schema.json + validate the --validate CLI mode"
```

---

### Task 7: `/daily` integration — non-blocking harvest step

**Files:**
- Modify: `plugins/portfolio-advisor/scripts/daily_brief.py`
- Create: `investment_screener/backend/tests/py_services/test_daily_brief_prediction_harvest.py`

**Interfaces:**
- Consumes (Tasks 2-3): `harvest_predictions.harvest_action_and_dcf_claims`, `harvest_predictions.harvest_rebalance_and_breaker_claims`.
- Produces: a new `_harvest_predictions_step() -> int | None` function in `daily_brief.py`; `run()`'s brief dict gains a new `"predictions_harvested": int | None` key.

**Design note:** `daily_brief.py`'s other dependencies (`compute_risk_snapshot`, `compute_market_regime`, etc.) are imported *locally inside* `run()`, not as module-level attributes of `daily_brief` — so they can't be mocked via `patch.object(daily_brief, "compute_risk_snapshot", ...)`, and this codebase's existing test file (`test_daily_brief_thesis_breakers.py`) deliberately tests `render()` in isolation rather than mocking `run()` end-to-end. Follow that same convention here: extract the new step into its own small function and unit-test that directly, rather than exercising the full `run()` pipeline.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for daily_brief.py's E3 prediction-harvest integration."""
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[4]
PY_SERVICES = REPO_ROOT / "investment_screener/backend/py_services"
SCRIPTS_DIR = REPO_ROOT / "plugins/portfolio-advisor/scripts"
sys.path.insert(0, str(PY_SERVICES))
sys.path.insert(0, str(SCRIPTS_DIR))

import daily_brief  # noqa: E402


class TestHarvestPredictionsStep:
    @patch("harvest_predictions.harvest_rebalance_and_breaker_claims", return_value=[])
    @patch("harvest_predictions.harvest_action_and_dcf_claims", return_value=[{"id": "A"}, {"id": "B"}])
    def test_returns_total_harvested_count(self, _mock_action_dcf, _mock_rebalance_breaker):
        result = daily_brief._harvest_predictions_step()
        assert result == 2

    @patch("harvest_predictions.harvest_action_and_dcf_claims", side_effect=RuntimeError("boom"))
    def test_degrades_to_none_on_failure(self, _mock_action_dcf):
        result = daily_brief._harvest_predictions_step()
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_daily_brief_prediction_harvest.py -v`
Expected: FAIL with `AttributeError: module 'daily_brief' has no attribute '_harvest_predictions_step'`

- [ ] **Step 3: Write the implementation**

Add to `plugins/portfolio-advisor/scripts/daily_brief.py`, as a new module-level function (place it near the other helpers in the "Core pipeline" section, just before `def run(`):

```python
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
```

In `run()`, add a new pipeline step after the existing "5b. Thesis breaker evaluation" block (after the `except Exception as exc:` block ending around what is currently line 277), before "## 6. Deltas vs yesterday":

```python
    # ── 5c. Prediction ledger harvest (E3 — additive, non-blocking) ──────────
    print("▶ Prediction harvest...", file=sys.stderr)
    predictions_harvested = _harvest_predictions_step()
```

Add `"predictions_harvested": predictions_harvested,` to the `brief` dict literal (alongside the existing `"thesis_breakers_triggered": triggered_breakers,` entry).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_daily_brief_prediction_harvest.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full existing daily_brief test suite to confirm no regression**

Run: `cd investment_screener/backend && python3 -m pytest tests/py_services/test_daily_brief_thesis_breakers.py -v`
Expected: PASS (all existing tests still pass — the new step is additive only)

- [ ] **Step 6: Commit**

```bash
git add plugins/portfolio-advisor/scripts/daily_brief.py investment_screener/backend/tests/py_services/test_daily_brief_prediction_harvest.py
git commit -m "feat: wire prediction harvest into /daily as a non-blocking step"
```

---

### Task 8: `/weekly-review` integration — grading + track record section

**Files:**
- Modify: `plugins/portfolio-advisor/agents/weekly-review-agent.md`

**Interfaces:**
- Consumes (Tasks 4-5): `grade_predictions.py`, `generate_track_record_report.py` (both invoked as CLIs, no Python interface needed — this is a prose/agent-instruction file, not code).

This task has no unit test (it's a markdown agent-instruction file, same as every other Fable5 sub-spec's agent-wiring task — G2's `risk-officer-agent.md`/`red-team-agent.md` wiring was likewise prose-only). Verification is a manual dry-run of the two CLI commands referenced.

- [ ] **Step 1: Add a new Phase 1b section**

In `plugins/portfolio-advisor/agents/weekly-review-agent.md`, insert after the existing "### Phase 1: Range-Based Drift & Performance Audit" section (after its bullet list, before "### Phase 2: Weekly Catalyst Sweep"):

```markdown
### Phase 1b: Track Record Grading (E3 — additive, sparse initially)
Grade any predictions that matured this week and refresh the rolling hit-rate report:
```bash
python3 investment_screener/backend/py_services/grade_predictions.py
python3 investment_screener/backend/py_services/generate_track_record_report.py --json
```
Present the hit-rate table (per claim type: correct / incorrect / inconclusive / hit rate) alongside the drift audit. **This will be sparse or empty for a while** — claims need 90-180 days to mature before they're gradable, and harvesting only started once E3 shipped. That's expected, not a bug; don't treat an empty report as a failure.
```

- [ ] **Step 2: Manually verify both CLI commands run clean**

Run:
```bash
cd investment_screener/backend
python3 py_services/grade_predictions.py --dry-run
python3 py_services/generate_track_record_report.py --json
```
Expected: both exit 0. The report will show `"totalPredictions": 0` (or a small number) and an empty `"byClaimType"` on a fresh ledger — this is the expected, documented sparse state, not an error.

- [ ] **Step 3: Commit**

```bash
git add plugins/portfolio-advisor/agents/weekly-review-agent.md
git commit -m "feat: wire E3 grading + track-record report into /weekly-review Phase 1b"
```

---

## Final whole-branch review

After all 8 tasks are committed on the worktree branch, run the full test suite to confirm no regressions before merge:

```bash
cd investment_screener/backend
python3 -m pytest tests/py_services/ -v
```

Expected: all tests pass, including every pre-existing test (443+ from the last recorded full-suite count, plus this sub-spec's ~62 new tests). Then proceed to the standard whole-branch review (opus) → merge to local `main` → push `main` directly to `origin/main`, per the corrected git policy in `start_here.md`.
