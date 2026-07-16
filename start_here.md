# Session Start Briefing — InvestmentToolkit
_Last updated: 2026-07-15 | Phase 5: COMPLETE (shipped, merged to `origin/main`; worktree/branches
cleaned up at `fd2bfaa`) | Phase 6: NOT YET STARTED — no spec, no plan, not even brainstormed. Read
the section immediately below before touching any code._

> **Read this first at the start of every new session.**

---

## 🆕 NEXT: Fable5 Elevation Guide — Phase 6 ("G3" — Skill/Sub-Agent Architecture Cleanup) — not yet scoped

**Phase 6 is the last phase of the original 6-phase Fable5 roadmap** (see the roadmap line
preserved in the Phase 4 section below: "(1) data layer, (2) valuation committee, (3) executable
scoring framework + local TA engine, (4) TradingView/Pine hardening, (5) risk engine + rebalancer +
prediction ledger + backtesting, (6) skills/sub-agent architecture cleanup" — note this numbering
sketch predates how the phases actually shipped in practice; Phases 1-5 as actually built covered
data layer, valuation committee (2a/2b), risk/rebalancer (Phase 3: E1/C2/B5/E2/G2), track record
(Phase 4: E3/B4/G4/E4), and TV/Pine hardening (Phase 5: 5A-5E) — Phase 6 is simply whatever's left:
skill/agent architecture cleanup).

**Unlike every phase before it, Phase 6 has ZERO prior scoping work** — no spec doc, no plan doc,
no brainstorming session. Every other phase in this file had a `docs/superpowers/specs/*-design.md`
and `docs/superpowers/plans/*.md` written *before* any `subagent-driven-development` dispatch. Phase
6 has neither. **Do not start implementing anything for Phase 6 without running
`superpowers:brainstorming` with the user first** — this is exactly the "let's build X" case that
skill exists for, and CLAUDE.md's TDD/TDO rule (no dev without a spec/failing-test first) applies
here just as much as everywhere else in this repo.

### Where the name "G3" / "Phase 6" comes from (verified this session via grep, not assumed)

The term "Phase 6" appears scattered across existing spec/plan docs as forward references, never as
its own document:
- `docs/superpowers/specs/2026-07-05-fundamental-analyst-ta-design.md:275` — "G-series skill/agent
  architecture cleanup — separate phase (6) per the guide."
- `docs/superpowers/plans/2026-07-09-thesis-breakers.md:1738,1890` — "`evals/evals.json` is created
  empty, matching the repo-wide convention (G3 in the elevation guide — filling skill evals is
  explicit Phase 6 scope, not B5's)."
- `docs/superpowers/plans/2026-07-12-phase4-e4-backtest-harness.md:143` and
  `docs/superpowers/plans/2026-07-12-phase5-tradingview-pine-hardening.md:357,364` — both mention,
  as a *speculative, non-committed* aside: "Phase 6 (future) will use Phase 5's audit trails
  (`orders_executed.jsonl`) to train reward models" on execution quality. This is an idea someone
  jotted down while writing those specs, NOT confirmed scope — treat it as one candidate among
  several during brainstorming, not a locked requirement.

There is no single master "elevation guide" document — the guide is a conceptual roadmap referenced
piecemeal across the specs above. If a fresh session needs the full picture, these grep hits are the
only source; don't assume a canonical doc exists somewhere unfound.

### Concrete candidate scope — real data gathered this session, NOT a locked plan

These are inputs for the brainstorming session, not decisions already made:

**1. Skill/agent eval coverage gap** (the most concrete, explicitly-named Phase 6 item — "G3...
filling skill evals is explicit Phase 6 scope"):
- 45 `SKILL.md` files exist across all plugins; only 6 have an `evals/evals.json` at all
  (this count is now stale as of 2026-07-16 — `questrade-token-setup` was archived to
  `ARCHIVE/questrade/` as part of a full Questrade REST integration removal, so it no longer
  counts toward either the numerator or denominator; see the Questrade archive spec/plan under
  `docs/superpowers/specs/` and `docs/superpowers/plans/` dated 2026-07-16).
- Of the original 6: **4 were filled** (`stock-valuation/skills/stock_valuation`,
  `portfolio-advisor/skills/portfolio-health`, `toolkit-manager/skills/questrade-token-setup`
  — now archived, no longer applicable — `toolkit-manager/skills/run-screener`) and **2 were empty
  scaffolds** (`{"evals": []}` — `portfolio-advisor/skills/calibrate-targets`,
  `portfolio-advisor/skills/set-thesis-breakers`).
- **37 of 45 skills have no `evals/` directory at all** — including every skill built during Phases
  3-5 (`rebalance-portfolio`, `x-news-sweep`, `daily-loop`, `daily-brief`, `place-order`,
  `cancel-order`, `alert-list`, `alert-sync`, `pine-inject`, `norberts-gambit`, and ~27 more). Full
  list obtainable via: `find plugins -name "SKILL.md" | while read f; do d=$(dirname "$f"); [ -f
  "$d/evals/evals.json" ] || echo "$d"; done`.
- **All 11 `agents/*.md` files have zero evals coverage** (`risk-officer-agent`, `red-team-agent`,
  `data-quality-agent`, `daily-loop-agent`, `thesis-review-agent`, `weekly-review-agent`,
  `portfolio-advisor-orchestrator`, `single-stock-advisor`, `ta-guide`, `toolkit-onboarding-guide`,
  `tradingview-onboarding`).
- The 4 filled examples (especially `stock_valuation`'s — it has 8 evals covering trigger accuracy,
  schema compliance, adversarial robustness, sycophancy resistance, degradation, and a near-miss
  routing case, plus explicit `benchmark_targets`) are the template to replicate, not a from-scratch
  design exercise.

**2. `AGENTS.md` invocation-contract documentation** — flagged as a known gap back when Phase 3
closed out (see that section further down this file): "input artifact path → output artifact path
per specialist agent" was never written for Phase 3's 5 new agents, and is presumably even further
behind now after Phase 4/5 added more skills/agents. `AGENTS.md` (repo root, 160 lines) is a curated
routing guide, not exhaustive — worth an audit pass to confirm it still reflects reality (e.g. does
it mention `/place-order`, `/tv-alert-list`, the risk-officer/red-team/data-quality agents, the
Phase 4 track-record commands?) before deciding whether/how to expand it.

**3. Anything else the user wants folded in** — "skill/agent architecture cleanup" is broad; the
brainstorming session should also ask the user directly whether there's dead/superseded skill
content worth pruning (per `.agent/rules/skill-deletion-guard.md` — deletions need that rule's
process, not ad-hoc `rm`), whether the `plugins/*/agents/` vs `plugins/*/skills/` split still makes
sense given how much has been built since it was first drawn, and whether the speculative "reward
modeling on execution quality" idea (item 4 above) is worth pursuing now that Phase 5's audit trail
(`orders_executed.jsonl`) actually exists and is live-wired (see the Phase 5 section immediately
below).

### First action for the next session

Run `superpowers:brainstorming` with the user, presenting the candidate scope above as a starting
menu, not a plan. Only after that produces a real spec (`docs/superpowers/specs/2026-07-XX-phase6-*-design.md`)
and plan (`docs/superpowers/plans/2026-07-XX-phase6-*.md`) should any `subagent-driven-development`
dispatch happen — same sequencing every prior phase followed.

### Loose ends from Phase 5 — now fully resolved (2026-07-15, same session as the merge)

- **Worktree removed**: `.worktrees/feature-fable5-phase5-tradingview-pine-hardening` is gone
  (`git worktree remove --force`, after confirming its commits were fully merged into `main` via
  `git merge-base --is-ancestor ... main`). The uncommitted, duplicated `predictions.jsonl` entries
  (5 lines by the time of cleanup — the bug below fired 3 times across the session) were inspected
  entry-by-entry and confirmed to be pure timing artifacts with no distinct analytical content (same
  consensus EPS within each date group, only incidental intraday price-snapshot differences) —
  discarded, not preserved.
- **Both fully-merged feature branches deleted**, local + `origin`, confirmed via `git branch -vv`,
  `git branch -r`, and an independent `git fetch --prune` + `git ls-remote --heads origin`:
  `feature/fable5-phase5-tradingview-pine-hardening` and
  `feature/checkpoint-conventions-pass-and-tv-alerts` (the latter already merged via PR #74, just
  never cleaned up).
- **Test-isolation bug — logged, not fixed**: `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_*`
  makes a real yfinance call and appends to the real `data/predictions.jsonl` merely by running the
  test suite (reproduced 3 times this session alone). Now logged in `.agent/map-debt.md` under
  "harvest-earnings tests mutate the real, tracked predictions.jsonl instead of a fixture" (Status:
  OPEN) — a good, small, unrelated-to-Phase-6 fix to knock out early in a fresh session (isolated,
  quick, not gating). Recommended fix already written up there: find the fixture/path-override
  pattern other `py_services` tests already use (e.g. `test_place_order_gates.py`'s
  `PLACE_ORDER_PORTFOLIO_PATH` env override) and apply the equivalent to whichever function resolves
  the real `predictions.jsonl` path.

---

## ✅ COMPLETE: Fable5 Elevation Guide — Phase 5 (TradingView/Pine Hardening) — all 40 tasks shipped, merged, pushed

**Phase 5 at a glance:**
- **5A (8 tasks)** — TV CDP Resilience: health checks, recovery, retry logic, circuit breaker,
  caching, error logging, integration into the real 19-call-site `tv_call()`.
- **5B (8 tasks)** — Pine Script Manager: registry, validation, injection, version control,
  rollback, library management, auto-discovery, `/daily` integration.
- **5C (7/8 tasks, 1 intentionally skipped)** — Alert & Signal Sync: creation (+ condition-shape
  bugfix), dedup, state sync, metadata, E3 linking, webhook receiver ⏭️ (skipped, user decision),
  correlation, advisory-only `/daily` integration.
- **5D (8 tasks)** — Data Window Extraction: reader, OHLCV validation, indicator extraction,
  caching, cache-hit logic, lag-tolerant wrapper, validation harness, order-execution integration
  (liquidity score + RSI veto).
- **5E (8 tasks)** — Order Execution & Risk Gates: MRC gate, cluster variance gate, thesis breaker
  veto, order-size gate, balance gate, composite gate check, post-trade validation (trade log
  matching + slippage check), non-blocking audit trail logger. All in
  `investment_screener/backend/py_services/order_risk_gates.py`.

Spec: `docs/superpowers/specs/2026-07-12-phase5-tradingview-pine-hardening-design.md`. Plan:
`docs/superpowers/plans/2026-07-12-phase5-tradingview-pine-hardening.md`.

### Whole-branch review found a real gap — closed before merge, not papered over

The first whole-branch review (opus, against `4170ad5..b3b799e`, 51 commits) came back **"Ready to
merge: With fixes"** — code quality was strong (390/390 Phase 5 tests green, no crash bugs, no
sacred-file risk) but it found two real Important findings, not cosmetic ones:

1. `order_risk_gates.py`'s `check_risk_gates()` (5E's composite of all 5 order-risk gates) had
   **zero production callers** — a fully-tested but entirely dormant safety layer.
2. `data_window_validator.py`'s `check_order_data_readiness()` (5D-8: liquidity score + RSI-overbought
   veto) was also never called — 5E-4 built a separate ADV-based liquidity check instead of
   consuming 5D-8's signal, leaving 5D-8 orphaned.

Given the choice to either (a) actually wire the gates in, or (b) document the gap as deferred and
ship the library-only version, **the call was made to wire it in for real** — this is the
project's live-trading order-placement path, and "risk gates on every trade" was the spec's
headline promise; shipping it dormant would have been misleading. A follow-up fix (commit
`4b2bd6d`) added `build_portfolio_state_for_order()` (reuses `risk_engine.py`'s pillar-map pattern
+ `portfolio_io.py`'s broker-authoritative weight computation, never shares×price) and
`check_data_readiness_gate()` (the missing 5D→5E connection — vetoes BUY orders on a live
RSI-overbought Data Window read, surfaces liquidity score informationally), then wired
`check_risk_gates()` into `place_order.py`'s `--preflight` (blocking with exit code 6 +
`RISK_GATES_BLOCKED` unless `--override-risk-gates`, audit-logged either way) and 5E-7's post-trade
validation into `--submit`. A second, narrower re-review (opus, `b3b799e..ea5955a`) independently
traced the real call chain end-to-end and confirmed both gaps genuinely closed (not stubs), symlink
integrity intact, and returned **"Ready to merge: Yes."** A trivial Minor finding (`orders_executed.jsonl`/
`alerts_state.jsonl` missing from `.gitignore`) was fixed in the same pass (commit `ea5955a`).

### Merge

Merged `feature/fable5-phase5-tradingview-pine-hardening` into local `main` via a real merge commit
(`54b4276`) — one real conflict in `tv_cdp_health.py`'s module docstring (main's "coding conventions
pass" had reformatted the header while Phase 5 added real new functions to the same file; resolved
by keeping the newer structural convention but populating it with the real, complete function list
rather than the stale/lossy template). Full `py_services/` suite post-merge: **1109 passed, 35
failed** — the 35 are the exact same pre-existing/environmental failures already present before this
branch (jsonschema version mismatch in `earnings_expectations`/`evolution_events` tests, a missing
`chrome-remote-interface` npm dependency affecting 2 `place_order.py` subprocess tests) — zero
regressions from the merge. Pushed straight to `origin/main` (confirmed via `git fetch` +
`git log origin/main`), per this project's standing git policy — no separate PR-wait step.

### Two known loose ends, deliberately not touched this session

1. **Worktree left in place**: `.worktrees/feature-fable5-phase5-tradingview-pine-hardening` was
   NOT removed. It has an uncommitted, real (if duplicated) harvested-earnings entry in
   `investment_screener/backend/data/predictions.jsonl` (2× the same AAPL 2026-07-14 consensus,
   harvested ~90 seconds apart — an artifact of the known test-isolation bug below, not anything
   this session did deliberately). `git worktree remove` will refuse while this is dirty; discarding
   it was deliberately left as a call for the user, not force-removed. Safe to delete once reviewed
   (`git worktree remove --force` after inspecting/discarding, or `git stash`/copy the one unique
   line into `main`'s copy first if it's worth keeping).
2. **Newly observed, real, pre-existing bug — not part of Phase 5, not fixed this session**: running
   `investment_screener/backend/tests/py_services/test_harvest_earnings_expectations_*` makes a
   REAL live yfinance network call and appends a REAL entry to the tracked
   `data/predictions.jsonl` as a side effect of merely running the test suite — not test-isolated at
   all (should be writing to a `tmp_path` fixture, not the live data file). This was triggered twice
   this session (once by the fix subagent, once by this session's own post-merge full-suite run) and
   reverted both times from the main checkout, but the root cause (wherever `harvest_predictions.py`
   resolves its output path in test context) is unfixed. Worth a dedicated small fix — log to
   `.agent/map-debt.md` if not already there.

### Established gotchas from this session, worth keeping for next time

- **Bash cwd drift**: the shell's cwd repeatedly drifted back to the main checkout mid-session.
  Always run `pwd` immediately before any `git log -1` / merge-related git command.
- **Worktree isolation**: checked `git status --short` in the main checkout after every subagent
  dispatch — zero leaks across all of Phase 5 (40/40 tasks) and both fix/review subagents this
  closing session.
- **Model choice**: `sonnet` for implementers/fixers, `opus` for whole-branch/re-review — consistent
  with this project's established finding that `haiku`-tier dispatches have leaked to `main` before,
  `sonnet`-tier never has.
- **Stash discipline**: the main checkout had real pre-existing uncommitted WIP
  (`context/events.jsonl`, `plugin-sources.json`, `skills-lock.json`, 2 untracked spec docs) sitting
  on `feature/checkpoint-conventions-pass-and-tv-alerts` (already merged via PR #74) when this
  session needed to switch to `main` for the Phase 5 merge — stashed with `-u`, switched, merged,
  pushed, then popped back cleanly onto `main`. Zero work lost.

---

## ✅ COMPLETE: Fable5 Elevation Guide — Phase 4 fully closed (E3/B4/G4/E4 shipped, 4 of 4 sub-specs done)

**Context:** Fable5's 6-phase roadmap: (1) data layer, (2) valuation committee, (3) executable 
scoring framework + local TA engine, (4) TradingView/Pine hardening, (5) risk engine + rebalancer 
+ prediction ledger + backtesting, (6) skills/sub-agent architecture cleanup.

**Phase 3 (§9: Risk & Rebalancer) — COMPLETE, all 5 sub-specs on `origin/main`:**
E1 (risk engine, PR #63), C2 (market regime), B5 (thesis breakers), E2 (rebalancer v2), 
G2 (risk-officer + red-team + data-quality). Full integration into `/daily` and rebalance workflows.

**Phase 4 (§10: Track Record) — COMPLETE, all 4 sub-specs shipped to `origin/main`:**
- ✅ **E3 (Prediction Ledger)** — Commit 61bcd7e. Captures action ratings, DCF values, rebalance 
  orders, breaker forecasts into `data/predictions.jsonl`. Grades outcomes weekly. Feeds track-record 
  report (rolled hit-rate stats by claim type).
- ✅ **B4 (Earnings Intelligence)** — Commit 4496fec. Harvests yfinance consensus, grades BEAT/MEET/MISS, 
  emits `earnings_expectation` claims to E3 ledger. Wired into `/daily` (consensus display) and 
  `/weekly-review` (grades + correlations).
- ✅ **G4 (Structured Evolution Events)** — Commit 7304621. Logs 6 event types (earnings catalysts, 
  breaker overrides, rebalances, large price moves, dividends, forced exits) to `data/evolution_events.jsonl`. 
  Tracks 7d/30d outcomes (NULL until window passes, no lookahead bias). Weekly correlation report.
- ✅ **E4 (Backtest Harness)** — Commit ac627f8. Historical rebalance replay via target-portfolio.json 
  versioning, counterfactual order execution (±5% threshold, ±1d timing), execution quality analysis, 
  E3 correlation report. Complete feedback loop: predictions → grades → correlations → counterfactuals.

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

### ✅ Phase 3, Sub-Spec 5 — G2 Risk Officer + Red Team + Data Quality — COMPLETE, on local `main`, pushed to `origin`
Closes the two gaps E2 deliberately left open and formalizes a third. **`risk_officer.py`**
(new) — turns E2's warn-only `riskGateWarnings`/`breakerWarnings` (already computed on every
`rebalance_plan.json` order) into a real veto: any order carrying either warning is vetoed
by default, reusing E2's exact thresholds (no new numeric caps). `classify_orders()` +
`compute_risk_officer_review()` write a new `data/risk_officer_review.json`; overrides are
logged to a new append-only `data/risk_officer_overrides.jsonl` via `--log-override`,
mirroring B5's `log_breaker_override()` pattern exactly. **`risk-officer-agent.md`** wraps
it: real enforcement inside `/rebalance` (new SKILL.md Step 1b — vetoed orders pulled into a
"⛔ Vetoed by Risk Officer" section, override handled one order at a time, always logged),
read-only banner inside `/daily` (new Step 1.5 — only surfaces a one-line warning if a
*fresh* `/rebalance` plan on file has vetoes; never generates a plan itself, never blocks
Step 2/3). **Pins Phase 3's deferred acceptance criterion** ("a deliberately cap-breaching
plan that gets vetoed") via `test_compute_risk_officer_review_writes_file_and_round_trips`.

**`red-team-agent.md`** — no new engine, purely conversational, `tools: ["Read"]` only
(mandate enforced at the tool-permission level, not just prose): given a projection or
rebalance plan, produces ≥3 falsifiable objections + a "what would change my mind" list,
explicitly forbidden from proposing trades. **Mandatory on every run** — new Step 1c in
`/rebalance` and new Step 4.5 in `/evaluate-stock`, both printing objections above the final
recommendation, never persisted to disk.

**`data-quality-agent.md`** — closes a real gap found mid-build: `market_data.py`'s
`dataQuality` signal (staleness + cross-source conflicts) existed since Phase 1 but every
caller silently dropped it, so nothing could ever trigger this agent. Fixed by wiring
`dataQuality` passthrough into `get_prices()` (new `_price_staleness()`) and into
`wacc.py`/`comps_valuation.py`/`peer_bench.py`/`technicals.py`'s own outputs — all four
already called `get_fundamentals()`/`get_prices()` but dropped the field. New mandatory
checks in `/evaluate-stock` Steps 3.5/3.6 dispatch the agent on a flag; its 5-rule
DEGRADE/HALT decision tree (documented in the agent file) treats `wacc`/`comps` as
gate-feeding (can HALT before persistence on a ≥15% conflict) and `peerBench`/`technicals`
as informational-only (always DEGRADE). **Known limitation, documented not fixed:**
`comps_valuation.py` never threads a `cik` into its `get_fundamentals()` calls, so EDGAR is
always skipped and its `dataConflicts` is structurally always empty — the conflict-driven
HALT path is effectively `wacc`-only today; a one-line note was added to both
`data-quality-agent.md` and the SKILL.md rather than fixing the cik-threading itself
(explicitly out of scope, flagged by the final whole-branch review).

Built as 11 TDD-gated tasks via `superpowers:subagent-driven-development` in a fresh
worktree (`.worktrees/feature-fable5-phase3-g2-risk-officer-red-team`, now cleaned up).
**Two more worktree-isolation leaks this session** (Tasks 4 and 9 — both `haiku`-tier
dispatches committed straight onto `main` despite the mandatory `pwd`/`git branch` check
instruction), a third and fourth occurrence of the same failure class documented for C2 and
Phase 2b — both caught immediately (review-package showing "0 commits" for the expected
range) and fixed identically each time: cherry-pick the commit onto the worktree branch,
`git revert --no-edit` on `main` (never `reset --hard`, since a concurrent, unrelated
`/daily` session had real uncommitted portfolio/thesis edits in the main checkout the whole
time — verified untouched after every fix). Observed pattern worth carrying forward:
`haiku`-tier implementer dispatches leaked twice this session, `sonnet`-tier dispatches
never did — later tasks in this session were deliberately switched to `sonnet` for exactly
this reason. One real bug also caught by the final full-suite run (not by any task review):
`test_price_staleness_boundary_is_inclusive_not_stale` used local `date.today()` while the
function under test compares against UTC time — flaky right at the local/UTC day boundary,
fixed to use `datetime.now(timezone.utc).date()`. Final whole-branch review (opus) returned
**Ready to merge: With fixes** — one Important finding (the comps `cik` limitation above,
documented rather than fixed) and a handful of confirmed-Minor items (stale docstrings not
mentioning the new `dataQuality` key, a couple of cosmetic test-style inconsistencies) — all
resolved or explicitly deferred before merge.

**Merged to local `main` via a real merge commit** (main had diverged — the same concurrent
`/daily` session's uncommitted edits, verified zero file overlap with this branch's diff
before merging, confirmed still intact and untouched after). `feature/fable5-phase3-g2-risk-officer-red-team`
pushed to `origin` as a backup/PR source — **not yet merged to `origin/main`**, same GitHub
PR flow as every prior phase, user merges on their own timing.

### 🚦 Git policy going forward
**CORRECTED 2026-07-10 — this section was wrong for six phases.** It previously said
"Claude never merges or opens the PR into `origin/main`." The user's actual standing
instruction (stated directly, superseding this file): **after a worktree is merged into
local `main`, push straight to `origin/main`, every change, every phase — no waiting on a
separate PR review step.** So the corrected sequence per phase: brainstorm → spec → plan →
`subagent-driven-development` in a fresh worktree → whole-branch review → merge to local
`main` → **push `main` directly to `origin/main`.** Do not stop at a feature-branch-only
push and wait for the user to PR it themselves — that was this file's own error, not the
user's actual preference, and it cost real time/trust to sort out. If a feature branch was
already pushed separately (habit from the old, wrong policy), that's harmless — just also
push `main` itself.

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
**Phase 3 is fully closed out (5 of 5 sub-specs: E1, C2, B5, E2, G2 all shipped).** Per the
elevation guide, next up is **Phase 4** (Track Record: E3 prediction ledger, E4 backtest
harness, B4 earnings intelligence, G4 structured evolution events) — not yet brainstormed.
Confirm with the user whether to proceed directly into Phase 4 or pause for the map-debt
sweep below first, since "once every Fable5 phase (3 through 6) has shipped" was the
original trigger condition for that sweep and Phase 3 is now complete. Also worth raising:
`.agents/AGENTS.md`'s invocation-contract documentation (input artifact path → output
artifact path per specialist agent) was never written for E1/C2/B5/E2/G2's five new agents
— a natural pre-Phase-4 cleanup item, not blocking.

**Worktree-isolation lesson from this session (G2), worth repeating going forward:** two more
leaks occurred (Tasks 4 and 9, both `haiku`-tier dispatches), a third/fourth occurrence of
the same failure class first seen in Phase 2b and repeated in C2. Both were caught
immediately via `review-package` showing "0 commits" for the expected range (not just
`git status --short`, which only catches *uncommitted* leaks — a clean commit landing on
`main` needs `git log --oneline` checked too) and fixed via cherry-pick + `git revert`
(never `reset --hard`, given the concurrent `/daily` session's real uncommitted work in the
main checkout). The pattern observed this session — `haiku`-tier implementers leaked twice,
`sonnet`-tier dispatches never did — is not proven causally, but is a reasonable prior for
future sessions: consider defaulting mechanical-but-git-touching tasks to `sonnet` rather
than the cheapest tier, or add the same "every git command starts with `cd <path> &&`"
reinforcement used in G2's later dispatches (Tasks 5-11) as a standing instruction rather
than something added mid-session after the first leak.

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
- **Portfolio sync fallback** — after fills: Express API → direct CDP snapshot (Questrade REST tier retired 2026-07-16 — see Questrade archive spec/plan)
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
