# Portfolio Advisor — Evolution Log

Each daily-loop session appends an entry here. The agent reads this log to detect
patterns: consecutive EXIT signals, pillar stress, repeated user overrides, tool
regressions. This is the memory that makes the loop smarter over time.

---

<!-- Sessions are appended below in reverse-chronological order (newest first) -->

## 2026-07-18 — Weekly Review & Target Calibration

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

**Tier: 2 (Failure)** — `GET /api/projections/CACI` returned `401 Unauthorized — missing or invalid local API token` during `/evaluate-stock CACI` run. Root cause: `localAuth` middleware was added to the Express backend but no skill documentation was updated to include the `Authorization: Bearer` header.

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