# Session Start Briefing — InvestmentToolkit
_Last updated: 2026-07-04 | Thesis v9.7 | Portfolio ~$32,904 USD (reconciled from Questrade screenshots)_

> **Read this first at the start of every new session.**

---

## 🚦 Git policy while Fable5 Elevation Guide is in progress

**Do NOT push to `origin/main` until all 6 Fable5 phases are complete** — this is an
explicit user instruction (2026-07-04). Local `main` accumulates completed work normally
(merge each finished phase's branch locally, verify tests, delete the local branch). After
each milestone, also push a dedicated `feature/fable5-<milestone>` branch to `origin` as a
backup — never `origin/main` directly. Local `main` will keep drifting ahead of
`origin/main` by design until the user says otherwise.

Backup branches on GitHub so far (all supersets of each other, safe to leave):
- `worktree-market-data-layer` — Phase 1 data layer, 17 commits, pre-dashboard-fixes
- `feature/dashboard-fixes-2026-07-02` — the dashboard/data-integrity fixes commit alone
- `feature/fable5-phase1-data-layer-complete` — **current milestone**, everything merged
  into local `main` so far (data layer + dashboard fixes)

---

## 🔥 ACTIVE: Fable5 Elevation Guide — Market Data Layer Build (resume here first)

**Context:** User had Fable5 (primary), Gemini, GPT, Grok review the codebase for
"next level" improvements — reviews saved at `temp/bundles/full-bundle/reviews/`.
Fable5's guide (`fable5-ELEVATION_GUIDE.md`) is the one being executed — it's the only
review grounded in the actual repo. Decomposed via brainstorming into sub-projects;
started with **Phase 1: data layer** (`market_data.py` provider abstraction — directly
motivated by two real bugs found this session, see below).

**Artifacts (all committed to `main`):**
- Design spec: `docs/superpowers/specs/2026-07-02-data-layer-design.md`
- Implementation plan: `docs/superpowers/plans/2026-07-02-market-data-layer.md` (8 tasks)
- Progress ledger: `.claude/worktrees/market-data-layer/.superpowers/sdd/progress.md`

**Execution mode:** `superpowers:subagent-driven-development`, in an isolated worktree —
`.claude/worktrees/market-data-layer` (branch `worktree-market-data-layer`). The worktree
was fast-forwarded to local `main` at creation, so it has the two committed spec/plan
commits but **not** the 40 files of uncommitted fixes below (worktrees don't share
uncommitted changes across checkouts — this was verified to be fine because Tasks 1-8 are
self-contained new files with no runtime dependency on those uncommitted changes).

**Status: ALL 8 TASKS COMPLETE** (commits `43f042e..f04cdbf` on branch
`worktree-market-data-layer`, HEAD = `f04cdbf`). Every task went through implementer →
review → fix-round (where needed) → re-review, all now Approved. Full detail in the ledger:
`.superpowers/sdd/progress.md`.

| Task | What | Outcome |
|---|---|---|
| 1 | `cache.py` (shared TTL cache) | Approved (1 fix: docstrings) |
| 2 | `get_prices()` | Approved (1 fix: **critical** NaN-crash on misaligned trading calendars — e.g. TSX holiday gaps) |
| 3 | `get_quote()` | Approved (1 fix: **critical** batch-crash on bad/delisted ticker) |
| 4 | `get_estimates()` | Approved first pass — implementer proactively avoided the NaN/crash pattern |
| 5 | `edgar_facts.py` (SEC EDGAR XBRL client) | Approved (1 fix: malformed-value crash + docstrings) |
| 6 | `data_quality.py` (disagreement/staleness gate) | Approved first pass — tests written directly (primary-owned per plan), implementation delegated to Haiku |
| 7 | `get_fundamentals()` (EDGAR/yfinance waterfall) | Approved — 5-scenario robustness proactively built & verified with value-level assertions |
| 8 | Schema + full regression check | Approved — `jsonschema` added properly via `requirements.in`+pip-compile, 162 passed/3 skipped/2 pre-existing-verified-failed |

**Recurring pattern (worth remembering for future plans in this style):** 3 of 8 tasks
shipped with a "crashes or silently zeroes on missing/malformed data" bug that review
caught via direct reproduction and sent back for one fix round each — exactly the bug
class this data layer exists to eliminate. By Task 4, implementers started proactively
guarding against it without review needing to catch it at all.

**Known, deliberately-deferred follow-up (not a blocker, zero current callers):**
`get_fundamentals()` (Task 7) and `get_estimates()` (Task 4) share the same cache key
`(ticker, "fundamentals")` with incompatible entry shapes. Confirmed safe (each guards its
own read, no misread), but whichever runs second overwrites the other's cache entry —
if a future caller ever fetches both for the same ticker, it defeats the 24h TTL and
doubles live EDGAR+yfinance calls. Fix: give `get_fundamentals()` a distinct data-class
key (e.g. `"fundamentals_full"`) before wiring anything that calls both together.

**Whole-branch review: DONE, verdict "Ready to merge: Yes with minor fixes."** Caught 3
Important cross-task issues no single per-task review could see in isolation:
1. `data_quality.py`'s gates compared EDGAR annual figures against yfinance TTM figures —
   would have made staleness read `True` ~8 months/year for every US filer, and made the
   5% disagreement threshold fire constantly on ordinary growth, training users to ignore it.
2. `edgar_facts.py` only checked the `Revenues` GAAP tag — many large real filers use
   `RevenueFromContractWithCustomerExcludingAssessedTax` instead, silently falling back to
   yfinance and quietly defeating the point of using EDGAR.
3. SEC's required ≤10 req/s rate limit was never implemented, and the `"edgar"` 7-day cache
   TTL class in `cache.py` was dead — `get_company_facts()` never actually cached anything.

**All 3 fixed** (commit `0a0f3b5`, "fix: decouple EDGAR staleness from annual period, add
revenue tag fallback, wire caching/throttle"): staleness now uses the most recent filing of
*any* form (10-K or 10-Q) while the reported value still comes from the latest 10-K;
disagreement now cross-checks against yfinance's *annual* `.financials` instead of TTM
`.info`; revenue extraction falls back to the alternate GAAP tag; `get_company_facts()` is
now cache-first (7-day TTL) with a 0.15s throttle on real network calls only. Targeted suite
34/34 passed; full suite 175 passed / 3 skipped / 2 pre-existing-and-verified failed
(`test_math_parity` path bug, a date-sensitive `test_place_order_gates` weekend-gate test —
both confirmed unrelated via `git stash`, same two that showed up throughout this whole
build). Fix report (not committed, gitignored by convention):
`.claude/worktrees/market-data-layer/.superpowers/sdd/whole-branch-review-fix-report.md`.

**✅ Whole-branch-review fix (`0a0f3b5`): RE-REVIEWED, "Ready to merge: Yes."** All 3
findings confirmed genuinely resolved (correct precedence/decoupling logic, comprehensive
tests), previously-verified paths (both-sources-missing, EDGAR-unavailable) confirmed
unchanged. One note: the fix report's claim that test-isolation work "exposed a latent
pre-existing defect" in Task 5 was overstated by the reviewer's own assessment — it was
necessary hygiene for newly-wired caching, not a review-process miss (pre-fix code had no
cache calls at all). Not a blocker either way.

**✅ Merged to local `main`** (fast-forward, `43f042e..0a0f3b5`), worktree removed
(`ExitWorktree action:"remove"` — safe, commits already fast-forwarded into `main` first).
Tests verified on `main` post-merge: 187 passing, same 2 pre-existing-unrelated failures.

**✅ Phase 1 (data layer) is fully DONE.** Nothing left to do on it except the two
deliberately-deferred follow-ups below — both are separate future work, not blockers.

**Deliberately deferred (separate future work, not blockers on Phase 1 completion):**
1. **The 13-file yfinance migration** onto this new `market_data.py` layer — needs each of
   the 13 files (`fetch_financials.py`, `portfolio_performance.py`, `macro_regime.py`,
   `earnings_calendar.py`, `fetch_quotes.py`, `overnight_gaps.py`,
   `fetch_portfolio_heatmap.py`, `history_store.py`, ETF/TV scripts, one TS-adjacent file)
   read fresh for accurate before/after steps. `fetch_financials.py` has its own bespoke
   1hr-TTL cache at `plugins/stock-valuation/scripts/cache/` that must be *replaced*, not
   duplicated, by the new shared `cache.py`.
2. **Cache-key collision** between `get_fundamentals()` and `get_estimates()` (both key on
   `(ticker, "fundamentals")`, confirmed safe/no-misread but cache-defeating) — fix before
   any future caller uses both functions for the same ticker together.

**Next up: pick the Phase 2 sub-project from the Fable5 guide** (valuation committee /
executable scoring framework / TA engine / TradingView-Pine hardening / risk engine +
rebalancer + prediction ledger / skills cleanup — see `fable5-ELEVATION_GUIDE.md` §2-8 for
the full menu). Follow the same process as Phase 1: brainstorm → spec → plan →
`subagent-driven-development` in a fresh worktree → whole-branch review → merge to local
`main` only (see git policy banner at the top of this file — do not push `origin/main` yet).

---

## ⚠️ UNCOMMITTED WORK ON MAIN — 40 files, do not lose

The main checkout (`/Users/richardfremmerlid/Projects/InvestmentToolkit`, NOT the worktree)
has ~40 files of real, tested, working fixes from the 2026-07-02 session that were **never
committed** (only asked-for commits get made, per standing instruction). Run `git status`
there first thing. Highlights:

- **`portfolioSnapshot.ts`** — `preserveAuthoritativeTotal()` + `computeWeightsMap()`,
  fixes the dashboard "+29.79% today" bug and a real $685.82 cash-undercount bug (only
  RRSP's cash was being read, not all 3 accounts). Portfolio totals were manually
  reconciled from Questrade screenshots and written to `portfolio.json` with
  `totalSource: "tv_authoritative"` — this will hold until the next real sync IF
  `preserveAuthoritativeTotal()` ships (it's currently uncommitted).
- **`portfolio_performance.py`** — fixed `safe_float(NaN)->0.0` silently zeroing PSU-U.TO's
  value on TSX holidays (Canada Day), which caused the impossible +29.79% 1-day return.
- **`standardize_metrics.py`** — fixed `net_income`/`profit_margin` silently defaulting to
  0.0 when raw data has `profit_margin` but no `net_income` key (found via PLTR).
- **`fetch_broker_data.py`** — `build_totals_from_balances()` now tags `totalSource:
  "tv_authoritative"` so Python-sourced totals are also protected by
  `preserveAuthoritativeTotal()` once both land.
- **`.agent/rules/no-silent-nan-to-zero.md`** — new rule (untracked), the throughline
  connecting the above three bugs.
- **`.agent/rules/news-technical-confluence.md`** — new rule (untracked) requiring
  `[CONFLUENCE]/[PARTIAL]/[CONFLICT]` verdicts on every ACCUMULATE/EXIT/TRIM recommendation,
  checked against both news (Grok/Gemini sweeps) and technicals. Wired into
  `daily-loop-agent.md`, `portfolio-advisor-orchestrator.md`, `thesis-review-agent.md`,
  `weekly-review-agent.md`, and the `x-news-sweep` skill.
- **`target-portfolio.json`** — weight-sum drift fixed (99.29%→99.9998%) via
  `validate_weights.py --normalize --write`; root cause was BE's deliberate 2026-06-29
  weight reduction never being rebalanced. New local git hook
  `.git/hooks/pre-commit-thesis-sync-check` now blocks any future commit that leaves this
  file out of sync (local-only, like the repo's other hooks — not tracked in git).
- **`PLTR.json` projection + research report** — fresh DCF (HOLD, FV $147.06 vs $130.96),
  resolves a `[CONFLICT]` between a stale prior SELL call and Grok/Gemini's "INITIATE NOW."
- New test files (untracked): `test_standardize_metrics.py`, `test_compute_current_weights.py`
  (cross-language parity with TS, mirrors `test_math_parity.py`), `test_portfolio_performance.py`,
  `test_build_totals_from_balances.py`. All green; only the pre-existing `test_math_parity.py`
  path bug remains as an unrelated failure.

**Ask the user before committing this** — it's a lot of real fixes, but commit scope/message
grouping should be a conscious decision, not automatic.

## 🟡 Other open items from 2026-07-02 (not yet resolved)

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
