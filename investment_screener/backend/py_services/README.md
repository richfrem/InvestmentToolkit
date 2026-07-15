# Python Analytical Services (`backend/py_services/`)

This directory houses the Python-based financial analysis, quantitative modeling, scraping, and execution engines for the **InvestmentToolkit**. 

All data aggregation, performance calculations, and broker integrations run in this directory via subprocess calls from the Express backend or direct CLI invocations from AI agent tools.

---

## 📂 Core Sub-Systems & Scripts

The scripts in this directory are organized into logical modules:

### 1. Valuation & Financial Scrapers
- `fetch_financials.py` — Scrapes yfinance for statement data, Piotroski F-Scores, and Rule of 40.
- `dcf_scenarios.py` — Bear / Base / Bull scenario calculator.
- `dcf_sensitivity.py` — Sensitivity grids for growth rates vs. exit multiples.
- `reverse_dcf.py` — Solves for the implied growth rate embedded in current market prices.
- `wacc.py` — Calculates weighted average cost of capital.
- `comps_valuation.py` — Comparable company trading multiple valuation grids.

### 2. Portfolio Management & Rebalancing
- `rebalancer.py` — Formulates rebalancing trade recommendation arrays.
- `lock_and_normalize_targets.py` — Validates and locks conviction target weight arrays.
- `verify_portfolio_total.py` — Reconciles calculated portfolio assets against broker reports.
- `verify_thesis_sync.py` — Validates that active target weights and real weights are aligned.
- `apply_portfolio_updates.py` — Writes rebalance order updates back to data files.
- `portfolio_io.py` — Utility library for read/write file operations.

### 3. Daily Loop & Triage Briefing
- `daily_brief.py` — Generates morning brief documents containing macro data and market trends.
- `compute_conviction_scores.py` — Scores holdings conviction based on DCF and technical levels.
- `macro_regime.py` — Gauges economic regime trends (inflation, yield curve, dollar index).
- `overnight_gaps.py` — Monitors gaps in key assets before market open.

### 4. SEC 13F EDGAR Scraping
- `edgar_facts.py` — Queries SEC EDGAR REST API for institutional filings.
- `earnings_calendar.py` — Parses upcoming earnings events.
- `earnings_expectations.py` — Pulls consensus earnings estimates.

### 5. Quantitative backtesting & Performance
- `backtest_harness.py` — Simulates historical portfolio rebalancing drift and performance.
- `generate_track_record_report.py` — Generates metrics and charts for backtest outputs.
- `grade_predictions.py` — Audits conviction level accuracy against actual forward outcomes.
- `harvest_predictions.py` — Updates prediction ledger status values.
- `ytd_return.py` — Calculates time-weighted returns (TWR) using deposit cash flows.

---

## 🧪 Running Tests

Unit and integration tests for these scripts are located in `investment_screener/backend/tests/py_services/`.

To execute the test suite, run:
```bash
python3 -m pytest investment_screener/backend/tests/py_services/
```

---

## 📜 Development Rules

All scripts in this directory must strictly comply with the following conventions:
1. **No Inline Analytical Calculations**: All financial/analytical mathematical formulas must be versioned in a script inside this folder.
2. **File Headers**: Every script must start with a purpose block, listing **Key Input Dependencies**, **Key Output Dependencies**, and a complete **Functions Index**.
3. **Type Annotation**: Every function signature must include complete Python type hints.
4. **Google-Style Docstrings**: Every function must document parameters (`Args:`) and return values (`Returns:`).
