# CRSP Research Timeline

## 2026-07-05 — CRSP research import (2026-07-05)

# CRSP — CRISPR Therapeutics — Deep Dive Research Report
**Date**: 2026-07-05 | **Analyst**: Claude Sonnet 5 | **Action**: WATCHLIST | **DCF Fair Value**: $16.23 (SELL signal, -73% vs. $60.08 price)

## TL;DR
CRSP's canonical DCF says SELL, and two independent cross-checks (reverse-DCF, Monte Carlo) confirm it on a fundamentals-only basis — but this is a structural DCF-tool mismatch, not a clean overvaluation call. CRSP's own reported revenue is tiny because its CASGEVY economics run through a 40%-profit-share collaboration with Vertex (Vertex books the sales; CRSP books a share of profit), and a 5-year revenue-multiple DCF cannot price the company's real assets: the first-ever approved CRISPR therapy, a $2.44B cash position, and a broad pipeline (CTX310/CTX320 ANGPTL3 programs) with binary but real optionality. This is the same shape as OKLO's existing `DCF_GATE_SUSPENDED` standing decision in this portfolio. Recommend WATCHLIST — do not treat the $16.23 fair value or the auto-derived price levels as actionable trading signals.

## Company Snapshot

| Metric | Value |
|---|---|
| Price | $60.08 |
| Market Cap | $5.92B |
| Diluted Shares | 98.48M |
| TTM Revenue (raw feed) | $0 (anomalous — see Data Quality) |
| FY2024 Revenue (used as DCF base) | $35M |
| FY2023 Revenue (one-time Vertex milestone) | $370M |
| Cash & Marketable Securities (Q1 2026) | $2.44B |
| Recent Financing | $600M convertible notes, 1.7308% coupon, due 2031 (Q1 2026) |
| Analyst Consensus | Buy · 21 analysts · mean target $83.52 · median $76 · range $44–$291 |
| CASGEVY System-Wide Sales | FY2025 $115.8M (up from $10M FY2024) · Q1 2026 $43M |
| CRSP's Economic Share of CASGEVY | 40% of profits (Vertex: 60%, and is manufacturer/exclusive license holder) |

## Investment Thesis

CRISPR Therapeutics occupies the "In-Vivo Liver / Epigenetic Core" slot in this portfolio's Metabolic Reprogramming sub-strategy, anchored by its CTX310 and CTX320 programs targeting ANGPTL3 for permanent LDL/triglyceride reduction — a direct genetic alternative to continuous GLP-1/statin maintenance therapy, which is the core thesis this sub-strategy is built around. Beyond that pipeline fit, CRSP also holds a genuinely unique structural asset: CASGEVY, developed with Vertex Pharmaceuticals, is the first-ever regulatory-approved CRISPR/Cas9 gene-edited therapy anywhere in the world (approved December 2023 for transfusion-dependent beta-thalassemia and severe sickle cell disease). That approval alone is a real, durable moat — patent estate, first-mover regulatory and manufacturing experience, and proof that the platform can clear the FDA/EMA bar that most gene-editing peers haven't yet reached.

The complication is economic structure, not commercial traction. Under the 2021-amended Vertex collaboration, Vertex leads global development, manufacturing, and commercialization of CASGEVY and books 60% of program costs/profits; CRSP gets the remaining 40%. Vertex's own reporting shows CASGEVY revenue accelerating sharply — $10M in FY2024, $115.8M in FY2025, and Vertex guiding combined CASGEVY+Journavx revenue to nearly triple in 2026 — but that acceleration does not show up cleanly on CRSP's own income statement, because CRSP recognizes its collaboration economics differently (a profit/cost share, not a direct revenue line). CRSP's own reported total revenue was $370M in FY2023 (dominated by a one-time approval/upfront milestone payment), fell to roughly $35M in FY2024, and the raw data feed used for this analysis shows $0 for the trailing twelve months — which is very likely a stale or lagging data point given the real underlying commercial momentum, not a sign the company has no revenue at all.

This mismatch is exactly why the DCF-derived numbers in this report should be read with caution. A standard 5-year revenue-CAGR/exit-multiple DCF, built on CRSP's own reported (small, profit-share) revenue line, will always undervalue a story where the real assets are (a) an approved product's economics running through a partner's books, (b) a $2.44B cash cushion providing ~24 months of guided runway to reach binary pipeline catalysts, and (c) standalone platform/M&A optionality. The portfolio already has a precedent for exactly this situation: OKLO carries a `DCF_GATE_SUSPENDED` standing decision because "this is a pre-revenue... thesis where DCF is not the right valuation tool." CRSP is a closer analog to that than to a normal DCF-suitable equity.

Financially, the company remains loss-making across every historical year in the dataset (EPS of -$8.36, -$1.94, -$4.34, and -$6.47 over the last four fiscal years), and continues to fund its broad pipeline (CTX310/CTX320 cardiovascular programs, CTX112/CTX131 CAR-T oncology programs, plus CASGEVY's own commercialization costs) through a mix of collaboration payments and capital raises — most recently a $600M convertible note issued in Q1 2026. That raise strengthened the balance sheet (cash rose from $1.98B to $2.44B quarter-over-quarter) but is a reminder that further dilution is a live risk if pipeline costs run ahead of collaboration inflows.

## Scenario Analysis

### Bear Case (30% weight)
Slow patient-access ramp continues (Vertex has already cited apheresis-center capacity and reimbursement friction as causes of a slower-than-expected 2025 launch), CTX310/CTX320 cardiovascular readouts disappoint or slip, and R&D burn continues largely unabated.

| Assumption | Value | Rationale |
|---|---|---|
| 5-yr Revenue CAGR | 15% | Off the $35M FY2024 base; modest continued collaboration-revenue growth only |
| Year 5 Revenue | $70.4M | |
| Net Margin (Yr 5) | 1% | Mechanical floor — the canonical DCF calculator hard-rejects negative margins ([0,100] range); realistically, continued losses are the base expectation here, not 1% profitability |
| Exit P/E | 18x | Sector-low (Healthcare Biotech benchmark) |
| Quality Multiplier | 0.90 | No moat premium; discount for undifferentiated near-term execution risk |
| Share Change | +3.0%/yr | Continued dilution funding losses (consistent with the Q1 2026 convert raise) |
| **Year 5 EPS** | **$0.01** | — |
| **Year 5 Price** | **$0.10** | — |
| **Present Value** | **$0.07** | — |

### Base Case (45% weight)
Measured commercial ramp of CRSP's CASGEVY profit share as global patient initiations scale (500+ as of Q1 2026, up from ~150 in all of 2025), deliberately set well below the raw analyst-consensus-implied path given how wide analyst dispersion is (2026 estimates range from $0M to $251M across 21 analysts).

| Assumption | Value | Rationale |
|---|---|---|
| 5-yr Revenue CAGR | 45% | Below raw consensus-implied path (~300% Y1→Y2) given genuine forecast uncertainty about profit-share recognition |
| Year 5 Revenue | $224.3M | |
| Net Margin (Yr 5) | 8% | Approaching breakeven as profit share scales against continued pipeline R&D |
| Exit P/E | 28x | Sector-mid |
| Quality Multiplier | 1.05 | Modest premium for the approved-product/cash position |
| Share Change | +1.5%/yr | Moderate continued dilution |
| **Year 5 EPS** | **$0.17** | — |
| **Year 5 Price** | **$4.97** | — |
| **Present Value** | **$3.55** | — |

### Bull Case (25% weight)
Consensus-track hypergrowth materializes, pediatric label expansion (ages 5-11, US filing submitted, decisions expected through 2026) broadens the addressable population, and positive CTX310/CTX320 ANGPTL3 Phase 1/2a data — the exact milestone gate already named in `metabolic_rewriting.md` — triggers a platform re-rating.

| Assumption | Value | Rationale |
|---|---|---|
| 5-yr Revenue CAGR | 90% | Tracks closer to raw consensus-implied trajectory (2027E $145.1M) |
| Year 5 Revenue | $866.6M | |
| Net Margin (Yr 5) | 18% | Full profit-share scale-up plus early pipeline monetization/milestones |
| Exit P/E | 45x | Near sector-high, reflecting platform optionality |
| Quality Multiplier | 1.15 | >1.1 — justified: first-ever approved CRISPR/Cas9 therapy + validated in-vivo ANGPTL3/PCSK9 pipeline directly feeding this portfolio's thesis + $2.44B cash |
| Share Change | 0%/yr | Self-funding via profit share + existing cash, no further dilution assumed |
| **Year 5 EPS** | **$1.58** | — |
| **Year 5 Price** | **$81.97** | — |
| **Present Value** | **$58.44** | — |

**Note**: even this bull-case present value ($58.44) sits below the current $60.08 price.

## Valuation Math

- **Discount rate (WACC)**: 7.0% (computed: risk-free 0.449%, beta 1.449 (2yr OLS), ERP 4.5%, cost of debt 5.0% fallback; a floor was applied)
- **Discount divisor (5yr)**: 1.40255
- Weighted fair value = 0.30×$0.07 + 0.45×$3.55 + 0.25×$58.44 = **$16.23**
- Upside vs. $60.08 current price: **-73.0%** → canonical DCF action: **SELL**

### Cross-Checks
- **Reverse-DCF**: implied 5-year growth to justify the current price (at base margin/exit-PE assumptions) is **161.2%/yr** — 116pp above this analysis's own base case, and beyond even the 90% bull case. Verdict: `PRICING_IN_MORE_THAN_BULL`.
- **Monte Carlo** (5,000 simulations across the scenario assumption ranges): P10 $1.58 / P50 $4.11 / P90 $9.56. **Probability overvalued: 100%.**
- **Comps**: insufficient peer data — no existing DCF projections in this repo for gene-editing peers (NTLA, BEAM, EDIT) to cross-check against. Not fabricated; genuinely not run.

**Interpretation**: all three numeric lenses that could run agree the stock is not supportable by a fundamentals-only revenue DCF. Zero of the available lenses support an ACCUMULATE signal per the portfolio's Phase 2a valuation-committee gate. This is treated as a tool-mismatch finding (see Key Risks and Data Quality below), not dismissed.

## Key Risks

1. **DCF-tool mismatch (primary caveat)**: CRSP's real economic engine (40% profit share on a partner's product sales, plus a broad clinical pipeline) is structurally not well captured by a 5-year revenue-multiple DCF. The $16.23 fair value should not be read as "this is what CRSP is worth" — it should be read as "this tool doesn't work well for this company's structure," the same conclusion already reached for OKLO in this portfolio.
2. **Revenue-recognition ambiguity**: 21 sell-side analysts show a $0M–$251M range for 2026 revenue alone — even the Street doesn't have a clean, shared model for how CRSP's collaboration economics will show up.
3. **Binary clinical risk**: the bull case depends on CTX310/CTX320 Phase 1/2a cardiovascular data, which carries genuine failure risk like any clinical-stage program.
4. **Continued losses and dilution**: every historical year shows deep net losses; the Q1 2026 $600M convertible raise is a reminder that further capital raises (dilutive or debt-funded) remain likely if pipeline costs run ahead of collaboration inflows.
5. **Auto-derived price levels are not usable**: the mechanical buy/sell tiers derived from this DCF ($2.66 buy / $3.55–$70.13 sell) are artifacts of the degenerate fair-value output and should not be used for real order placement without an explicit override decision.

## What to Watch
- CTX310/CTX320 Phase 1/2a cardiotoxicity and lipid-reduction durability data (the milestone gate already specified in `metabolic_rewriting.md`)
- Vertex's quarterly CASGEVY commercial updates (patient initiations, geographic expansion, pediatric label decision)
- Any disclosure clarifying how CRSP's 40% profit share flows onto its own income statement going forward
- Further capital raises (dilutive equity or additional convertible debt)

## Comparables
Insufficient peer data — NTLA (Intellia Therapeutics), BEAM (Beam Therapeutics), and EDIT (Editas Medicine) have no existing DCF projections in this repository to cross-check against. Not fabricated.

## Data Quality & Confidence Score

**Confidence: 0.35/1.0**

- Base: 1.0
- -0.30: revenue-recognition ambiguity (the Vertex profit-share structure makes the "revenue" input itself genuinely contestable, not just uncertain in magnitude)
- -0.20: DCF-tool mismatch (mechanical margin floor forced by the calculator's [0,100] validation range; same failure mode already documented for OKLO)
- -0.15: wide analyst dispersion (2026 revenue estimates span $0M–$251M across 21 analysts)

**Flags**:
- Raw fetch TTM revenue = $0 despite real, growing CASGEVY system-wide sales ($115.8M FY2025, $43M Q1 2026) — treated as stale and overridden with the FY2024 actual ($35M) via the DCF calculator's `--revenue` flag.
- CRSP's own reported revenue is far smaller than headline "CASGEVY revenue" because of the 40%-profit-share collaboration structure.
- Historical net margins are not meaningful as percentages in early years due to a near-zero revenue denominator against large absolute losses.
- The canonical `dcf_scenarios.py` validator hard-rejects `netMargin < 0` — the bear-case 1% margin is a tool constraint, not a realistic forecast.

## Discussion Log

*(empty — to be appended during Q&A)*

## Sources Checked
- Financial data: ✅ `fetch_financials.py` (raw fetch succeeded; TTM revenue field found anomalous and overridden — see Data Quality)
- Web verification: ✅ CRISPR Therapeutics Q1 2026 results (stocktitan.net, ir.crisprtx.com), FY2025 results (ir.crisprtx.com), Vertex/CRISPR collaboration terms (investors.vrtx.com)
- Projection persistence: ✅ Saved to `backend/data/projections/CRSP.json`
- Research report: ✅ This file
- Valuation benchmarks: ✅ `references/valuation-benchmarks.md` (Healthcare — Biotech row)
- Price levels: ✅ Written via `update_price_levels.py` — **flagged as not usable for actual trading** given the degenerate DCF fair values
- Thesis synchronization: pending final `verify_thesis_sync.py` re-run

## Sources
- [CRISPR Therapeutics Q1 2026 Results](https://ir.crisprtx.com/news-releases/news-release-details/crispr-therapeutics-provides-business-update-and-reports-first-7/)
- [CRISPR Therapeutics FY2025 Results](https://ir.crisprtx.com/news-releases/news-release-details/crispr-therapeutics-provides-business-update-and-reports-14/)
- [Vertex/CRISPR Casgevy Collaboration Amendment](https://investors.vrtx.com/news-releases/news-release-details/vertex-pharmaceuticals-and-crispr-therapeutics-amend)
- [CRISPR Therapeutics Q1 2026 10-Q Summary (StockTitan)](https://www.stocktitan.net/sec-filings/CRSP/10-q-crispr-therapeutics-ag-quarterly-earnings-report-73ee709365b8.html)

