# AI-sector forward valuation evidence

Apply this guide before valuing an AI-exposed company or treating its current
valuation signal as a trade-ready conclusion. Keep the canonical recommendation
separate from evidence readiness and standing-decision conditions.

## Contents

- [Forward estimates and dates](#forward-estimates-and-dates)
- [Memory and storage](#memory-and-storage)
- [Power and infrastructure](#power-and-infrastructure)
- [Capacity-to-earnings build](#capacity-to-earnings-build)
- [Cash-flow bridge](#cash-flow-bridge)
- [Recommendation readiness](#recommendation-readiness)
- [Verification cases](#verification-cases)

## Forward estimates and dates

Use dated primary sources: latest earnings release, earnings-call prepared
remarks/transcript, guidance and filings. Retrieve forward revenue and forward EPS
estimates with fiscal year, estimate date, range, analyst coverage and revision
direction when available. Distinguish management guidance, analyst consensus and
your own assumptions. A newly saved valuation can still omit newer information
or carry unsupported assumptions; age alone does not establish freshness.

Reconcile the next 1–3 years with management guidance and consensus before
forecasting years 4–5. Explain departures quantitatively. Do not annualize a peak
quarter as a certainty or normalize a growth business to an old cycle by default.
Mark unavailable estimates explicitly; never fabricate consensus figures.

## Memory and storage

Assess HBM alongside conventional DDR/server DRAM, LPDDR and NAND/enterprise SSD
demand. Examine inference concurrency, longer context, KV-cache placement/offload,
persistent agent memory, retrieval/data lakes and physical/edge AI. Product names,
model launches and agent adoption are research leads, not booked revenue.

Translate verified adoption into addressable workload, bytes per deployment,
shipments, product mix, selling prices and supplier share where evidence permits.
Test substitution between memory tiers and efficiency improvements as well as
aggregate demand growth. Separate HBM packaging limits from DRAM wafer capacity
and NAND/SSD supply. Assess competing capacity additions, customer inventories,
contract price protection and capex lead times before assuming a down-cycle or
permanent shortage.

## Power and infrastructure

Assess time-to-power: grid connection delays, turbine lead times, onsite fuel cells
and engines, and the earliest usable energized capacity. Trace adoption through
manufacturing output, fuel availability, permitting, installation, commissioning,
service economics and revenue recognition. Fast installation does not remove
factory or fuel constraints; Bloom is not the only possible power source.

Separate delivered capacity, signed non-cancellable orders, cancellable orders,
framework agreements/options, reservations, LOIs and announcements. Record delivery
dates, cancellation/force-majeure terms and customer financing/concentration. A
multi-year backlog is not an annual revenue floor, and a framework's maximum
capacity is not firm contracted revenue. Model verified delivery schedules and
enforceability rather than multiplying the entire pipeline into valuation.

## Capacity-to-earnings build

For data-center, power and other AI-infrastructure names, complete this build on
every valuation refresh and earnings review **before selecting a discount rate**.
The rate is applied to refreshed scenarios; never lower or raise a rate to
compensate for scenarios that were not rebuilt.

1. **Split reported revenue.** Separate recurring revenue (base rent, hosting,
   service contracts) from construction-linked or one-time revenue (tenant fit-out,
   hardware resale, recoveries). Annualize only the recurring part, and state the
   capacity that produced it.
2. **Derive unit economics.** Contracted base-term revenue ÷ lease term ÷ contracted
   capacity gives revenue per MW per year. Cross-check it against reported recurring
   revenue ÷ energized MW and explain any gap (ramp, rate escalators, mix).
3. **Build a dated capacity ladder.** Classify every MW as energized; funded and
   under construction; signed but unfunded; expected but unsigned; or an option,
   framework or management target. Record delivery dates and the funding status of
   each campus or project.
4. **Reconcile the near term.** Compare the implied next 1–2 fiscal years with
   management guidance and dated consensus. A model path far below an evidenced
   run-rate, or far above funded capacity, must be corrected or explained.
5. **Anchor the terminal year to the contracted floor.** Signed capacity fully
   delivered × revenue per MW is the contracted floor. Bear tests partial delivery
   or funding failure of signed capacity; base assumes signed capacity delivers on
   the evidenced schedule; bull adds named capacity with its catalyst. Capacity
   with no tenant or closed funding does not enter the base case, and a management
   capacity target is not a forecast.
6. **Translate to earnings for common shareholders.** State capex per MW where
   disclosed, closed versus open financing, the cost of new debt, expected dilution,
   and project partners or noncontrolling interests. Net margin and share count
   must reflect interest, depreciation and those claims; revenue growth is not
   common-earnings growth.
7. **Record the build.** Put the ladder, unit economics, changed assumptions and
   remaining gaps in the research report and outlook audit. Unverified margins or
   ownership waterfalls keep **NEEDS_REVALUATION** even when revenue is refreshed.

## Cash-flow bridge

For each scenario, show annual revenue → operating profit → cash taxes → cash
flow, including depreciation, capex, working capital and stock compensation/
dilution. Reconcile forward EPS with the revenue/margin/share-count forecast.
Specify FCFF versus FCFE, discount rate, terminal assumptions and the cash/debt
bridge; do not count accumulated cash twice. Identify maintenance versus growth
capex and customer deposits/financing effects.

dcf_scenarios.py retains its terminal EPS × P/E mode as a discounted earnings/
multiple model. Its explicit `annual_fcff` mode discounts annual operating cash
flows and a separately normalized terminal forecast. Use the latter when annual
cash flow is requested; never label net income as distributable free cash flow.
Annual forecast amounts use dollars, margins/tax use percentage units (20 = 20%),
and discount/terminal growth rates use decimals (0.12 = 12%). Include fiscal
stubs/discount periods and a disclosed cash/debt/other-claims bridge. Retain SBC
as an operating expense without another share-change haircut; disclose current
diluted-share versus debt-outstanding conventions for convertibles/warrants.
`recalculate_forward_valuation.py --model INPUT.json --output DIR` delegates to
this engine, produces sensitivities and validates persistence artifacts.

Base should reflect evidenced adoption and execution capacity. Bear should test
specific delays, supply additions, pricing or customer failures without ignoring
enforceable contracts. Bull must identify additional adoption and capacity needed
to deliver it. Explain scenario weights and any structural margin/multiple
re-rating. Do not lift fair value merely to match the share price or preferred
action. Stress discount rate, terminal growth/multiple, margins and delivery timing.

## Recommendation readiness

Record sources/dates, verified forward changes, revised assumptions, cash-flow
effects, disconfirming evidence and what would change the conclusion. If material
drivers are missing, estimates contradict the model, or a new catalyst is not
incorporated, mark review readiness **NEEDS_REVALUATION**. If sources cannot be
verified, say **UNVERIFIED_SOURCE**. These are review flags, not new action enums.

Refresh the valuation before relying on it for a buy/trim/exit proposal. Fast daily
scans can flag and route a refresh without running a full valuation for every
ticker. Keep standing decisions and execution conditions visible. Persist reviewed
valuations through the canonical scripts, then read updated recommendations from
recommendation.py; never re-derive a competing action in the research narrative.

## Verification cases

- MU: an HBM-only thesis must also examine server DRAM and NAND/SSD context storage;
  a post-boom normalization needs evidence on pricing, capacity and contracts.
- BE: a grid-delay thesis must show executable manufacturing/deployment capacity;
  Oracle framework capacity must be separated from firm orders.
- APLD: Q1 FY2027 revenue of $341.9M included $183.5M of tenant fit-out and $65.8M of
  base rent; $36B over 15 years on 1.41 GW is about $1.7M per MW per year, so a base
  case below roughly $2.4B of terminal rent needs a delivery or funding failure to justify it.
- A valuation saved today using yesterday's guidance is not automatically current.
- Strong demand with weak cash conversion can still warrant a cautious valuation.
- A fresh model may still imply TRIM; the evidence gate must not force a bullish result.
