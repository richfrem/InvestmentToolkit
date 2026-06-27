# Portfolio Advisor — Evolution Log

Each daily-loop session appends an entry here. The agent reads this log to detect
patterns: consecutive EXIT signals, pillar stress, repeated user overrides, tool
regressions. This is the memory that makes the loop smarter over time.

---

<!-- Sessions are appended below in reverse-chronological order (newest first) -->

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
failed because TradingView's Questrade panel was showing a reconnect dialog, not live positions.
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
- TV Questrade session can drop silently; broker panel shows reconnect dialog without any CDP-visible error
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
