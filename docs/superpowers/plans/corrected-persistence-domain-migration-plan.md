# Corrected Persistence-Domain Migration Plan

Supersedes the "hybrid" framing in the prior certification work. This is a plan, not a
completion claim — nothing in this document has been executed. Every classification below is
based on direct evidence gathered from this repository (real producer/consumer file counts via
grep, real on-disk shape via direct JSON inspection), not inference from prior reports.

**Correction of prior failure:** the earlier SQLite work added a database populated with one
narrow slice of data (80 research events) that the running application does not read from at
runtime, while calling that "migration complete." This plan starts over from the actual
objective: reduce real JSON/JSONL dependency, migrate what should move, and give explicit,
falsifiable justification for anything that stays JSON — no domain gets `RETAIN_AS_*` without
answering the required questions.

---

## Classification Legend

1. `MIGRATE_TO_SQLITE_EVENT_MODEL` — append-only historical record, one row per dated
   occurrence, never edited after creation.
2. `MIGRATE_TO_SQLITE_DOMAIN_TABLE` — current-state data, mutated in place, benefits from SQL
   even though it isn't event-shaped.
3. `GENERATED_FROM_SQLITE` — derived output, safe to regenerate, not authoritative itself.
4. `RETAIN_AS_CONFIGURATION_JSON` — static config, not runtime data.
5. `RETAIN_AS_EXTERNAL_CACHE` — mirrors an external system's state; the external system is
   authoritative, this is a local cache/mirror.
6. `RETAIN_AS_SEPARATE_APPROVED_LEDGER` — already event-sourced JSONL, but a genuinely separate
   domain from the intelligence ledger; not migrated to intelligence.sqlite specifically.
7. `ARCHIVE_AFTER_VERIFIED_MIGRATION` — superseded once migration lands; not yet, since nothing
   has migrated under this corrected plan.
8. `UNKNOWN_BLOCKER` — needs a decision or information not available from repo evidence alone.

---

## Domain-by-Domain Classification

### 1. `investment_screener/backend/data/portfolio.json`

- **Shape:** single DICT (`holdings`, `totals`, `tvSnapshot`) — current-state snapshot.
- **Scale:** 70+ referencing files across backend routes, py_services scripts, frontend
  components, and 3 plugins (`tradingview`, `stock-valuation`, `portfolio-advisor`). This is the
  single most deeply load-bearing file in the entire repository.
- **Authoritative or derived:** derived — it's a local mirror of TradingView/broker state,
  refreshed by `fetch_broker_data.py` / `BrokerSyncService.ts`. The broker is authoritative.
- **Why not an event:** it's "what do I hold right now," not a log of holding-changes.
- **Classification:** `RETAIN_AS_EXTERNAL_CACHE`, with a caveat — see below.
- **Caveat / real answer to "what would break if removed":** everything. 70+ files read this
  file directly, several via direct `fs.readFile`/`json.load`, not through a service abstraction.
  Migrating this to SQLite is architecturally reasonable (`MIGRATE_TO_SQLITE_DOMAIN_TABLE` is
  defensible too), but is a multi-week undertaking on its own — not a task to fold into a
  research-ledger migration. Flagging as a **separate, explicitly scoped future migration**, not
  attempting it here. It is gitignored (private financial data) — that constraint carries over
  regardless of storage engine.

### 2. `investment_screener/backend/data/theses/target-portfolio.json`

- **Shape:** single DICT — `pillars`, `holdings`, `globalSettings`, whole-document
  `version`/`updatedAt`. Mutated in place on save, not appended.
- **Scale:** 39 referencing files.
- **Authoritative or derived:** authoritative — this is the actual source for target weights and
  the `standingDecision` anchor (CLAUDE.md rule #8: never flip BUY→SELL on <15% variance without
  reading this file first).
- **Why not an event:** `standingDecision` is a single current decision per ticker, revised in
  place. There is no requirement to query decision *history* today.
- **Why not currently a SQL table:** it's read as one whole document by every consumer (drift
  calculations, rebalancing, weight sums) — a genuine multi-row SQL table would require every one
  of those 39 consumers to change from "load one JSON blob" to "query N rows," for a benefit
  (search/indexing) nothing currently needs.
- **Classification:** `MIGRATE_TO_SQLITE_DOMAIN_TABLE` — architecturally the right target
  eventually (one row per ticker, `standingDecision`/`targetWeight` as columns, real SQL update
  semantics instead of whole-file rewrites), but scoped as a **separate future migration** given
  the 39-consumer blast radius. Not `RETAIN_AS_*` — this should move, just not in this pass.

### 3. `investment_screener/backend/data/cash_flows.json`

- **Shape:** mixed — `starting_balance_cad`/`starting_date` (single baseline values) +
  `cash_flows` (a genuine append-only array: 3 dated deposit/withdrawal entries, immutable once
  recorded).
- **Scale:** 3 referencing files (`portfolio.ts`, `audit_json_usage.py`, `ytd_return.py`).
- **Classification:** `MIGRATE_TO_SQLITE_EVENT_MODEL` for the `cash_flows` array (it's already
  event-shaped: date, type, amount, account — maps directly onto the same event pattern as
  `intelligence_event`). The baseline fields (`starting_balance_cad`/`starting_date`) are
  `MIGRATE_TO_SQLITE_DOMAIN_TABLE`-shaped (single current config values) or could live as a
  seed/baseline row. Small blast radius (3 consumers) — this is a **real, near-term candidate**,
  not a someday-maybe.

### 4. `investment_screener/backend/data/projections/*.json` (144 files)

- **Shape:** per-ticker array of version entries (`[{version: 1, aiThesis: {...}}, {version: 2,
  ...}]`) — append-style: new versions get added, old versions are read but not rewritten.
- **Scale:** 23 referencing files.
- **Authoritative or derived:** authoritative — this is the DCF/valuation model's actual output,
  including thesis rationale and the `researchReport` pointer this whole prior effort was built
  around.
- **Why this looks event-shaped but wasn't treated that way:** each version is effectively an
  immutable "on this date, this model produced this valuation" record — structurally close to
  `intelligence_event`. It was classified `ALLOWED_MODEL_ARTIFACT_JSON` in the earlier audit
  without interrogating this properly.
- **Classification:** `MIGRATE_TO_SQLITE_EVENT_MODEL` is defensible for the version-history
  aspect. This needs real design work (23 consumers, and it's the file every valuation skill
  writes to) — flagged as a **separate future migration**, not `RETAIN_AS_*` by default. The
  prior audit's `ALLOWED_MODEL_ARTIFACT_JSON` classification undersold this file's real shape.

### 5. `investment_screener/backend/data/ta-sweep-results.json`

- **Shape:** single DICT, overwritten every run (`timestamp`, `scan_date`, `results`) — a latest
  snapshot cache, not a log itself.
- **Scale:** 6 referencing files.
- **Real status:** the event-shaped version of this data (`TECHNICAL_SWEEP`) already has working,
  tested dual-write code in `ta_sweep_batch.py`, verified correct by a real non-mocked test
  (`test_save_sweep_results_writes_to_ledger_and_sqlite`). It has never fired in production
  (`observations.jsonl` has zero `TECHNICAL_SWEEP` events).
- **Classification:** `GENERATED_FROM_SQLITE` for this specific file (once the ledger has real
  `TECHNICAL_SWEEP` history, this snapshot file could be a generated view rather than a
  standalone write target) — but this requires actually running the pipeline for real first,
  which has never happened. Not archivable yet — there's no verified ledger data to regenerate
  it from.

### 6. `investment_screener/backend/data/daily-briefs/*.json` (10 files)

- **Shape:** one file per date — already a de facto event log (10 dated snapshots).
- **Scale:** 9 referencing files.
- **Real status:** same pattern as #5. `daily_brief.py` has `REVIEW_DAILY` dual-write code, but
  I found **no real (non-mocked) test proving it's even correct**, and `observations.jsonl` has
  zero `REVIEW_DAILY` events. The 10 existing dated files were never backfilled.
- **Classification:** `MIGRATE_TO_SQLITE_EVENT_MODEL` — correct target, code partially exists,
  but is **unverified and unexercised**. Before this can be trusted: (a) write a real
  non-mocked test for the `REVIEW_DAILY` write path, (b) build and run a historical backfill
  script (mirroring `migrate_research_to_ledger.py`'s pattern) for the 10 existing files, (c)
  verify parity the way the research corpus was verified.

### 7. Weekly review — **no JSON file exists**

`weekly-review-agent.md` describes writing Markdown (not JSON) to
`investment_screener/backend/data/history/reviews/weekly/`. That directory does not exist on
disk. Either this has never been run, or the documented path is stale.
- **Classification:** `UNKNOWN_BLOCKER` — cannot classify a persistence domain that doesn't exist
  on disk. Needs you to confirm whether weekly review output should exist somewhere and doesn't,
  or whether the agent doc is describing an aspirational/unbuilt feature.

### 8. Grok output/report — **no persisted JSON file exists**

Grok sweep responses are explicitly ephemeral by design: the agent docs describe presenting a
generated prompt, the user pastes Grok's response back into the conversation, and it's referenced
from `temp/news-sweep-responses/{grok,gemini}/` — the `temp/` convention (CLAUDE.md pitfall #16)
is scratch space, not permanent storage.
- **Classification:** `UNKNOWN_BLOCKER` — same reasoning as #7. If Grok sweep output should be
  durably retained (it currently isn't, anywhere), that's a new capability to design, not a
  migration of an existing file.

### 9. Market research — **already covered, not JSON**

`data/research/` contains zero `.json`/`.jsonl` files. It's Markdown, and it's the one domain
that genuinely did get migrated into the ledger this session (80 dated files → `RESEARCH_IMPORT`
events). See §"What Actually Happened" below for the honest accounting of that migration's real
state.

### 10. Valuation/calculation — **same file family as #4**

There is no separate valuation/calculation JSON file. DCF outputs, scenario math, and thesis
rationale all live inside `projections/*.json`. See #4.

### 11. Holdings/current position — **same file family as #1**

`portfolio.json` *is* the holdings/current-position file. See #1.

### 12. `investment_screener/backend/data/watchlist.json`

- **Shape:** DICT wrapping a single `watchlist` list — current-state, mutated in place.
- **Scale:** 6 referencing files.
- **Classification:** `MIGRATE_TO_SQLITE_DOMAIN_TABLE` is defensible (small, simple, one row per
  watched ticker) but low priority given its small footprint and that it's arguably a subset of
  the larger `portfolio.json`/`target-portfolio.json` consolidation you floated earlier in this
  conversation. Flagged for the same future-migration bucket as #1/#2, not `RETAIN_AS_*` by
  default — there's no strong reason for it to stay JSON specifically, just no urgency either.

### 13. `investment_screener/backend/data/predictions.jsonl`

- **Shape:** already JSONL, one line per dated prediction claim (`id`, `date`, `ticker`, `type`,
  `claim`) — genuinely event-shaped, structurally close to `intelligence_event`.
- **Scale:** 7 referencing files.
- **Classification:** `MIGRATE_TO_SQLITE_EVENT_MODEL` — this is the single strongest, lowest-risk
  candidate in this entire list. It's already shaped exactly like what the intelligence ledger
  was built for, small consumer count, and the value (querying prediction accuracy over time)
  is real and currently unavailable.

### 14. `investment_screener/backend/data/orders_executed.jsonl`

- **Shape:** already JSONL, one line per executed-order decision (`timestamp`, `order`,
  `decision`, `gate_result`) — genuinely event-shaped, audit-trail by nature.
- **Scale:** 2 referencing files.
- **Classification:** `MIGRATE_TO_SQLITE_EVENT_MODEL` — same reasoning as #13. Small blast
  radius, clean event shape, real query value (trade history).

### 15. `investment_screener/backend/data/trade-log.json`

- **Shape:** LIST of 52 entries, each an immutable trade record (`id`, `date`, `loggedAt`) —
  event-shaped despite the `.json` extension rather than `.jsonl`.
- **Scale:** 4 referencing files.
- **Classification:** `MIGRATE_TO_SQLITE_EVENT_MODEL` — same reasoning as #13/#14.

### 16. `investment_screener/backend/data/observations.jsonl` / `research/archive/*`

Already migrated under the prior (mischaracterized) pass. Real, verified content — 80
`RESEARCH_IMPORT` events, byte-parity confirmed against `research/archive/*.md`. Both are
committed to git. **What's actually still wrong, stated plainly:** the live application does not
query this data at runtime; it reads static files generated from it once. See §"What Actually
Happened" below.
- **Classification:** `RETAIN_AS_SEPARATE_APPROVED_LEDGER` for the storage itself (this part is
  fine) — but the *consumption* side needs real work, tracked separately, not re-classified here.

### 17. Configuration / cache / test-fixture domains (unchanged from prior audit, re-confirmed correct)

- `account_policy.json` — DICT of rules/caps/config, zero runtime data.
  `RETAIN_AS_CONFIGURATION_JSON`. Why: it's never mutated by the running app, only by manual
  edits; there is no event or row-per-record shape here at all.
- `thesis_breaker_state.json` — single current-state snapshot (`generatedAt` + per-holding
  breaker status), regenerated wholesale each run, not appended.
  `MIGRATE_TO_SQLITE_DOMAIN_TABLE` is defensible but low-value (6 consumers, single-value nature)
  — flagged low-priority future work, not urgent.
- `tradingview_alerts_actual.json` — LIST of 203 entries, but each represents *current* alert
  state mirrored from TradingView (`active`, `last_fired` get updated in place on sync, not
  appended as new immutable records). `RETAIN_AS_EXTERNAL_CACHE` — TradingView is authoritative,
  this is a synced mirror, same reasoning as `portfolio.json`.
- `investment_screener/backend/data/research/{TICKER}.summary.md`/`.timeline.md` (144 files) —
  `GENERATED_FROM_SQLITE`, confirmed accurate — these really are regenerable from the ledger, and
  proven so this session.
- `investment_screener/backend/data/research/{TICKER}.md` (72 bare files) — pre-existing, unrelated
  to any ledger, `UNKNOWN_BLOCKER` on whether these should ever be reconciled with the ledger
  corpus at all (they hold different content for overlapping tickers — a real data question, not
  an engineering one).

---

## What Actually Happened vs. What Should Happen (Honest Accounting)

The prior pass built the storage and migrated one domain's *data* (research), but never made the
*application* depend on it — `docs.ts` generates static files from the ledger once and the live
app reads those files, bypassing SQLite entirely for every real request. That is the actual gap,
and it applies to every domain above that gets a `MIGRATE_TO_SQLITE_*` classification: **migrating
data without rewiring the actual read/write path in the app is not migration.**

## Required Follow-On Work (Not Yet Started)

For `research`/`observations.jsonl` (the one domain with real migrated data already):
1. Make `docs.ts` actually query SQLite live for the common request shape, or make the
   static-file-generation step a genuine part of the write path (triggered on every ledger
   append, not run manually once) so the "generated from SQLite" claim is continuously true
   instead of a one-time export.
2. Backfill and verify `TECHNICAL_SWEEP`/`REVIEW_DAILY` for real, with the same rigor applied to
   research (real test, real backfill, real byte-parity check) before either can be called
   migrated.

For the domains newly classified `MIGRATE_TO_SQLITE_EVENT_MODEL` in this plan
(`predictions.jsonl`, `orders_executed.jsonl`, `trade-log.json`, `cash_flows.json`'s flow array,
`daily-briefs`): none of this work has started. This document is the classification and
justification step only.

For the domains classified `MIGRATE_TO_SQLITE_DOMAIN_TABLE` but flagged as separate future
migrations (`portfolio.json`, `target-portfolio.json`, `projections/*.json`, `watchlist.json`,
`thesis_breaker_state.json`): these are large, blast-radius-heavy changes (up to 70+ consumer
files) that were never in scope of the original research-ledger work and should not be
attempted inside it. They need their own scoped plans.

## Explicit Non-Recommendation

I'm not proposing to execute any of the above right now. This document answers the classification
requirement. Next step is yours: which domain(s) do you want actually migrated for real — data,
producer, consumer, and app-runtime-dependency, all four — starting with which one first.
