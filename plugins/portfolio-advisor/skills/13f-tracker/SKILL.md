---
name: 13f-tracker
plugin: portfolio-advisor
description: Polls SEC EDGAR for 13F-HR institutional filings from target funds, downloads and parses holdings into structured JSON, and generates quarter-over-quarter diffs.
---

# 13F Tracker

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- SEC EDGAR rate limit is ~10 requests per second; respect backoff if throttled.
- Situational Awareness LP CIK is `0002045724` (Aschenbrenner; AI/ASI infrastructure focus).
- All parsed holdings and diff files must be stored in `investment_screener/backend/data/13f/`.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/fetch_13f.py --cik 0002045724 --poll
```

## Workflow
1. **Poll**: Compare cached accession numbers against EDGAR submissions index for the target CIK.
2. **Fetch**: Download XML holdings table for new filings and parse into structured JSON.
3. **Diff**: Compute quarter-over-quarter position changes (new, closed, increased, decreased).
4. **Export**: Save `{CIK}_index.json`, `{accession}.json`, and `{CIK}_diff.json` to the data directory.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/fetch_13f.py --cik 0002045724 --summary
python3 plugins/portfolio-advisor/scripts/fetch_13f.py --cik 0002045724 --diff
```
