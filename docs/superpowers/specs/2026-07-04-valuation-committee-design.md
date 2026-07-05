# Design Spec: Valuation Committee (`reverse_dcf.py`, `wacc.py`, `dcf_sensitivity.py`, `comps_valuation.py`)

**Date:** 2026-07-04
**Status:** [DRAFT]
**Topic:** Phase 2a of the Fable5 Elevation Guide — multiple independent valuation lenses per ticker, with disagreement surfaced instead of averaged away. Backend-only; frontend heatmap explicitly deferred to a later, separately-scoped pass. Phase 1 (`market_data.py` data layer) is shipped and merged to `origin/main`; this phase builds on it.

## 1. Problem Statement

Today every ticker gets exactly one valuation number: a single DCF-weighted fair value from `dcf_scenarios.py`, using a flat 10% discount rate regardless of company risk profile, with no cross-check against what the market is actually pricing in or against peer multiples. `aiThesis.action` is then set by agent judgment alone, with no enforced consistency check across signals.

This is a single point of failure: if the DCF's growth/margin/PE assumptions are wrong, nothing catches it, because nothing else is being asked. The elevation guide's premise is that **disagreement between independent lenses is itself information** ("Market is pricing ~X% CAGR; your base case is Y%" or "38% chance this is overvalued on your own assumptions" are more honest than a single weighted FV) — and today the codebase has no mechanism to produce or enforce that disagreement signal.

## 2. Proposed Architecture

```
fetch_financials.py (existing, market_data.py-backed)
        │
        ▼
   wacc.py ──────────────────► per-company discount rate (replaces flat 10% default)
        │                       risk-free (10Y via market_data.get_prices), beta (local OLS
        │                       vs SPY), equity risk premium (4.5% default), after-tax cost
        │                       of debt. Capped/floored [7%, 14%] with a warning flag outside.
        ▼
dcf_scenarios.py (existing, +--wacc-file, --discount-rate kept for reproducibility)
        │
        │  weighted fair value, per-scenario PVs (unchanged math)
        │
        ├──► reverse_dcf.py ────────► bisection-solve implied 5yr revenue CAGR from current
        │                              price; verdict vs base/bull case
        │
        ├──► dcf_sensitivity.py ────► 2D grid (growth ±5pp × exit PE ±4 turns) fair-value
        │                              matrix + Monte Carlo (triangular dist. from existing
        │                              bear/base/bull) → P10/P50/P90, P(fairValue < price)
        │
        └──► comps_valuation.py ────► peer-median EV/Sales implied price range
                                       (EV/EBITDA deferred, no EBITDA source today),
                                       reading a per-ticker `peers: []` list
        │
        ▼
validate_projection.py (extended: check_accumulate_gate())
        │  blocks aiThesis.action = ACCUMULATE unless >=2 of 3 lenses agree
        │  (DCF upside, comps upside, impliedGrowth < baseCase growth);
        │  flags >25% cross-lens spread as a required disagreement note
        ▼
projections/{TICKER}.json
    .analyticsLog.wacc
    .analyticsLog.reverseDcf
    .analyticsLog.sensitivity
    .analyticsLog.monteCarlo
    .analyticsLog.comps
```

All four new scripts are independent, single-purpose CLI tools consumable standalone or chained by the `/evaluate-stock` skill — none of them fetch data inline; all consume `market_data.py` or `dcf_scenarios.py` output.

## 3. Components

- **`market_data.py` waterfall extension (prerequisite, built first)** — adds `totalDebt`, `cashAndEquivalents`, `interestExpense` to `get_fundamentals()`'s per-metric dict, sourced from yfinance `.info` only (`totalDebt`, `totalCash`, `interestExpense` keys) for this pass — no EDGAR tag mapping yet, following the same "yfinance-only, deliberate boundary" precedent already set by `operatingIncome`. Both `wacc.py` and `comps_valuation.py` depend on this. **Not delegated** — small, but it's a shared seam both downstream scripts build on, so the primary implementer locks its contract and tests first, same as `market_data.py`'s original interface in Phase 1.
- **`wacc.py`** — Inputs: risk-free rate from `market_data.get_prices(["^TNX"], period="5d")` (latest close /10), levered beta from local OLS regression of ticker vs SPY log returns (`market_data.get_prices` for both, 2yr daily), equity risk premium (default 4.5%, `--erp` override), after-tax cost of debt (`interest_expense / total_debt * (1 - tax_rate)`). **Prerequisite data-layer gap:** `market_data.get_fundamentals()` today only returns `revenue`/`netIncome`/`operatingIncome` — no debt, cash, or interest expense. This phase adds `totalDebt`, `cashAndEquivalents`, `interestExpense` to its waterfall, sourced yfinance-`.info`-only for this pass (a deliberate scope boundary, same pattern as the existing EDGAR-only `operatingIncome` field — EDGAR tag-mapping for these is deferred, not silently faked). Emits full decomposition (each input value + its source) so the agent can explain the number, not just consume it. Cap/floor [7%, 14%] — outside range emits a `"betaWarning"` flag rather than silently clamping without explanation (pre-revenue names produce garbage betas per the guide). **Delegation candidate** — self-contained, fixture-testable (frozen SPY/ticker return series); the `market_data.py` waterfall extension is a small, isolated addition reviewed by the primary implementer before `wacc.py` is built on top of it.
- **`reverse_dcf.py`** — Inverts `compute_scenario()`: given price, shares, margin, exit PE, quality multiplier, discount rate, solve via bisection for the growth rate that reproduces that price as `presentValue`. Output: `impliedGrowth`, `impliedGrowthVsGuidance` (vs company's own guided growth if available), `impliedGrowthVsBaseCase` (vs the `base` scenario's growthRate), verdict enum `PRICING_IN_MORE_THAN_BULL | BETWEEN_BASE_AND_BULL | BETWEEN_BEAR_AND_BASE | BELOW_BEAR`. **Delegation candidate** — pure math, no I/O beyond reading one projection file.
- **`dcf_sensitivity.py`** — Grid mode: fair value at each (growthRate ± 5pp step, exitPE ± 4 turns step) combination around the `base` scenario, holding other params fixed → JSON matrix. Monte Carlo mode: N samples (default 5000) from triangular distributions with (bear, base, bull) as (min, mode, max) for growth, margin, and exitPE independently; recompute `compute_scenario`-equivalent PV per sample → P10/P50/P90 fair value, `P(fairValue < currentPrice)`. **Delegation candidate** — pure math over existing scenario params, fixture-testable with a fixed RNG seed.
- **`comps_valuation.py`** — Reads `peers: []` from the target projection (new field). `projections/{TICKER}.json` is a list of versioned entries (existing format — see `portfolio_action.py._load_ai_upside` for the established "latest AI_AGENT entry, else `[0]`" read pattern this script reuses); for each peer, reads its latest entry's `snapshot` (`price`, `shares`, `revenue`) plus `market_data.get_fundamentals()` for `totalDebt`/`cashAndEquivalents` (same waterfall extension `wacc.py` needs — built once, shared by both). EV is computed on the fly (`price * shares + debt - cash`). EBITDA is **not** reliably available anywhere in the current data layer, so this phase computes **EV/Sales only** — EV/EBITDA comps is deferred until an EBITDA source exists (out of scope for 2a; note this narrowing in the ADR). Returns a clean `{"status": "insufficient_peer_data"}` (not an error) when `peers` is empty or fewer than 2 peers have usable data. **Delegation candidate** — pure computation over existing projection files, no network.
- **`validate_projection.py` gate extension** — New `check_accumulate_gate(projection: dict) -> GateResult` reading `analyticsLog.{wacc,reverseDcf,comps}` plus the existing DCF `upsidePct`. Lens agreement definition: (1) DCF upside > 15% (existing BUY threshold), (2) comps implied price > current price, (3) `impliedGrowth < base-case growth` (market pricing in less than what we believe — margin of safety signal). `aiThesis.action == "ACCUMULATE"` requires >=2 of 3 true; violation is a validation **error** (same severity tier/blocking behavior as existing required-field checks in `validate_projection.py`), not a warning. Cross-lens spread >25% (max vs min of the three implied prices/upsides) always appends a `warnings` entry requiring a disagreement note in `rationale`, independent of the gate outcome. **Not delegated** — this is the seam that changes existing gating behavior; owned by the primary implementer along with its full test matrix.
- **`stock_valuation` skill instructions** (`plugins/stock-valuation/skills/stock_valuation/` docs) — updated to call `wacc.py`/`reverse_dcf.py`/`dcf_sensitivity.py`/`comps_valuation.py` in sequence before writing a projection, and to run the new gate check before finalizing `aiThesis.action`.
- **`docs/architecture/ADR-valuation-committee.md`** — records the 2-of-3 gate rule, why 4 lenses replace 1, and the "surface disagreement, never average" principle, consistent with the existing confluence-gate/standing-decision philosophy already in this codebase.

## 4. Data Contract (locked before any delegated work starts)

```python
# wacc.py
def compute_wacc(ticker: str, financials: dict, erp: float = 0.045) -> dict:
    """Returns {
        "wacc": float,               # capped/floored [0.07, 0.14]
        "riskFreeRate": float, "beta": float, "erp": float,
        "costOfDebt": float, "capApplied": bool, "floorApplied": bool,
        "betaWarning": str | None,   # e.g. "beta 2.8 outside typical range, pre-revenue name?"
        "source": {"riskFree": "market_data:^TNX", "beta": "local_ols_2y", ...},
    }"""

# reverse_dcf.py
def solve_implied_growth(price: float, base_shares: float, discount_rate: float,
                          horizon: int, margin: float, exit_pe: float,
                          quality_multiplier: float, base_revenue: float) -> dict:
    """Returns {
        "impliedGrowth": float, "impliedGrowthVsBaseCase": float,
        "impliedGrowthVsGuidance": float | None,
        "verdict": "PRICING_IN_MORE_THAN_BULL" | "BETWEEN_BASE_AND_BULL"
                 | "BETWEEN_BEAR_AND_BASE" | "BELOW_BEAR",
        "converged": bool, "iterations": int,
    }"""

# dcf_sensitivity.py
def sensitivity_grid(base_scenario: dict, discount_rate: float, horizon: int) -> dict:
    """Returns {"grid": [{"growthRate": .., "exitPE": .., "fairValue": ..}, ...]}"""

def monte_carlo(bear: dict, base: dict, bull: dict, discount_rate: float,
                 horizon: int, n: int = 5000, seed: int | None = None) -> dict:
    """Returns {"p10": float, "p50": float, "p90": float,
                "probabilityOvervalued": float, "n": int, "seed": int}"""

# comps_valuation.py
def comps_implied_range(target_metrics: dict, peer_tickers: list[str],
                         projections_dir: str) -> dict:
    """Returns {"status": "ok", "impliedPriceRange": {"low": .., "high": ..},
                 "peersUsed": [...], "evSalesMedian": ..}
             or {"status": "insufficient_peer_data", "peersUsed": [...]}"""

# validate_projection.py addition
def check_accumulate_gate(projection: dict) -> dict:
    """Returns {"gatePassed": bool, "lensesAgreeing": int,
                 "lensResults": {"dcf": bool, "comps": bool, "impliedGrowth": bool},
                 "spreadPct": float, "disagreementNoteRequired": bool}"""
```

## 5. Data Flow — one ticker through `/evaluate-stock`

1. `fetch_financials.py` (existing) produces normalized metrics via `market_data.py`.
2. `wacc.py` computes the discount rate from those metrics + market data; result feeds `dcf_scenarios.py --wacc-file`.
3. `dcf_scenarios.py` runs unchanged scenario math with the computed rate → weighted fair value, per-scenario PVs.
4. `reverse_dcf.py` takes that same scenario shape + current price → implied growth.
5. `dcf_sensitivity.py` takes the same bear/base/bull params → grid + Monte Carlo.
6. `comps_valuation.py` takes the ticker's `peers` list (seeded for current holdings, see §8) → implied comps range.
7. All four outputs are merged into `analyticsLog` and the projection is passed to `validate_projection.py`, which runs `check_accumulate_gate()` before the projection is considered final/persistable.
8. Agent (stock_valuation skill) surfaces the 4-lens panel and any disagreement note in its conversational output and in the persisted `rationale`.

## 6. Error Handling

- `wacc.py`: insufficient price history for beta (new listing) → falls back to sector-average beta constant with a flag, never a silent 0 or NaN beta.
- `reverse_dcf.py`: bisection non-convergence (pathological params) → `"converged": false`, agent must not present a non-converged implied growth as fact.
- `comps_valuation.py`: <2 usable peers → clean `insufficient_peer_data` status, never a fabricated range from 0-1 data points.
- Gate: a projection that fails the gate is a **validation error** (blocks persistence via the existing `validate_projection.py` exit-code convention), not a soft warning — matches this repo's existing "surface the conflict, don't auto-resolve" pattern (confluence gate, standing decisions).

## 7. Testing (TDD — failing test first per script)

- `market_data.py` extension: fixture test that `totalDebt`/`cashAndEquivalents`/`interestExpense` are sourced and tagged `"source": "yfinance"`; missing-field fixture confirms omission (never zeroed), consistent with existing `get_fundamentals()` tests.
- `wacc.py`: boundary tests at exactly 7%/14% cap-floor; a fixture pre-revenue ticker triggers `betaWarning`; source decomposition present on every call.
- `reverse_dcf.py`: **round-trip property test** — feed `dcf_scenarios.py`'s own `presentValue`/params back into `solve_implied_growth`, recover the original `growthRate` within 0.1pp. This is the regression trap for the forward model per the guide.
- `dcf_sensitivity.py`: grid dimensions/bounds match spec exactly; Monte Carlo with fixed seed is deterministic across runs; P10 <= P50 <= P90 invariant.
- `comps_valuation.py`: golden fixture with 3 synthetic peers → known implied range; 0-peer and 1-peer fixtures both return `insufficient_peer_data`.
- Gate: full 2^3 truth-table test over lens agreement combinations, confirming ACCUMULATE is blocked exactly when <2 lenses agree and allowed when >=2 agree; spread-threshold boundary test at exactly 25%.
- Migration: run `check_accumulate_gate()` against all existing `projections/*.json` with a currently-ACCUMULATE action — document (not silently fix) any that would now fail the gate, as a follow-up list for the agent to re-review.

## 8. Peer Seeding (comps data)

`peers: []` is a new optional field on `projections/{TICKER}.json`. As part of this phase's acceptance criteria, peer lists are curated (agent-assisted, one-time) for the ~13 current portfolio holdings only. Tickers without a seeded list simply get `insufficient_peer_data` from `comps_valuation.py` until curated — this is expected, not a bug, and new tickers get their `peers` list added the next time they go through `/evaluate-stock`.

## 9. Delegation Plan

Primary implementer (no delegation, owns the seam): `market_data.py` waterfall extension + its tests (locked contract before delegated work starts), `validate_projection.py` gate extension + its full truth-table test suite, final integration of all four scripts into the `/evaluate-stock` pipeline, ADR.

Delegation candidates (dispatched via the Agent tool, reviewed against the locked data contract above before integration): `wacc.py`, `reverse_dcf.py`, `dcf_sensitivity.py`, `comps_valuation.py` — each is pure-computation, fixture-testable, and independently verifiable against the contract in §4 without needing the others to exist first.

## 10. Success Criteria

1. `reverse_dcf.py` round-trip property test passes (implied growth recovers input growth within 0.1pp).
2. `wacc.py` output is consumed by `dcf_scenarios.py` via `--wacc-file`, replacing the flat 10% default for any ticker with a computed rate.
3. `comps_valuation.py` and `dcf_sensitivity.py` outputs persist into `analyticsLog` for all ~13 seeded holdings.
4. `check_accumulate_gate()` blocks a fixture projection where only 1 of 3 lenses supports ACCUMULATE, and passes one where 2 of 3 agree.
5. A migration pass against existing `projections/*.json` documents any currently-ACCUMULATE tickers that would now fail the gate (no silent auto-correction).
6. `run_tests.py` T0/T0.5/T1 tiers green for all new/touched modules.
