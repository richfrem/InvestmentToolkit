# Qualitative Research Corpus Migration — Execution & Validation Report

This report documents the execution and validation of the qualitative research corpus migration into the SQLite Intelligence Ledger. It confirms that the 80 dated research files have been successfully migrated to the central database, the 118 dated references in the projections have been re-routed, and retrieval has been verified.

---

## 1. Pre-Migration Baseline

Before executing the migration, the repository state was captured:

*   **Git Status**: Clean (no staged or unstaged changes in source directories).
*   **Total Dated Research Files**: `80`
*   **Total Canonical/Summary Research Files**: `72`
*   **Total versions with `researchReport` references**: `120`
*   **Remaining Migration Candidates**: `1` (`evolution_events.py` telemetry logger)

---

## 2. Execution Log

The migration was performed in the following sequence:

### Step 1: Run `migrate_research_to_ledger.py`
Command:
```bash
python3 -c "
import sys
sys.path.insert(0, 'investment_screener/backend/py_services')
from migrate_research_to_ledger import migrate_to_ledger
res = migrate_to_ledger(
    'investment_screener/backend/data/research',
    'investment_screener/backend/data/observations.jsonl',
    'investment_screener/backend/data/research/archive'
)
print(res)
"
```
*   **Observed Output**: `{'migrated_count': 80}`
*   **Result**: 80 dated files successfully appended to `observations.jsonl` and moved to `data/research/archive/`.

### Step 2: Replay into `intelligence.sqlite`
Command:
```bash
python3 -c "
import sys
sys.path.insert(0, 'investment_screener/backend/py_services')
from rebuild_db import run_rebuild
res = run_rebuild(
    'investment_screener/backend/data/observations.jsonl',
    'investment_screener/backend/data/intelligence.sqlite'
)
print(res)
"
```
*   **Observed Output**: `{'ledger_valid_lines': 80, 'projected_rows': 80, 'skipped': 0, 'verified': True}`
*   **Result**: 100% database parity verified. 80 rows inserted into the `intelligence_event` table.

### Step 3: Run `migrate_research_report_pointers.py`
Command:
```bash
python3 -c "
import sys
sys.path.insert(0, 'investment_screener/backend/py_services')
from migrate_research_report_pointers import migrate_pointers
res = migrate_pointers('investment_screener/backend/data/projections')
print(res)
"
```
*   **Observed Output**: `{'rewritten_count': 118}`
*   **Result**: 118 versions rewritten from dated filenames to `{TICKER}.summary.md`.

---

## 3. Discrepancies & Observations

*   **Pointers Discrepancy (118 vs 120)**:
    *   *Observation*: The pre-flight check counted 120 versions with a `researchReport` field. The pointer rewriter successfully modified 118 fields.
    *   *Verification*: The 2 remaining fields already pointed to canonical `*.summary.md` and `*.timeline.md` files, which correctly did not match the dated regex. A follow-up check verified `0` remaining dated references across all projections.

---

## 4. Post-Migration Validation & Retrieval Tests

Retrieval was verified end-to-end through the ledger-backed API layers:

### A. Python Bridge Helper Test (`query_ledger_research.py`)
Tested retrieval of `AAPL_2026-05-02.md`:
```bash
python3 investment_screener/backend/py_services/query_ledger_research.py --get AAPL_2026-05-02.md
```
*   **Result**: Successfully retrieved `RESEARCH_IMPORT` event containing the complete markdown body text.

### B. Node/Express Endpoint Test (`docs.ts` route helper)
Tested retrieval of `AAPL`, `MSFT`, and a randomly selected migrated ticker (`ALAB`):
```bash
# AAPL
node -e "const { queryLatestResearchFromLedger } = require('./investment_screener/backend/dist/routes/docs'); queryLatestResearchFromLedger('AAPL_2026-05-02.md').then(console.log)"

# MSFT
node -e "const { queryLatestResearchFromLedger } = require('./investment_screener/backend/dist/routes/docs'); queryLatestResearchFromLedger('MSFT_2026-05-02.md').then(console.log)"

# ALAB (random migrated ticker)
node -e "const { queryLatestResearchFromLedger } = require('./investment_screener/backend/dist/routes/docs'); queryLatestResearchFromLedger('ALAB_2026-05-02.md').then(console.log)"
```
*   **Result**: All three returned the correct JSON payload from SQLite containing the full markdown text.
*   **List Verification**: `queryResearchListFromLedger()` returned exactly `80` active ledger references combined with local canonical files.

---

## 5. Risks & Rollback Instructions

If a rollback is required, run the following commands to revert all changes:

1. **Revert projection pointer changes**:
   ```bash
   git checkout -- investment_screener/backend/data/projections/
   ```
2. **Move files back from archive**:
   ```bash
   mv investment_screener/backend/data/research/archive/*.md investment_screener/backend/data/research/
   rmdir investment_screener/backend/data/research/archive
   ```
3. **Reset ledger and database**:
   ```bash
   rm investment_screener/backend/data/observations.jsonl
   rm investment_screener/backend/data/intelligence.sqlite
   # DB is regenerated empty or re-created on demand
   ```
