# Portfolio Advisor — Evolution Log

Each daily-loop session appends an entry here. The agent reads this log to detect
patterns: consecutive EXIT signals, pillar stress, repeated user overrides, tool
regressions. This is the memory that makes the loop smarter over time.

---

<!-- Sessions are appended below in reverse-chronological order (newest first) -->

## 2026-10-04 — One closing refresh for strategic, daily and weekly reviews; targets re-based to holdings

**Trigger:** After a strategic review, the Daily Brief and Portfolio Advisor pages still showed the old picture: a 3-day-old brief with blank momentum cards, GEV as EXIT, four INITIATE names, and none of the review's trims. User direction (2026-10-04): use existing code, and have `/strategic-review`, `/daily` and `/weekly-review` all run the same code at the end.

**Root cause:** Each workflow ended differently and none republished the brief or regenerated the review JSON after its decisions, so the pages drifted from what the session concluded.

**Actions Taken:**
1. One standard function: `refresh_all.py --publish` (`run_refresh(publish=True)`). `refresh_all.py` was already the shared post-change orchestrator (called by `update_targets.py`, `update_thesis.py` and both broker syncs) but stopped at roles and the thesis blueprint. `--publish` adds the review JSON, the brief republish and `verify_refresh.py`. Default behaviour is unchanged so the frequent callers stay fast. `generate_review_json.py` gained `--yes` so the chain runs unattended.
2. 13 skills now end with that one call: strategic-review, daily-loop, weekly-review, calibrate-targets, update-portfolio-targets, news-sweep, thesis-review, 13f-analyze, set-thesis-breakers, stock-intake, update-stock-analysis, tv-portfolio-sync, questrade-sync-portfolio. Not added: portfolio-health (read-only), rebalance-portfolio (plan only), norberts-gambit (manual broker steps). Only `/strategic-review` scaffolds the narrative review with `generate_review.py`; running it daily would replace "Latest Review" with an empty scaffold.
3. Targets re-based (user decision): targets = actual holdings; RIOT, PANW, BE, IREN and MU cut by one third with 6.2pp moved to cash (12.8%); NVDA, META, VST, PSIX to 0%; GEV 0% to 1.7%. Total 100.00% (was 97.40%). Written with `update_targets.py --write --blueprint`.

**Open:**
- The Daily Brief's recommendations come from conviction bands, so it shows MU, PANW and RIOT but not BE or IREN (their stored DCF action is MAINTAIN). It also proposes selling all of MU, not a third. Refreshing BE and IREN valuations is the existing route to fix that.
- `generate_review.py` still prompts before overwriting a same-day narrative review.
- `daily_brief.py` reported "Prediction harvest skipped: unable to open database file" (non-blocking, not investigated).
- Lifecycle labels were not changed: GEV still `exit`, INTC/NVDA/META/VST/PSIX still `initiate` at 0% targets.
- `strategy_pillar` targets still disagree with the sum of holding targets.

---

## 2026-10-04 — Test suite repair: 49 failing tests, and tests that wrote to real data

**Trigger:** After PR #237 the Python suites had ~50 failures on `main`. User asked for them to be fixed.

**Incident (Tier 2):** `test_stock_intake_persist.py` ran the intake CLI with no database override, so every run of the suite in the main checkout overwrote real `domain_model.sqlite` rows: INTC (target weight, lifecycle status, standing-decision reason, price levels) and BE (agent rationale). This happened during a baseline run on 2026-10-04 at 18:46Z. `test_peer_bench.py` likewise fetched and cached fundamentals for fake tickers (`fundamentals_PEERA/PEERB/TARGET.json`) in the real cache.

**Root causes found:**
1. **Tests left behind by storage cutovers** — order audit trail, trade log, prediction ledger and TA-sweep tests still targeted retired JSON/JSONL paths after the SQLite/ledger waves.
2. **Mocks that never applied** — `patch.dict("sys.modules", {"yfinance": ...})` against a module that imports `yf` at load time, so 12 "unit" tests hit live Yahoo Finance; `mock_date` used where the patch was bound as `mock_date_class`.
3. **Split database reads (real bugs)** — `portfolio_action.py --db` and `order_risk_gates.build_portfolio_state_for_order(db_path=...)` used the override for targets/pillars but always read holdings from the real database.
4. **Prior earnings beat rate always 0% (real bug)** — `get_earnings_context()` searched for "BEAT" inside the prediction ID; the BEAT/MEET/MISS grade was computed and discarded.
5. **Time- and randomness-dependent tests** — a hard-coded "future" date that passed in July; random DCF inputs landing in the validator's decimal-fraction band (~1 run in 15).
6. **Hand-copied schema in a test** drifted from the real DDL (`as_of` vs `fetched_at`); the same test existed twice under one filename, breaking combined collection.

**Actions Taken:**
1. `stock_intake_persist.py` takes `--db-path` / `db_path`; its tests run on a seeded temp database and assert the real file is untouched.
2. `portfolio_io.load_portfolio_state(..., db_path=None)`; `portfolio_action.py` and `order_risk_gates.py` pass their override through, so one run reads one database.
3. `EarningsGrade` stores `earningsGrade` and `epsSurprisePct`; the beat rate is counted from them, matched on the exact `TICKER:earnings_expectation:` prefix.
4. Stale tests ported to the current APIs; mocks pointed at `earnings_expectations.yf`; dates pinned with a real `date` subclass; parity test seeded.
5. Retired: the real-repo `ta-sweep-results.json` audit test (per its own docstring), `test_pine_advisor_skill.py` (skill no longer exists), and the duplicate backend `test_manage_watchlist.py`.

**Verification:** all three suites in one invocation, with a copy of real data in the worktree: 1803 passed, 2 failed, 5 skipped; the 2 failures are `test_place_order_gates` needing `node_modules` (they skip when it is present and no broker is connected). A before/after file snapshot showed the run wrote nothing under `data/` or `plugins/`.

**Open:** real INTC/BE rows need restoring from the pre-run snapshot (user approval required). `get_earnings_context()` has no production caller. `tv_pine_manager.py` is referenced by no skill. `TestFetchSourceLive` needs a live TradingView session.

---

## 2026-10-04 — Strategic Review Upgrade: Master Portfolio Coordinator & Technical Ingestion (Tier 1 Evolution)

**Trigger:** User identified that `/strategic-review` description and workflow were overly academic/narrow, disconnected from the interactive needs of the user (options 1-5, ranked priorities to trim, exit, accumulate, initiate), and isolated from the live technical momentum and conviction scoring engines.

**Root Causes & Friction:**
1. **Academic Scoping**: `SKILL.md` framed `/strategic-review` as an abstract "formula improvement" tool rather than an executive review of what to sell, trim, accumulate, and initiate.
2. **Misleading Quickstart**: Pointed to `update_targets.py --show` rather than `scan_opportunities.py` or `generate_review.py`.
3. **Technicals & Conviction Silo**: `scan_opportunities.py` and `generate_review.py` did not incorporate RSI, ADX, or composite conviction bands from `compute_conviction_scores.py` / `intelligence.sqlite`.
4. **Disjointed Workflow**: Strategic review, target calibration, and portfolio rebalancing were siloed into disconnected commands requiring manual user bridging.

**Actions Taken:**
1. **Engine Enhancement (`scan_opportunities.py`)**: Added `load_conviction_scores` with smart sibling DB resolution and `_enrich_with_scores` so every opportunity table (EXIT, TRIM, ACCUMULATE, INITIATE, CONFLICTS) outputs live RSI, ownership-aware conviction bands, and composite scores.
2. **Template Modernization**: Replaced legacy `portfolio.json` mentions with `domain_model.sqlite`.
3. **Interactive Coordinator Architecture (`SKILL.md`)**: Re-architected `/strategic-review` into a 4-phase master coordinator:
   - Phase 1: Multi-source opportunity scan across live SQLite, DCF, and technicals.
   - Phase 2: Executive critical review of capital trapped, pillar stress, and strategic conflicts.
   - Phase 3: Interactive Socratic menu (Options 1–5) guiding user focus.
   - Phase 4: Downstream handoff directly into `/calibrate-targets` and `/rebalance-portfolio`.
4. **Verification**: Added unit tests in `test_scan_opportunities.py` (9/9 pass) and verified `audit_skill.py` (PASS, 0 warnings).

---

## 2026-10-04 — Daily Brief Technical Telemetry Backfill & Ownership-Aware Conviction Logic (Tier 1 Evolution)

**Trigger:** Technical momentum cards on `/daily-brief` were rendering blank (null RSI/ADX/Vol Bias) and conviction score tables exhibited logical incoherence by showing `HOLD` / `REDUCE` on watchlist assets that the portfolio does not own. In addition, 15 decommissioned tickers were requested for permanent removal.

**Root Causes & Friction:**
1. **TradingView Headless Failure**: When TradingView Desktop was offline or resting on `app/new-tab`, CDP sweeps skipped or failed, leaving `intelligence_event` rows for TA null.
2. **Missing Indicator Plots**: `ai-ta-levels.pine` lacked explicit `plot(..., display=display.data_window)` for RSI and RSI-based MA, causing Data Window queries to return null for these indicators.
3. **Band & DCF Ownership Agnosticism**: `_band()` and `_normalize_dcf_action()` in `compute_conviction_scores.py` scored all tickers solely on numerical points without verifying whether the asset was held (`actual_weight > 0`).

**Actions Taken:**
1. **Watchlist Purge**: Permanently purged 15 tickers (`KRC`, `PUMP`, `TSEM`, `LBRT`, `RKLB`, `DXYZ`, `AXTI`, `PLUG`, `DRAM`, `DDOG`, `IBIT`, `ETHA`, `HUMN`, `NKE`, `AAOI`) across `domain_model.sqlite`, `intelligence.sqlite`, and `observations.jsonl`.
2. **Pine Script Telemetry**: Added `rsi_val = ta.rsi(close, rsi_len)` and Data Window plots (`"RSI"`, `"RSI-based MA"`) to `ai-ta-levels.pine`.
3. **CDP Auto-Navigation & Local Fallback**: Enhanced `tradingview-cdp/connection.js` to navigate from `new-tab` to chart automatically. Added `backfill_missing_technicals()` and `run_headless_sweep()` via `technicals.py` in `ta_sweep_batch.py` and `daily_brief.py`.
4. **Ownership-Aware Actions**:
   - Held assets (`actual_weight > 0`): Bands limited to `ACCUMULATE`, `HOLD`, `REDUCE`, `EXIT`; DCF actions limited to `ACCUMULATE`, `HOLD`, `TRIM`, `EXIT`.
   - Non-held assets (`actual_weight == 0` / watchlist): Bands limited to `INITIATE`, `WATCH`, `AVOID`; DCF actions limited to `INITIATE`, `WATCHLIST`, `AVOID`.
5. **Frontend Alignment**: Updated `DailyBriefPage.tsx` types and styling for `INITIATE` and `AVOID`, prioritized held positions in Technical Momentum Cards, and confirmed zero TypeScript build errors.

---

## 2026-10-04 — Weekly News Sweep Multi-Model Catalyst Integration & Projection Sync (Tier 1 Evolution)

**Trigger:** Applied multi-agent triangulated news catalysts (Claude, ChatGPT, Gemini, Grok) across core portfolio and watchlist holdings via `apply_catalyst.py`, synchronized SQLite domain model with projection JSON files, and generated refreshed daily brief snapshot.

**Actions Taken:**
1. **Material Catalyst Ingestion (`domain_model.sqlite`)**:
   - Applied calibrated probability shifts and updated `agent_rationale` across 12 tickers:
     - `MU`: FQ4 beat & raise ($54.2B rev, $32B LT agreements) $\rightarrow$ FV $764.85 $\rightarrow$ $829.45.
     - `AMD`: World Labs $8.2B acquisition $\rightarrow$ FV $391.28 $\rightarrow$ $421.20.
     - `AVGO`: Anthropic $42B financing deal / TPU lease $\rightarrow$ FV $395.25 $\rightarrow$ $420.89.
     - `LITE`: FQ4 revenue doubling (+109% y/y to $1B), optical switch ramp $\rightarrow$ FV $271.61 $\rightarrow$ $290.32.
     - `COHR`: PhotonLink launch with 20+ active engagements $\rightarrow$ FV $201.88 $\rightarrow$ $229.64.
     - `APLD`: Polaris Forge 1 energized 75 MW (250 MW live) $\rightarrow$ FV $24.09 $\rightarrow$ $27.97.
     - `CLSK`: $2.276B senior notes (7.875%) for Meta Sandersville lease $\rightarrow$ FV $16.72 $\rightarrow$ $20.17.
     - `ORCL`: Force majeure notice on Project Jupiter power delays $\rightarrow$ FV $305.48 $\rightarrow$ $252.61.
     - `CBRS`: Gimlet Labs 100 MW systems agreement $\rightarrow$ FV $237.56 $\rightarrow$ $287.22.
     - `NVDA`: $150B buyback authorization addition ($235B remaining) $\rightarrow$ FV $429.89 $\rightarrow$ $471.57.
     - `SPCX`: Starship orbital flight & Google Suncatcher in orbit $\rightarrow$ FV $287.12 $\rightarrow$ $329.08.
     - `CACI`: ICE tactical communications task order ($150M ceiling) $\rightarrow$ FV $770.49 $\rightarrow$ $829.25.
2. **Weekly Sweep Stamping**:
   - Stamped 81 remaining tickers with `--record-sweep --date 2026-10-04`.
3. **Projection JSON Synchronization**:
   - Synchronized 22 `investment_screener/backend/data/projections/{TICKER}.json` files with latest SQLite scenario weights, fair values, and catalyst histories.
4. **Daily Brief Snapshot Published**:
   - Re-ran `daily_brief.py --skip-ta` to update `data/daily-briefs/2026-10-04.json` and sync with `intelligence.sqlite` so the web app `/daily-brief` page reflects fresh macro and DCF data.

---

## 2026-10-04 — Watchlist Pruning: Complete Removal of Nike (NKE) (Tier 0/1 Evolution)

**Trigger:** Pruned non-core consumer discretionary broken thesis (NKE) completely from active watchlist, thesis definitions, and sweep templates following multi-agent review consensus.

**Actions Taken:**
1. **Database Purge**:
   - Removed NKE rows and child records from `domain_model.sqlite` (`projection_scenario`, `projection_version`, `price_level_tier`, `price_level_set`, `alert`, `investment_price`, `investment`).
   - Verified 0 remaining NKE rows and 0 foreign key integrity errors introduced.
2. **Artifact Cleanup**:
   - Removed temporary evaluation and cache JSON files (`temp/evaluations/NKE_*.json`, `py_services/cache/NKE*`, `data/cache/ohlcv_NKE2y1d.json`).
3. **Template & Thesis Alignment**:
   - Removed NKE from `investment_thesis.md` Untracked/Watchlist table.
   - Removed NKE from `daily_sweep.md.template` and `weekly_sweep.md.template` Legacy / Non-Core Watchlist lists (Rule 12).

---

## 2026-10-04 — Retirement of Legacy Grok Script Names & Symlinks (Tier 1 Evolution)

**Trigger:** Completed retirement of legacy script filenames (`generate_grok_prompt.py`, `grok_sweep.py`, `test_generate_grok_prompt.py`) and their symlinks in favor of `generate_news_prompt.py` and `news_sweep.py`.

**Tier 1 Evolution:**
1. **Permanent Script Retirement**:
   - Removed `plugins/portfolio-advisor/scripts/generate_grok_prompt.py` and `grok_sweep.py`.
   - Removed legacy test `plugins/portfolio-advisor/tests/test_generate_grok_prompt.py` (superseded by `test_generate_news_prompt.py`).
2. **Symlink and Registry Cleanup**:
   - Removed legacy destination symlinks in `plugins/portfolio-advisor/skills/news-sweep/scripts/` and `investment_screener/backend/py_services/`.
   - Cleaned `symlinks.json` of the 3 legacy entries, verified with `symlink_manager.py audit`.
3. **Reference Updates**:
   - Updated test imports in `test_wave3_portfolio_json_closure.py` to import `generate_news_prompt`.
   - Updated architecture references in `docs/architecture/`, skill evals, and playbook.

---

## 2026-10-04 — Multi-Agent Generic Sweep Scripts & News-Sweep Modernization (Tier 1 Evolution)

**Trigger:** Renamed skill `x-news-sweep` to `news-sweep` and generalized underlying prompt generation and sweep execution scripts to support multi-frontier models (Grok, Claude, ChatGPT, Gemini).

**Tier 1 Evolution:**
1. **Generic Prompt Generator (`generate_news_prompt.py`)**:
   - Replaces `generate_grok_prompt.py` with multi-model prompt generation, baseline anchor injection, and multi-model response placeholder scaffolding (`temp/news-sweep-responses/{grok,gemini,claude,chatgpt}/`).
   - Retains `generate_grok_prompt.py` as a transparent, monkeypatch-safe proxy for 100% backward compatibility.
2. **Generic Sweep Script (`news_sweep.py`)**:
   - Replaces `grok_sweep.py` with automated fallback discovery across `temp/news-prompts/` and `temp/grok-prompts/`.
   - Retains `grok_sweep.py` as a backward-compatible proxy.
3. **Weekly Review Alignment**:
   - `weekly_review.py` outputs prompts to `temp/news-prompts/weekly_news_prompt.md` with legacy mirroring.
4. **Symlink and Lock Registry Sync**:
   - Registered canonical symlinks in `symlinks.json` (`generate_news_prompt.py` and `news_sweep.py` into `py_services/` and `skills/news-sweep/scripts/`).
   - Audited via `symlink_manager.py audit` (182 links verified OK).
   - Added unit test coverage in `test_generate_news_prompt.py` (84 tests passing).

---

## 2026-09-06 — Daily Loop Deterministic Checklist Verifier (Tier 1 Evolution)

**Trigger:** Added independent, deterministic Python verification to `/daily` and `daily-loop-agent` to eliminate shortcut execution and self-attestation.

**Tier 1 Evolution:**
1. **Deterministic Verification Script (`verify_daily_run.py`)**:
   - Audits structured phase completion artifacts (`step0_readiness.json` through `step5_summary.json`) written to an isolated run directory (`temp/daily_run_<TIMESTAMP>/`).
   - Validates that every step ran to `COMPLETED` status with required invariant fields present.
   - Cleans up the temporary directory upon 100% verified pass (`--cleanup`).
2. **Skill and Agent Persona Updates**:
   - `plugins/portfolio-advisor/agents/daily-loop-agent.md`: Enforces step-by-step artifact logging and calls `verify_daily_run.py` at Step 5.
   - `plugins/portfolio-advisor/skills/daily-loop/SKILL.md`: Codified the deterministic verification mandate.
3. **Unit Tests**:
   - `plugins/portfolio-advisor/tests/test_verify_daily_run.py`: 4 tests validating success, missing steps, invalid status, and cleanup.
   - Fixed pre-existing column name bug in `test_manage_watchlist.py` (`fetched_at` vs `as_of`).

---

## 2026-09-02 — Grok News Sweep Model-Intelligence Synthesis & Review Fixes (Tier 0/1 Evolution)

**Trigger:** Enhancement to `/news-sweep` prompt generation to inject deep model intelligence (scenario risks, standing decision anchors, SA/DCF tension) into the Grok prompt with mandatory Phase 1.5 agent review.

**Tier 0/1 Friction & Fixes Landed:**
1. **`portfolio_io.py` Omission (`standing_decision_*`)**:
   - *Friction:* `load_thesis_holdings()` omitted `standing_decision_reason` and `standing_decision_type` from the returned dict, rendering anchor thesis branches in `generate_grok_prompt.py` dead code.
   - *Fix:* Extended `portfolio_io.py:load_thesis_holdings()` to extract both fields from the SQLite `investment` table.
2. **Markdown Table Cell Sanitization & Token Bounding**:
   - *Friction:* Raw scenario risks contained unbounded 200–300+ character strings, and inter-item join used `" | "` which created pipe-count mismatches (corrupting 26% of table rows).
   - *Fix:* Added `_clean_markdown_text()` with safe character bounding and whitespace normalization; changed join separator to `"; "` to strictly preserve Markdown table columns. Added automated pipe-count validation.
3. **Phase 1.5 Mandatory Protocol (`news-sweep/SKILL.md`)**:
   - *Friction:* Prompt generation previously relied on static script output without live context review.
   - *Fix:* Codified Phase 1.5 in `SKILL.md` requiring the AI Agent to inspect recent repository context (daily briefs, macro regime, earnings alerts) and directly synthesize surgical inquiries prior to Grok dispatch.
4. **Upstream Rule Enforcement (`agent-plugins-skills` PR #489)**:
   - *Friction:* Agent models treated the `PRE-COMPLETION GATE` as an end-of-session summary rather than an autonomous per-turn contract.
   - *Fix:* Merged and synced PR #489 across `self-evolution-policy.md` and `graph-planning-superpowers-policy.md` to mandate proactive turn-by-turn gate emission.

**Artifacts Updated:**
- `plugins/portfolio-advisor/scripts/generate_grok_prompt.py`
- `plugins/portfolio-advisor/assets/templates/daily_sweep.md.template`
- `plugins/portfolio-advisor/skills/news-sweep/SKILL.md`
- `investment_screener/backend/py_services/portfolio_io.py`
- `references/map-debt.md` (`DEBT-20260902-01`)
- `.agent/rules/self-evolution-policy.md` & `.agent/rules/graph-planning-superpowers-policy.md`

---

**Macro Regime:** RISK-ON (score=2). VIX stable around 15-16, credit yields supportive. Semiconductor rotation and memory consolidation active. Hyperscaler capex remains structurally robust with nuclear and power agreements (Meta/Microsoft PPAs).
**TA Sweep:** Full batch scan completed for holdings and watchlist. Key levels mapped for major movers (SNDK, PLTR, SPCX, SKHY).
**Actions taken:** target-portfolio.json updated to establish a clean target baseline. 29 holdings calibrated, unlisted holdings (META, CLSK, CRM, NOW, TEAM, WQTM, CACI) set to 0. USD_CASH added as a target-weight holding (3.0%).
**User overrides:** n/a (targets calibrated per user's specifications).
**Tool failures:** none (all script tools executed successfully).
**Thesis revisions:** templates daily_sweep.md.template and weekly_sweep.md.template updated to align with the new target baseline.
**Notes:** Portfolio successfully synced from TradingView with 56 verified positions. High-conviction memory/HPC assets maintained. P&L context rules active for underwater positions (OKLO, BE, CEG).

## 2026-07-02 — Dashboard Data-Integrity Fixes (Tier 2/3 Evolution)

**Trigger:** User caught an impossible "+29.79% today" on the Portfolio Summary dashboard,
plus a suspected ~$1,500 total-value discrepancy.

**Tier 3 regression fixed — target weight drift:** `target-portfolio.json` target weights
summed to 99.29% instead of 100%. Root cause: BE's weight was deliberately reduced
2.9654% -> 2.26% on 2026-06-29 (documented, intentional) but never rebalanced against
the other 30 holdings, and the change landed inside an unrelated commit
("Compress instruction files..."). Fixed via `validate_weights.py --normalize --write`.
Added `.git/hooks/pre-commit-thesis-sync-check` (local, untracked like the repo's other
hooks) to run `verify_thesis_sync.py` automatically whenever `target-portfolio.json` is
staged, so this class of drift can't land again unnoticed.

**Tier 2 bug fixed — standardize_metrics.py:** `net_income`/`profit_margin` silently
defaulted to 0.0 when raw `fetch_financials.py` metrics provided `profit_margin` directly
but no `net_income` key (e.g. PLTR) — reported a 43.7%-margin company as 0% profitable.
Fixed with TDD (`test_standardize_metrics.py`); derives net_income from
profit_margin x revenue when the raw key is absent.

**Tier 3 architectural fix — portfolio weight/total split-brain:** Audit found 5
independent "actual weight %" implementations across Python and TypeScript with 2
different denominator conventions, and two independent writers of `portfolio.json`'s
`totals.totalUSD` (Python's TV-authoritative writer vs. TS's shares*price recompute,
which could silently clobber the authoritative figure on any price refresh). Consolidated
to a single canonical implementation: `buildPortfolioSnapshot()` +
`preserveAuthoritativeTotal()` + `computeWeightsMap()` in `portfolioSnapshot.ts`, with
`validate_weights.py::compute_current()` (Python, used by chat-agent sessions) mirroring
the identical formula and a cross-language parity test
(`test_compute_current_weights.py`, mirrors the existing `test_math_parity.py` pattern
for DCF math). Backend rebuilt and restarted mid-session.

**Tier 2 bug fixed — portfolio_performance.py:** root cause of the +29.79% display bug.
`safe_float(NaN) -> 0.0` zeroed out PSU-U.TO's (TSX) full ~$8,000 value for 2026-07-01
(Canada Day, TSX closed, US tickers traded normally), understating yesterday's total and
inflating the 1-day return. Fixed by forward-filling (`.ffill()`) the price series before
computing any point-in-time total; extracted a pure, tested `compute_performance()`
function (`test_portfolio_performance.py`, injected-NaN-gap test pattern). New rule
created: `.agent/rules/no-silent-nan-to-zero.md` — missing price data must never
silently become $0 in a financial calculation.

**Tool failures:** none (all fixes were genuine pre-existing bugs found via user-reported
symptoms, not tool/script execution failures).

**Unresolved, flagged for next session:** `fetch_broker_data.py --snapshot` still doesn't
fetch account balances in the same call, so `totals.totalUSD` currently falls back to
`computed_fallback` (shares*price) rather than TV-authoritative — the balance-tab
`clickTab()` fix attempted this session (mousedown/mouseup/click dispatch in
`broker_data.js`) did not fully resolve it. `PortfolioTable.tsx`'s client-side live-refetch
% was flagged as a legitimate (not broken) separate "right now" display, left as-is.

---

## 2026-06-29 — Card Format Enhancement (Tier 1 Evolution)

**Macro:** RISK-ON (score=2)
**TA Sweep:** skipped (--skip-ta flag; TA data from prior sweep used)
**Actions taken:** 0 — session in progress at time of evolution entry
**User overrides:** n/a
**Tool failures:** none

**Evolution applied (Tier 1 — new capability):**
User requested that every triage card include:
1. **P&L position** — book price, current price, gain/loss $ and %, PROFIT vs UNDERWATER label.
   Rule added: never recommend selling a REDUCE signal on an underwater position unless thesis
   is broken (DCF SELL) or score ≤ -3 (EXIT). Always show break-even price.
2. **TA-derived action levels** — four price targets per card: Exit/Stop-loss, Trim/Reduce at,
   Hold zone, Accumulate at. Derived from: (a) DCF bear/base/bull projections, (b) targetEntryPrice
   from target-portfolio.json, (c) RSI/ADX context rules. Labels distinguish `(DCF ref)` vs `(TA ref)`.
3. **Triage queue reasons** — each queue item now shows a one-line reason explaining the signal
   (e.g. "DCF SELL, RSI 78 cooling, thesis broken") alongside the P&L %.
4. **DCF agree/conflict narrative** — card narrative must explicitly call out whether TA and
   DCF are aligned or pulling in opposite directions, since conflicting signals require user judgment.

**Files updated:** `plugins/portfolio-advisor/agents/daily-loop-agent.md` (Step 2 triage format
+ Step 3 card format + TA levels derivation rules + P&L context rules + triage history
recording + pattern detection + optimization pass in Step 4c).
`plugins/portfolio-advisor/references/triage-history.json` — created (first entry: MSFT 2026-06-29).

**Consecutive EXIT signals (3+ days):** BE, CORZ (both ALLOWLISTED — no action without user direction)
**Score improvements vs yesterday:** CLSK +4 · CACI +3 · CRWV +2 · APLD +2 · OKLO +2
**Score deteriorations:** MSFT -3 (largest single-day delta) · FOTO -1 · KOID -1 · BE -1
**Notes:** WYFI confirmed sold by user — remove from future triage. 15 holdings with >5% overnight
gaps today (ASTS +9.4%, RKLB +9.0%, CRWD +6.8%, PANW +6.7% UP; WYFI -10.5%, SNDK -8.6%,
COHR -8.6% DOWN). Only 1 actionable recommendation today (MSFT trim, score -1, weight at target).

## 2026-06-27 — Weekly Review

**Macro Regime:** RISK-OFF (with sector stabilization). Semi rout mid-June led to tech de-rating, but MU blowout earnings late-week catalyzed memory/HBM recovery. VIX elevated; credit/yields show macro caution. Hyperscaler capex scrutinized but remains robust.
**TA Sweep:** Checked PLTR, CLSK, ASTS, RKLB, CACI, SNDK. Support levels mapped to GTC limit orders.
**Actions Recommended:**
- **Accumulate Dips**: Core compute & memory (NVDA, TSM, AMD, SNDK, MU), power pillars (CEG, VST, BE, OKLO), and space/ontological pillars (PLTR, RKLB, RDW).
- **Trims**: Exit non-core consumer discretionary names showing secular relative weakness (CAKE, CELH, NKE) to consolidate capital into higher-conviction AI infrastructure.
- **Initiates**: Focus on buying PLTR, CLSK, and CACI on support dips.
**Prompt Evolution Observations:**
- *Grok Prompts*: Ingested prompt layout was extremely successful. Explicitly forcing a table row for every ticker solved the omission bug, listing all 82 equities with detailed news summaries or sector-relative context.
- *Friction/Deficiencies*: Some smaller tickers received shorter sector-level summaries. Rule 12 codified to prevent future prompt laziness. No retry needed this session; Grok's data depth is highly actionable.

## 2026-06-22

**Macro:** Not run (user skipped morning brief — focused on single trade decision)
**TA Sweep:** Live CDP read (1H + Weekly + 1min + Daily via user screenshots)
**Actions taken:** 1 sold (WYFI 12 shares TFSA, market, ~$42.75)
**User overrides:** None — user initiated EXIT independently, agent concurred
**Tool failures:**
- Tier 2: `--submit` failed after dialog timed out during TA review pause. Fixed by re-running `--execute` then `--submit`. No code change needed — expected timeout behavior.
- Tier 2: `fetch_broker_data.py --snapshot | json.load(sys.stdin)` failed (empty stdin). Fixed by capturing output first, finding JSON start index. Lesson: always use `capture_output=True` pattern or pipe through file, not direct stdin parse.
**Score improvements vs yesterday:** N/A
**Consecutive EXIT signals:** WYFI was flagged 🟡 TRIM in thesis — user escalated to full EXIT after 145% gain in ~1 month
**Notes:**
- WYFI exited at ~$42.75, book $17.46, +145% gain. DCF fair value was $32.00 (stock was 34% above FV). Daily RSI 74.17 (overbought). Two consecutive +10%+ days (yesterday +10.78%, today +12.61%). User identified the exit independently — correct call.
- WYFI was speculative, not in target-portfolio.json, low-confidence DCF (0.45). Booking gains on names like this is textbook discipline.
- Order dialog timeout: if TA review takes >2 min, re-run `--execute` before `--submit`. Add note to pre-submit check.
- Portfolio confirmed post-trade: WYFI = NONE in TV positions ✓

## 2026-06-22 — Tier 2: Backend Local API Auth Missing from All Skill curl Calls

**Tier: 2 (Failure)** — `GET /api/projections/CACI` returned `401 Unauthorized — missing or invalid local API token` during `/update-stock-analysis CACI` run. Root cause: `localAuth` middleware was added to the Express backend but no skill documentation was updated to include the `Authorization: Bearer` header.

### Root Cause
`investment_screener/backend/src/middleware/localAuth.ts` reads/creates a bearer token at `.runtime/api-token` on first boot and gates all `/api/*` routes. SKILL.md files across 7 plugins contained raw `curl http://localhost:3001/api/...` calls with no auth header. The `/health` endpoint is correctly exempt.

### Fix Applied (2026-06-22)
1. **Created** `investment_screener/backend/py_services/utils/local_api.py` — authenticated HTTP client for Python scripts. Reads token once from `.runtime/api-token`, exposes `api_get()`, `api_post()`, `health_check()`. All future Python scripts calling the backend should import this instead of using raw curl/subprocess.
2. **Updated** `plugins/stock-valuation/skills/stock_valuation/SKILL.md` — added auth note section with both shell (`API_TOKEN=$(cat .runtime/api-token)`) and Python (`from utils.local_api import api_get`) patterns. Fixed all 3 curl commands in Steps 0, 0.5, and 6.
3. **Fixed** `standardize_metrics.py` stdin bug in SKILL.md Step 2 (script requires file path arg, not piped stdin).

### Remaining Work (next session)
The following SKILL.md files still contain unauthenticated curl calls and need the same treatment:
- `plugins/stock-valuation/skills/stock-research/SKILL.md` (Step 0 freshness check)
- `plugins/tradingview/skills/cancel-order/SKILL.md` (POST to /api/trading/cancel)
- `plugins/portfolio-advisor/skills/calibrate-targets/SKILL.md`
- `plugins/portfolio-advisor/skills/update-portfolio-targets/SKILL.md`
- `plugins/portfolio-advisor/skills/portfolio-health/SKILL.md` (curl + subprocess.run)
- `plugins/portfolio-advisor/skills/rebalance-portfolio/SKILL.md` (curl + subprocess.run)
- `plugins/portfolio-advisor/skills/strategic-review/SKILL.md` (curl + subprocess.run)

### Rule Going Forward
Any new SKILL.md that calls the backend MUST use `API_TOKEN=$(cat .runtime/api-token)` and `-H "Authorization: Bearer $API_TOKEN"`. Python scripts MUST use `utils.local_api`.

## 2026-06-19 (addendum) — US Market Holiday: Inactive Orders Are Normal

**Learning**: June 19 is Juneteenth — a US federal market holiday. Orders placed on a holiday show as "Inactive" and do not fill because the market is closed. This is expected behavior, not a broker error or wrong ticker.

**Rule**: Before diagnosing an unfilled order, check whether today is a US market holiday. Day limit orders queued on a holiday carry over and activate at the next regular session open (Monday June 23 in this case). CRWV orders at $119 are correctly queued and will attempt to fill Monday.

**Agent behavior**: If orders show Inactive and prices look right, check the market calendar before troubleshooting CDP automation or order routing.

## 2026-06-19 (addendum) — BE Double-Reduce: Trade History Not Cross-Checked

**Tier: 2 (Failure)** — System recommended reducing BE when user had already reduced BE in a prior session. User missed subsequent +13.3% gap because position was smaller than intended.

### Root Cause
The daily loop triage computes TRIM/EXIT recommendations from current-weight-vs-target comparison only. It does NOT cross-check `trade-log.json` for recent user actions on the same ticker. A prior-session BE trim moved actual weight closer to target, but this was not visible to the scorer in the current session — so the same TRIM signal fired again.

The trade log has a cancelled BE buy from 2026-05-18 but the manual sells were not logged (done outside the system or logged with a different flow). This means even a trade-log check would have missed it unless we require all trades to be logged.

### Required Fix (Tier 2 — to implement next session)
**Step 1**: Before any TRIM/REDUCE/EXIT recommendation is presented in the triage card, the daily loop MUST check `trade-log.json` for filled/submitted sells of that ticker in the last 14 days. If found, annotate: `[RECENTLY TRIMMED {date} — verify current weight before acting again]`.

**Step 2**: If the ticker's actual weight has moved ≥0.5pp closer to target since the last session brief, add a note: `[Weight improved — confirm triage action still needed]`.

**Step 3**: Make it easy for users to say "I already trimmed X" and have that recorded immediately — add a `standingDecision: { type: RECENTLY_ACTED, date: ... }` that expires after 14 days.

### VRT Update (same session)
User confirmed intent to re-enter VRT on a meaningful pullback. Updated `standingDecision` from `POSITION_CLOSED` to `REENTRY_ON_PULLBACK`. Target 0.94% remains as re-entry placeholder.

### Process Rule Added
The daily loop must read the last 14 days of `trade-log.json` sells as Step 0.5, before presenting any TRIM/EXIT triage cards. If a sell for that ticker is found in that window, escalate to user with "already trimmed recently" context before recommending again.

---

## 2026-06-19 — Standing Decision Gap: VST and VRT recommended incorrectly

**Macro:** RISK-OFF (score=-2) — VIX neutral, SPY below 200D, credit unavailable
**TA Sweep:** fresh (ran at session start)
**Actions taken:** 0 trades — session interrupted by standing-decision failures
**User overrides:** N/A
**Tool failures:** 1 systemic, Tier 2

### Root Cause — Standing Decision Not Surfaced in Scorer

VST's `agentRationale` contained a documented override ("SA LP CLOSED entire $252M position — Grok ACCUMULATE BLOCKED 2026-06-08") but no formal `standingDecision` object. The conviction scorer returned score=+3 (ACCUMULATE) from pure TA/DCF data, and I presented VST as "Fine to add" — directly contradicting the documented guidance the user had received days earlier.

VRT was similarly presented as an INITIATE target despite the user having fully closed the position.

The system's `standingDecision` field IS read by the scorer (it correctly blocked BE, CORZ, CEG, OKLO today). The gap is that informal guidance written into `agentRationale` text is NOT parsed by the scorer — only the structured `standingDecision` object is.

### Fix Applied

**Fix 1 — VST standing decision formalized**
- Added `standingDecision: { type: SA_LP_EXIT_OVERRIDE }` to VST in `target-portfolio.json`
- SA LP exit overrides DCF ACCUMULATE. No adds until user lifts explicitly.
- File: `investment_screener/backend/data/theses/target-portfolio.json`

**Fix 2 — VRT position closed flag**
- Added `standingDecision: { type: POSITION_CLOSED }` to VRT
- Will not surface as INITIATE until user confirms re-entry
- File: `investment_screener/backend/data/theses/target-portfolio.json`

### Process Rule Added

**Any time a Grok sweep or user action results in "DO NOT ADD / BLOCKED" — MUST write a formal `standingDecision` object immediately, not just text in agentRationale.** The scorer reads objects, not prose.

### Overnight Gaps (notable)
BE +13.3%, WYFI +11.2%, SNDK +8.7%, CBRS +7.2%, DRAM +6.0%

### Consecutive EXIT signals (3+ days)
CEG, OKLO — both underwater, standing SELL_ONLY_WHEN_GREEN

### Notes
- User correctly called out that VST was recommended as EXIT/REDUCE in a prior session, and today I said ACCUMULATE. This is a trust-degrading failure.
- User also confirmed VRT position fully closed.
- ACCUMULATE queue (NBIS, PSIX, CRWV) gated by RISK-OFF macro — valid entries on macro improvement.

## 2026-06-15 — Share Count Integrity Failure + Hardening

**Macro:** RISK-ON (score=2) — massive broad market rally day
**TA Sweep:** fresh (ran at session start)
**Actions taken:** User trimmed DRAM and SNDK based on incorrect weight recommendations
**User overrides:** N/A — trades executed before data integrity issue was discovered
**Tool failures:** 2 critical, both Tier 2, fixed this session

### Root Cause
`portfolio.json` file mtime was 0.1h old (looked fresh) because yfinance refreshes prices
continuously. However `tvSnapshot.positions` was empty (0) — the TV broker sync had silently
failed because TradingView's broker panel was showing a reconnect dialog, not live positions.
`write_snapshot()` did not abort on 0 positions; it silently preserved stale share counts.
The daily-loop Step 0 only checked file age, not tvSnapshot integrity. Triage ran with wrong
share counts → wrong weights → user over-sold DRAM and SNDK.

### Fixes Applied

**Fix 1 — Tier 2 — `fetch_broker_data.py` silent pass on empty positions**
- `write_snapshot()` now aborts holdings merge and prints explicit error when TV returns 0 positions
- File: `plugins/tradingview/scripts/fetch_broker_data.py`

**Fix 2 — Tier 3 — `broker_data.js` getAccounts() MutationObserver miss**
- `getAccounts()` now retries up to 3 times (800ms apart) before returning empty
- Extracted `_getAccountsOnce()` helper; public `getAccounts()` wraps with retry loop
- File: `tradingview-cdp/core/broker_data.js`

**Fix 3 — Tier 1 — daily-loop Step 0 missing tvSnapshot integrity gate**
- Step 0 now reads `tvSnapshot.positions` count alongside file age
- Hard gate added: if positions == 0, loop stops and requires user confirmation before triage
- All weight-based recommendations flagged [UNVERIFIED WEIGHTS] if user overrides the gate
- File: `plugins/portfolio-advisor/agents/daily-loop-agent.md`

### Consecutive EXIT signals (3+ days)
CORZ, OKLO, PANW — all have standing decisions, no action required

### Notes
- TV Broker session can drop silently; broker panel shows reconnect dialog without any CDP-visible error
- File mtime is NOT a reliable proxy for share count freshness — only tvSnapshot.positions > 0 confirms shares are current
- User manually confirmed correct cash balance from TV screenshots: TFSA $3,461.76 + RRSP $1,715.19 = $5,176.95 USD
- VRT removed from portfolio (position closed, stale entry persisted from earlier sync)

## 2026-06-10 — System Audit & Engine Hardening Session

**Macro:** NEUTRAL at session start (live brief run below)
**TA Sweep:** fresh (ran 2026-06-10 14:21 UTC, 29 holdings)
**Actions taken:** 0 trades — engineering session (full-system audit + 3 engine fixes)
**User overrides:** none this session
**Tool failures:** 4 found via audit, 4 fixed, all Tier 2/3, all under 3 attempts

### Evolution entries

1. **Tier 2 — `ta_sweep_batch.py` pctToFV denominator bug (FIXED)**
   - `add_dcf_flags()` computed `(FV − price) / FV` instead of `(FV − price) / price`.
   - Evidence: OKLO showed −742.6% and IONQ −594.4% "to fair value" — mathematically
     impossible for a price-relative gap (floors at −100%). APLD showed +29.9% when true
     upside at price was +42.6%. SNDK showed stale +49% while the user had manually noted
     real upside was ~14% — engine now computes +15.3%.
   - Fix: denominator corrected at the source; `compute_conviction_scores.py` gained
     `_resolve_pct_to_fv()` which always recomputes from the sweep's live close + FV,
     so historical sweep files with the bad values are corrected at read time.
   - Tests: `TestPctToFVDenominator` (tv), `TestResolvePctToFV` (py_services).

2. **Tier 2 — `compute_conviction_scores.py` directionless momentum bonus (FIXED)**
   - `_score_momentum()` awarded +1 for ADX≥30 with no RSI_COOLING — but ADX measures
     trend *strength*, not direction. A stock in free-fall (ADX 45, RSI 30, no cooling
     flag because RSI never peaked) earned +1 "momentum intact" — a falling-knife
     amplifier feeding the ACCUMULATE queue.
   - Fix: direction gate via RSI. +1 only when RSI>55; −1 when RSI<45 (strong downtrend)
     or cooling; 0 when ambiguous (45–55) or RSI missing.
   - Observed effect on live data: WYFI dropped from ACCUMULATE(+3) to HOLD(+2) — its
     ADX-35 trend has no clear direction (RSI 47.1). Correct demotion.
   - Tests: `TestScoreMomentumDirection`.

3. **Tier 3 — `macro_regime.py` fail-open on data blackout (FIXED)**
   - With yfinance unavailable (rate limits cluster during volatility spikes — exactly
     when the gate matters), all components silently scored 0 → regime defaulted NEUTRAL
     → +4 ACCUMULATE actions permitted on zero data.
   - Fix: `_classify_regime(score, unavailable)` — 2+ of 3 signals unavailable forces
     RISK-OFF with `degraded: true` and an explicit details line. ImportError path also
     now fails safe. One missing signal is tolerated (remaining two still gate).
   - Tests: `TestClassifyRegime`, `TestDegradedField`.

4. **Tier 2 — `ta_sweep_batch.py` enrichment lost after ADX validation (FIXED)**
   - `main()` did `res = validate_adx(res)` inside `for res in scan_results:` —
     `validate_adx` returns a shallow copy when nulling out-of-range ADX, so the nulled
     value AND all subsequent action/targetWeight enrichment landed on a discarded copy.
     The persisted JSON silently kept the invalid ADX and lacked the action fields.
   - Fix: extracted `enrich_results()` which builds and returns the enriched list;
     `main()` persists its output. Tests: `TestEnrichmentPreservedAfterAdxValidation`.

5. **Tier 3 — stale test expectation in `test_verify_thesis_sync.py` (FIXED, attempt 1)**
   - Test asserted the old error string "missing in investment_thesis.md"; production
     script now prints "missing in thesis documentation". Behavior (exit 1 + error
     listed) was correct; expectation aligned to current message.

### Audit findings deferred (next sessions, in leverage order)
- **No standing-decisions layer:** CORZ (user-allowlisted SA/DCF conflict, ACCUMULATE),
  PANW (Q3 beat, ACCUMULATE), CEG/OKLO ("sell only when green") all rank as EXIT in the
  scorer — the daily loop's top triage cards directly contradict documented user
  decisions every single day. Needs a versioned `conviction-overrides.json` consumed by
  `compute_conviction_scores.py` that ANNOTATES (never mutes — no-sycophancy rule) each
  scored row with the standing decision + reason + expiry.
- **DCF staleness invisible to the score:** 54/73 projections >30 days old; a 60-day-old
  BUY counts the same +2 as a fresh one. Add `dcf_age_days` + decay/flag.
- **Score deltas only exist for tickers present in both snapshots** — new positions
  never show as "new signal".
- **investment_thesis.md blueprint is stale** (header says v9.4, history says v9.7;
  PSU.U.TO duplicate EXIT row at 17.08% from before the alias fix) — regenerate via
  `generate_portfolio_blueprint.py --write` after next target change.
- **7 zero-byte `.pylock` files** in `data/projections/` (BE, CORZ, CRWV, IREN, NBIS,
  PANW, RKLB — May 31–Jun 5) — stale locks from crashed processes. Deletion requires
  user permission per self-evolution policy; flagged here instead.

**Score improvements vs yesterday:** n/a — first logged session (this is entry #1 in the log)
**Consecutive EXIT signals (3+ days):** unknown — no prior session history; CORZ/OKLO/PANW/CLSK/IONQ are at EXIT today; track from tomorrow
**Notes:** First session where the evolution log is actually written. The daily-loop-agent
spec mandates an entry every session — before today the log was empty despite the system
being live since June 1. The loop only compounds if this file grows.

## 2026-06-29 — Daily Session (Partial — user on break)

**Macro:** RISK-ON (score=2) · VIX 18.1 · SPY +7.0% vs 200D · HYG/LQD 0.729
**TA Sweep:** skipped (--skip-ta; prior cache used)
**Actions taken:** 0 trades · 4 HOLD decisions · 1 target weight reduced (BE 2.97%→2.26%)
**Deferred:** Card 5 — CLSK/CACI score improvements (carry to tomorrow)

**Decisions:**
- MSFT: HOLD — TA noise (-1 score), DCF BUY +74%, at target weight, underwater -12%
- BE:   HOLD — allowlisted (SA LP #1 long), target reduced to 2.26% to match actual, role→hold
- CORZ: HOLD — allowlisted (SA LP long), in profit +17.6%, approaching bull FV ceiling ($30)
- CEG:  HOLD — SELL_ONLY_WHEN_GREEN, underwater -28.8%, SQUEEZE_ON forming
- OKLO: HOLD — SELL_ONLY_WHEN_GREEN, underwater -49.1%, distribution ongoing

**User note:** All cash deployed to PSU-U.TO (90 shares, $9,003) for high-interest parking
while waiting for re-entry opportunities. PSU-U.TO earns yield while dry powder holds.

**Overnight movers noted (>5%):** ASTS +9.4%, RKLB +9.0%, CRWD +6.8%, PANW +6.7%
WYFI -10.5% (user confirmed already sold), SNDK -8.6%, COHR -8.6%

**Tool failures:** none

**Evolution applied this session (Tier 1):**
1. daily-loop-agent: P&L context + TA levels + triage-history recording + optimization pass
2. daily-loop-agent: taLevels written to projection JSONs for web app display
3. single-stock-advisor: same three additions (P&L in Phase 1, taLevels in Phase 2, triage-history in Phase 4)
4. AIAnalysisModal.tsx: TA Price Levels tile section added (stop/trim/hold/accumulate)
5. api.ts Projection interface: taLevels field added

**taLevels written today:** MSFT, BE, CORZ, CEG, OKLO
**triage-history.json entries:** 5

**Consecutive EXIT signals:** BE (2+ sessions, allowlisted) · CORZ (2+ sessions, allowlisted)
**Score improvements vs yesterday:** CLSK +4 · CACI +3 · CRWV +2 · APLD +2 (carry to tomorrow)
**Notes:** CEG watching for SQUEEZE_ON resolution. CORZ approaching bull FV $30 — monitor.
PSU-U.TO fully loaded as cash reserve. Next session: start with CLSK/CACI card.
echo "Gap logged"
## [2026-08-28]

**Tool failures:** Tier 2 — daily-loop-agent's Step 0 readiness check measured
portfolio staleness from `portfolio.json`'s file mtime + `tvSnapshot` field.
That file/field has been dead since Wave 3 (every real sync path — Questrade
sync/price-refresh, TradingView `--snapshot` — writes only to
`domain_model.sqlite` now). Evidence: `portfolio.json` last modified Aug 23;
`domain_model.sqlite` last modified Aug 27 (today's real syncs). The check
reported "106.6h stale" despite multiple real refreshes the day before, because
it was reading a retired file that nothing updates. Fixed: readiness check now
reads `MAX(account_investment.last_synced_at)` from `domain_model.sqlite`
directly. Verified against the real DB: correctly reports 20.6h old, 51
positions (vs the false 106.6h/0-positions reading before the fix).
**Files patched:** `plugins/portfolio-advisor/agents/daily-loop-agent.md`
(Step 0 script + readiness card + hard-gate text, now source-agnostic between
TradingView and Questrade MCP sync paths).

## 2026-09-06 — Daily Loop Consolidation & Hardened Control Plane Receipts
- Consolidated morning operations into `/daily` (`--scan` vs `--interactive`).
- Cleanly deleted `/daily-brief` to eliminate dual-command ambiguity.
- Created `daily_receipts.py` with canonical JSON serialization, float normalization, and `BEGIN IMMEDIATE` transaction isolation with a UNIQUE index on `gate_name`.
- Added explicit terminal closure receipt (`DAILY_RUN_<run_id>_TERMINAL`) to prevent prefix truncation attacks.
- Upgraded `verify_daily_run.py` with 4-way cleanup sandboxing and process-liveness checking stale janitor.

## 2026-10-01 — Multi-model news-sweep assessment and ETF awareness

- First sweep run on all three models (Grok, Gemini 3.8 Flash, ChatGPT GPT-6.1 SOL). Gemini gave a
  wrong 10-year yield (3.84% vs 5.31%) and reused a stale MU quarter, then corrected after challenge;
  ChatGPT questioned the prompt's own SPCX anchor ($185 vs actual $135 IPO) and noticed a 7.9% coverage gap;
  Grok's actions mirrored the prompt's pre-assigned Action column. Ratings, fact-check gate and roles are
  recorded in `references/news-sweep-model-assessment.md`; `daily-loop-agent.md` Step 2 and the skill point to it.
- **Tool failure (Tier 1, missing capability):** FOTO, HUMN and KOID (thematic ETFs, 7.93% of the portfolio) were
  absent from the sweep because `generate_grok_prompt.py` excludes every ticker with an `etf_analysis/` file and
  nothing replaced them. The agent now requires a held-ticker coverage check and an ETF card/sector questions.
  Prompt-generator change (ETF section + coverage assertion) is a follow-up, not yet built.
- Open: the brief shows DCF-style actions (`ACCUMULATE`, `pct_to_fv` 2.1/9.5/7.4) for the three ETFs; source not established.
- **Cadence decision (user, 2026-10-01):** daily sweep = Grok alone with the fact-check and coverage gates;
  escalate to ChatGPT on capital-gated actions, imminent binary events, failed gates, signal conflicts or
  unsourced trade-relevant claims; weekly = all available models, which is also when model ratings are re-scored.
- **User observation (2026-10-01):** Gemini needed 3+ rounds of user call-outs to reach correct figures (it never self-checked). Recorded in `news-sweep-model-assessment.md` as a cost dimension; weekly-only for such a model.
- **Skill/agent merge (user decision, 2026-10-01):** `daily-loop-agent` folded into the `daily-loop` skill (one interactive skill; no persona switch). Interactive-run verification gap logged as DEBT-20261001-01. After merge: resync `.agents` with plugin-syncer and remove the old agent artifact.
- **Opus 5.5 comparison and SA LP (2026-10-01):** Opus was accurate on all checked figures and caught the 2026-07-30 SA LP liquidation that
  ChatGPT and Gemini missed. Prompt fixed (generator + weekly template, test added), news-sweep gates annotated, ETF note added to
  `daily-brief-methodology.md`, model assessment addendum written.
- **Correction (2026-10-01):** Opus 5.5's CRDO price (~$150-170) was wrong vs market ($202.66); assessment corrected and a price spot-check added to the fact-check gate.
- **Post-merge corrections (2026-10-01):** target totals corrected to 17.5% / 112.5% (an earlier figure was an addition error); logged DEBT-20261001-04 (TA sweep writes null indicators but reports success), -05 (`update_targets.py` silent normalization), -06 (target over-allocation recurrence).
- **Brief sizing bug (2026-10-01):** a REDUCE signal at or under target proposed selling half the position (RIOT ~$365, MU ~$745 after its target moved). Fixed test-first in `brief_recommendations.py` (REDUCE within 0.5pp of target now HOLDs with no trade). Logged as DEBT-20261001-07.
- **Skill Alignment Retrofit (2026-10-04):** Retrofitted all 21 skills in `plugins/portfolio-advisor/` to the canonical 6-section structure (`Title`, `Contents`, `Constraints`, `Quick start`, `Workflow`, `Verification`, and conditionally `References`). Removed unmanaged real files `acceptance-criteria.md`, moved shared references (`fallback-tree.md`, `strategic_review_prompt.md`, `rebalance_prompt.md`, `questrade.md`) to plugin root `references/`, and symlinked via `symlink_manager.py`. Fixed heading anchors and early TOCs across referenced markdown files (`daily-brief-methodology.md`, `strategic_review_prompt.md`, `thesis-challenge-prompt.md`, `investment_thesis.md`). Added complete routing evals for `data-quality-audit`, `portfolio-coverage-audit`, `screener-integrity-audit`, `stock-intake`, and `weekly-review`. All 21 skills pass `audit_skill.py` with 0 errors and 0 warnings; all 78 pytest tests pass.
- **Canonical recommendation (2026-10-04):** the app produced twelve different rule sets for TRIM/EXIT/ACCUMULATE (BE showed five different answers across pages). Added `recommendation.py` as the single decision function (valuation vs fair value, ±15% band, explicit exit signal; target weights play no part because recommendations precede targets). `portfolio_action.derive_action` is now a shim over it. Remaining producers (browser re-derivation in `ScreenerTable.tsx`, `routes/stock.ts` technical action, `ThesisService`, brief `_band`, `relabel_actions`, `apply_catalyst`) are being removed in follow-up commits on this branch.
- **Canonical recommendation completion (2026-10-04):** Finished the web/API/script consumer audit from checkpoint 9425f92d. Current actions now share recommendation.py and a single React snapshot; score bands, technical regimes, target drift, stale snapshot cards, and caller-supplied upside cannot issue competing recommendations. Standing decisions gate trade proposals without changing displayed signals. Fixed unheld current-price lookup and cash-inclusive weight regression coverage. Added real SQLite/bridge/HTTP contracts, ADR-032, and a consumer inventory in docs/architecture/canonical-recommendation-audit.md. Broad Python suite: 1741 passes plus 14 sandbox-sensitive passes; backend 188 passes with two failures also reproduced on main; frontend 33 passes. Follow-up remains in the existing feature worktree for review.
- **Backend baseline repairs (2026-10-04):** Fixed the outdated holding fixture's missing assetClass and the price-level schema's mismatch with persisted SQLite annotations and nullable metadata. Added a real SQLite regression contract that preserves imported labels, suppressed levels and zero/null unavailable prices while rejecting negative prices/tier indices. Private ground-truth tests support TEST_DOMAIN_MODEL_DB for a backup instead of replacing worktree data. Entire backend suite: 191 passed; backend build passed. Main's pre-existing rule edit and the BE worktree remain unchanged.

- **AI forward-evidence gate (2026-10-05):** Linked five review/intake skills to the stock-valuation shared guide and embedded the gate in daily/weekly sweep templates. Reviews must check dated forward estimates, DDR/LPDDR and NAND/SSD alongside HBM, time-to-power, executable delivery capacity and cash conversion. Missing drivers route to revaluation before action proposals; canonical actions and standing decisions remain authoritative. Added MU/BE evaluation cases and focused template/reference contracts. Static audits verified; behavioral model evals not run.
- **Reward-versus-risk view (2026-10-08):** The ±15% action band could not show which held positions sit above fair value with poor remaining reward, tables recomputed fair value and upside in the browser, and the Portfolio Table left Price, Gain and Upside blank by reading the wrong heatmap field. Added canonical `risk_reward.py` (probability-weighted reward:risk, loss odds, premium, reduce flag, action alignment, four-check valuation support) attached to every `recommendation.py` record, plus shared range-bar, reward:risk, support and check columns and a Reduce candidates filter on both tables (ADR-034). Actions are unchanged. Unit, real-SQLite and component tests pass; verified against a copy of the live database in an isolated app instance.
- **Recent-trade context (2026-10-08):** Recommendations had no memory of what was just traded, so a trimmed position kept reading TRIM with no acknowledgement. Added canonical `recent_trades.py` and a filled-trades repository query; every `recommendation.py` record now carries shares sold and bought in the last 14 days and whether that already follows the action (ACTED, OPPOSED, RECENT). Both holdings tables show it beside the action. Actions are unchanged; daily-loop and weekly-review route to the Questrade sync when a session is connected.
- **TradingView-default trade refresh (2026-10-08):** `daily-loop` and `weekly-review` told agents to use Questrade whenever a session was connected. They now refresh positions and executed trades through `/tv-portfolio-sync` by default and offer Questrade only when `broker_sources.py` reports it enabled, asking the owner which to use (ADR-036).
- **Daily Brief cards acknowledge trades (2026-10-08):** Recent-trade context reached the holdings tables but not the Daily Brief, so a TRIM the owner had just executed still read as an untouched recommendation. `brief_recommendations.py` now carries `recentTrades` on every card, appends what was sold or bought to the rationale, and words any remaining sizing as a further trade; the page shows the trade tag beside the action.
- **Comments describe current behaviour (2026-10-09):** About 100 comment and docstring lines in `py_services/` and the plugin scripts they link to said `portfolio.json` or `target-portfolio.json` was read, or narrated history ("previously ...", "Wave N cutover", "retired"). Several headers listed `portfolio.json` as an input for scripts that read SQLite or no data file. They now state what the code does today and list real inputs and outputs; parameters that are accepted but ignored say so. Comments and docstrings only (AST-identical with docstrings stripped; the `generate_reports.py` loader docstring now states what it returns). Code that still touches the files is left for separate fixes: `place_order.py` freshness gate and `system_health.py` check read `portfolio.json`'s age; `update_thesis.py` reads and writes `target-portfolio.json`, which is absent, and `thesisBreakers` has no column in `investment` so `thesis_breakers.py` evaluates none; `fetch_broker_data.py --compare` reads `portfolio.json`; the Express `portfolio.ts`, `stock.ts`, `screener.ts` and `BrokerSyncService.ts` keep file fallbacks.
- **Retired-file guard (2026-10-09):** Retiring `portfolio.json`, `target-portfolio.json` and related files was done script by script and nothing checked for leftover readers, so 14 Python files still read, wrote or stat-checked them (some silently doing nothing). Added `toolkit-manager/scripts/audit_sqlite_usage.py` and `test_no_retired_file_access.py` (wired into the `run_tests.py` T0 gate), reclassified the files as `RETIRED_PORTFOLIO_DATA` in `audit_json_usage.py`, and wrote ADR-038. The guard is red on purpose until the tool ports (WS2-WS4) land; the listed findings are in `docs/plans/sqlite-single-source-of-truth-spec.md` Appendix A.
- **Thesis breaker tables and one role vocabulary (2026-10-09):** Breaker definitions and evaluated state had no SQLite home (`investment.thesis_breaker_status` empty for every row), `portfolio_change_log` had no writer, and role names disagreed across tools (`core` defaults, `LIFECYCLE`/`INACTIVE_ROLES` copies, `update_thesis.py` `VALID_ROLES`). Migration `0002_thesis_breakers` adds `thesis_breaker` and `thesis_breaker_state`; `thesis_breaker_repository` (Python and TypeScript) holds the shared breaker vocabulary and reads/writes; `record_change()` numbers change-log entries; `portfolio_io.LIFECYCLE_STATUSES` is the one role list (a test fails if the TypeScript copy drifts); `load_thesis_holdings()` and `build_thesis_map()` now return stored `thesisBreakers`. The state writer, its readers and `update_thesis.py` move in WS2. Files added or touched by WS0/WS1 were then brought in line with `coding-conventions.md` (headers, docstrings, functions split below the complexity ceiling), behavior unchanged.
- **Standing-decision coherence and daily priority (2026-10-08):** Cards showed the valuation action beside a contradicting standing decision with no reconciliation (IREN: TRIM and HOLD AT TARGET; ZS: TRIM and accumulate on 200 EMA retest; GEV: a watchlist entry call on a held position), ranked by a score nearly every card shared, and kept acted-on trades at the top. Added canonical `standing_decision_check.py` (AGREES, CONFLICT, WAITS, OUTDATED, UNCLEAR, with an effective stance and decision age) on every `recommendation.py` record; Daily Brief cards show one reconciled stance, explain the disagreement, and are ordered ready, needs-decision, no-trade, waiting, acted-on, with an A–Z toggle; added `set_standing_decision.py` as the one way to update or clear a decision; added the shared `recommendation-coherence.md` procedure linked into six review and valuation skills. Chart-level condition evaluation is specified in the procedure for agents; evaluating it in code is not yet built.
- **One stance per card, confirmed decisions, checked conditions, refresh-first (2026-10-08):** A card held by a standing decision showed a "signal ACCUMULATE" chip beside MAINTAIN and read as two recommendations; a decision the owner had set that day still ranked as "Needs your decision"; conditions such as "add below $9" were never compared with the price; and top cards could be acted on from a 37-day-old valuation with no forward-earnings review. `standing_decision_check.py` gained the CONFIRMED relation (decision set within 30 days) and `decision_condition` (price levels in the decision type, EMA level from the decision's reason); `risk_reward.refresh_advice` flags stale valuations; Daily Brief cards lead with the stance, state the valuation view as one sentence, show the distance to the owner's level, lift met conditions to the top group, and put a `/update-stock-analysis` chip on stale top-five cards; every page reads the action through one `stanceOf` helper; acted-on rows sort last in the screener's action sort. `verify_refresh.py` no longer lists the exited HUMN as a no-change position. Not built: the technical sweep still does not store EMA values, so EMA conditions use the level recorded in the decision.
- **Debt shown beside every valuation (2026-10-08):** Fair value, the valuation range and reward:risk gave no sign of how debt was treated. `risk_reward.debt_view` adds a `debt` field to every `recommendation.py` record from what the valuation saved (leverage grade, rate check, previous fair value); both holdings tables show a debt badge beside the check, including "Debt ?" for a valuation never checked (ADR-037).
- **Re-based valuations read as fresh; Daily Brief gets the valuation visuals (2026-10-08):** The debt re-base saved 84 valuations again with a new rate, so the support check dated them to the save (0 days old) and counted the re-base's own `valuationModel` entry as a forward-earnings review; support rose from 2 to 3 of 4 and the refresh-first chips disappeared from stale cards. `risk_reward.evidence_date` now dates a re-based valuation from its original analysis and `_forward_check` ignores re-base bookkeeping. `debt_view` no longer describes unaudited firm cash-flow valuations as audited. Daily Brief cards show the tables' range bar, gap to fair value, reward:risk, support and debt badge through one shared `ValuationStrip`.
- **Daily loop refreshes prices in Step 0 (2026-10-09):** The `/tv-portfolio-sync` refresh updates positions, cash and trades but not `investment_price`, so a scan run straight after a clean sync still priced every card off the previous day's closes (stored total US$33,457 against TradingView's live US$33,736, the US$278.69 `CASH_INVARIANT` warning). The only price writer was the Express `/refresh-prices` route, which made a database skill depend on the web server. New `plugins/tradingview/scripts/tv_price_refresh.py` reads the held and watchlisted symbols from `domain_model.sqlite`, resolves prices with the canonical `fetch_portfolio_data` (TradingView first, yfinance fallback), and writes through `investment_price_repository`; tested against a temporary SQLite database, and against a copy of the real one it refreshed the same 89 symbols as the route with every price within 2%. Deliberate difference from the route: a symbol with no usable quote keeps its previous row and is reported as `stale` with exit 1, instead of its row being deleted first. `daily-loop` Step 0 and `tv-price-refresh` now call the script. The `tv-price-refresh` skill had documented a script that did not exist and claimed `tv_batch_quotes.py` saves prices. `audit-skill`: 0 errors and 0 warnings before and after on both skills, evals byte-identical (daily-loop 15, tv-price-refresh 6). The `tv-price-refresh` evals' `pass_condition` text still cites `portfolio.json` and 'Hard Rule N'; left unedited because it changes expected outcomes and needs the owner's call. Still open: the Express route keeps its own copy of this logic (rule 22); remaining `portfolio.json` readers are `fetch_broker_data.py::fetch_broker_snapshot` (`--compare`), `system_health.py::_check_portfolio_file`, `run_investment_toolkit.py` bootstrap, and the TypeScript `readPortfolio()` fallbacks.
