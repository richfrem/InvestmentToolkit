---
name: 13f_tracker
plugin: portfolio-advisor
description: >
  Poll SEC EDGAR for 13F-HR institutional filings from a target fund, download
  and parse holdings into structured JSON, and generate quarter-over-quarter
  diffs. Trigger on "check 13F", "SA LP filings", "poll for new 13F", or
  "show SA LP holdings".
allowed-tools: Bash, Read, Write
---

# 13F Tracker Skill

## What This Skill Does

1. **Polls** SEC EDGAR for new 13F-HR filings vs the local cache (no API key required)
2. **Downloads** and parses holdings XML into structured JSON
3. **Diffs** the latest filing against the prior quarter — new positions, closed, increased, decreased
4. **Summarises** current holdings ranked by portfolio weight
5. **Integrates** with x-news-sweep Gate 5 (SA LP cross-check uses `{CIK}_diff.json` as authoritative source)

---

## API

SEC EDGAR data is **free, no authentication required**. Rate limit ~10 req/s.

| Endpoint | Purpose |
|---|---|
| `https://data.sec.gov/submissions/CIK{CIK10}.json` | Filing history — all 13F-HR accession numbers and dates |
| `https://www.sec.gov/Archives/edgar/data/{CIK}/{acc}/` | Filing folder — discover holdings XML filename per filing |
| `https://www.sec.gov/Archives/edgar/data/{CIK}/{acc}/{file}.xml` | Holdings data (ns1:informationTable XML) |

---

## Known Funds

| Fund | CIK | Notes |
|---|---|---|
| Situational Awareness LP | `0002045724` | Aschenbrenner; AI/ASI infrastructure concentrated |

Add more CIKs to this table as needed.

---

## Commands

### Daily poll (run at session start)
```bash
python3 scripts/fetch_13f.py --cik 0002045724 --poll
```
Compares cached latest filing date against EDGAR. Prints `🆕 New filing detected` if found,
then automatically downloads and diffs. Exit 0 either way.

### Full initialisation (first run or catch-up)
```bash
python3 scripts/fetch_13f.py --cik 0002045724 --fetch-last 4
```

### Current holdings summary
```bash
python3 scripts/fetch_13f.py --cik 0002045724 --summary
```

### Quarter-over-quarter diff
```bash
python3 scripts/fetch_13f.py --cik 0002045724 --diff
```

### All at once (poll + fetch + summary + diff)
```bash
python3 scripts/fetch_13f.py --cik 0002045724 --all
```

---

## Data Files

All output lives in `investment_screener/backend/data/13f/`:

| File | Contents |
|---|---|
| `{CIK10}_index.json` | Filing list cache — accession numbers, dates, periods |
| `{accession_nodash}.json` | Full parsed holdings for one filing |
| `{CIK10}_diff.json` | Latest vs prior quarter — new/closed/increased/decreased |

### Holdings JSON schema
```json
{
  "cik": "0002045724",
  "fund": "Situational Awareness LP",
  "filing_date": "2026-02-11",
  "period_of_report": "2025-12-31",
  "accession": "0002045724-26-000002",
  "total_value_thousands": 1234567,
  "position_count": 18,
  "holdings": [
    {
      "name": "INTEL CORP",
      "cusip": "458140100",
      "title_class": "COM",
      "value_thousands": 98765,
      "value_pct": 8.2,
      "shares": 2500000,
      "type": "SH",
      "put_call": "Call",
      "discretion": "SOLE"
    }
  ]
}
```

### Diff JSON schema
```json
{
  "from_date": "2025-09-30",
  "to_date": "2025-12-31",
  "new_positions": [...],
  "closed_positions": [...],
  "increased": [{"name": "...", "delta_shares": 0, "delta_pct": 0.0, ...}],
  "decreased": [...],
  "unchanged": [...]
}
```

---

## 13F Filing Calendar

13F-HR filings are due **45 days after quarter-end**:

| Quarter | Period End | Filing Deadline |
|---|---|---|
| Q1 | Mar 31 | ~May 15 |
| Q2 | Jun 30 | ~Aug 15 |
| Q3 | Sep 30 | ~Nov 15 |
| Q4 | Dec 31 | ~Feb 15 |

Run `--poll` daily during the two weeks around each deadline.

---

## Integration: x-news-sweep Gate 5 (SA LP Cross-Check)

Gate 5 in the x-news-sweep skill says: "Flag any SA LP claim that contradicts known Q4 2025 13F data."

With this skill active, use the diff JSON instead of relying on Grok's recall:

```bash
cat investment_screener/backend/data/13f/0002045724_diff.json
```

Cross-check Grok's SA LP claims against `new_positions`, `closed_positions`, `increased`, and `decreased` arrays. Flag any discrepancy before applying a recommendation.

---

## Hard Rules

1. **Never apply** an SA LP signal from Grok without cross-checking `{CIK}_diff.json` first
2. **Run `--poll`** at every `/x-news-sweep` session start during May, Aug, Nov, Feb
3. **Values are in thousands** — divide by 1000 for $M display
4. **`put_call` null = common shares**; "Call"/"Put" = options position

---

## Sources Checked Declaration

```
## 13F Sources
- SEC EDGAR submissions API:   [✅ CIK 0002045724 — Situational Awareness LP]
- Latest filing cached:        [{filing_date} — period {period_of_report}]
- Holdings parsed:             [{N} positions, ${total}M AUM]
- Diff generated:              [{from_date} → {to_date}]
- Gate 5 cross-check:          [✅ diff JSON used as authoritative source]
```
