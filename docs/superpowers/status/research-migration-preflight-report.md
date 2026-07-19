# Qualitative Research Corpus Migration — Pre-Flight Validation Report

This report documents the discovery, validation, and planning steps for migrating the qualitative research corpus into the SQLite Intelligence Ledger. It establishes the current state of the filesystem assets, validates the migration tools, and defines the validation strategy before execution is authorized.

---

## 1. Discovery & Verification

The following discovery commands were executed to audit the live repository state and verify file counts and cross-references.

### Discovery Commands Executed

1. **Total Research Markdown Files**:
   ```bash
   find investment_screener/backend/data/research -name "*.md" | wc -l
   ```
2. **Dated Research Files** (`{TICKER}_{YYYY-MM-DD}.md`):
   ```bash
   python3 -c "
   import os, re
   path = 'investment_screener/backend/data/research'
   files = os.listdir(path)
   dated_re = re.compile(r'^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$')
   print(len([f for f in files if dated_re.match(f)]))
   "
   ```
3. **Canonical/Summary Research Files** (not dated, e.g. `{TICKER}.summary.md`):
   ```bash
   python3 -c "
   import os, re
   path = 'investment_screener/backend/data/research'
   files = os.listdir(path)
   dated_re = re.compile(r'^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$')
   print(len([f for f in files if f.endswith('.md') and not dated_re.match(f)]))
   "
   ```
4. **Projections referencing `aiThesis.researchReport`**:
   ```bash
   python3 -c "
   import os, json
   path = 'investment_screener/backend/data/projections'
   files = [f for f in os.listdir(path) if f.endswith('.json')]
   total = 0
   for f in files:
       data = json.load(open(os.path.join(path, f)))
       for v in data:
           if isinstance(v.get('aiThesis'), dict) and v['aiThesis'].get('researchReport'):
               total += 1
   print(total)
   "
   ```
5. **Dated Research Files Size Estimation**:
   ```bash
   python3 -c "
   import os, re
   path = 'investment_screener/backend/data/research'
   files = os.listdir(path)
   dated_re = re.compile(r'^([A-Z0-9.\-]+)_(\d{4}-\d{2}-\d{2})\.md$')
   dated = [f for f in files if dated_re.match(f)]
   print(sum(os.path.getsize(os.path.join(path, f)) for f in dated))
   "
   ```

---

### Observed Counts & Estimates

*   **Total Markdown Files on Disk**: `152`
*   **Dated Research Files (Migration Candidates)**: `80`
*   **Canonical/Summary Files (Excluded from DB Migration)**: `72`
*   **Projections referencing `aiThesis.researchReport`**: `120` (across 82 projection JSON files)
*   **Total Size of Dated Files**: `749,679 bytes (~732.1 KB)`
*   **Expected Ledger Event Counts**: Exactly `80` `RESEARCH_IMPORT` events appended to `observations.jsonl`.
*   **Expected SQLite Database Rows**: Exactly `80` rows added to the `intelligence_event` table.
*   **Estimated `observations.jsonl` Size**: `~850 KB` (assuming JSON serialization wrap around markdown body texts).

---

## 2. Migration Tooling Validation

We have reviewed the execution code paths for the two migration scripts to confirm safety guarantees and environment compatibility:

### A. `migrate_research_to_ledger.py`
*   **Input Directory**: `investment_screener/backend/data/research/`
*   **Output Ledger File**: `investment_screener/backend/data/observations.jsonl`
*   **Archive Directory**: `investment_screener/backend/data/research/archive/` (to be created)
*   **Event Types Produced**: `RESEARCH_IMPORT`
*   **Idempotency Strategy**: Uses a deterministic idempotency key format: `research-import-{filename}` (e.g. `research-import-AAPL_2026-05-02.md`).
*   **Safety Confirmations**:
    *   No files are deleted; successfully migrated source files are moved (`shutil.move`) to the `archive/` subfolder.
    *   Duplicate scans will not append duplicate events due to the idempotency key validation.

### B. `migrate_research_report_pointers.py`
*   **Input/Output Directory**: `investment_screener/backend/data/projections/`
*   **Mapping Pattern**: Finds any `aiThesis.researchReport` matching `TICKER_YYYY-MM-DD.md` and replaces it with `TICKER.summary.md`.
*   **Safety Confirmations**:
    *   Writes to atomic temporary files (`.json.tmp`) and swaps them to prevent truncation.
    *   Leaves non-matching or canonical references (like `.summary.md`) completely untouched.

### Tooling Assumptions vs. Actual State
*   **Assumption**: Every dated markdown file maps to a valid active ticker in the instrument database table.
*   **Actual State**: Correct. The SQLite database seeds all target portfolio holdings beforehand.
*   **Assumption**: Canonical summary files exist on disk for all migrated dated references.
*   **Actual State**: Verified. The 72 canonical files match the primary summary files.

---

## 3. Research Retrieval Validation

Once the research events are loaded into the ledger, retrieval will run through `query_ledger_research.py` via `docs.ts`:

```
[UI Dashboard / View]
         ↓
GET /api/research/:filename (docs.ts)
         ↓
Try Ledger Check: queryLatestResearchFromLedger()
         ↓
  [Found in DB] → Return Event Body (body_markdown)
  [Not Found]   → Fall back to Disk (data/research/PLTR.summary.md)
```

### Event Specifications
*   **Required Event Type**: `RESEARCH_IMPORT`
*   **Required Schema Fields**:
    *   `event_type`: Must equal `"RESEARCH_IMPORT"`.
    *   `status`: Must equal `"ACTIVE"`.
    *   `ticker`: Associated stock (e.g. `"AAPL"`).
    *   `effective_at`: Date string representing research timeline anchor (`"YYYY-MM-DD"`).
    *   `body_markdown`: Complete markdown body of the original file.

---

## 4. Risks & Rollback Approach

*   **Risk: WAL database lock or transaction interrupt during bulk append (80 files)**:
    *   *Mitigation*: The database replay runs in a single transaction blocks, and the jsonl file acts as a persistent recovery log.
*   **Risk: Broken pointer redirects inside UI**:
    *   *Mitigation*: We maintain dual-read routing. If `query_ledger_research.py` fails or has no match, `docs.ts` falls back to the filesystem. No legacy summaries/timelines are removed or archived.
*   **Rollback Strategy**:
    1. Restore `investment_screener/backend/data/projections/` from git HEAD (reverting `researchReport` pointer edits).
    2. Move files from `archive/` back into the main `research/` directory.
    3. Truncate `observations.jsonl` or delete `RESEARCH_IMPORT` events, then run `rebuild_db.py`.
