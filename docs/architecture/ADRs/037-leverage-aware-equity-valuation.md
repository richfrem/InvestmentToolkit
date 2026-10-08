# ADR-037: Debt enters equity valuations through the rate, a leverage grade and scenario weights

Date: 2026-10-08
Status: Proposed

## Problem

All 24 valued holdings used year-5 EPS × exit P/E. That formula has no line for
debt. Their saved discount rates were blended rates (WACC) between 7% and 12%,
and WACC falls as a company borrows more, so heavier debt produced a *higher*
fair value. CoreWeave, with net debt about 12× EBITDA and larger than its market
value, was discounted at 8.16% and showed 10.7× reward:risk. Debt/EBITDA,
interest coverage and current ratio were computed for the quality score but did
not reach fair value, the valuation range or reward:risk.

## Decision

1. **One module.** `plugins/stock-valuation/scripts/leverage.py` owns the rules:
   `leverage_profile` (grade LOW/MODERATE/HIGH/SEVERE from net debt/EBITDA,
   interest coverage, current ratio, net debt/market value),
   `apply_leverage_weights` (5 or 10 points of probability moved to the bear
   case for HIGH or SEVERE) and `rate_basis_check` (equity earnings must not be
   discounted below the cost of equity). The quality score imports its interest
   coverage and current ratio thresholds from here.
2. **Saved with the valuation.** The grade and rate check are stored as
   `valuationModel.leverage` and `valuationModel.rateBasis`. Fair value and
   scenario weights are saved already adjusted, so every reader (fair value,
   range bar, reward:risk, action) uses the same numbers and nothing is adjusted
   at display time.
3. **Shown, including when missing.** `risk_reward.debt_view` puts a `debt` field
   on every recommendation record. Tables show "Debt high", "Debt severe",
   "Rate low", or "Debt ?" for a valuation never checked for debt.
4. **Existing valuations are re-based, not rewritten.**
   `rebase_equity_valuations.py` keeps each saved scenario's growth, margin,
   multiple and share change, raises the rate to a CAPM cost of equity and
   applies the weight shift. It saves a new version, records the previous rate,
   weights and fair value in `rebasedFrom`, never lowers a rate, and skips
   audited, FCFF and non-reproducible valuations.

## Choices and their limits

- **Beta.** Two-year regression beta, Blume-adjusted (0.67 × raw + 0.33) and
  bounded to 1.0–2.0. Raw betas for the AI infrastructure names run 2.5–3.3 and
  would give rates near 17–20%; the reviewed APLD valuation used 1.81. This is an
  automated approximation, labelled "not a sourced rate audit". It does not light
  the "audited discount rate" support check.
- **Weight shift.** 5 and 10 points are judgment, not an estimate of default
  probability. They are constants in one place and the previous weights are
  saved.
- **Not built.** Interest cost is not separately modelled inside each scenario's
  margin, and no valuation was migrated to the FCFF debt bridge. Both belong to a
  full `/update-stock-analysis` per ticker.

## Consequences

Fair values for leveraged, high-beta holdings fall materially (CoreWeave about
$250 to $137; Core Scientific $28.73 to $19.15), several actions change, and
reward:risk falls with them. Three holdings (CRDO, GEV, SHAZ) cannot be
reproduced from their saved scenario rows and need a full update.
