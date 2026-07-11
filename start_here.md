# Session Start Briefing — InvestmentToolkit
_Last updated: 2026-07-10 (Phase 3 E2 shipped) | Thesis v10.8 | Portfolio value: check live snapshot (user actively trading — do not trust a stale figure here)_

> **Read this first at the start of every new session.**

---

## 🔥 ACTIVE: Fable5 Elevation Guide — Phase 3 E2 DONE, start Phase 3 G2 here (final sub-spec)

**Context:** User had Fable5 (primary), Gemini, GPT, Grok review the codebase for
"next level" improvements — reviews saved at `temp/bundles/full-bundle/reviews/`.
Fable5's guide (`fable5-ELEVATION_GUIDE.md`) is the one being executed — the only review
grounded in the actual repo. It's a 6-phase roadmap: (1) data layer, (2) valuation
committee, (3) executable scoring framework + local TA engine, (4) TradingView/Pine
hardening, (5) risk engine + rebalancer + prediction ledger + backtesting, (6) skills/
sub-agent architecture cleanup. Phase 2 was split into two sub-phases during brainstorming
(2a = Valuation Committee, 2b = Executable Framework + local TA) because it bundled two
loosely-coupled workstreams. **Phase 3 (§9 in the guide: Risk & Rebalancer) was likewise
decomposed into 5 sub-specs during brainstorming — E1/C2/B5/E2/G2, built strictly in that
order since E2 and G2 both consume E1's `risk_snapshot.json`, C2's `market_regime.json`,
and B5's `thesisBreakers`/`thesis_breaker_state.json` as data contracts, and G2 additionally
consumes E2's `data/rebalance_plan.json` order-plan format.** E1 (portfolio risk engine), C2
(market regime classifier), B5 (thesis breakers), and E2 (rebalancer v2) are now all
shipped; this session starts fresh on Phase 3's fifth and final sub-spec, **G2
(risk-officer + red-team agents)** — Phases 1, 2a, 2b, and all of Phase 3's E1 + C2 + B5 +
E2 are fully shipped and verified. E1 is merged all the way to `origin/main` (PR #63); C2,
B5, and E2 are all merged to local `main` and pushed to `origin` as
`feature/fable5-phase3-c2-market-regime`, `feature/fable5-phase3-b5-thesis-breakers`, and
`feature/fable5-phase3-e2-rebalancer-v2` respectively, **none yet merged to `origin/main`**
— same PR-yourself pattern as every phase, waiting on the user's GitHub review. Nothing
from any of them needs redoing.

**Also shipped this session, unrelated to the Fable5 phases:** a `norberts-gambit` skill
(`plugins/portfolio-advisor/skills/norberts-gambit/`) — a broker-agnostic guide for
converting cash between CAD and USD via the DLR.TO/DLR.U ETF pair, with a Questrade
appendix (`references/questrade.md`); more brokers can get their own appendix file later
without touching the core. Registered in both `plugin.json` manifests and
`marketplace.json`. On `feature/norberts-gambit-skill`, pushed to `origin`, **not yet
merged** — same backup/PR pattern as the phase branches, just not part of the Fable5
numbering.

### ✅ Phase 1 (data layer) — COMPLETE, on `origin/main`
`py_services/market_data.py` (+ `cache.py`, `edgar_facts.py`, `data_quality.py`, schema) —
a unified, cached, quality-gated provider abstraction (yfinance + SEC EDGAR). Built as 8
TDD-gated tasks via `superpowers:subagent-driven-development`. Merged via PR #59.

**Deliberately deferred, NOT part of Phase 1, pick up whenever convenient (not blockers):**
1. **13-file yfinance migration** onto the new `market_data.py` — `fetch_financials.py`,
   `portfolio_performance.py`, `macro_regime.py`, `earnings_calendar.py`, `fetch_quotes.py`,
   `overnight_gaps.py`, `fetch_portfolio_heatmap.py`, `history_store.py`, ETF/TV scripts,
   one TS-adjacent file. Each needs reading fresh for accurate before/after steps.
   `fetch_financials.py` has its own bespoke 1hr-TTL cache at
   `plugins/stock-valuation/scripts/cache/` that must be *replaced*, not duplicated.
2. **Cache-key collision**: `get_fundamentals()` and `get_estimates()` share cache key
   `(ticker, "fundamentals")` — confirmed safe (no misread) but whichever runs second
   overwrites the other's entry. Fix before any caller uses both for the same ticker.

### ✅ Phase 2a (Valuation Committee) — COMPLETE, on `origin/main`
Four new independent valuation lenses replacing the single flat-10%-discount-rate DCF, plus
a gate requiring 2-of-3 agreement before `ACCUMULATE`. Spec: `docs/superpowers/specs/2026-07-04-valuation-committee-design.md`.
Plan: `docs/superpowers/plans/2026-07-04-valuation-committee.md`. ADR: `docs/architecture/ADR-valuation-committee.md`.

- **`wacc.py`** — per-company discount rate (risk-free rate + local-OLS beta vs SPY + ERP +
  after-tax cost of debt, capped/floored [7%, 14%]), replacing the flat 10% default.
- **`reverse_dcf.py`** — bisection-inverts `compute_scenario()` to find the growth rate the
  market is pricing in at the current price, classified vs bear/base/bull.
- **`dcf_sensitivity.py`** — 2D grid (growth × exit-PE) + Monte Carlo (P10/P50/P90,
  P(overvalued)).
- **`comps_valuation.py`** — peer-median EV/Sales cross-check (EV/EBITDA deliberately out of
  scope — no EBITDA source in the data layer yet). Peers seeded for 10 current holdings
  (CORZ, PANW, CRWV, NBIS, BE, SNDK, CEG, OKLO, APLD, MSFT); CBRS deliberately left unseeded
  (no confident peer knowledge).
- **`market_data.py`** extended with `totalDebt`/`cashAndEquivalents`/`interestExpense`
  (yfinance-only for now — no EDGAR tag mapping yet).
- **`dcf_scenarios.py`** gained `--wacc-file` (an explicit `--discount-rate` still wins, for
  reproducing old runs — `compute_scenario()`'s math itself is untouched).
- **`validate_projection.py`** gained `check_accumulate_gate()` — blocks `ACCUMULATE` unless
  ≥2 of 3 lenses agree (DCF upside >15%, comps upside, implied-growth-below-base-case); a
  >25% cross-lens spread triggers a non-blocking disagreement-note warning.
- **`SKILL.md`** (stock_valuation) updated with the full 5-script pipeline (Step 3.5) — a
  whole-branch-review fix round added the missing `analyticsLog.dcf` wiring instruction,
  since without it the gate would have silently run as 2-of-2 instead of 2-of-3.

Built as 8 TDD-gated tasks via `superpowers:subagent-driven-development` in a fresh worktree
(`.worktrees/feature-fable5-phase2a-valuation-committee`, now cleaned up). Two tasks needed
one fix round each after task-level review; the final whole-branch review (opus) caught and
fixed the `analyticsLog.dcf` gap above. **Merged via PR #60** (`git log origin/main` shows
`32bbe85` as the merge commit) — user merged themselves on GitHub, confirmed via
`git fetch` + `git log origin/main`, not assumed.

**Follow-up flagged by the migration-audit test, not yet acted on:** 5 existing projections
carry `aiThesis.action = ACCUMULATE` from before this phase and have no `analyticsLog.{dcf,comps,reverseDcf}`
data yet, so they'd fail the new gate if re-validated as-is: **COHR, GOOG, VST, WQTM, ZS**.
This is expected (documented in the ADR), not a bug — each just needs to go through
`/evaluate-stock` again to pick up the new lens data. Not urgent, but don't be surprised if
`validate_projection.py` rejects one of these five before it's been re-run.

### ✅ Phase 2b (Fundamental Analyst + Local TA Engine) — COMPLETE, on local `main`
Executable version of the investment-framework scoring doc, automated peer benchmarking,
and a headless local TA engine — all three informational/advisory only, none gate
`aiThesis.action`. Spec: `docs/superpowers/specs/2026-07-05-fundamental-analyst-ta-design.md`.
Plan: `docs/superpowers/plans/2026-07-05-fundamental-analyst-ta.md`.

- **`framework_score.py`** — sector-aware weighted composite score (revenue growth, Rule of
  40 Method A/B, operating margin, ROIC, EV/Sales valuation, FCF yield, averaged balance-sheet
  score, qualitative moat/news via `--qualitative-file`) with missing-metric reweighting
  (never zero-filled). New `sector` field (`saas_cyber`/`chips_ai`/`energy_infra`) added to
  projections, same agent-curated pattern as `peers`.
- **`peer_bench.py`** — Z-score/percentile peer benchmarking table, reuses
  `framework_score.compute_raw_metrics()` as the single source of truth (zero formula
  duplication). Z-score correctly uses peer-only mean/stdev (a pooling bug caught and fixed
  during task review).
- **`technicals.py`** — hand-rolled local TA engine (RSI Wilder, EMA 21/50/200, MACD, ADX,
  ATR, Bollinger/Keltner squeeze, anchored VWAP, volume ratio, relative strength vs.
  benchmark — date-aligned, not positional). Sources OHLCV via `market_data.get_prices()`
  (yfinance), never TV CDP (pitfall #7: CDP can't do batch/background history).
- **`ta_sweep_batch.py --validate`** — new opt-in mode cross-checking local RSI/ADX against
  the TV Data Window scrape, flags >2pt divergence. Default sweep behavior unchanged.
- **`market_data.py`** extended with `ebitda`/`currentRatio`/`freeCashflow` (yfinance-only,
  same scope-boundary pattern as Phase 2a's `totalDebt`/`cashAndEquivalents`).
- **`validate_projection.py`** gained an optional `sector` enum check (no-op if absent, no
  change to the Phase 2a `check_accumulate_gate()`).
- Framework doc renamed `defininitive_...` → `definitive_professional_investment_framework.md`
  (fixed the long-standing typo), old path kept as a real compat symlink via
  `symlink_manager.py`.
- **`SKILL.md`** (stock_valuation) gained Step 3.6 wiring the three new scripts into the
  `/evaluate-stock` pipeline, merging into `analyticsLog.{framework,peerBench,technicals}`.

Built as 9 TDD-gated tasks via `superpowers:subagent-driven-development` in a fresh worktree
(`.worktrees/feature-fable5-phase2b-fundamental-analyst-ta`, now cleaned up). Four tasks
needed a fix round after task-level review (composite weights summed to 1.05 not 1.00 —
inherited from an arithmetic error in the source doc itself; peer Z-score pooling bug;
relative-strength positional-alignment bug; an unguarded empty-price-data crash path) — all
caught and fixed before the final whole-branch review, which returned **Ready to merge: Yes**
with zero Critical/Important findings. Two trivial cosmetic follow-ups from that final review
(a wrong type hint, an undocumented simplification) were applied in one more commit. **Merged
to local `main` via fast-forward** (main hadn't diverged); `feature/fable5-phase2b-fundamental-analyst-ta`
pushed to `origin` as a backup/PR source — **not yet merged to `origin/main`**, the user
merges via GitHub's PR flow on their own timing, same as Phase 1/2a.

**One real process incident this phase, already resolved:** a Task 3 implementer subagent
briefly `cd`'d into the main checkout (then on `feature/metabolic-rewriting-thesis`) instead
of the worktree, committing that task's change onto the user's active branch. Caught by
independently verifying `git log`/`readlink` after the report instead of trusting it,
`git revert`ed cleanly there (not `reset --hard`, to preserve an unrelated pre-existing
uncommitted change on that branch), and redone correctly in the worktree on retry. Worth
being extra explicit about worktree paths in dispatch prompts for any future multi-task
session — the fix already got folded into every subsequent dispatch this session.

### ✅ Phase 3, Sub-Spec 1 — E1 Portfolio Risk Engine — COMPLETE, on local `main`
`risk_engine.py` — correlation matrix, annualized portfolio volatility/beta (current
actual weights, never re-derived from shares×price), marginal risk contribution per
holding, concentration (HHI/top-3/effective N), pillar-level cluster exposure (reuses
target-portfolio.json's curated `pillarId` taxonomy), historical stress replay (2022 rate
shock + worst drawdown found in a separate 5y fetch), and parametric+historical VaR/CVaR
(95%/99%, 1-day horizon, explicitly labeled as estimates — no scipy dependency, z-scores
and normal PDF hand-computed). Orchestrated by `compute_risk_snapshot()` (CLI +
importable), writing `data/risk_snapshot.json`. Wired into `/daily`'s morning brief as a
compact `RISK: vol 28% · beta 1.4 · top cluster 61% · MRC leader: NVDA 18%` line
(`daily_brief.py`), degrading gracefully (with an stderr breadcrumb) if the risk engine
fails. Backend-only this pass — a dedicated `Risk.tsx` frontend page is an explicit
fast-follow, not yet built. Spec: `docs/superpowers/specs/2026-07-05-risk-engine-design.md`.
Plan: `docs/superpowers/plans/2026-07-05-risk-engine.md`.

Built as 7 TDD-gated tasks via `superpowers:subagent-driven-development` in a fresh
worktree (`.worktrees/feature-fable5-phase3-e1-risk-engine`, now cleaned up). One task
(stress replay) needed a fix round after task-level review — a real, reproduced accuracy
bug (worst-drawdown detection structurally can't recognize a peak on the very first date
of the 5-year fetch window, since that date is dropped as the `pct_change()` baseline);
user chose to document + pin with a regression test rather than redesign the function's
contract mid-branch. A second real bug was caught and fixed *before* it ever shipped: the
orchestrator would have passed cluster-exposure the full unfiltered weights instead of the
mrc-eligible subset, letting an excluded ticker's weight leak into a pillar while
contributing zero variance — fixed in the plan itself before the orchestrator task was
even dispatched. Final whole-branch review (opus) returned **Ready to merge: Yes** with
zero Critical/Important findings; two trivial Minor cleanups (silent exception swallowing
in `daily_brief.py`, a stale `excludedHoldings` field in the design doc's example JSON
that was never actually implemented) were applied in one more commit before merge.
**Merged to local `main` via a real merge commit** (main had diverged — an unrelated
map-debt-logging commit landed on main directly mid-session); `feature/fable5-phase3-e1-risk-engine`
pushed to `origin` and **merged to `origin/main` via PR #63**, confirmed via `git fetch` +
`git log origin/main` (`06810b0`), same GitHub PR flow as every prior phase.

**Baseline-verification finding, logged not fixed (see Map Debt section below):** two
pre-existing, unrelated test failures were found while confirming a clean baseline before
starting this sub-spec — a `PROJECT_ROOT` path bug in `test_math_parity.py`, and 3
weekend/market-hours-coupled tests in `test_place_order_gates.py`. Both logged to
`.agent/map-debt.md`, deliberately deferred (out of scope for this sub-spec).

### ✅ Phase 3, Sub-Spec 2 — C2 Market Regime Classifier — COMPLETE, on local `main`, pushed to `origin`
`market_regime.py` — 4-tier composite regime (RISK_ON/NEUTRAL/RISK_OFF/STRESS) that
*wraps, not replaces*, `macro_regime.py`'s existing 3-signal classifier (VIX, SPY-vs-
200d, HYG/LQD credit — reused directly via `_classify_vix`/`_classify_spy`/
`_classify_credit`, no duplicated point tables) and adds three new macro signals
(term-slope via IEF/SHY 20-day % change, breadth = % of active portfolio holdings above
their own 200d SMA, USD strength via UUP vs its own 200d), plus a per-ticker layer
(trend state, momentum percentile, volatility percentile) for every active holding.
3-of-6-signals-unavailable forces STRESS as a fail-safe. Wired **additively** into
`/daily`'s morning brief — a new `REGIME:` line plus `brief["market_regime"]` — without
touching the existing RISK-OFF/NEUTRAL ACCUMULATE gate, which still runs entirely off
the untouched `macro_regime.py`. `macro_regime.py` itself was never modified. Spec:
`docs/superpowers/specs/2026-07-06-market-regime-classifier-design.md`. Plan:
`docs/superpowers/plans/2026-07-07-market-regime-classifier.md`.

Built as 7 TDD-gated tasks via `superpowers:subagent-driven-development` in a fresh
worktree (`.worktrees/feature-fable5-phase3-c2-market-regime`, now cleaned up). Two
tasks (Task 3's WEAKENING-state test, Task 4's momentum-percentile test) had fixture
arithmetic that turned out to be a hidden tie rather than genuine signal — both caught
(one by a task reviewer, one proactively by the controller re-checking the plan before
dispatch) and fixed with hand-verified, non-tied fixtures. Task 6 needed a refactor
round (113-line orchestrator split into 3 helpers) and Task 7 needed two fix rounds: a
real `NameError` from an incomplete variable rename (would have fired on any day with
≥1 ACCUMULATE-band holding — common for this portfolio) caught by the controller
*before* review even ran, then a dropped NEUTRAL-regime terminal reminder restored
after review. **The final whole-branch review (opus) caught two real cross-task bugs no
per-task review could have seen**: the term-slope signal was a dead constant (absolute
IEF/SHY ratio never crosses the ~1.02 threshold against a real ~1.13–1.18 range) and the
DXY signal's polarity was inverted vs. the spec's stated risk-off intent. Both fixed and
independently re-verified against live yfinance data before merge — the user confirmed
fixing now rather than shipping known-bad signals into E2's future data contract.

**Second process incident this phase, now fixed at the root (not just patched):** during
Task 7's fix rounds, a subagent left a stray, uncommitted, *incomplete* copy of its
changes in the **main checkout** instead of only the worktree — despite passing the
standard `cd`-and-confirm-`pwd`/`git branch` check at task start. This is the same
failure class as Phase 2b's Task 3 incident (documented below at the time, never
formally logged), now confirmed as a repeat rather than a fluke. Caught during final
pre-merge `git status` on the main checkout, safely discarded (it was a partial
duplicate of work already properly committed on the feature branch), and fixed forward
per `.agent/rules/self-evolution-policy.md`: new durable rule
`.agent/rules/worktree-subagent-isolation.md` mandates a `git status --short` check in
the **main checkout** (not the worktree) after every subagent-driven-development task,
before generating the review package — catches a leak within one task cycle instead of
only at final merge. Logged as `Status: RESOLVED` (not deferred) in `.agent/map-debt.md`
per the policy's "Repeat: YES requires action on next encounter" rule. **Apply this rule
starting with B5's first task dispatch.**

**Merged to local `main` via a real merge commit** (main had diverged — two doc-fix
commits made directly on main mid-session, one of which duplicated a worktree commit's
content under a different SHA via cherry-pick; `git merge` resolved this cleanly with no
conflicts). `feature/fable5-phase3-c2-market-regime` pushed to `origin` as a
backup/PR source — **not yet merged to `origin/main`**, same GitHub PR flow as every
prior phase, user merges on their own timing.

### ✅ Phase 3, Sub-Spec 3 — B5 Thesis Breakers — COMPLETE, on local `main`, pushed to `origin`
`thesis_breakers.py` — turns the framework's "3 specific, measurable thesis breakers" from
markdown prose into structured, evaluated data. Each holding in `target-portfolio.json` can
carry a `thesisBreakers` array (human-owned, edited only via `update_thesis.py`'s new
`--set-breaker`/`--set-breaker-status`/`--remove-breaker` flags, routed through the
existing versioned `save_thesis()` path). Breakers are `auto` (checked every `/daily` run
against a 5-metric enum — `rsi`, `dcfFairValueGapPct`, C2's `trendState`,
`momentumPercentile`, `pillarAvgScore` — all sourced from data `daily_brief.py` already
computes, never refetched) or `manual` (hand-set status, e.g. NDR/GRR, with a
`reviewCadenceDays` staleness flag). Auto breakers use a **persisted, run-based streak**
(consecutive evaluated `/daily` runs, not calendar days — no historical time-series store
exists or was added) written to a new machine-owned `data/thesis_breaker_state.json`, which
`thesis_breakers.py` owns exclusively — it never mutates `target-portfolio.json`, mirroring
how E1's `risk_snapshot.json` and C2's embedded `market_regime` never do either. A
`TRIGGERED` breaker renders as the very **first content** in `/daily`'s brief — above
overnight gaps, macro/regime/risk context, and every TA-signal-driven section — satisfying
this sub-spec's literal Phase 3 acceptance criterion ("a fixture triggered thesis-breaker
appears at top of triage"), proven by a fixture test asserting the exact line ordering. This
is **visibility escalation only**: it never flips `aiThesis.action` or bypasses
`standingDecision`, same as every other signal in this repo — `brief_recommendations.py` is
untouched. Overrides (holding through a `TRIGGERED` breaker) get an accountability trail via
a new append-only `data/theses/breaker-overrides.jsonl`, written by the daily-loop-agent via
`thesis_breakers.py --log-override`. A new interactive HITL skill,
`plugins/portfolio-advisor/skills/set-thesis-breakers/` (`/set-thesis-breakers`), means
nobody hand-authors raw breaker JSON — it reads a holding's rationale/DCF params/Phase 2b
`analyticsLog`, proposes 2-3 candidate breakers, explains the auto/manual tradeoff in plain
language, and calls the CLI under the hood. Spec:
`docs/superpowers/specs/2026-07-09-thesis-breakers-design.md`. Plan:
`docs/superpowers/plans/2026-07-09-thesis-breakers.md`.

Built as 7 TDD-gated tasks via `superpowers:subagent-driven-development` in a fresh
worktree (`.worktrees/feature-fable5-phase3-b5-thesis-breakers`, now cleaned up). Two
brainstorming-stage design gaps were caught and resolved *before* the plan was written, not
during implementation: the horizon/streak semantics were underspecified (resolved as a
persisted, run-based counter rather than a calendar-day or recomputed-history approach,
since no time-series store exists), and a `dcfFairValueGapPct` auto-metric risked creating a
second, competing path around the `standingDecision` >15%-material-delta gate (resolved as
explicitly notification-only, matching how existing EXIT/REDUCE bands already defer to a
standing decision). One task (5, the `daily_brief.py` triage integration — the task
implementing the literal acceptance criterion) needed a fix round after task-level review: a
manual-breaker-staleness collection block nested 4 levels deep, violating this repo's
"refactor at 3+ nesting levels" rule; extracted to a `_stale_manual_breakers()` helper,
independently re-verified to still render byte-identical output. The final whole-branch
review (opus) returned **Ready to merge: Yes** with zero Critical/Important findings; two
Minor items were fixed in one more commit before merge (a `note`-overwrite behavior that
silently discarded a manual breaker's original rationale on every status update — fixed to
append instead, matching what the docstring already promised; and CLI handlers raising raw
`ValueError` instead of this file's existing `sys.exit(f"ERROR: ...")` convention). A third,
newly-discovered issue surfaced *while verifying* those two fixes: a test comparing
`statusSetAt` against the local machine's date rather than UTC (which the production code
correctly uses, consistent with the rest of the codebase) — a latent bug in Task 4's
original test that only manifests when local time and UTC cross a calendar-day boundary,
independently reproduced by the controller before dispatching the fix, and corrected in one
more commit. Every task's main-checkout isolation was verified clean per
`.agent/rules/worktree-subagent-isolation.md` — no repeat of the C2 leak incident this
phase. **Backfilling real `thesisBreakers` data for the 73 existing holdings is deliberately
out of scope** (matches C2's "produce the data, don't gate yet" pattern) — natural follow-up
work for `thesis-review-agent` or a dedicated pass, not a blocker.

**Merged to local `main` via fast-forward** (main hadn't diverged since the worktree was
branched). `feature/fable5-phase3-b5-thesis-breakers` pushed to `origin` as a backup/PR
source — **not yet merged to `origin/main`**, same GitHub PR flow as every prior phase, user
merges on their own timing.

### ✅ Phase 3, Sub-Spec 4 — E2 Rebalancer v2 — COMPLETE, on local `main`, pushed to `origin`
`rebalancer.py` — formalizes what `/rebalance` + `portfolio_action.py` used to do informally
as an LLM-orchestrated skill. **Drift bands, not point targets**: per-holding band =
`max(±20% relative, ±1.5pp absolute)` around `targetWeight` (config in new
`data/account_policy.json`, not `target-portfolio.json` — `globalSettings.driftThresholdPct`/
`criticalDriftPct` were retired via a one-time migration and `account_policy.json`'s
`bandConfig` is now the single source of truth, read by both the Python engine and
`ThesisService.ts`'s dashboard health-check band formula, independently verified identical).
Inside-band holdings get no order at all. **Three hard-exclude rules** (never appear in
`orders[]`, only in `skippedRestores[]`): EXIT/SELL-rated valuation action on a buy (reads
the latest AI projection's `aiThesis.action`, not `derive_action()`'s unrelated
portfolio-weight-ratio label), price above `targetEntryPrice`, conflicting
`standingDecision`. **Two warn-only checks** (order stays in `orders[]`, never excluded — a
deliberate scope boundary: real veto power belongs to G2's risk-officer-agent, built next):
a risk-budget check against E1's `risk_snapshot.json` (MRC/cluster-variance caps, default
25%/60%, explicitly labeled an estimate), and a flag-only cross-reference against B5's
`thesis_breaker_state.json` (a `TRIGGERED` breaker warns on a proposed buy, never suppresses
it — same visibility-only posture B5 itself uses). **Canada-aware account/tax placement**:
`account_policy.json`'s `accountPreferenceRules` route each buy to exactly one account (real
per-account data from `portfolio.json`'s `tvSnapshot` when synced, heuristic TFSA-full/
RRSP-~1/3-mirror fallback otherwise), the PSU-U.TO same-account funding rule now lives in
code (`ceil(shortfall / price / 100)`), and Cash-account sells get a capital-gains estimate
(forward-looking — no Cash account exists yet in this user's portfolio). **Order-plan
output**: `data/rebalance_plan.json` — `rebalance-portfolio` `SKILL.md` was rewritten to a
thin wrapper (`rebalancer.py --pretty` → present plan → HITL per order, execution path
unchanged); most of its old inline drift-classification/capital-sequencing prose is gone.
Spec: `docs/superpowers/specs/2026-07-09-rebalancer-v2-design.md`. Plan:
`docs/superpowers/plans/2026-07-09-rebalancer-v2.md`.

Built as 11 TDD-gated tasks via `superpowers:subagent-driven-development` in a fresh
worktree (`.worktrees/feature-fable3-e2-rebalancer-v2`, now cleaned up). This phase found
the most task-review bugs of any sub-spec so far, all caught before merge: a real
check-ordering bug in Task 2's brief code; a genuine type-hint mismatch in Task 3 that
required amending the plan itself mid-flight (before any downstream task built against the
wrong shape — `load_account_positions()`'s return signature changed from a 2-tuple to a
3-tuple, splitting account cash out of the per-ticker dict); an **escalating oversell bug**
in Task 4's account-routing math that took two follow-up fix rounds to fully close (round 1
fixed the single-account case, round 2 fixed the multi-account case and proactively found
and fixed a third variant in the remainder-redistribution logic) — the final fix was
verified via algebraic proof plus a 20,000-trial randomized fuzz test, not just the unit
tests; two separate truthiness bugs in Tasks 5 and 6 (`if not cost_basis`/`if not old_mrc`
would have mistreated a legitimate `0.0` value as "missing," both defended with `is None`
checks instead); and **three rounds of "fabricated field" cleanup** in Task 11's skill
rewrite, where each successive full-file re-read found more prose referencing
`rebalance_plan.json` fields/columns/scores that don't actually exist in the engine's real
output — most seriously, an early draft still instructed creating a fabricated TFSA+RRSP
dual-entry buy pattern that actively contradicted the new engine's real single-account-per-
buy routing. The final whole-branch review (opus) returned **Ready to merge: Yes** with zero
Critical/Important findings.

**Post-review, at the user's explicit request** ("i hate seeing errors/failures ignored
after testing"), two pre-existing test failures logged as map debt since before Phase 3 E1
even started were fixed rather than deferred further: `test_math_parity.py`'s `PROJECT_ROOT`
path bug (one-line fix, matches the pattern every other test file in that directory already
used), and `test_place_order_gates.py`'s wall-clock/market-hours coupling (added
`PLACE_ORDER_NOW_OVERRIDE`, an env-var time injection for `place_order.py`'s market-hours
gate — production behavior unchanged when unset, independently reviewed given it touches
live-trading gate code, hardened with a loud stderr warning if the override is ever active).
Both `.agent/map-debt.md` entries are now `RESOLVED`. Full suite: 443 passed, 0 failed (was
439/3 before this cleanup).

**Merge required manual conflict resolution** — the user was actively trading via the web
app during the session (a real, ongoing shares update on an SA LP holding, unrelated to
E2), which collided with `target-portfolio.json` (Task 9's migration rewrites the whole
file). Resolved by treating `main`'s live data as authoritative for all real portfolio
fields (shares, timestamps) while keeping E2's actual intended change (the `globalSettings`
field removal) — confirmed correct via `verify_thesis_sync.py` post-merge. **Merged to
local `main` via a real merge commit** (main had diverged — the user's own concurrent
portfolio/thesis commit landed mid-session, committed first per user's explicit choice
before merging). `feature/fable5-phase3-e2-rebalancer-v2` pushed to `origin` as a backup/PR
source — **not yet merged to `origin/main`**, same GitHub PR flow as every prior phase, user
merges on their own timing.

### 🚦 Git policy going forward
**Standing pattern, now confirmed five times (Phase 1, Phase 2a, Phase 2b, Phase 3 E1, Phase 3 E2):** after each
phase's whole-branch review passes, Claude pushes a dedicated `feature/fable5-phase<N>-<name>`
branch to `origin` as a backup/PR source — **Claude never merges or opens the PR into
`origin/main`.** The user reviews and merges via GitHub's PR flow themselves, on their own
timing. So the full sequence per phase: brainstorm → spec → plan →
`subagent-driven-development` in a fresh worktree → whole-branch review → merge to local
`main` → push `feature/fable5-phase<N>-<name>` to origin → **stop there** — report the
branch is ready, do not merge/PR/touch `origin/main`.

**Git hygiene lesson, worth repeating:** after pushing a backup branch, keep
committing/pushing as work continues — don't let further edits (e.g. to this file) sit
uncommitted after a branch is already pushed, or the backup silently goes stale. Verify any
"is it pushed"/"is it merged" claim with `git fetch` + `git log <ref>` before asserting it's
done, not from memory of having run `git push` earlier.

**Worktree lesson from Phase 2b:** when dispatching implementer subagents that touch git
(commits, mv, symlinks), state the exact worktree path as the first, non-negotiable
instruction and have the subagent confirm `pwd`/`git branch --show-current` before its first
command — a subagent with two valid-looking checkouts on disk (main repo + worktree) can
`cd` to the wrong one silently. Independently verify a subagent's git claims (`git log`,
`readlink`, `git branch --show-current`) rather than trusting the report — this session's
Task 3 incident was caught exactly this way, not by the subagent noticing its own mistake.

### Next step for this session
Phase 3 sub-spec 5 of 5 (the **final** sub-spec — closes out Phase 3) — **G2
risk-officer + red-team agents** (§8 G2 in the guide). Per the guide, G2 defines three new
agent definitions under `agents/`, per the existing daily-loop pattern:
1. **`risk-officer-agent.md`** — consumes E1's `risk_snapshot.json` **and now E2's
   `data/rebalance_plan.json` order-plan format** (E2 shipped since this section of the
   guide was written); has **veto-with-rationale power** over plans that breach cluster
   caps or hit a TRIGGERED thesis breaker (E2 deliberately only *warns* on both —
   `riskGateWarnings`/`breakerWarnings` fields on each order — precisely so this agent
   would be the one with real veto authority, per the scope boundary drawn during E2's
   brainstorming). User can override; override is logged to the ledger. Runs inside
   `/daily` Step 2.5 and `/rebalance`. **This is also where E2's own design spec (§6.3)
   deferred the Phase 3 acceptance criterion** — "a deliberately cap-breaching plan that
   gets vetoed" — pin this as the acceptance test for the risk-officer-agent specifically,
   not re-litigated as an E2 gap.
2. **`red-team-agent.md`** — formalizes the "Adversarial Objectivity Constraint." Invoked
   with a completed analysis artifact (projection JSON, rebalance plan); must produce ≥3
   specific, falsifiable objections + a "what would change my mind" list; explicitly
   forbidden from proposing trades. `/evaluate-stock` and `/rebalance` route their outputs
   through it before user presentation.
3. **`data-quality-agent.md`** (lightweight) — invoked when `data_quality.py` flags
   degradation; decides degrade-gracefully vs halt per a short decision tree. (Guide lists
   this under G2 too; confirm with the user during brainstorming whether it's in scope for
   this sub-spec or a separate follow-up — not decided yet, same as every prior "confirm
   scope first" gate.)

Orchestrators (`daily-loop`, `run-advisor`, `weekly-review`) stay the only user-facing
agents; specialists are invoked, produce structured artifacts, and return. Document the
invocation contract (input artifact path → output artifact path) in `AGENTS.md`, per the
guide. Confirm scope with the user first (brainstorming skill gate) before writing a spec,
same as every prior sub-spec.

**Before dispatching G2's first task**, continue applying
`.agent/rules/worktree-subagent-isolation.md`'s mandatory post-task `git status --short`
check in the **main checkout** after every implementer/fix subagent — used cleanly
throughout B5 and E2 with zero leaks, keep it standard.

**After G2: Phase 3 is fully closed out (5 of 5 sub-specs).** Per the elevation guide, next
up is Phase 4 (Track Record: E3 prediction ledger, E4 backtest harness, B4 earnings
intelligence, G4 structured evolution events) — not yet brainstormed, confirm with the user
whether to proceed directly into Phase 4 or pause for the map-debt sweep below first, since
"once every Fable5 phase (3 through 6) has shipped" was the original trigger condition for
that sweep and Phase 3 will be complete after G2.

### 🗺️ Map debt — sweep `.agent/map-debt.md` before/after Phase 4 kickoff
The two pre-existing test failures logged before Phase 3 E1 started are now **RESOLVED** (fixed
during the E2 session, 2026-07-10, at the user's explicit request — see E2's section above
and `.agent/map-debt.md` for full resolution notes; not re-described here). No other OPEN
entries as of this writing, but re-check `.agent/map-debt.md` directly rather than trusting
this summary, since new entries may have accumulated during G2.

For historical reference: the two `test_math_parity.py`/`test_place_order_gates.py` entries
above are now `RESOLVED` (fixed 2026-07-10 during the E2 session — `PROJECT_ROOT` path fix
and a `PLACE_ORDER_NOW_OVERRIDE` env-var time injection respectively, see
`.agent/map-debt.md` for full detail). The worktree/subagent isolation leak
(`.agent/rules/worktree-subagent-isolation.md`) was already resolved before this file was
last updated and remains resolved — no repeat incidents during E2's 11 tasks.

---

## 🟡 Other open items from 2026-07-02 (not yet resolved, unrelated to Fable5)

1. **BE position** — user said they'd exit manually ("I'll do it myself, standby") after
   overriding the `ALLOWLISTED_CONFLICT` standing decision. TV showed the position still
   fully held (2 TFSA + 1 RRSP) as of the last check — confirm current status before
   assuming it's closed.
2. **CRWV/PANW target-weight update** — proposed (CRWV 5.23%→6.07%, PANW 4.45%→3.65%) to
   lock in the user's manual trades as new standing targets. Never confirmed/written.
3. **TV balance fetch (`fetch_broker_data.py --snapshot`)** — still doesn't fetch account
   balances in the same call as positions (needs a separate `--balances` call). One repair
   attempt (mousedown/mouseup/click dispatch fix to `clickTab()` in `broker_data.js`,
   uncommitted) did not fully resolve it — `totals.totalUSD` still falls back to
   `computed_fallback` until this is fixed properly.

---

## ⚡ Start Every Day With One Command

```
/daily
```

The `daily-loop-agent` handles everything interactively — no checklist to follow manually:
1. Checks portfolio.json freshness → auto-syncs from TradingView if stale
2. Runs the morning brief: macro regime (VIX + SPY 200D + HYG/LQD), TA sweep, conviction scores, earnings calendar
3. Ranks holdings by urgency: IMMINENT events → EXIT signals → REDUCE → ACCUMULATE
4. Walks through each as a card — proposes a trade, waits for your yes/no
5. Offers `/x-news-sweep` on news/catalyst days
6. Logs the session to `plugins/portfolio-advisor/references/evolution-log.md`

**After 7+ daily runs**, the agent surfaces multi-day patterns: consecutive EXIT signals, deteriorating pillars, repeated score drops. It auto-recommends `/strategic-review` when pillar stress is detected — the loop compounds.

**Cadence:**
| Situation | Command |
|-----------|---------|
| Every session | `/daily` |
| Weekend review (markets closed) | `/weekly-review` |
| After 13F filing or major catalyst | `/run-advisor` |
| Evaluating a new stock or thesis change | `thesis-review-agent` |

---

## 📊 Portfolio Snapshot

| | Value | % |
|--|-------|---|
| Total equity | ~$34,643 | 100% |
| USD Cash (raw) | $2,663 | 7.7% |
| PSU-U.TO (56sh) | $5,601 | 16.2% |
| **Cash + equiv** | **$8,264** | **23.9%** |

**Thesis:** Investment Thesis v9.4 · `investment_screener/backend/data/theses/target-portfolio.json`

---

## 🔴 Pending Decisions / Open Items

### 1. Dashboard: Show Entry Prices in Recommendations Table ← **PRIORITY TASK**
The modal currently shows `ACCUMULATE`, `INITIATE`, `TRIM` etc. but **not the target entry price**.
`targetEntryPrice` is now a first-class field in `target-portfolio.json` (added 2026-06-04).

**What needs building:**
- `generate_review_json.py` → include `targetEntryPrice` in the per-holding JSON output
- `InvestmentThesisModal.tsx` (or equivalent frontend component) → display "ACCUMULATE @ $X" instead of just "ACCUMULATE"
- The table column should show: `Action | Entry Price` — e.g. "ACCUMULATE @ $210" for NBIS
- If `targetEntryPrice` is null → show "—" or "at market"

**Only SNDK has a price set so far ($1,350).**
After the dashboard is wired up, run a pass to set entry prices for all ACCUMULATE positions.
Use formula as a starting point: `min(dcf_fair_value * 0.85, current_price * 0.85)` — then adjust per TA.

### 2. GTC Automation for Limit Orders ← **TV CDP BUG**
`/place-order` places limit orders as **Day** duration by default.
TradingView's "Extra Settings → Time in force" dropdown opens correctly via CDP but the
"Good till cancelled" option text isn't found (the dropdown uses fixed-position elements
that escape standard visibility checks).

**Where to fix:** `tradingview-cdp/core/trading.js` → `setGoodTillCancelled()`
The `clickDayAndSnapshot()` diagnostic shows the dropdown opens; the GTC option text
needs a position:fixed-aware selector or coordinate-based click.

**Workaround until fixed:** After placing a GTC limit, manually change duration in
TradingView broker panel → Orders tab.

### 3. Active GTC Limit Order
- **CBRS @ $185 TFSA** — lock-up dip target (Nov 2026). User manually set to GTC on 2026-06-01.
  Do not cancel unless user instructs.

### 4. PSU-U.TO Target Reconciliation
- **Actual: 16.2%** vs **Target: 11.9%** → TRIM signal of ~4.3pp
- User has NOT instructed a trim — PSU is their HISA/cash reserve, they're comfortable overweight
- Do not prompt to trim PSU unless user raises it

---

## 📈 Current Positions & Key Notes

| Ticker | Actual% | Target% | Action | Entry Price | Notes |
|--------|---------|---------|--------|-------------|-------|
| PSU-U.TO | 16.2% | 11.9% | HOLD | — | HISA cash equiv, ~$100/sh, monthly dividend |
| CORZ | 3.7% | 8.4% | ACCUMULATE | — | SA/DCF conflict, allowlisted |
| PANW | 4.0% | 5.9% | ACCUMULATE | — | Q3 FY2026 beat, AI cyber |
| CRWV | 3.7% | 5.5% | ACCUMULATE | — | Vera Rubin, $100B backlog |
| NBIS | 2.1% | 5.5% | ACCUMULATE | — | SA LP 5.6% stake, DCF BUY +100% |
| BE | 4.8% | 5.4% | MAINTAIN | — | $2.6B NBIS fuel cell deal |
| SNDK | 4.2% | 3.7% | MAINTAIN | **$1,350** | Do NOT add above $1,350. DCF FV $1,982, but was valued at $1,333 — real upside at current price only ~14%. 0.8 shares held. |
| CEG | 2.5% | 3.8% | HOLD | — | Underwater −27%, break-even ~$364. Hold, trim on strength only |
| OKLO | 1.9% | 2.8% | HOLD | — | Underwater −37%, break-even ~$101. Hold, trim on strength only |
| CBRS | 1.8% | 2.4% | ACCUMULATE | — | 3 shares held (1 RRSP + 2 TFSA @ $215). $185 GTC active |
| APLD | 2.5% | 1.9% | MAINTAIN | — | SA LP core holding, NOT exit |
| MSFT | 2.5% | 2.4% | MAINTAIN | — | Hold 2 shares, no add/trim |
| DXYZ | 0% | 0% | EXIT | — | Fully exited 2026-06-03, small loss |

---

## 🛠️ Recent System Changes (June 2026)

### New Capabilities
- **`/weekly-review` Command**: Extends sweep functionality to the weekend, conducting a range-based drift analysis and compiling a news sweep prompt.
- **Dynamic ETF/Cash Exclusions**: Grok prompt generators automatically scan `etf_analysis/*.json` and filter them out from standard stock sweeps along with cash.
- **Grok Prompt Templates**: Centralized in `plugins/portfolio-advisor/assets/templates/` (`daily_sweep.md.template` and `weekly_sweep.md.template`) for programmatic generation.
- **Thesis-Template Auto-Sync**: Enforced via self-evolution policy and `thesis-review-agent` execution step. Templates auto-update when strategic pillars shift.
- **Strict Compliance instructions**: Anti-laziness rules prevent Grok from outputting lazy placeholders and enforce single-ticker entries for all listed stocks.
- **`targetEntryPrice` field** — GTC limit price per holding in `target-portfolio.json`
- **Fractional shares** — `place_order.py --shares 0.2` now works
- **Portfolio sync fallback** — after fills: Express API → direct CDP snapshot → Questrade REST
- **`fetch_broker_data.py --snapshot`** — now fetches balances BEFORE positions, writes live `cashUSD` + `totalUSD` to portfolio.json
- **Auto-proceed in `/x-news-sweep`** — no longer waits for "apply" when all items APPROVED/WARN-allowlisted. Only gates on CONFIRM/BLOCKED.

---

## 🚀 Next Session

**Start with `/daily` — it handles the rest.**

Open items to pick up:
1. **Priority build**: Wire `targetEntryPrice` into review JSON + dashboard modal (see item #1 above)
2. **Set entry prices** for all ACCUMULATE positions once dashboard shows them
3. **GTC automation fix** in `trading.js` → `setGoodTillCancelled()` (see item #2 above)
4. **SNDK**: Do not add unless price drops to $1,350 or below
5. **CEG/OKLO**: Hold, only trim when back in profit ($364 / $101 respectively)

---

## 💡 Key Principles (user preferences)

- Recommendations must include **target entry price** — "ACCUMULATE" without a price is incomplete
- **Valuation always matters** — factor in current price vs DCF, not just directional signal
  (e.g. SNDK DCF says BUY +49% but that was calculated at $1,333; real upside at $1,741 is only 14%)
- **PSU-U.TO is HISA/cash equivalent** — not a trade, not a trim candidate unless user says so
- **CEG/OKLO**: only sell when green — both are underwater, hold discipline
- **Account structure**: TFSA is primary (larger), RRSP mirrors at ~1/3 share count
- **GTC limit orders**: after placing via CLI, manually change duration in TradingView broker panel
- **PSU cash source**: PSU-U.TO can be sold to fund new buys if cash is depleted
