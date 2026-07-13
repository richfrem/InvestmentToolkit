# Phase 4, Sub-Spec 2 — B4 Earnings Intelligence

**Status:** Draft, pending user review
**Phase:** Fable5 elevation guide, Phase 4 ("Track Record")
**Sub-spec order:** After E3 (Prediction Ledger) → Before G4 (Structured Events)

## 1. Problem

E3's prediction ledger captures action ratings, DCF fair values, and rebalance orders, but
ignores one of the highest-impact forecast categories: **earnings surprises**. When a company
beats or misses consensus estimates by 10-20%, that's a material surprise that should move
portfolio weight — but we have no structured way to (a) record what we predicted vs. what
happened, or (b) calibrate which earnings signals (analyst consensus, guidance deltas,
pre-earnings technicals) actually moved price correctly.

Additionally, `/daily` currently sources earnings dates from `earnings_calendar.py`
(yfinance ETdata), but the date alone isn't actionable without context: consensus estimates,
guidance, prior-beat history, TA setup at earnings time.

## 2. Scope

**In scope (this sub-spec):**
- A unified earnings expectations schema (estimate source: yfinance consensus) + actual result.
- An `earnings_expectation` claim-emitter that harvests consensus EPS/revenue estimates from
  earnings calendar fetch, logs pre-earnings prediction, grades post-earnings surprises.
- Wiring into E3's prediction ledger (emits `earnings_expectation` claim type).
- Integration into `/daily`: surface upcoming earnings for ACCUMULATE-band holdings, show
  prior-year surprise % (if available).
- Integration into `/weekly-review`: grading pass on matured earnings (actual results published),
  feed into track-record report.
- A simplified pre-earnings checklist: "Stock X reports in 2 days — consensus EPS $Y.ZZ, beat
  chance 67% (historical), current TA: STRONG (RSI 72, above 200d, MACD positive)."

**Out of scope (deferred):**
- Retroactive backfilling earnings surprises from before this ships — earnings archives exist
  in yfinance but reconstructing what we "predicted" is inherently speculative (different from
  E4's historical portfolio state, which is auditable). Ledger starts recording from deploy.
- Guidance revisions tracking (mid-quarter CFO updates) — only initial pre-earnings + actual.
- Options/IV crush correlation — pure flow analysis, orthogonal to this.
- Earnings beats/misses in the context of a portfolio-level rebalance trigger — that's G4's job
  (structured events). This sub-spec just records and grades the claims.
- Custom consensus overrides (e.g., "I don't trust Street consensus, here's my estimate"). Keeps
  it simple: one estimate source (yfinance), one grading curve.

## 3. Current-state findings

- **Earnings calendar is fetched fresh in `/daily`** via `earnings_calendar.py` (`yfinance.Ticker
  .calendar.earnings_dates`, one-week window). Schema: `ticker, date, consensus_eps, consensus_revenue`.
- **`consensus_eps` and `consensus_revenue` are often NULL in yfinance** — especially for newly
  IPO'd or micro-cap names. Graceful degrade: "no consensus" = no claim emitted (not an error).
- **We already have `fetch_financials.py` with TTL-cached `get_earnings_dates()`** — can be
  reused, or we can fetch fresh in B4 (depends on latency tradeoffs vs. staleness).
- **`aiThesis.fairValue` + `target-portfolio.json` entry's `targetWeight` exist for all
  holdings** — enough to surface "this is an ACCUMULATE candidate and earnings are in 3 days".
- **yfinance provides no historical "consensus at date X" archive** — we can only compare
  current consensus vs. actual after the fact, not what consensus *was* the week before. Grading
  curve: simple directional (beat/meet/miss), not magnitude.

## 4. Architecture

### New file: `py_services/earnings_expectations.py`

Three functions (CLI-callable, importable):

1. **`harvest_earnings_expectations()`** — run every `/daily`
   - Fetches earnings calendar for the week (yfinance)
   - For each date, queries `target-portfolio.json` to find holdings reporting that date
   - Checks `data/predictions.jsonl` tail for the most recent `(ticker, earnings_expectation)`
     claim
   - If consensus EPS/revenue changed OR no prior record exists, appends new `earnings_expectation`
     claim to prediction ledger
   - Dedup logic: matches on `(ticker, "earnings_expectation", earnings_date)` — if the
     consensus_eps value is identical to last logged value, skip (no change = no new claim)

2. **`grade_earnings_expectations()`** — run every `/weekly-review` Phase 2
   - Scans `data/predictions.jsonl` for ungraded `earnings_expectation` claims where
     `earnings_date <= today` (the earnings have already happened)
   - Fetches latest earnings results from yfinance (same source, refreshed daily)
   - Compares consensus EPS vs. actual EPS
   - Grades as: BEAT (actual > consensus * 1.02), MEET (±2%), MISS (actual < consensus * 0.98)
   - Appends grading record to `data/predictions_graded.jsonl` (reuses E3's grading schema)

3. **`get_earnings_context(ticker, days_ahead=7)`** — called by `/daily` brief generator
   - Returns a dict: `{ ticker, next_date, days_until, consensus_eps, consensus_revenue,
     prior_beat_pct, current_holding_weight, target_weight, action }`
   - Used to populate the "📊 Upcoming Earnings" section in the daily brief

### Schema changes to `predictions.jsonl` (E3 contract)

No breaking changes — B4 just adds a new claim type. E3's schema already reserves:
```json
{
  "id": "uuid",
  "ticker": "NVDA",
  "date": "2026-07-12",
  "type": "earnings_expectation",
  "source": "yfinance_consensus",
  "claim": {
    "consensus_eps": 0.52,
    "consensus_revenue": 9.4e9,
    "earnings_date": "2026-07-15"
  },
  "v": 1
}
```

Grading output to `data/predictions_graded.jsonl`:
```json
{
  "prediction_id": "uuid",
  "grade_date": "2026-07-16",
  "grade": "BEAT",
  "actual_eps": 0.56,
  "actual_revenue": 9.8e9,
  "eps_surprise_pct": 7.7,
  "revenue_surprise_pct": 4.3,
  "v": 1
}
```

### Wiring points

**`/daily` (new subsection in brief generator)**
- After macro/regime context, before TA sweep
- Heading: `📊 UPCOMING EARNINGS (7-day window, ACCUMULATE holdings highlighted)`
- For each holding in target-portfolio with earnings in next 7 days:
  - ` • NVDA (ACCUMULATE, +12.5% target) reports 2026-07-15 (in 3d)
       Consensus: EPS $0.52 | Rev $9.4B | Beat rate: 67% (5yr)`
- Graceful degrade: if no consensus, show "Consensus: Not available"
- Non-blocking: if earnings calendar fetch fails, skip section with stderr note

**`/weekly-review` (new phase)**
- Add Phase 2: `Earnings Grade` (after Phase 1 Risk Officer review, before macro/regime)
- Call `grade_earnings_expectations()` and pass results to brief
- Format: `🎯 Earnings Summary (past week):
   • NVDA: BEAT by 7.7% (actual $0.56 vs. $0.52 consensus)
   • CRWV: MISS by -2.1% (actual $1.87 vs. $1.91 consensus)
   • 1 TBD (CORZ reports 2026-07-18)`
- Feeds into track-record report (E3's `generate_track_record_report.py` totals by claim type)

## 5. Test coverage (TDD)

- **`test_harvest_earnings_expectations_dedup_on_unchanged_consensus.py`** — same consensus
  value twice in a row → no new claim logged (pure dedup)
- **`test_harvest_earnings_expectations_logs_consensus_change.py`** — consensus revises from
  $1.00 → $1.10 → new claim appended
- **`test_harvest_earnings_expectations_null_consensus_degrades_gracefully.py`** — yfinance
  returns NULL consensus → no claim emitted (not an error)
- **`test_grade_earnings_expectations_classifies_beat_meet_miss.py`** — actual $1.08, consensus
  $1.00 → BEAT; $0.99 → MISS; $1.00-$1.02 → MEET
- **`test_grade_earnings_expectations_only_grades_past_dates.py`** — earnings date in future →
  no grade attempt (structural check)
- **`test_get_earnings_context_returns_prior_beat_rate.py`** — function returns 5-year win
  rate (or NULL if <5 data points exist)
- **`test_earnings_expectation_claim_round_trips_ledger.py`** — harvest → ledger → grade →
  predictions_graded, then re-read to verify all fields intact

## 6. Known limitations & trade-offs

1. **yfinance consensus staleness** — consensus updates throughout earnings season but yfinance
   doesn't version it. We record *current* consensus when harvest runs; if consensus revised
   between last fetch and earnings date, we don't know. Acceptable: most consensus stickiness
   happens weeks out; day-of revisions are rare. Mitigation: run harvest daily.

2. **No historical consensus archive** — can't answer "what did the Street think on Day 1 vs.
   Day 3 before earnings?" Acceptable: keep it simple, one-shot harvest per week per ticker.

3. **Binary beat/meet/miss grade** — no magnitude scoring (e.g., a 15% beat counts same as a
   1% beat). Acceptable: directional matters more than magnitude for signal calibration.
   Future: can add P10/P50/P90 bucketing if we accumulate enough data.

4. **Manual entry for non-consensus estimates** — if user wants to log a private estimate
   (e.g., "I think EPS is $0.58, Street says $0.52"), they can't. Out of scope: would require
   a new SKILL for interactive estimate entry. Rare enough that we skip it.

## 7. Acceptance criteria

- `harvest_earnings_expectations()` deduplicates on unchanged consensus and appends claims to
  `data/predictions.jsonl`
- `grade_earnings_expectations()` runs post-earnings-date, fetches actual results, grades,
  appends to `data/predictions_graded.jsonl`
- `/daily` surfaces upcoming earnings for ACCUMULATE holdings with consensus + historical beat %
- `/weekly-review` shows past-week earnings grades and feeds into track-record report totals
- All 7 TDD test cases pass
- Schema round-trips: harvest → ledger → grade → graded ledger, no data loss
