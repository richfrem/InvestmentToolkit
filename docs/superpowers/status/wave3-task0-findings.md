# Wave 3 Task 0 — Final Pre-Implementation Verification Sweep

**Date:** 2026-07-20
**Worktree:** `worktree-domain-model-v3-wave3`
**Scope:** Read-only investigation per `.superpowers/sdd/task-0-brief.md`. No application code touched.

## Recommendation: **NO-GO**

Two independent, blocking findings (Step 4 schema/shape mismatch, and a corrected duplication
finding that changes Task 0 Step 2's premise) mean Tasks 1–3 as currently written in
`docs/superpowers/plans/2026-07-20-domain-data-model-v3-wave3-implementation-plan.md` will silently
corrupt real, private TFSA/RRSP account attribution if executed as-is. Stop before Task 1.

---

## (a) Newly found real producers/consumers not already in the plan's tables

Repo-wide grep run (Step 1):
```
grep -rln "portfolio\.json\|PORTFOLIO_FILE\|PORTFOLIO_PATH\|PORTFOLIO_JSON" \
  investment_screener plugins .agents \
  --include="*.ts" --include="*.tsx" --include="*.py" --include="*.js" \
  2>/dev/null | grep -v "/tests/\|test_\|\.test\.\|ARCHIVE/\|node_modules\|__pycache__"
```
75 files matched. Every hit not already in the plan's "Confirmed REAL" / "Confirmed FALSE POSITIVE"
/ "spot-verified consumers" lists was read and classified against actual `open()`/`fs.writeFileSync`/
`json.load`/`load_json` calls (not docstrings/comments).

**New REAL producer:**
- `investment_screener/backend/src/utils/paths.ts` (line 17) defines
  `PORTFOLIO_FILE = path.join(__dirname, '../../data/portfolio.json')`.
- `investment_screener/backend/src/index.ts` (lines 71–74): on backend startup, if
  `!fs.existsSync(PORTFOLIO_FILE) && fs.existsSync(PORTFOLIO_EXAMPLE)`, it runs
  `fs.copyFileSync(PORTFOLIO_EXAMPLE, PORTFOLIO_FILE)` — a real write path (clean-clone seeding),
  missing from the plan's 5-producer table entirely. Low-risk (dev-bootstrap only, not a live sync
  writer) but must be rewired or explicitly named as an accepted JSON-fallback exception, since after
  migration this line would seed a *file* nothing else reads.

**New REAL consumers:**
- `investment_screener/backend/py_services/system_health.py::_check_portfolio_file()` (lines 89–97)
  — opens `DATA / "portfolio.json"`, checks existence + `mtime` for a staleness diagnostic
  (`/tv-portfolio-sync` freshness check). Real file-presence/freshness consumer, absent from the
  spot-verified list.
- `plugins/portfolio-advisor/scripts/ytd_return.py` (line 170) — `load_json(PORTFOLIO_PATH)` for
  live portfolio balances feeding YTD return calculation. Real consumer, absent from the list.
- `plugins/portfolio-advisor/scripts/generate_grok_prompt.py` (line 113) and
  `plugins/portfolio-advisor/scripts/generate_review_json.py` (line 52) — both call
  `validate_weights.compute_current(PORTFOLIO)`, which does `open(portfolio_path)` /
  `json.load(f)` (confirmed in `validate_weights.py` lines 51–53, itself already a listed real
  consumer). Two more real callers of that same read path, not listed.

**Confirmed false positives (checked, no real touch):** `audit_json_usage.py` (classifies filenames
into an audit taxonomy string set — never opens `portfolio.json`'s content itself),
`evolution_events.py`, `fetch_quotes.py`, `file_lock.py`, `sector_overrides.py`,
`ticker_aliases.py`, `refresh_all.py`, `apply_catalyst.py`, `reverse_dcf.py`, `wacc.py`,
`portfolio_action.py` (reads `domain_model.sqlite` only), `update_targets.py`,
`domain_model/backfill_investment_universe.py`, `domain_model/migrate_target_portfolio_to_sqlite.py`,
`migrations/remove_drift_threshold_fields.py` (all four are `target-portfolio.json`/Wave-2-domain
only — grep false-matched the substring "portfolio.json" inside "target-portfolio.json"),
`zod-schemas.ts` (comment-only, no file I/O itself), `InvestmentRepository.ts` (only
`target-portfolio.json` references, same substring false-match).

## (b) Resolution of the two `generate_portfolio_blueprint.py` implementations question

**The plan's claim is wrong.** The plan states (line 115): *"A real duplication, not a symlink"* —
this is the opposite of reality:

```
$ ls -la investment_screener/backend/py_services/generate_portfolio_blueprint.py \
         plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py
lrwxr-xr-x  ... generate_portfolio_blueprint.py -> ../../../plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py
-rw-r--r--  ... plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py
$ diff <both files>
(no output — byte-identical, confirmed by reading both in full)
```

`investment_screener/backend/py_services/generate_portfolio_blueprint.py` **is a symlink** to the
`plugins/portfolio-advisor/scripts/` copy — already following CLAUDE.md rule 5 (symlink-only), not
violating it. There is exactly **one real file** reachable from two paths, not two independent
implementations. Both read paths go through `portfolio_io.py::load_portfolio_state()` (via
`build_actual_map`) and `validate_weights.compute_current(PORTFOLIO_JSON)` — a single real consumer,
already counted once in the plan's 7-caller `portfolio_io.py` list and once in the spot-verified
list (double-listed as "two copies" there, which should be corrected to "one file, two paths").

No collapse/follow-up work is needed — there is nothing to collapse. This is a factual correction to
the plan's premise, not a new duplication-cleanup task.

## (c) Confirmation of `portfolio.json`'s real top-level shape

```
$ python3 -c "import json; d = json.load(open('investment_screener/backend/data/portfolio.json')); \
  print(list(d.keys())); print(type(d.get('holdings')))"
['holdings', 'totals', 'tvSnapshot']
<class 'list'>
```

Top-level keys match the plan's assumption (`holdings` + `totals` + `tvSnapshot`). However, the
**internal shape of `holdings` and the location of per-account data does not match what Tasks 1–3
assume**:

- `holdings` (29 entries) is a **flat, cross-account-aggregated** view. Sample entry:
  `{"symbol": "CRCL", "shares": 13, "book_price": 109.31, "market_value": 821.86, "price": 63.22,
  "last_updated": "..."}` — **no `account` field on any entry.** `shares: 13` is the sum across
  both TFSA and RRSP (matches the plan's own test comment at line 499: "13 (TFSA 10 + RRSP 3)").
- `totals` is a **portfolio-level scalar** (`holdingsUSD`, `cashUSD`, `totalUSD`, `totalCAD`,
  `exchangeRate`, `timestamp`, `totalSource: "tv_authoritative"`) — not per-account, not per-position.
- The **real per-account breakdown lives only in `tvSnapshot`**:
  - `tvSnapshot.accounts` — 3 real broker accounts: `RRSP` (`accountId: "53408195"`),
    `CASH` (`accountId: "40049489"`), `TFSA` (`accountId: "53408189"`).
  - `tvSnapshot.snapshots` — per-account balance objects (`cashUSD`, `marketValueUSD`,
    `totalEquityUSD`, `totalEquityUSDCombined`, etc.) keyed by `accountType`/`accountId`.
  - `tvSnapshot.positions` — **56 entries**, each with real per-account attribution:
    `{"symbol": "CRCL", "direction": "Long", "quantity": 4, "avgFillPrice": 108.59, "profit": -169.2,
    "positionId": "...", "accountType": "RRSP", "accountId": "53408195"}`.

**This differs materially from what Tasks 1–3 assume**, and the plan's own Task 2 explicitly named
this exact risk (line 437–441: *"a portfolio-level total, if still needed as a scalar, is Task 3's
job to place correctly once Task 0's Step 4 confirms the real portfolio.json shape... if Task 0
finds the real shape needs a new column, stop and get it approved"*) and Task 3's own fixture
(`FIXTURE_PORTFOLIO`, lines 615–621) invents an `"account": "TFSA"` / `"account": "RRSP"` key on
each holding that **does not exist anywhere in the real file**.

## (d) GO/NO-GO recommendation with reasoning

**NO-GO.** Two blocking issues, both explicitly anticipated and gated by the plan itself:

1. **Task 3's migration script silently mis-attributes every holding to TFSA.**
   `_load_holdings()` / `run_real_migration()` read `h.get("account", "TFSA")` — since no real
   holding carries an `"account"` key, **every one of the 29 aggregated (TFSA+RRSP-summed) holdings
   would be written into the `TFSA` account row**, and the RRSP split would be silently dropped
   entirely. This is a real per-account attribution bug on real, private financial data — exactly
   the class of failure CLAUDE.md rule 8/`portfolio-total-validation` memory exists to prevent. The
   real per-account source data (`tvSnapshot.positions`) uses a structurally different shape
   (`quantity`/`avgFillPrice`/`accountId`/`accountType`, not `shares`/`price`/`account`) that Tasks
   1–3 never reference. Tasks 2–3 need to be rewritten against `tvSnapshot.positions`, not the flat
   `holdings` array, before implementation starts.

2. **`total_usd`'s real-broker-total column has no home**, exactly as Task 2 itself flagged pending
   this step's findings. The real `totals.totalUSD` (`tv_authoritative`-sourced) is a
   portfolio-level scalar; `account_investment` is a per-position table with no place for it. Per
   CLAUDE.md pitfall #27 and the MEMORY.md "Portfolio Total Validation" critical rule (never compute
   totals from shares×price — always use the broker-reported total), Task 2's current fallback
   (`sum(shares × price)`, `_totals_from_broker: False` always) would **regress this invariant**
   for every real consumer relying on `load_portfolio_state()`'s `total_usd` if shipped as-is. This
   needs the same explicit user-approved schema decision Wave 2 required before proceeding (new
   column on `account`, or a small new table) — not a silent default.

3. (Non-blocking, but must be corrected before Task 8 or any consumer rewiring references it) The
   plan's premise for Task 0 Step 2 was backwards: the two `generate_portfolio_blueprint.py` "copies"
   are a correctly-symlinked single file, not two divergent implementations. No collapse work is
   needed; the plan's Task 8 (and its lead-in commentary) should drop the "resolve the duplication"
   framing.

4. (Non-blocking additions to the producer/consumer inventory, folded in before restarting Task 0):
   `investment_screener/backend/src/index.ts` (new real producer, dev-bootstrap seed-from-.example),
   `system_health.py`, `ytd_return.py`, `generate_grok_prompt.py`, `generate_review_json.py` (four
   new real consumers), and `investment_screener/backend/src/utils/paths.ts` (the TS-side constants
   module analogous to `portfolio_io.py` — every TS producer/consumer routes through
   `PORTFOLIO_FILE` defined here, so this is a useful single rewire point on the TS side, worth
   naming explicitly the way `portfolio_io.py` was on the Python side).

**Per Task 0 Step 5's own instructions:** these findings — a real schema-mismatch blocking Task 2/3
as designed, plus new real producers/consumers absent from the plan's tables — are exactly the
"materially different from this plan's tables" case that requires stopping and presenting to the
user before Task 1, not proceeding.
