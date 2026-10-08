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
- **Method and rate contract**: Apply [Valuation method and discount-rate protocol](references/valuation-method-and-discount-rate.md). Match FCFF to WACC and common-equity earnings to cost of equity; retain dated inputs and the reproducible rate audit. Explain and obtain acceptance of a concrete method migration unless already explicitly authorized in this session. Never silently replace a model during an earnings update.
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- **Adversarial objectivity**: Never anchor fair value to current market price. Derive scenarios independently from fundamentals.
- **Scenario differentiation**: Bear must cite structural risk or historical trough; Bull must name $\ge 1$ specific catalyst; Base must reflect normalized operating leverage.
- **Single source of truth**: Use `persist_valuation.py` for versioned valuations in `domain_model.sqlite`; verify any separate intelligence sweep and closing refresh. Never write to retired JSON targets or use ad hoc SQL.
- **Standing decision anchor**: Check existing `standing_decision_type` before recommending an action change; never flip BUY $\rightarrow$ SELL on $<15\%$ variance.
- **Local API authentication**: Express `/api/*` endpoints require Bearer token loaded from `.runtime/api-token`.

## Quick start

```bash
python3 plugins/stock-valuation/scripts/fetch_financials.py {TICKER} > temp/evaluations/{TICKER}_raw.json
```

## Workflow

1. **Check Freshness & Context**:
   Load prior projection, method, rate inputs and standing decision through supported API/repository scripts. Reproduce the prior result or label it not reproducible.
2. **Fetch Financials & Multi-Lens Data**:
   - Run `fetch_financials.py {TICKER}` for yfinance fundamentals and consensus metrics.
   - Run `comps_valuation.py` for its supported peer EV/Sales comparison; do not claim unsupported EBITDA/P/E corroboration.
   - Run `reverse_dcf.py` to calculate the market-implied growth rate.
3. **Construct 3-Scenario Valuation**:
   - Rebuild forward scenarios first: reconcile annual forward estimates and cash conversion, and for AI-infrastructure names complete the capacity-to-earnings build in the AI forward guide. Justify Bear/Base/Bull assumptions and weights (20%/60%/20% is a starting point).
   - Then select the cash-flow claim and rate basis using the shared protocol. Run `wacc.py --inputs temp/evaluations/{TICKER}_rate_inputs.json --pretty` and save the output as `{TICKER}_rate_audit.json`; inputs must include a plain-language `rationale`, which the app displays. Review sources, capital claims and tax-shield availability. Use the selected decimal rate in the calculation and persistence payload.
   - Run `dcf_scenarios.py` with reviewed `annual_fcff` forecasts for cash-flow requests, or retain and accurately label the existing terminal earnings mode. `recalculate_forward_valuation.py --model INPUT.json --output DIR` forces FCFF; do not use it for an unaccepted method migration.
   - Report operating scenarios separately from rate sensitivities; unresolved material financing/capex/ownership gaps mean diagnostic ranges and `NEEDS_REVALUATION`, not a validated replacement fair value.
   - Benchmark exit multiples against `references/valuation-benchmarks.md`.
4. **Adversarial Review Gate**:
   - Validate that scenario spread ratio is reasonable ($<50\times$).
   - Check firm contracted deliveries, enforceability and cash conversion; gross backlog is not a guaranteed annual revenue or equity-value floor.
   - Dispatch `red-team-agent` to challenge assumptions before finalizing.
5. **Validate & Persist**:
   Include `projection.researchReport: "{TICKER}_{YYYY-MM-DD}.md"` in the payload so the saved projection links to the published report.
   ```bash
   cat temp/evaluations/{TICKER}_projection.json | python3 plugins/stock-valuation/scripts/validate_projection.py --verbose
   python3 plugins/stock-valuation/scripts/persist_valuation.py --file temp/evaluations/{TICKER}_valuation_payload.json --rate-audit temp/evaluations/{TICKER}_rate_audit.json --db /ABSOLUTE/MAIN_CHECKOUT/investment_screener/backend/data/domain_model.sqlite
   ```
6. **Compile Research Report**:
   Write the Markdown deep dive, then publish with `persist_research.py --file REPORT.md --db /ABSOLUTE/MAIN_CHECKOUT/investment_screener/backend/data/intelligence.sqlite --jsonl /ABSOLUTE/MAIN_CHECKOUT/investment_screener/backend/data/observations.jsonl`. Dated reports are served from the ledger, so a file alone is insufficient. Read back with `query_ledger_research.py --get {TICKER}_{YYYY-MM-DD}.md`.
7. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification

- Verify saved `analyticsLog.valuationModel.discountRateAudit`, method, selected rate, scenario prices and canonical action through the main database/API. App views read the persisted results; they must not recalculate rate assumptions. Python rates are decimals; API `globalSettings.discountRate` is a percentage.
- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
- Confirm `validate_projection.py` passes with zero schema errors.
- Confirm SQLite record insertion:
  ```bash
  python3 investment_screener/backend/py_services/portfolio_io.py --ticker {TICKER} --json
  ```
- Run `python3 -m pytest plugins/stock-valuation/tests/` and validate routing cases against `evals/evals.json`.

## References
- [Valuation Method and Discount-Rate Protocol](references/valuation-method-and-discount-rate.md) - Method selection, sourced rate inputs, migration review, sensitivity and SQLite persistence.
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- [Valuation Benchmarks](references/valuation-benchmarks.md): Sector P/E multiples and net margin baseline tables.
- [Analysis Prompt Guide](references/analysis_prompt.md): Prompt templates and research synthesis guidelines.
- [API Reference](references/api_reference.md): Express backend routes and authentication schemas.
- [Fallback Tree](references/fallback-tree.md): Operational degradation procedures when data sources fail.
- [ADR DCF Calculator](references/ADR-dcf-calculator.md): Mathematical specification for discounted cash flow engine.
