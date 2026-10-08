# Valuation method and discount-rate protocol

Authoritative procedure for `update-stock-analysis` and `stock-research`. Apply before selecting a rate, changing a valuation method, or publishing a replacement projection. A rate is an assumption supported by evidence, not a precise measurement of future risk.

## Contents

- [Existing model](#1-establish-what-the-existing-model-values)
- [Method and claim](#2-match-the-rate-to-the-claim)
- [Rate evidence and script](#3-build-a-dated-rate-evidence-file)
- [Project economics](#4-reconcile-project-economics-and-common-shareholder-value)
- [Changes and uncertainty](#5-explain-changes-and-uncertainty)
- [SQLite publication](#6-publication-and-verification)
- [Debt and leverage](#7-debt-and-leverage)

## 1. Establish what the existing model values

Load the current projection, input artifacts, and standing decision through supported repository/API or portfolio scripts. Record model family/version, valuation date, currency, nominal or real basis, horizon, share count/dilution convention, ownership perimeter, and rate type. Attempt to reproduce its result before changing inputs. An inherited rate whose inputs cannot be recovered is **not reproducible**; do not invent an explanation from today's data.

Distinguish a historical replay from a current valuation. Retaining old assumptions to verify arithmetic does not validate those assumptions against new earnings. Research should identify which dated guidance, estimates, contracts, costs, financing and ownership claims changed. Reconcile fiscal years and GAAP versus adjusted earnings before using consensus.

## 2. Match the rate to the claim

| Valuation basis | Rate | Toolkit support / conditions |
|---|---|---|
| Annual free cash flow to the firm (`annual_fcff`) | WACC | Forecast operating cash flows before financing, then reconcile enterprise value to common equity. |
| Future common EPS × exit P/E (`terminal_earnings`) | Cost of equity (`Ke`) | Existing discounted terminal-equity-price model; disclose omitted interim distributions. This is not annual cash-flow DCF. EPS must belong to common shareholders after financing and senior claims. |
| Annual free cash flow to common equity (FCFE) | Cost of equity | Not implemented in the current scenario engine; do not relabel FCFF inputs as FCFE. |

CAPM: `Ke = riskFreeRate + beta × ERP`.
For a simple equity/debt structure: `WACC = equityWeight × Ke + debtWeight × preTaxDebtCost × (1 − usableTaxShieldRate)`, with market-value capital weights. These distinctions follow [Damodaran's firm-versus-equity valuation framework](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/val.html).

For FCFF, specify each year's revenue, operating margin, cash taxes, depreciation, capital expenditures and working-capital change. Reinvestment must support growth. Do not deduct interest in FCFF and again include financing costs through WACC. Terminal growth must be sustainable, below the terminal discount rate, and supported by reinvestment. An invalid perpetuity or loss-making EPS×P/E result is not a credible equity-value floor.

## 3. Build a dated rate evidence file

Use the valuation's currency, not the listing exchange, to choose the risk-free curve. Default research convention for nominal USD forecasts is the dated US 10-year Treasury yield; justify a different tenor or term structure. Record instrument, date, units, source URL and retrieval date; convert explicit percentage units to decimals. Do not infer units from whether a Yahoo quote looks large. [Treasury's feed](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed) provides the official series.

Record a dated ERP series, market/country coverage and estimation method. Use a pinned observation rather than an undated constant. [Damodaran's datasets](https://pages.stern.nyu.edu/adamodar/New_Home_Page/datacurrent.html) are one source; historical and implied premiums are different methods and must be labeled.

For beta, retain the benchmark, window, frequency, observation count and estimation uncertainty. Use returns paired on identical dates; inspect distortions from sparse trading or business transformation. Cross-check against operating peers when the business or leverage has changed, following the [bottom-up beta approach](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/TenQs/TenQsBottomupBetas.htm). Neither a noisy regression nor an unexplained override establishes a reliable central estimate.

For debt, use current financing terms/yields where available. Historical interest divided by debt is only a disclosed proxy. Missing debt is distinct from confirmed zero debt. Record debt valuation basis/date and market equity value/date in the same currency. Book debt as a market-value proxy requires justification. A loss-making company may not realize a current tax shield: do not automatically apply 21%. A changing tax shield or capital structure requires an appropriately reviewed model, not an average-rate shortcut presented as exact.

### Reproducible script path

Use the existing canonical script in **explicit-input mode**, without a network fetch or silent substitutions:

```bash
python3 plugins/stock-valuation/scripts/wacc.py \
  --inputs temp/evaluations/TICKER_rate_inputs.json --pretty \
  > temp/evaluations/TICKER_rate_audit.json
```

Required JSON shape (synthetic arithmetic example, not a stock recommendation):

```json
{
  "method": "annual_fcff",
  "asOf": "2026-10-07",
  "currency": "USD",
  "riskFreeRate": 0.04,
  "beta": 1.0,
  "erp": 0.06,
  "marketCap": 800,
  "totalDebt": 200,
  "costOfDebtPreTax": 0.05,
  "taxShieldRate": 0.20,
  "rationale": "One or two plain sentences: why this rate basis and this beta, and what was rejected",
  "sources": [{
    "date": "2026-10-07",
    "url": "https://example.org/synthetic-fixture",
    "use": "Synthetic example only; replace with evidence for every input"
  }]
}
```

This yields WACC **8.8%**, or Ke **10%** with `method: "terminal_earnings"`. Rates and tax-shield fractions use decimals, capital values use one common currency/unit, beta is dimensionless. Output retains original inputs, unrounded Ke/WACC and capital weights, `rateType`, `selectedRate` and `readiness: REVIEW_REQUIRED`. Sources must cover every input and include the research details above; the script checks basic shape/arithmetic, not source authenticity or adequacy.

`rationale` is required and is rejected when blank. The app shows it verbatim under **Why this rate**, with the saved formula, on the Stock Analysis rate card and in the thesis popup, so write it for the portfolio owner: name the rate basis, the beta source (regression window or peer industry and leverage) and the main alternative that was rejected with its numerical effect. A hand-derived input such as a relevered peer beta must show its arithmetic in `sources`.

Select the rate only after the forward operating scenarios are rebuilt; for AI-infrastructure names that means the [capacity-to-earnings build](ai-forward-valuation.md#capacity-to-earnings-build) comes first.

Explicit mode requires even zero debt and zero tax shield to be supplied. It has no rate cap/floor or fallback. It supports a simple common-equity/debt capital structure only. Its nonnegative-beta input contract excludes negative-beta cases; those require separate reviewed support. Preferred capital, unusual financing, time-varying rates and project waterfalls require further modeling rather than invented zero inputs.

The legacy `--ticker --market-cap` path remains a diagnostic: it still has defaults, inferred yield units, historical debt-cost proxies and a 7–14% WACC clamp. Its added `components` expose the raw rate. Do not use its bounded output as a decision-ready selected rate without rebuilding the explicit audit.

## 4. Reconcile project economics and common-shareholder value

For financed data-center builders and similar structures, reconcile parent versus project ownership, debt, preferred returns, noncontrolling interests, restricted cash and funding commitments. Consolidated FCFF requires consolidated financing claims in the equity bridge; proportionate/project flows require matching claims. Do not reduce cash flows for ownership and then deduct all consolidated project debt again. EBITDA, contracted megawatts and gross backlog are not common-equity cash flow.

Forecast financing needs and share dilution separately from current shares. Avoid charging stock compensation twice through both expense and equivalent dilution without reconciliation. If material capex, financing terms or common-equity waterfall data are missing, present diagnostic ranges and identify the gaps; do not publish a validated central fair value or actionable replacement recommendation.

## 5. Explain changes and uncertainty

Before a method, ownership perimeter or rate-method migration, prepare a reviewable comparison:

1. Existing method + existing inputs (reproduction).
2. Existing method + refreshed evidence (operating/input changes).
3. Proposed method + refreshed evidence (method effect and limitations).

Explain why the method is appropriate and what is supported. Obtain acceptance of a concrete migration unless the current session already explicitly authorizes it. A request to update earnings is not permission to silently replace EPS/P/E with FCFF. Preserve the active valuation while a proposed migration awaits acceptance. A mismatched inherited rate should be flagged for correction, not silently treated as validated.

Separate operating bear/base/bull assumptions and probabilities from rate uncertainty. Report valuation sensitivity to plausible rates and terminal growth/multiples using the same supported model and cash-flow claim. Explain any rate override and its numerical impact; never tune the rate to achieve a desired price. Do not count the same execution risk repeatedly through bearish forecasts, probability weights, quality haircuts and an unexplained rate premium. Comps and reverse valuations only qualify as corroboration if they use compatible definitions and reliable inputs.

## 6. Publication and verification

The agent must enforce this protocol before persistence; current schema validation alone does **not** enforce every condition here. Reject publication as a decision-ready replacement for method/rate mismatches, invalid or nonfinite calculations, inconsistent ownership/debt bridges, material missing inputs, contradictory saved rates or an unaccepted method migration. Use `NEEDS_REVALUATION` in the report/outlook audit for unresolved material gaps; it does not replace the canonical action or standing decision.

Preserve the complete calculator output plus model family/version, nominal/real basis, evidence limitations, chosen-rate justification and sensitivity in `projection.valuationModel.discountRateAudit` of the `persist_valuation.py` payload. That existing `valuationModel` path is retained in `analyticsLog`; do not assume arbitrary new top-level fields survive persistence. Set the payload's `projection.discount_rate` explicitly to the audited selected rate and pass the same decimal through `dcf_scenarios.py --discount-rate` (or its Python `run(..., discount_rate=...)` call). Calculator/model `discountRate` and audit `selectedRate` use decimals; API/UI `globalSettings.discountRate` uses percentages. Retain any existing `valuationModel` fields. Legacy storage may also call the rate `wacc` even for equity valuation: the audit's `rateType` is authoritative about its meaning, and the report must label it correctly.

Run the supported calculation and schema validation, then persist the reviewed values and audit together:

```bash
python3 plugins/stock-valuation/scripts/persist_valuation.py \
  --file temp/evaluations/TICKER_valuation_payload.json \
  --rate-audit temp/evaluations/TICKER_rate_audit.json \
  --db /ABSOLUTE/MAIN_CHECKOUT/investment_screener/backend/data/domain_model.sqlite --json
```

Python callers can use `attach_discount_rate_audit(payload, audit)` followed by `persist_valuation(payload, db_path=...)`. The CLI attaches the audit without replacing other model metadata. Audited writes recompute rate arithmetic from the explicit inputs and reject conflicting method, rate type, components or selected/payload rates **before opening the database**. Known nested model/scenario method and rate fields are checked when present; generic model labels such as `5yr_dcf_scenarios` are not claims about the cash-flow method. This checks metadata consistency, not proof that scenario values were recomputed. Recalculate scenarios with the selected rate before attaching the audit. It does not authenticate sources or approve a method migration.

No schema migration is needed: `projection_version.snapshot_json` stores the selected rate, `analytics_log_json` stores the full evidence audit, and `projection_scenario` stores calculated targets. The backend's projection repository returns that audit as `analyticsLog.valuationModel.discountRateAudit` and translates the stored decimal rate to API/display percentage units. JSON files are calculation/review artifacts, not the dashboard's source of truth. Views read persisted results and do not rerun rate estimation.

Never write ad hoc SQL. `recalculate_forward_valuation.py` currently forces `annual_fcff` and is not a method-neutral migration tool. Do not use it to overwrite a terminal-earnings model. The scenario engine and legacy unaudited persistence still contain rate defaults; this workflow must supply the explicit rate rather than rely on them.

Read back from the **main checkout's actual database** through the supported API/repository, even when working in a worktree. Verify saved method, rate audit, rate units, fair value, scenario prices, quote timestamp and canonical recommendation agree in the app. Domain persistence, intelligence notes and closing refresh are separate operations; verify each rather than claim a transaction across both databases. Respect the standing-decision anchor and use the canonical recommendation function; a fresh valuation alone does not authorize a trade.

## 7. Debt and leverage

An earnings-multiple valuation has no line for debt, so debt must enter in three explicit places. `plugins/stock-valuation/scripts/leverage.py` is the only implementation of these rules.

1. **Rate.** Year-5 EPS × exit P/E is discounted at the cost of equity, never WACC. WACC falls as a company borrows more, so using it here makes more debt produce a higher fair value. `rate_basis_check` returns `MISMATCH` when the rate is more than 0.5 points below the cost of equity.
2. **Grade.** `leverage_profile` grades the balance sheet from net debt/EBITDA (above 2.5×, 4× and 8×), interest coverage (below 5× and 2×), current ratio (below 1.0) and net debt above half of market value: `LOW`, `MODERATE`, `HIGH` or `SEVERE`. Net cash caps the grade at `MODERATE`.
3. **Scenario weights.** `apply_leverage_weights` moves 5 points (`HIGH`) or 10 points (`SEVERE`) of probability to the bear case, from the bull case first and then the base case. State the weights before and after. Interest and scheduled refinancing must also be inside each scenario's net margin; say what interest cost the margin assumes.

For a `HIGH` or `SEVERE` company, prefer `annual_fcff` with the debt bridge (enterprise value + cash − debt − other claims) when the data supports it, and explain the choice.

Save the grade and rate check as `valuationModel.leverage` and `valuationModel.rateBasis` in the persistence payload. The tables show them as a debt badge beside the check; a valuation without them shows "Debt ?".

**Existing valuations.** `python3 plugins/stock-valuation/scripts/rebase_equity_valuations.py` recomputes saved earnings-multiple valuations with unchanged scenario assumptions, a CAPM cost of equity (two-year regression beta, Blume-adjusted, bounded to 1.0–2.0) and the leverage weight shift. It reports old against new; `--write` saves a new version and keeps the previous one. It never lowers a rate, skips audited and FCFF valuations, and refuses a valuation whose saved scenario prices it cannot reproduce. Its rate is an automated approximation marked "not a sourced rate audit": it corrects the direction of the error, and a full `/update-stock-analysis` with a sourced audit replaces it.
