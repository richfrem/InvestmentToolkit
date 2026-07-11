# G2 — Risk Officer + Red Team + Data Quality Agents (Fable5 Elevation Guide, Phase 3 Sub-Spec 5 of 5, final)

**Status:** Design — pending user review
**Date:** 2026-07-10
**Depends on:** E1 (`risk_engine.py` / `risk_snapshot.json`), C2 (`market_regime.py`), B5
(`thesis_breakers.py` / `thesis_breaker_state.json`), E2 (`rebalancer.py` /
`rebalance_plan.json`) — all shipped on local `main`.
**Guide reference:** §8 G2 ("Sub-agent roles"), §9 Phase 3 acceptance criteria.

## 1. Goal

This is the fifth and final sub-spec of Phase 3. It closes two gaps E2 deliberately left open
and formalizes one the elevation guide calls out on its own:

1. **E2's `riskGateWarnings`/`breakerWarnings` are warn-only by design** (spec §6.1 for E2)
   — real veto power was explicitly deferred to this sub-spec. **`risk-officer-agent`** now
   provides that veto, with a logged, HITL-respecting override path.
2. **No systematic adversarial check exists on `/evaluate-stock` or `/rebalance` output** —
   the "Adversarial Objectivity Constraint" from the investment framework doc is currently
   just prose. **`red-team-agent`** makes it a reusable, mandatory step.
3. **`market_data.py`'s cross-source data-quality signal (`dataQuality`: staleness +
   conflicts) is computed but silently dropped by every caller** — nothing today could ever
   trigger a degrade/halt decision. **`data-quality-agent`**, plus wiring to make the signal
   reachable, closes this.

**Phase 3 acceptance criterion this satisfies:** "a deliberately cap-breaching plan that gets
vetoed" (deferred from E2 §6.3).

**After this ships, Phase 3 (E1/C2/B5/E2/G2) is fully closed out.**

---

## 2. Architecture

Three new agent definitions under `plugins/portfolio-advisor/agents/`, following the
established split between deterministic engines (testable Python) and thin LLM-agent
wrappers (judgment, presentation, HITL) that every prior sub-spec uses:

```
risk_officer.py  (new engine)  ──┐
                                  ├─→ risk-officer-agent.md   (wrapper, veto + override HITL)
rebalance_plan.json (E2, input) ─┘

<projection.json | rebalance_plan.json> ─→ red-team-agent.md  (no new engine, purely conversational)

market_data.py's dataQuality  ─→ [wacc.py, comps_valuation.py,     ─→ data-quality-agent.md
  (existing, currently dropped)   peer_bench.py, technicals.py]       (wrapper, degrade/halt)
                                   (wiring: propagate the field)
```

None of the three agents mutate `target-portfolio.json`, `rebalance_plan.json`, or
`risk_snapshot.json` — same input-file-ownership boundary every prior sub-spec respects.
`risk_officer.py` owns a new `data/risk_officer_review.json` exclusively.

---

## 3. `risk-officer-agent`

### 3.1 `risk_officer.py` — deterministic classification engine

New file, `investment_screener/backend/py_services/risk_officer.py`. Pure classification —
no new numeric thresholds. An order is vetoed **iff** its `rebalance_plan.json` entry has a
non-empty `riskGateWarnings` or `breakerWarnings` (i.e., the exact same
`account_policy.json` `riskBudgetCaps` — 25% MRC / 60% cluster variance — and TRIGGERED
thesis-breaker signals E2 already computes). No new config surface.

```python
def classify_orders(orders: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split rebalance_plan.json's orders into (vetoed, approved).

    An order is vetoed iff riskGateWarnings or breakerWarnings is non-empty.
    Returns each order dict unchanged, plus a "vetoReasons" key on vetoed
    entries (the concatenation of both warning lists).
    """
```

```python
def compute_risk_officer_review(
    rebalance_plan_path: Path = REBALANCE_PLAN_PATH,
) -> dict:
    """Load rebalance_plan.json, classify orders, write risk_officer_review.json.

    Returns the same dict that gets written. If rebalance_plan_path is
    missing or its blockedReason is non-null, returns
    {"status": "no_plan" | "plan_blocked", "vetoedOrders": [], "approvedOrders": []}
    without writing a file — there is nothing to review yet.
    """
```

Output — `data/risk_officer_review.json`:

```json
{
  "generatedAt": "2026-07-10T14:00:00Z",
  "sourceRebalancePlanGeneratedAt": "2026-07-10T13:58:00Z",
  "vetoedOrders": [
    {
      "ticker": "CORZ",
      "action": "buy",
      "account": "TFSA",
      "shares": 15,
      "rationale": "Out of band: -3.1pp vs 1.5pp band",
      "vetoReasons": [
        "Estimated MRC would reach 31.2% (estimate) > 25% cap",
        "TRIGGERED breaker 'corz-margin-floor': current value 0.041, streak 5"
      ]
    }
  ],
  "approvedOrders": [ "...same order shape, no vetoReasons key..." ]
}
```

CLI:

```bash
python3 investment_screener/backend/py_services/risk_officer.py --pretty
python3 investment_screener/backend/py_services/risk_officer.py --log-override \
  --ticker CORZ --action buy --account TFSA --rationale "Conviction unchanged, MRC estimate is first-order only"
```

`log_risk_officer_override()` mirrors `thesis_breakers.py`'s `log_breaker_override()` exactly
— append-only, one JSON object per line, to a new `data/risk_officer_overrides.jsonl`:

```json
{"date": "2026-07-10", "ticker": "CORZ", "action": "buy", "account": "TFSA", "shares": 15, "vetoReasons": ["..."], "rationale": "Conviction unchanged, MRC estimate is first-order only", "overriddenBy": "user"}
```

An order is identified by `(ticker, action, account)` — `rebalance_plan.json`'s orders have no
separate id field and this triple is already unique per plan (matches how `_build_order_entries`
constructs them).

### 3.2 `/rebalance` integration (real enforcement)

`rebalance-portfolio/SKILL.md` gains a new step between the existing "Step 1: Run the
Rebalancer Engine" and "Step 5: Present Trade Recommendations":

- **Step 1b: Risk Officer Review.** Run `risk_officer.py --pretty`. Vetoed orders are removed
  from the trade plan shown in Step 5's table and instead rendered in a new **"⛔ Vetoed by
  Risk Officer"** section (same visual pattern as the existing "Skipped Restores" section),
  each with its `vetoReasons` listed.
- If the user wants to proceed with a vetoed order anyway, that is an explicit override: ask
  for a one-sentence rationale, log it via `risk_officer.py --log-override`, then treat the
  order exactly like a normal confirmed trade for the rest of the flow (Step 5b posting, Step
  6 confirm+log). No silent downgrades — every override is a logged, human decision, per the
  HITL-is-sacred constraint.
- If `risk_officer.py` reports `"status": "no_plan"` (shouldn't happen inside `/rebalance`,
  since Step 1 always just generated one) or fails, degrade gracefully: show a one-line
  warning and proceed with the unreviewed plan, exactly like E1/C2's existing degrade pattern
  in `daily_brief.py`.

### 3.3 `/daily` integration (read-only banner)

New step in `daily-loop-agent.md`, inserted after Step 1 (Morning Brief) and before Step 2
(Triage) — call it **Step 1.5**:

```bash
python3 investment_screener/backend/py_services/risk_officer.py --pretty 2>/dev/null
```

- If `data/rebalance_plan.json` doesn't exist, or its `generatedAt` is older than 24h, skip
  silently — no banner. (`/daily` never generates a rebalance plan itself; only `/rebalance`
  does.)
- If a fresh plan exists and has ≥1 vetoed order, render one line before the triage queue:
  `⛔ RISK OFFICER: {N} order(s) in the last /rebalance plan were vetoed — run /rebalance to review.`
- This is visibility only — it never blocks or alters Step 2/3's existing triage flow, and it
  never re-runs `rebalancer.py` itself (that stays `/rebalance`-only). Step 3's DCF/TA-derived
  card sizing is unchanged — out of scope for this sub-spec.

### 3.4 `risk-officer-agent.md`

Frontmatter matches the existing agent pattern (`daily-loop-agent.md`,
`thesis-review-agent.md`): `name`, `description`, `dependencies: [skill:rebalance-portfolio]`,
`tools: ["Bash", "Read", "Write"]`. Body: run `risk_officer.py --pretty`, present vetoed vs
approved orders in the format from §3.2, handle the override conversation one order at a time
(never batch-override), call `--log-override` on confirmation. This agent is what
`rebalance-portfolio/SKILL.md`'s new Step 1b and `daily-loop-agent.md`'s new Step 1.5
delegate to — both existing skills dispatch it via the Agent tool rather than inlining its
logic, so the veto/override behavior lives in exactly one place.

---

## 4. `red-team-agent`

No new Python engine — purely conversational, and **explicitly forbidden from proposing
trades** (mandate boundary, not a suggestion). Dispatched via the Agent tool with one input
artifact: either a completed projection JSON (`/evaluate-stock`) or `data/rebalance_plan.json`
(`/rebalance`).

**Contract:** given the artifact, produce:
- **≥3 specific, falsifiable objections** — each naming a concrete claim in the artifact and
  the specific evidence that would contradict it (not generic risk-off boilerplate).
- **A "what would change my mind" list** — the observable events/data that would resolve each
  objection either direction.

Output is printed to the user, above the final recommendation, every time. **Not persisted to
disk** — no schema change to either `analyticsLog` or `rebalance_plan.json`. This is a
presentation-time check, not a data contract other engines read (unlike E1/C2/B5/E2's
artifacts).

**Integration — mandatory on both:**
- `stock_valuation/SKILL.md` gains a new final step after Step 4 (Validate & Repair) and
  before the existing Step 8 conversational summary: dispatch `red-team-agent` with the
  validated projection, print its objections, *then* present the summary.
- `rebalance-portfolio/SKILL.md` gains a new step after §3.2's Step 1b (Risk Officer Review)
  and before Step 5 (Present Trade Recommendations): dispatch `red-team-agent` with
  `rebalance_plan.json` (post-veto-filtering — it reviews what will actually be proposed),
  print its objections, then present the trade table.

`red-team-agent.md`: `name`, `description`, `tools: ["Read"]` (no `Bash`/`Write` — it never
computes or persists anything, only reads the artifact and reasons over it, reinforcing the
"forbidden from proposing trades" boundary at the tool-permission level).

---

## 5. `data-quality-agent`

### 5.1 The gap

`market_data.py`'s `get_fundamentals()` already computes and returns a `dataQuality` dict
(`{"staleness": bool, "dataConflicts": list, "flags": list}`) via `check_disagreement()` /
`check_staleness()` from `data_quality.py`. But every Phase 2a/2b script that calls
`get_fundamentals()` — `wacc.py`, `comps_valuation.py`, `peer_bench.py` — drops that field
from its own JSON output before returning. `technicals.py` calls `get_prices()`, which has no
`dataQuality` field at all today. Net effect: nothing in this codebase could ever trigger a
degrade/halt decision, even though the underlying detection logic has existed since Phase 1.

### 5.2 Wiring (minimal, additive)

- `wacc.py`, `comps_valuation.py`, `peer_bench.py`: each already receives a `dataQuality` dict
  per ticker from its `get_fundamentals()` call(s). Add a top-level `"dataQuality"` key to
  each script's JSON output — for scripts pulling multiple tickers (peer comps, peer bench),
  emit `{ticker: dataQuality}` keyed by ticker; for single-ticker scripts (`wacc.py`), emit
  the dict directly.
- `market_data.get_prices()`: add a lightweight staleness-only variant — no cross-source
  conflict check exists for OHLCV (no second price source to disagree with). New helper:
  ```python
  def _price_staleness(df: pd.DataFrame, max_age_days: int = 5) -> bool:
      """True if the last row's date is more than max_age_days old. Reuses
      check_staleness() from data_quality.py against the last close's date."""
  ```
  `get_prices()`'s per-ticker return dict gains `"dataQuality": {"staleness": bool}`.
  `technicals.py` passes this through the same way as the fundamentals-based scripts.
- No change to `data_quality.py` itself — `check_disagreement()`/`check_staleness()` are
  reused as-is, not modified.

### 5.3 `stock_valuation/SKILL.md` integration

Steps 3.5 and 3.6 (§ references to the existing SKILL.md) each gain one check after their
script list: if any script's `dataQuality.staleness` is `true` or `dataQuality.dataConflicts`
is non-empty for the ticker being evaluated, dispatch `data-quality-agent` with:
- which script flagged it (`wacc` / `comps` / `peerBench` / `technicals`)
- the specific conflict or staleness detail
- whether that script's output feeds `aiThesis.action`'s gate (Step 3.5's `wacc`/`comps`
  outputs do — `dcf_scenarios.py --wacc-file` consumes `wacc.py`'s discount rate directly;
  Step 3.6's `framework`/`peerBench`/`technicals` are informational-only, never gate)

`data-quality-agent` decides:
- **DEGRADE** — proceed with the pipeline; the agent's decision + the flagged detail get
  appended to the projection's existing `analyticsLog.dataQualityFlags` array (Step 3's
  pre-existing field — no new schema). No change to Step 4's validator.
- **HALT** — stop before Step 4 (Validate & Repair persists nothing); tell the user which
  signal was too unreliable to proceed on and why. The partially-built `analyticsLog` in
  `temp/evaluations/{TICKER}_projection.json` is left as-is (not deleted, not persisted to
  `data/projections/`) so the user can inspect what was gathered before the halt.

**Decision tree (documented in `data-quality-agent.md`, not hardcoded logic elsewhere):**
1. Staleness only (no conflicts), on an informational-only lens (Step 3.6) → always DEGRADE.
2. Staleness only, on a gate-feeding lens (Step 3.5) → DEGRADE, but the appended
   `dataQualityFlags` note must say the fair value may be stale-input-affected.
3. A `dataConflicts` entry with `diffPct` under 15% → DEGRADE (same materiality bar
   Standing Constraint §8/CLAUDE.md rule 8 already uses for DCF fair-value deltas).
4. A `dataConflicts` entry with `diffPct` ≥ 15% on a gate-feeding lens (`wacc`/`comps`) →
   HALT.
5. A `dataConflicts` entry with `diffPct` ≥ 15% on an informational-only lens → DEGRADE with a
   prominent flag (never halts a pipeline over data that doesn't feed the actual valuation
   number).

`data-quality-agent.md`: `name`, `description`, `tools: ["Read"]` — read-only, decision-only;
it never edits `analyticsLog` itself (the calling skill does the append, same separation as
`red-team-agent`'s read-only boundary).

---

## 6. Non-goals / explicitly deferred

- **Routing `/daily` Step 3's action cards through `rebalancer.py`/`risk_officer.py`.** Step 3
  sizes trades from DCF/TA levels directly today (already shipped, reviewed under E2). This
  sub-spec adds a read-only banner only (§3.3) — no change to Step 3's existing flow.
- **A stricter, separate veto-only threshold tier.** `risk_officer.py` reuses E2's exact
  `riskBudgetCaps` values — no new config surface in `account_policy.json`.
- **Persisting `red-team-agent`'s objections to disk.** Purely conversational, every run —
  matches its advisory-only mandate; no schema change to two other sub-specs' owned files.
  If a durable record of red-team findings is wanted later, that's a new, separate sub-spec.
- **Wiring `dataQuality` into `fetch_financials.py`.** That script is still on the Phase 1
  "13-file yfinance migration" deferred list (start_here.md) — it doesn't call
  `market_data.py` at all yet, so there's nothing to wire there until that migration happens.
- **Any auto-execution from a veto, override, or red-team objection.** Visibility/enforcement
  changes presentation and requires explicit confirmation — never places or blocks an order
  without a human in the loop (Standing Constraint, HITL is sacred).

---

## 7. Testing plan (TDD — failing test first, per repo convention)

`investment_screener/backend/tests/py_services/test_risk_officer.py`:
- `classify_orders()`: an order with non-empty `riskGateWarnings` only → vetoed; non-empty
  `breakerWarnings` only → vetoed; both empty → approved; both non-empty → vetoed with
  `vetoReasons` containing entries from both lists, in order.
- `compute_risk_officer_review()`: end-to-end fixture round-trip via a temp `rebalance_plan.json`
  — asserts `risk_officer_review.json`'s shape, and that `generatedAt` differs from
  `sourceRebalancePlanGeneratedAt` handling (pass both through, don't conflate).
  Missing/absent plan file → `{"status": "no_plan", ...}`, no file written. Plan with a
  non-null `blockedReason` → `{"status": "plan_blocked", ...}`, no file written.
- `log_risk_officer_override()`: appends one well-formed JSONL line, doesn't clobber existing
  lines (mirrors `test_thesis_breakers.py`'s equivalent case).
- CLI: `--log-override` requires `--ticker`, `--action`, `--account`, `--rationale`; missing
  any → `sys.exit(f"ERROR: ...")` (this file's existing convention, not raw `ValueError`).

`investment_screener/backend/tests/py_services/test_data_quality_wiring.py` (or extend
existing `test_wacc.py`/`test_comps_valuation.py`/`test_peer_bench.py`/`test_technicals.py`):
- Each script's fixture test asserts a `dataQuality` key is present in its output and
  correctly shaped, using a fixture where `get_fundamentals()`/`get_prices()` is mocked to
  return a known staleness/conflict state.
- `_price_staleness()`: fixture with last row 3 days old (not stale, `max_age_days=5`) vs. 10
  days old (stale) — boundary at exactly 5 days is not stale (inclusive, matching
  `check_staleness()`'s existing inclusive-boundary convention).

**Acceptance test (pins the deferred Phase 3 criterion):** a fixture `rebalance_plan.json`
with one order whose `riskGateWarnings` deliberately breaches the 25% MRC cap →
`risk_officer.py --pretty` produces a `risk_officer_review.json` with that order in
`vetoedOrders`, not `approvedOrders`.

No test coverage is prescribed for `risk-officer-agent.md`, `red-team-agent.md`, or
`data-quality-agent.md` themselves — these are markdown agent definitions (conversational
judgment + tool orchestration), not testable Python, matching how `daily-loop-agent.md` and
`thesis-review-agent.md` have no test files today. Their correctness is verified by exercising
the underlying engines (`risk_officer.py`) and by the SKILL.md integration steps being
followed exactly as written — same verification boundary the repo already draws.

---

## 8. Standing constraints checklist

1. HITL is sacred — §3.2 (override requires stated rationale, one order at a time, never
   batch), §4 (red-team never proposes trades, only objects), §5.3 (halt still requires human
   investigation before proceeding, never auto-retries).
2. Decision support, not advice — all three agents render analysis; a human decides in every
   case (override, halt-vs-continue, whether to act on a red-team objection).
3. `standingDecision` anchor semantics unchanged — none of the three agents touch
   `target-portfolio.json` or its `standingDecision` fields.
4. No silent schema breaks — `risk_officer_review.json` and `risk_officer_overrides.jsonl` are
   new files (no migration needed); `dataQuality` passthrough fields are additive keys on
   existing script outputs; `analyticsLog.dataQualityFlags` is a pre-existing field, appended
   to, not restructured.
5. Reproducibility over cleverness — `risk_officer.py`'s classification is a pure function of
   `rebalance_plan.json`'s already-computed warnings; no new numeric estimation introduced.
6. Provider terms — n/a, no new external data source.
