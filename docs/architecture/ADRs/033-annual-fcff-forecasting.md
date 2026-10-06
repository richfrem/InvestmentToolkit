# ADR-033: Annual FCFF and AI-sector forward valuation

Date: 2026-10-06
Status: Proposed

## Problem

The existing projection path emphasized a normalized year and could understate
step-changes in demand or cash requirements. AI infrastructure exposes this in
memory (HBM, conventional DRAM, NAND/SSD) and power supply (time-to-power,
equipment deliveries, and factory expansion).

## Decision

Use explicit annual unlevered free-cash-flow forecasts in the canonical
`dcf_scenarios.py` engine when recent guidance or demand evidence materially
changes the forward trajectory. Inputs distinguish company guidance, analyst
estimates, contracted deliveries, conditional frameworks, and assumptions.
Revenue, operating margins, taxes, D&A, capex, and working capital are explicit.

Discount partial fiscal years using their stated `discountPeriod`; the reported
horizon and discount divisor use the same final forecast period. Continue to
expense stock-based compensation through GAAP operating margins. Model cash,
debt, and other claims in the equity bridge without an AI premium. Include
dilution sensitivities; when a convertible is modeled as converted, remove its
debt carrying value in that same case.

Terminal growth and normalized terminal cash flows remain explicit. Report
terminal value contribution, sensitivities to discount rate and terminal
growth, and operating margin, capex, and dilution stresses. Reverse valuation
is diagnostic, not independent corroboration.

The annual FCFF valuation informs the projection and canonical recommendation
data only. It does not overwrite standing decisions or targets, and it does
not execute trades. The model assesses demand alongside supply response, unit
economics, customer commitments, timing, and cash conversion; thematic demand
alone is not a forecast.

## Consequences

AI-sector updates can reflect rapid changes in estimates and operating plans
with auditable cash-flow assumptions. Forecasts remain uncertain where margins,
factory capacity, and terminal economics extend beyond company guidance.

## Implementation

Implemented by the shared `dcf_scenarios.py` annual FCFF mode and the
`recalculate_forward_valuation.py` audit runner. MU and BE input fixtures are
under `plugins/stock-valuation/tests/fixtures/forward-valuation/`; dated
valuation results are under
`plugins/stock-valuation/references/forward-valuation-reviews/2026-10-06/`.
