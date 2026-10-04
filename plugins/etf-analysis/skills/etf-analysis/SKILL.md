---
name: etf-analysis
plugin: etf-analysis
description: Performs autonomous ETF and fund analysis across closed-end funds (NAV premium, private stakes), thematic ETFs (holdings alignment, expense drag), and cash funds. Persists structured JSON and synchronizes SQLite domain model. Trigger on /analyze-etf or "analyze [TICKER]".
allowed-tools: Bash, Read, Write
---

# ETF Analysis

Autonomous fund analysis engine for closed-end funds, thematic ETFs, and cash reserves.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **No DCF for funds**: Never use DCF valuation for fund analysis; funds hold investment portfolios, not direct business operations.
- **Mandatory NAV premium**: Always state NAV premium/discount for closed-end funds before any action recommendation.
- **Overlap & expense audit**: Always evaluate annualized expense drag and portfolio overlap against existing direct holdings for thematic ETFs.
- **Database authority**: Target actions and rationales must be written to `domain_model.sqlite` via `persist_etf_analysis.py`; never write to retired JSON files.
- **Dual-write persistence**: Persist to both `investment_screener/backend/data/etf_analysis/{TICKER}.json` and `domain_model.sqlite` `projection_version`.

## Quick start

Run data fetch for the target fund:

```bash
python3 plugins/etf-analysis/scripts/fetch_fund_data.py {TICKER} > temp/evaluations/{TICKER}_raw.json
```

Output contract: structured fund payload conforming to `assets/templates/etf_analysis_template.json`.

## Workflow

1. **Classify Fund Type**:
   - `CLOSED_END`: `quoteType=EQUITY`, private holdings valuation, NAV premium % (BUY `<100%`, HOLD `100-200%`, TRIM `>300%`, AVOID `>400%`).
   - `THEMATIC_ETF`: `quoteType=ETF`, sector/theme basket, holdings alignment score (ACCUMULATE `>70%`, HOLD `50-70%`, TRIM `<50%`, AVOID `<30%`).
   - `CASH_FUND`: Currency/treasury focus, yield calculation, dividend cycle timing (action always `HOLD`).
2. **Draft Analysis Object**:
   Read `assets/templates/etf_analysis_template.json` and generate `temp/evaluations/{TICKER}_etf.json`.
3. **Validate Schema**:
   ```bash
   cat temp/evaluations/{TICKER}_etf.json | python3 plugins/etf-analysis/scripts/validate_etf_analysis.py --verbose
   ```
4. **Persist Findings**:
   ```bash
   python3 plugins/etf-analysis/scripts/persist_etf_analysis.py --input temp/evaluations/{TICKER}_etf.json
   ```
5. **Record Timeline Memo**:
   Append dated qualitative memo to `investment_screener/backend/data/research/{TICKER}.timeline.md`.

## Verification

- Confirm schema validation exit code 0 from `validate_etf_analysis.py`.
- Verify database update:
  ```bash
  python3 investment_screener/backend/py_services/portfolio_io.py --ticker {TICKER} --json
  ```
- Run plugin test suite:
  ```bash
  pytest plugins/etf-analysis/tests/test_persist_etf_analysis.py
  ```
- Validate routing cases against `evals/evals.json`.

## References

- [ETF Analysis Template](assets/templates/etf_analysis_template.json): Official schema template and field definitions for persisted fund JSON.
