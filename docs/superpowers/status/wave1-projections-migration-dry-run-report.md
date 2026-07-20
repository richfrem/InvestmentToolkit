# Wave 1 Task 2 — Projections Migration Dry-Run Report

**Status: DRY RUN ONLY. No real database was written.** This report is the output of
`run_dry_run()` in `investment_screener/backend/py_services/domain_model/migrate_projections_to_sqlite.py`,
which operates entirely against an in-memory (`:memory:`) SQLite connection. The real
`domain_model.sqlite` file was never opened or touched by this run.

Generated: 2026-07-19, by running:

```bash
python3 -c "
import sys
sys.path.insert(0, 'investment_screener/backend/py_services')
from pathlib import Path
from domain_model.migrate_projections_to_sqlite import run_dry_run
import json
report = run_dry_run(Path('investment_screener/backend/data/projections'))
print(json.dumps(report, indent=2))
"
```

against the real directory `investment_screener/backend/data/projections/`.

## Headline numbers (verbatim from the real run)

| Metric | Value |
|---|---|
| Total `.json` files found | **82** |
| Expected file count (per task brief) | 144 |
| Delta | **-62** (see "File count delta" below) |
| Total `projection_version` rows the migration would create | **132** |
| Total `projection_scenario` rows the migration would create | **396** |
| Files that failed to parse under either known shape | **0** |
| Legacy-top-level-only shape entries | **0** |
| Entries with both top-level AND nested `aiThesis` fields (3rd shape) | **2** |
| Entries with no `scenarios` block | **0** |

## File count delta — 82 found vs. 144 expected

The task brief states an expectation of 144 files, carried over from when the wave plan
was drafted. As of 2026-07-19 the real `investment_screener/backend/data/projections/`
directory contains **82** `.json` files (confirmed via `find ... -type f -name "*.json" | wc -l`,
matching a plain directory listing — no subdirectories, no non-JSON files). This is a real
finding, not a bug in the dry-run script: the corpus has apparently shrunk or been
consolidated since the 144 figure was written into the plan (exact cause not
investigated further here — that's outside this task's scope, which is to report the
real number, not explain a directory's history). **The gate-review conversation in Step 6
should confirm with the user whether 82 is the expected current count before Task 4 is
approved.**

## Shape survey (real data, all 82 files / 132 entries)

Before writing `parse_projection_entry`, 15 real files were read directly (not just the
fixtures) — a mix of the 5 oldest files by git history (`DXYZ`, `DRAM`, `HUMN`, `KOID`,
`ETHA`), 5 mid-range files (`FOTO`, `IBIT`, `WQTM`, `APLD`, `AAPL`), and 5 of the newest
(`TSLA`, `ZS`, `OKLO`, `INTC`, `IONQ`) — followed by a full scan of all 82 files/132
entries to get exact totals. Findings:

- **130/132 entries** use only the current nested shape: `aiThesis.fairValue` /
  `aiThesis.action`. This is now the dominant real-world shape.
- **0/132 entries** use only the legacy top-level shape (`fairValue`/`action` present,
  no `aiThesis`). The "legacy" fixture (`LEGACY_ENTRY`) in the test suite exercises code
  that is not observed live in the current corpus, but is kept because the interface
  contract requires it and older archived/future data may still produce it.
- **2/132 entries — a third shape not named in the task brief** — carry **both** a
  top-level `fairValue`/`action` and a nested `aiThesis.fairValue`/`action`:
  - `IONQ.json`, entry `id=6c0140d1-b493-4a89-8a7c-8a528de89a88`, `version=1`,
    `savedAt=2026-05-04T15:09:22Z`: top-level `fairValue=10.24`, nested
    `aiThesis.fairValue=8.54` — **these disagree**. `action` agrees as `SELL` in both.
  - `QBTS.json`, entry `id=29b55aff-b8de-48f0-9e4a-6c845bf2445a`, `version=1`,
    `savedAt=2026-05-04T15:09:46Z`: top-level and nested values **agree**.

  A test (`test_parse_projection_entry_prefers_ai_thesis_when_both_shapes_present`) was
  added to `test_migrate_projections_to_sqlite.py` before implementing the handling for
  this case. `parse_projection_entry` treats `aiThesis` as authoritative whenever it is
  present, even if legacy top-level fields also exist and disagree with it — because
  130/132 real entries rely on `aiThesis` exclusively and both "both-shape" entries are
  early (`version: 1`, 2026-05-04, the earliest `savedAt` timestamps in the corpus),
  consistent with `aiThesis` being the newer, currently-written field and the top-level
  fields being stale leftovers from an older write path.
- **0/132 entries** have neither shape (i.e., no `fairValue`/`action` anywhere). No
  per-file or per-entry parse errors occurred.
- **0/132 entries** have a missing/empty `scenarios` block in the real corpus — every
  real entry has `bear`/`base`/`bull` scenarios, unlike the `NO_SCENARIOS_ENTRY` fixture
  which exercises the empty-scenarios code path defensively.

## Per-ticker breakdown (all 82 tickers, versions / scenarios / errors)

```
AAPL 2 6 []
ALAB 2 6 []
AMD 2 6 []
AMZN 2 6 []
ANET 3 9 []
APLD 1 3 []
ASML 1 3 []
ASTS 1 3 []
AVGO 3 9 []
BE 3 9 []
BITF 1 3 []
BTDR 1 3 []
BW 2 6 []
CACI 1 3 []
CAKE 2 6 []
CBRS 1 3 []
CEG 3 9 []
CELH 2 6 []
CIFR 1 3 []
CLSK 2 6 []
COHR 1 3 []
COIN 2 6 []
CORZ 3 9 []
CRCL 2 6 []
CRM 1 3 []
CRSP 1 3 []
CRWD 2 6 []
CRWV 3 9 []
DRAM 1 3 []
DXYZ 1 3 []
EQIX 3 9 []
EQT 1 3 []
ETHA 1 3 []
FOTO 1 3 []
GOOG 2 6 []
HUMN 1 3 []
HUT 1 3 []
IBIT 1 3 []
INTC 4 12 []
IONQ 1 3 []
IREN 1 3 []
KOID 1 3 []
KRC 1 3 []
KRMN 1 3 []
LBRT 1 3 []
LITE 2 6 []
LLY 1 3 []
META 3 9 []
MSFT 3 9 []
MU 1 3 []
NBIS 1 3 []
NKE 2 6 []
NOW 1 3 []
NVDA 5 15 []
OKLO 3 9 []
ORCL 2 6 []
PANW 2 6 []
PLTR 2 6 []
POET 1 3 []
PSIX 1 3 []
PUMP 1 3 []
QBTS 1 3 []
RDW 1 3 []
RGTI 1 3 []
RIOT 1 3 []
RKLB 1 3 []
SEI 1 3 []
SHAZ 1 3 []
SKHY 1 3 []
SNDK 3 9 []
SPCX 1 3 []
SYM 2 6 []
TEAM 1 3 []
TEM 1 3 []
TSEM 1 3 []
TSLA 1 3 []
TSM 1 3 []
VRT 2 6 []
VST 2 6 []
WQTM 1 3 []
WYFI 1 3 []
ZS 2 6 []
```

(format: `ticker versions_migrated scenarios_migrated errors`. Sum of `versions_migrated`
= 132. Sum of `scenarios_migrated` = 396. Every `errors` list is empty — `file_errors` at
the top level of the report is also `[]`.)

## Full raw JSON report

```json
{
  "total_files": 82,
  "total_versions": 132,
  "total_scenarios": 396,
  "legacy_shape_count": 0,
  "missing_scenarios_count": 0,
  "both_shapes_count": 2,
  "file_errors": []
}
```

(the `per_ticker` array from the raw report is reproduced in table form above; full raw
JSON including `per_ticker` is reconstructable by re-running the command at the top of
this report — it was not committed here verbatim a second time to avoid duplicating the
per-ticker table twice in the same file.)

## Hard-gate note

Per the wave plan, this dry run does not authorize any real write. Task 3 (explicit user
review of these numbers) and Task 4 (the real migration, gated on Task 3's approval) are
separate, later steps and were not run as part of this task.
