# E2 — Rebalancer v2 (Fable5 Elevation Guide, Phase 3 Sub-Spec 4 of 5)

**Status:** Design — pending user review
**Date:** 2026-07-09
**Depends on:** E1 (`risk_engine.py` / `risk_snapshot.json`), B5 (`thesis_breakers.py` /
`thesis_breaker_state.json`) — both shipped on local `main`.
**Guide reference:** §6 E2 ("Rebalancer v2"), §9 Phase 3 acceptance criteria.

## 1. Goal

Formalize what `/rebalance` + the `rebalance-portfolio` skill currently do informally (drift
classification, capital sequencing, account routing — all computed in-context by an LLM
following ~400 lines of `SKILL.md` prose) into a real, testable engine:
`py_services/rebalancer.py`, producing `data/rebalance_plan.json`. Drift bands replace point
targets (killing churn/small-order noise), a risk-budget check cross-references E1's variance
data (not just weight), Canada-aware account/tax placement becomes data + code instead of
prose, and the skill shrinks to: run engine → present plan → HITL per order (execution path
unchanged).

**Phase 3 acceptance criterion this satisfies:** "rebalancer evals pass on fixtures including a
deliberately cap-breaching plan that gets vetoed" — reinterpreted per §6 below as *warned*, not
excluded; see §6.3 for why.

## 2. Scope decisions (confirmed with user before this spec was written)

| Decision | Resolution |
|---|---|
| Does E2 read B5's `thesis_breaker_state.json`? | Yes, **flag-only** — a `TRIGGERED` breaker attaches a warning to a proposed ACCUMULATE order; never suppresses it. Visibility escalation only, same posture as B5 itself. |
| Relationship to `globalSettings.driftThresholdPct`/`criticalDriftPct`? | **Retired**, replaced by the new band formula. These fields turned out to be a TypeScript/dashboard concern (`ThesisService.ts`'s `/health` endpoint), not read by any Python script — see §5. |
| Relationship to `portfolio_action.py`'s `derive_action()` (0.85/1.15 ratio, the dashboard's ACCUMULATE/TRIM/MAINTAIN label)? | **Stays separate, untouched.** The new band only decides "should rebalancer.py generate a trade order this run" — a holding can show ACCUMULATE on the dashboard yet have no order generated because it's inside the no-churn band. Two different questions, deliberately not unified. |
| Account per-holding share splits | Use `portfolio.json`'s `tvSnapshot.snapshots[].positions` (real per-account data + `avgFillPrice` cost basis) when present; fall back to the existing TFSA-full/RRSP-~1/3 heuristic when an account's snapshot is missing/stale, flagged in the plan's `accountDataSource`. |
| Script vs. skill boundary | `rebalancer.py` becomes the engine; the skill becomes a thin wrapper (matches the `/daily` ↔ `daily_brief.py` pattern). Most of the skill's inline Steps 2–4 math is replaced by "read the plan." |
| Risk-budget violations: warn or veto? | **Warn only.** E2 never excludes an order for breaching a cap — it attaches `riskGateWarnings`. Real veto-with-rationale power belongs to G2's `risk-officer-agent` (explicitly scoped for after E2 in the guide, consuming E2's order-plan format as its input). |
| Cash-account capital-gains estimate | **Build it now**, generically, keyed off account type — even though the user's current accounts are TFSA + RRSP only (no Cash account yet). Forward-looking per the guide; cheap to add alongside the TFSA/RRSP routing logic since `account_policy.json` needs a Cash entry for completeness regardless. |
| `rebalancer.py` architecture | Single file, many pure `compute_*()` functions + one orchestrator + CLI — mirrors `risk_engine.py`/`market_regime.py`/`thesis_breakers.py` exactly (all three shipped clean at 490–560 lines in this shape). |

## 3. Data model

### 3.1 New static config — `data/account_policy.json` (human-edited, not machine-owned)

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
    "absolutePct": 1.5
  }
}
```

`accountPreferenceRules[].match` is a tag the rebalancer resolves per-ticker from existing
`target-portfolio.json` fields (`pillarId`, `role`) — no new per-holding fields required; a
ticker matching no rule falls through to `"default"`. This file is edited directly (or via a
future `update_account_policy.py --set` CLI, out of scope this pass) — same tier as
`target-portfolio.json`'s `globalSettings`, not written by any script.

### 3.2 `target-portfolio.json` changes

`globalSettings.driftThresholdPct` and `globalSettings.criticalDriftPct` are removed (not
replaced in-place — `bandConfig` lives in `account_policy.json` instead, since it's now shared
by both `rebalancer.py` and `ThesisService.ts`, and `account_policy.json` is the more natural
home for "how do we decide when to act" config vs. `target-portfolio.json`'s "what do we want"
data). Per Standing Constraint §10.4 (no silent schema breaks): version bump in
`target-portfolio.json`'s `schemaVersion`, `zod-schemas.ts` updated in the same change set,
`ThesisService.ts` updated to read the new location (§5).

### 3.3 New output — `data/rebalance_plan.json` (machine-owned, regenerated every run)

```json
{
  "generatedAt": "2026-07-09T13:00:00Z",
  "blockedReason": null,
  "bands": {
    "NBIS": { "currentWeight": 2.1, "targetWeight": 5.5, "bandPct": 1.5, "driftPct": -3.4, "inBand": false }
  },
  "orders": [
    {
      "ticker": "CRWD", "action": "sell", "account": "TFSA", "shares": 15,
      "rationale": "Out of band: +3.8pp overweight vs 1.5pp band",
      "gatesPassed": ["not_exit_gated", "band_check"],
      "riskGateWarnings": [],
      "breakerWarnings": [],
      "capitalGainsEstimate": null
    },
    {
      "ticker": "NBIS", "action": "buy", "account": "TFSA", "shares": 6,
      "rationale": "Out of band: -3.4pp underweight vs 1.5pp band",
      "gatesPassed": ["not_exit_gated", "band_check", "below_target_entry_price"],
      "riskGateWarnings": ["MRC would reach 27% > 25% cap"],
      "breakerWarnings": ["TRIGGERED: rsi > 75 (streak 3)"],
      "capitalGainsEstimate": null
    }
  ],
  "skippedRestores": [
    { "ticker": "INTC", "reason": "SELL-rated, drifted down — not restoring" }
  ],
  "accountDataSource": { "TFSA": "tvSnapshot", "RRSP": "heuristic_1_3_mirror" },
  "warnings": []
}
```

`blockedReason` (non-null) means the plan generated with `orders: []` and a reason string —
the no-trade conditions the skill currently checks in prose (§6.4). Does not write back to any
input file — same "owns exactly one output, mutates nothing it reads" boundary as
`risk_engine.py`/`market_regime.py`/`thesis_breakers.py`.

## 4. Core engine — `py_services/rebalancer.py`

New script, same shape as the three prior Phase 3 scripts: pure functions + an
importable/CLI orchestrator.

### 4.1 Functions

- `compute_bands(current_weights, target_weights, band_config) -> dict[ticker, dict]` — pure;
  `bandPct = max(target_weight * band_config.relativePct/100, band_config.absolutePct)`;
  `inBand = abs(driftPct) <= bandPct`.
- `load_account_positions(portfolio_path) -> dict[account, dict[ticker, {shares, costBasis}]]` —
  reads `tvSnapshot.snapshots[].positions` when present; per-account gaps fall back to the
  aggregated `holdings[]` list split via the TFSA-full/RRSP-~1/3 heuristic, tagging the source.
- `compute_account_routing(orders, account_positions, account_policy, target_data) -> list[dict]`
  — sequences sells before buys, resolves TFSA/RRSP/Cash placement per
  `accountPreferenceRules`, applies the PSU-U.TO same-account funding rule
  (`ceil(N * price / 100)`) when a buy needs capital beyond available cash in that account.
- `compute_capital_gains_estimate(ticker, shares_sold, sale_price, cost_basis) -> float | None` —
  `(sale_price - cost_basis) * shares_sold`; `None` when cost basis is unavailable (never a
  crash — appends a warning instead).
- `compute_risk_budget_check(proposed_orders, risk_snapshot, account_policy) -> dict[ticker, list[str]]`
  — approximates post-trade MRC/cluster share by scaling each affected ticker's existing
  `marginalRiskContribution`/`clusterExposure` entry proportionally to its weight change; warns
  (never excludes) when the projected value exceeds `riskBudgetCaps`.
- `compute_breaker_warnings(proposed_orders, thesis_breaker_state) -> dict[ticker, list[str]]` —
  cross-references any `TRIGGERED` entry for a ticker with a proposed `buy` order; degrades
  silently (empty dict) if the state file is missing/stale.
- `compute_rebalance_plan(target_portfolio_path=..., portfolio_path=..., risk_snapshot_path=...,
  thesis_breaker_state_path=..., account_policy_path=...) -> dict` — orchestrator; assembles
  every `compute_*()` result, checks no-trade conditions first (§6.4), returns the full plan
  dict. Does not write to disk — `main()`'s `--no-save`-gated write owns that, same convention
  as every prior Phase 3 script.

### 4.2 Carried-over hard rules (never warnings — these exclude the order entirely)

- Never generates a buy for an `EXIT`/`SELL`-gated holding (via `derive_action()`, called
  read-only — not modified).
- Never generates a buy above `targetEntryPrice` when the field is set.
- `standingDecision` on a holding is read but never overridden — a holding with a
  `standingDecision` still gets a band check, but any conflicting signal downgrades to a
  no-op with the same "signal stands but no trade proposed without your direction" framing
  `brief_recommendations.py` already uses for EXIT/REDUCE bands. `rebalancer.py` reuses
  `brief_recommendations.py`'s existing `load_standing_decisions()` loader for the data (no
  duplicate parsing), but implements its own small downgrade check inline — there's no
  standalone reusable decision function to call yet, only the inline check inside
  `build_recommendations()`. Extracting a shared helper is a fair future cleanup but is not
  required for this sub-spec's scope.

## 5. TypeScript changes — `ThesisService.ts` / `zod-schemas.ts`

`getHealth()`'s `DRIFT`/`CRITICAL` classification currently reads
`globalSettings.driftThresholdPct`/`criticalDriftPct` (lines 142–143, 177, 203–204). Both call
sites switch to reading `account_policy.json`'s `bandConfig` and applying the same
`max(relativePct, absolutePct)` formula server-side in TypeScript (an independent
re-implementation, not a shell-out to Python — consistent with how the rest of the backend's
math is done in-language). `zod-schemas.ts` gains a schema for `account_policy.json` (a new
file the backend now reads) and drops the two retired fields from the `globalSettings` schema.
Requires `npm run build -w backend` + restart (pitfall #3) before the dashboard reflects the
new thresholds.

## 6. Risk-budget check — design notes

### 6.1 What "post-trade" means here

`risk_snapshot.json` is a point-in-time snapshot computed from live 2y price history — a full
re-run of `risk_engine.py` against hypothetical post-trade weights is out of scope for this
sub-spec (expensive, and E2's job is to warn cheaply, not re-derive risk from scratch on every
candidate plan). Instead, `compute_risk_budget_check()` approximates: it scales each affected
ticker's *existing* `marginalRiskContribution` value by its proposed weight ratio
(`new_weight / old_weight`) as a first-order estimate, explicitly labeled `"estimate": true` in
the warning payload — same estimate-labeling discipline as E1's own VaR/CVaR fields.

### 6.2 Cap defaults

`maxMarginalRiskContributionPct: 25`, `maxClusterVarianceContributionPct: 60` — looser than the
skill's existing weight-based caps (15% single position / 40% pillar) because variance
contribution from a concentrated, volatile AI/semis/power thesis is expected to run structurally
higher than weight share; tighter caps would fire warnings on nearly every run given the guide's
own cited "72% of portfolio variance from one cluster" example. Configurable in
`account_policy.json`, not hardcoded.

### 6.3 Why "warn," not "veto," despite the guide's Phase 3 acceptance wording

§9's Phase 3 acceptance line — "a deliberately cap-breaching plan that gets vetoed" — describes
the *phase's* combined behavior (E1 + E2 + G2), not literally E2 in isolation. E2's own §6 spec
text is explicit that risk-budget violations "surface as warnings the user must acknowledge,"
while "veto-with-rationale power over plans that breach cluster caps" is named as G2's
`risk-officer-agent` responsibility, scoped for after E2, consuming E2's order-plan format as
input. Confirmed with the user: E2 implements warn-only; the cap-breaching-plan-gets-vetoed
fixture becomes a G2-level eval once that agent exists, not an E2-level one.

### 6.4 No-trade conditions (moved from skill prose into `blockedReason`)

Computed by the orchestrator before building any orders, same conditions the skill currently
checks manually:

| Condition | Check |
|---|---|
| `DATA_STALE` | `portfolio.json` timestamp > 60 min old |
| `TARGETS_INVALID` | `target-portfolio.json` weights don't sum to 100% ± 0.5% |
| `MISSING_VALUATIONS` | > 30% of thesis tickers have no DCF projection |

Any one of these sets `blockedReason` and short-circuits to an empty `orders: []` (bands/risk
checks still computed and returned for visibility, but no orders proposed). `EARNINGS_SEASON`
and `THESIS_OUT_OF_SYNC` (the skill's other two no-trade conditions) stay skill-side warnings
rather than hard blocks — they're softer "let the user decide" signals, not structural
blockers on the math itself.

## 7. Skill integration — `rebalance-portfolio` `SKILL.md`

- **Steps 1–4** (load state, classify drift, assess capital, build payload) collapse into:
  `python3 investment_screener/backend/py_services/rebalancer.py --pretty`.
- **Step 5** (present recommendations) reads `data/rebalance_plan.json` and renders the
  existing table format, now populated from computed fields. `riskGateWarnings` and
  `breakerWarnings` render as inline `⚠️` lines under their order.
- **Step 5b** (post to trade log) — unchanged; still posts `orders[]` in the plan's
  sells-then-buys order.
- **Step 6** (confirm + log) — unchanged; one HITL confirmation per order. A warned order's
  confirmation prompt includes its warning text so the user sees it before confirming.
- The skill's current Steps 2–4 prose (~150 lines of inline drift-classification,
  capital-sequencing, and account-heuristic instructions) is replaced with "read the plan" —
  per the deletions-forbidden rule, this is *replacing skill content*, the same treatment G1
  already describes for consolidated skills, not a deletion.
- `blockedReason` from the plan replaces the skill's manual `DATA_STALE`/`TARGETS_INVALID`/
  `MISSING_VALUATIONS` prose checks (§6.4); `EARNINGS_SEASON`/`THESIS_OUT_OF_SYNC` prose stays.

## 8. Non-goals / explicitly deferred

- **Veto power over cap-breaching orders.** Belongs to G2's `risk-officer-agent`, built next
  (§6.3).
- **Full historical re-run of `risk_engine.py` for exact post-trade risk figures.** §6.1's
  proportional-scaling estimate is intentionally cheap and approximate, labeled as such.
- **Real-world testing of the Cash-account capital-gains path** against live data — no Cash
  account currently exists in the user's `portfolio.json`. The logic is implemented and
  fixture-tested (§9) but will only be exercised against real data if/when a Cash account
  appears.
- **`update_account_policy.py` authoring CLI.** `account_policy.json` is hand-edited this pass,
  same as `target-portfolio.json`'s `globalSettings` before any dedicated CLI existed for it.
- **JSON Schema for `rebalance_plan.json`/`account_policy.json`** in `schemas/`. Workstream F4
  (schemas as single source of truth) hasn't started yet (only `market_data_response.schema.json`
  exists) — out of scope for this sub-spec, consistent with E1/C2/B5 not adding schemas either.

## 9. Testing plan (TDD — failing test first, per repo convention)

`investment_screener/backend/tests/py_services/test_rebalancer.py`, fixture-driven, no network
— mirrors `test_risk_engine.py`/`test_market_regime.py`/`test_thesis_breakers.py`:

- `compute_bands()`: in-band holding → `inBand: true`, no order; out-of-band → `inBand: false`.
  Boundary case: drift exactly equal to `bandPct` → in-band (uses `<=`).
- Hard-rule exclusions: out-of-band holding that's `EXIT`/`SELL`-gated → no buy generated even
  though underweight; out-of-band buy priced above `targetEntryPrice` → suppressed. Both
  produce no order, not a warned order.
- `compute_risk_budget_check()`: deliberately cap-breaching proposed order (MRC or cluster
  projected over cap) → order still appears in `orders[]` with non-empty `riskGateWarnings` —
  this is the fixture satisfying Phase 3's acceptance line, reinterpreted per §6.3.
- `compute_breaker_warnings()`: a `TRIGGERED` breaker on a ticker with a proposed buy → order
  still present, `breakerWarnings` populated; a non-`TRIGGERED` (`OK`/`WATCHING`) breaker →
  no warning.
- `load_account_positions()`: tvSnapshot present for TFSA only → RRSP falls back to heuristic
  split, `accountDataSource.RRSP == "heuristic_1_3_mirror"`; both accounts present → both use
  `"tvSnapshot"`.
- `compute_capital_gains_estimate()`: cost basis available → correct gain/loss figure;
  unavailable → `None` plus a warning, no exception.
- PSU-U.TO funding rule: a buy needing capital beyond available same-account cash triggers a
  same-account PSU trim sized via `ceil(N * price / 100)` — verified against the existing
  formula, not re-derived.
- `blockedReason` fixtures: stale portfolio timestamp, targets summing to 97%, and >30% missing
  valuations each produce the correct `blockedReason` string and `orders: []`.
- Missing `risk_snapshot.json`/`thesis_breaker_state.json` on disk → orchestrator degrades
  gracefully (warning appended, that gate's checks skipped), never raises.

Wired into `run_tests.py`'s **T1** tier (pure-math, no network, must run <60s) alongside
`risk_engine`/`market_regime`/`thesis_breakers`.

## 10. Standing constraints checklist

1. HITL is sacred — §7 (skill still confirms every order individually; E2 only *proposes*).
2. Decision support, not advice — plan is presented data, human decides per order.
3. `standingDecision` anchor semantics unchanged — §4.2 explicit; conflicting signals downgrade
   to no-op, never override.
4. No silent schema breaks — `target-portfolio.json` schema version bump +
   `zod-schemas.ts`/`ThesisService.ts` updated in the same change set (§5); new files
   (`account_policy.json`, `rebalance_plan.json`) are additive, no migration needed.
5. Reproducibility over cleverness — every figure in the plan is regenerable from the five
   input files + `rebalancer.py`; the risk-budget estimate is explicitly labeled as one (§6.1).
6. Provider terms — n/a, no new external data source.
