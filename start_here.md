# Session Start Briefing — InvestmentToolkit
_Last updated: 2026-07-05 | Thesis v9.7 | Portfolio ~$32,904 USD (reconciled from Questrade screenshots)_

> **Read this first at the start of every new session.**

---

## 🔥 ACTIVE: Fable5 Elevation Guide — Phase 2a DONE, start Phase 2b here

**Context:** User had Fable5 (primary), Gemini, GPT, Grok review the codebase for
"next level" improvements — reviews saved at `temp/bundles/full-bundle/reviews/`.
Fable5's guide (`fable5-ELEVATION_GUIDE.md`) is the one being executed — the only review
grounded in the actual repo. It's a 6-phase roadmap: (1) data layer, (2) valuation
committee, (3) executable scoring framework + local TA engine, (4) TradingView/Pine
hardening, (5) risk engine + rebalancer + prediction ledger + backtesting, (6) skills/
sub-agent architecture cleanup. Phase 2 was split into two sub-phases during brainstorming
(2a = Valuation Committee, 2b = Executable Framework + local TA) because it bundled two
loosely-coupled workstreams. **This session starts fresh on Phase 2b — Phases 1 and 2a are
fully shipped, verified, and merged to `origin/main`. Nothing from either needs redoing.**

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

### ✅ Phase 2a (Valuation Committee) — COMPLETE, on `origin/main` right now
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

### 🚦 Git policy going forward
**Standing pattern, now confirmed twice (Phase 1, Phase 2a):** after each phase's
whole-branch review passes, Claude pushes a dedicated `feature/fable5-phase<N>-<name>`
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
done, not from memory of having run `git push` earlier — this session confirmed PR #60's
merge this way before updating this file.

### Next step for this session
Phase 2b = Workstream B (Fundamental Analyst) + C1 from `fable5-ELEVATION_GUIDE.md`: **B1
scoring engine** (`framework_score.py` — encodes the full investment-framework doc into a
deterministic 0.25/0.20/… weighted composite score), **B3 peer benchmarking**
(`peer_bench.py` — reuses the `peers` field seeded in Phase 2a), and **C1 local TA engine**
(`technicals.py` — needed as a trend-input metric for the framework score; independent
ground truth alongside the TV scrape). Confirm scope/sequencing with the user first (this
repo's brainstorming skill gate applies: don't start implementation before a design is
proposed and approved) — likely worth the same brainstorming pass done for 2a (check
whether B1/B3/C1 should further split into separate specs, given C1 in particular is its own
substantial engine). §9 in the guide has the full phase/acceptance-criteria breakdown.

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
