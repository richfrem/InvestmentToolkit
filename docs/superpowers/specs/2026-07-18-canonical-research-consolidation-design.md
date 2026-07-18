# Design Spec: Canonical Research Consolidation & Unified Ingest Pipeline

## 1. Context & Goal
Our retail investment workstation has fragmented files containing qualitative analysis, sweeps, and temporary caches. 
The goal of this project is to consolidate stock-specific research markdown logs into single canonical ticker files (`research/{TICKER}.md`), move review reports from `temp/` to a git-committed history folder, and relocate raw JSON cache dumps to a structured caching path.

---

## 2. Directory Layout Migration Map

We are migrating directories as follows:

| Legacy Gitignored Path | New Committed Path | Purpose |
|---|---|---|
| `temp/daily-reviews/` | `investment_screener/backend/data/history/reviews/daily/` | Storing generated daily portfolio confluence scans |
| `temp/weekly-reviews/` | `investment_screener/backend/data/history/reviews/weekly/` | Storing generated weekly portfolio confluence scans |
| `temp/news-sweep-responses/` | `investment_screener/backend/data/history/sweeps/` | Archive of raw inputs from Grok/Gemini |
| `temp/*_raw.json` | `investment_screener/backend/data/cache/yfinance/` | Raw financial metrics caches |
| `temp/deep_timeframe_ta.json` | `investment_screener/backend/data/cache/tv_snapshots/` | Technical analysis temporary snapshots |

---

## 3. Canonical Research Profile Schema (`research/{TICKER}.md`)

Each ticker in `investment_screener/backend/data/research/` will have a single master file named `{TICKER}.md`.
It will begin with a structured YAML frontmatter block to allow scripts to parse and update metrics programmatically.

```yaml
---
ticker: PLTR
name: Palantir Technologies
lastUpdated: 2026-07-18T09:30:00Z
fairValue: 147.06
priceAtAnalysis: 130.96
action: HOLD
subStrategyId: sa-asi-race
---

# PLTR Canonical Research History

## Research Sweep — 2026-07-18
* **Catalysts:** AIP partnership with Nvidia for air-gapped deployments.
* **Metrics:** 85% YoY revenue growth, US commercial +133%.

## Research Sweep — 2026-07-02
* ...
```

---

## 4. Implementation Steps

### Step 1: Write and Verify the Consolidation Script (`consolidate_research.py`)
* The script groups legacy files by ticker, sorts chronologically, queries the corresponding `projections/{TICKER}.json` to extract YAML metadata, merges the dated markdown logs, writes `{TICKER}.md`, and cleans up dated duplicates with a `--delete-old` flag. *(Done & verified with tests in test_consolidate_research.py)*.

### Step 2: Update References in Code base
* Update path mappings in `generate_reports.py` and `weekly_review.py` to point to the new `history/reviews/` directories. *(Done & verified with tests in test_weekly_review.py)*.

### Step 3: Run the Consolidation Script
* Run `python3 plugins/portfolio-advisor/scripts/consolidate_research.py --delete-old` on the codebase to perform the physical file merge.

---

## 5. Spec Self-Review
1. **Placeholder Scan:** No "TBD" or "TODO" items remain in the implementation scope.
2. **Internal Consistency:** The YAML schema matches the exact properties exported by yfinance and the DCF model.
3. **Decomposition:** The scope is small and fully contained within the `portfolio-advisor` plugin environment.
