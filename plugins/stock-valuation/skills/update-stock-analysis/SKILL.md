---
name: update-stock-analysis
plugin: stock-valuation
description: Perform autonomous stock valuation for a ticker you already hold or track. Produces a 5-year scenario valuation persisted to SQLite domain model, updates price levels, and writes a qualitative research report. Trigger on /update-stock-analysis or "value [TICKER]".
allowed-tools: Bash, Read, Write
---

# Update Stock Analysis

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- **Adversarial objectivity**: Never anchor fair value to current market price. Derive scenarios independently from fundamentals.
- **Scenario differentiation**: Bear must cite structural risk or historical trough; Bull must name $\ge 1$ specific catalyst; Base must reflect normalized operating leverage.
- **Single source of truth**: Persist all valuations atomically into `domain_model.sqlite` and `intelligence.sqlite` via `persist_valuation.py`; never write to retired JSON targets.
- **Standing decision anchor**: Check existing `standing_decision_type` before recommending an action change; never flip BUY $\rightarrow$ SELL on $<15\%$ variance.
- **Local API authentication**: Express `/api/*` endpoints require Bearer token loaded from `.runtime/api-token`.

## Quick start

Execute full automated pipeline for a ticker:

```bash
python3 plugins/stock-valuation/scripts/fetch_financials.py {TICKER} > temp/evaluations/{TICKER}_raw.json
```

## Workflow

1. **Check Freshness & Context**:
   Query existing projection age and thesis standing decision from `domain_model.sqlite`.
2. **Fetch Financials & Multi-Lens Data**:
   - Run `fetch_financials.py {TICKER}` for yfinance fundamentals and consensus metrics.
   - Run `comps_valuation.py` for peer EV/EBITDA and P/E multiples.
   - Run `reverse_dcf.py` to calculate the market-implied growth rate.
3. **Construct 3-Scenario Valuation**:
   - Reconcile annual forward estimates and cash conversion; justify Bear/Base/Bull assumptions and weights (20%/60%/20% is a starting point).
   - Run `dcf_scenarios.py` with `annual_fcff` forecasts for cash-flow requests, or label its legacy terminal earnings mode accurately. `recalculate_forward_valuation.py --model INPUT.json --output DIR` creates reviewed-model artifacts per the shared guide.
   - Benchmark exit multiples against `references/valuation-benchmarks.md`.
4. **Adversarial Review Gate**:
   - Validate that scenario spread ratio is reasonable ($<50\times$).
   - Check firm contracted deliveries, enforceability and cash conversion; gross backlog is not a guaranteed annual revenue or equity-value floor.
   - Dispatch `red-team-agent` to challenge assumptions before finalizing.
5. **Validate & Persist**:
   ```bash
   cat temp/evaluations/{TICKER}_projection.json | python3 plugins/stock-valuation/scripts/validate_projection.py --verbose
   python3 plugins/stock-valuation/scripts/persist_valuation.py --file temp/evaluations/{TICKER}_valuation_payload.json
   ```
6. **Compile Research Report**:
   Write Markdown deep dive to `investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md`.
7. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
- Confirm `validate_projection.py` passes with zero schema errors.
- Confirm SQLite record insertion:
  ```bash
  python3 investment_screener/backend/py_services/portfolio_io.py --ticker {TICKER} --json
  ```
- Run unit test suite:
  ```bash
  pytest plugins/stock-valuation/tests/
  ```
- Validate routing cases against `evals/evals.json`.

## References
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- [Valuation Benchmarks](references/valuation-benchmarks.md): Sector P/E multiples and net margin baseline tables.
- [Analysis Prompt Guide](references/analysis_prompt.md): Prompt templates and research synthesis guidelines.
- [API Reference](references/api_reference.md): Express backend routes and authentication schemas.
- [Fallback Tree](references/fallback-tree.md): Operational degradation procedures when data sources fail.
- [ADR DCF Calculator](references/ADR-dcf-calculator.md): Mathematical specification for discounted cash flow engine.
