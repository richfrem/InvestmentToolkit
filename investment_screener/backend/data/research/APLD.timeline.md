# APLD Research Timeline

## 2026-09-28 — APLD research update v8 (Claude Opus 5.5, canonical WACC)

# APLD — Research Update 2026-09-28 (v8, Claude Opus 5.5)

*Supersedes evt_7ee0d09e3900 (computed at a hand-corrected 12.89% WACC before the wacc.py fix).*

## TL;DR
**MAINTAIN — fair value $24.20 vs $26.25 (-7.8%).** The AI lease backlog is real (~$36B base-term rent), but the stock is priced on funding and timing: ~$9B of 6.75-7% secured notes, a $2B Series G convertible preferred commitment, one-time-heavy FY26 revenue, and a sector-wide sell-off in leveraged AI landlords. Not a buy until financing clarity; not a sell inside model error.

## Company Snapshot
| Metric | Value |
|---|---|
| Price (2026-09-25 close) | $26.25 |
| Diluted shares | 284.3M |
| Market cap | $7.46B |
| TTM revenue | $611M (incl. ~$270.6M one-time tenant fit-out) |
| Q4 FY26 recurring base rent | $44.1M |
| FY26 GAAP net loss | $249.2M |
| TTM FCF | -$2.78B |
| Beta (2y OLS) | 2.82 |
| Analyst target mean / range | $66.43 / $22-$109 (15 analysts) |

## Why the stock is down ~47% from the May high ($49.65)
1. **Sector, not company**: since 2026-06-27 APLD -33%, CORZ -36%, WULF -39%, CIFR -32% while CRWV -9%, NBIS -1%, NVDA +17%. The sell-off is concentrated in debt-funded ex-miner landlords.
2. **Financing/dilution**: 2026-06-29 filing raised the Series G convertible preferred commitment $1.59B -> $2B (-7% day). 2026 secured notes: $2.15B at 6.75% (PF2), $1.59B at 7.00% (ELN-04), on top of $2.35B (Nov 2025). ATM ($200M) nearly exhausted.
3. **Earnings quality**: Q4 FY26 revenue $258.7M beat ~$95M consensus, but $152.4M was one-time fit-out; stock -12.8% on 2026-07-29.
4. **Return concerns**: Morgan Stanley initiated Equal Weight ($36.50, later $37.50), modelling 12.1% return on capex, below RIOT/HUT; Rothschild Neutral $22; UBS Buy $38.
5. **Rates**: 10Y at 5.23% raises the discount rate on long-dated lease cash flows.

## Investment Thesis
Signed 15-year leases with CoreWeave (Polaris Forge 1) and a US investment-grade hyperscaler (three campuses incl. Delta Forge 1 300 MW / $7.5B and Delta Forge 2 210 MW / $5.2B) underwrite a revenue ramp to roughly $2.7B by FY31. The equity question is how much of that reaches common shareholders after ~$0.6B/yr of interest, ~$0.7B/yr of depreciation, and Series G conversions. At a 12.68% WACC, the base case is worth about $21.99; the bull case needs new, unsigned leases.

## Scenario Analysis
### Bear (30%) — $2.94
Delays at Polaris Forge 2 / Delta Forge plus a CoreWeave credit event or lease renegotiation: revenue reaches only ~$1.8B by FY31 (below the ~$2.4B/yr contracted run-rate), interest on ~$9B of secured debt keeps net margin near 8%, and Series G conversions plus new equity drive max dilution (+5%/yr).

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 24% | from $611M TTM (incl. ~$270M one-time fit-out) |
| Year 5 Revenue | $1.79B | vs ~$2.4B/yr contracted base rent at full ramp |
| Net Margin (Yr 5) | 8% | rent NOI less D&A and interest |
| Exit P/E | 15x | Real Estate (REITs) row 15/20/28 |
| Quality Multiplier | 0.90 | lease contracts vs tenant concentration |
| Share Change | 5.0%/yr | Series G + financing dilution |
| **Year 5 EPS** | **$0.40** | — |
| **Year 5 Price** | **$5.33** | — |
| **Present Value** | **$2.94** | discounted at 12.68% |

### Base (50%) — $21.99
Signed leases (~$36B base-term rent, 15-yr terms) ramp on schedule to ~$2.7B revenue by FY31 (35% CAGR from $611M TTM, which includes ~$270M one-time fit-out). Rent NOI less ~$0.7B D&A and ~$0.6B interest leaves ~18% net margin; 28x exit (top of REIT P/E band, depreciation-heavy earnings); +4%/yr dilution from Series G and financing.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 35% | from $611M TTM (incl. ~$270M one-time fit-out) |
| Year 5 Revenue | $2.74B | vs ~$2.4B/yr contracted base rent at full ramp |
| Net Margin (Yr 5) | 18% | rent NOI less D&A and interest |
| Exit P/E | 28x | Real Estate (REITs) row 15/20/28 |
| Quality Multiplier | 1.00 | lease contracts vs tenant concentration |
| Share Change | 4.0%/yr | Series G + financing dilution |
| **Year 5 EPS** | **$1.43** | — |
| **Year 5 Price** | **$39.94** | — |
| **Present Value** | **$21.99** | discounted at 12.68% |

### Bull (20%) — $61.61
Catalyst: a new hyperscaler lease on the ~300 MW of marketed-but-unleased capacity within the 1.7 GW Morgan Stanley counts, plus Polaris Forge expansion, lifts revenue to ~$3.9B by FY31 at 25% net margin as debt refinances cheaper; 35x exit in line with listed data-center landlords; dilution slows to +2.5%/yr.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 45% | from $611M TTM (incl. ~$270M one-time fit-out) |
| Year 5 Revenue | $3.92B | vs ~$2.4B/yr contracted base rent at full ramp |
| Net Margin (Yr 5) | 25% | rent NOI less D&A and interest |
| Exit P/E | 35x | Real Estate (REITs) row 15/20/28 |
| Quality Multiplier | 1.05 | lease contracts vs tenant concentration |
| Share Change | 2.5%/yr | Series G + financing dilution |
| **Year 5 EPS** | **$3.05** | — |
| **Year 5 Price** | **$111.92** | — |
| **Present Value** | **$61.61** | discounted at 12.68% |

## Valuation Math
Weighted FV = 0.30 x $2.94 + 0.50 x $21.99 + 0.20 x $61.61 = **$24.20** (discount divisor 1.8165 at 12.68% over 5 years).

| Lens | Result |
|---|---|
| DCF (12.68% WACC) | $24.20 (-7.8%) |
| Monte Carlo (n=5000) | P10 $13.43 / P50 $21.13 / P90 $30.79; 76% probability overvalued |
| Reverse DCF | market implies 31.3% CAGR vs 35% base (between bear and base) |
| Comps (CORZ, IREN; EV/Sales 29x) | $45.53-$55.65 — low reliability (2 peers, ramp-stage multiples) |

Lenses disagree by >25%; not averaged.

## Key Risks
1. CoreWeave counterparty credit at Polaris Forge 1.
2. Series G convertible preferred dilution ($2B commitment).
3. Refinancing and interest burden on ~$9B of secured notes.
4. Construction/power slippage across four simultaneous campus builds.
5. Beta 2.8: historic average drawdown ~46% in market shocks.

## What to Watch
- Q1 FY27 earnings (~2026-10-09): recurring rent run-rate, Series G conversions, Delta Forge financing terms.
- Polaris Forge 2 energization (partial ops targeted year-end 2026).
- Any new lease on marketed-but-unleased capacity (bull catalyst).

## Red Team
**Objections:** Using P/E on a depreciation-heavy landlord undervalues it vs P/AFFO peers - base 28x may still be conservative.; Conversely, the base case assumes zero construction slippage across 4 simultaneous campus builds.; Bear PV $2.94 implies near-wipeout; plausible for levered developer but makes bear-derived stop levels meaningless.
**What would change my mind:** Recurring quarterly rent > $100M with Polaris Forge 2 energized (upside); Series G converted at a discount or new equity raise < $25 (downside); CoreWeave credit downgrade or lease renegotiation (downside)

## Data Quality & Confidence
Confidence **0.55/1.0**. Flags: wacc.py riskFreeRate was mis-scaled (^TNX 5.23 divided by 1000 -> 0.52%); fixed to handle percent quotes -> riskFreeRate 0.05234, WACC 12.68% (was 9.88%). | beta 2.82 outside typical range (wacc.py betaWarning). | TTM revenue $611M includes ~$270.6M one-time tenant fit-out (FY26 10-K); recurring base materially lower. | Comps uses only 2 peers (CORZ, IREN); CIFR/WULF lacked data; EV/Sales 29x distorted by ramp-stage peers. | Debt total conflicts across sources ($2.7B Feb-26 10-Q vs ~$5-6B+ after 2026 notes); modeled on issued notes $2.35B+$2.15B+$1.59B plus DF1/DF2 financing need. | yfinance historical_revenue/net_income have a zero first year (placeholder).

## Prior Analysis
v7 (Grok Live Sweep / Gemini 3.7 Flash, 2026-09-22): MAINTAIN, FV $35.76 at $28.25 -> now $26.25 (-7.1%). Flagged model; 9.72% discount rate too low; thesis text had lost all dollar amounts. Missed.

## Discussion Log


## 2026-09-22T04:31:50.359874+00:00 — Grok News Sweep: Wells Fargo PT  vs Redburn , 1.41 GW / $36B Backlog Confirmed

Wells Fargo Overweight ($50 PT), Redburn Neutral ($22 PT). 175 MW live at Polaris Forge 1, PF2 Harwood targeting partial ops end-2026. $36B 15-yr take-or-pay backlog. Net debt ~$5B vs $4.2B cash.

## 2026-09-03 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-09-02 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-08-28 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-08-25 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-08-21 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-08-13 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-07-23 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-07-10 — TA Sweep for APLD

Batch technical indicators for APLD.

## 2026-06-27 — Prediction claim: APLD dcf_fair_value (2026-06-27)

Direction: bullish, horizon: 180 days.

## 2026-05-02 — APLD research import (2026-05-02)

# APLD — Applied Digital Corporation
**Date**: 2026-05-02 | **Model**: Claude Sonnet 4.6 | **Action**: SELL | **Fair Value**: $11.93 vs $33.55 (−64.4%)

## TL;DR
Applied Digital is an AI HPC data center buildout story trading at an extreme P/S of 66.5x on $144M TTM revenue. Despite 139% revenue growth signaling strong AI infrastructure demand, the company remains loss-making with no credible path to profitability at current valuation. DCF analysis yields $11.93 fair value — a SELL at current prices.

## Company Snapshot
| Metric | Value |
|--------|-------|
| Price | $33.55 |
| Market Cap | $9.59B |
| Revenue (TTM) | $144.2M |
| Revenue Growth | 139.3% YoY |
| Net Margin (TTM) | Negative (PE=0) |
| Forward PE | Negative |
| P/S Ratio | 66.5x |
| Shares (Diluted) | 285.8M |

## Investment Thesis
Applied Digital pivoted from crypto mining to AI HPC data center hosting, targeting hyperscaler and enterprise customers needing dedicated GPU compute clusters. The 139% revenue growth is real — APLD has contracts with known AI customers and is building large-scale data centers in North Dakota and Texas. However, the company is deeply loss-making (negative forward PE) and the $9.59B valuation is pricing in a near-perfect execution of a bull case scenario.

The P/S of 66.5x places APLD alongside or above established cloud providers despite being a fraction of their scale and profitability. Even under a base-case scenario of 65% CAGR over 5 years — which would put Y5 revenue at ~$1.47B — the company would need to achieve 10% net margins (unprecedented for a colocation/HPC company at this stage) and trade at 18x PE to justify anywhere near current prices. Present value of that base case: $6.56/share.

Only the bull case (95% CAGR, 18% margin, 28x PE) yields a price above current levels ($44.48 PV), and this requires APLD to become a top-tier AI cloud provider rivaling CoreWeave or Lambda Labs — an outcome with low probability given hyperscaler competition.

The speculative premium reflects the AI infrastructure narrative rather than fundamentals. When AI capex cycles normalize, valuations compress sharply. The sector has no durable barrier to new entrants with cheaper capital.

## Scenario Analysis

### 🐻 Bear (35% weight): AI contract delays, continued losses
AI capex cycle peaks early; APLD fails to convert HPC contracts to recurring revenue; remains loss-making at scale; P/S compresses to 3x.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 25% | Contract delays; slower hyperscaler adoption |
| Year 5 Revenue | $438M | $144M × 1.25⁵ |
| Net Margin (Yr 5) | 3% | Marginal profitability; colocation cost structure |
| Exit P/E | 10x | Distressed AI infrastructure multiple |
| Quality Multiplier | 0.90 | No moat; commodity compute |
| Share Change | +2%/yr | Continued dilutive equity raises |
| **Year 5 EPS** | **$0.04** | — |
| **Year 5 Price** | **$0.38** | — |
| **Present Value** | **$0.23** | — |

### ⚖️ Base (45% weight): AI HPC demand sustains, path to modest profitability
APLD scales to 4+ hyperscaler customers; achieves 10% operating margin on $1.47B HPC/colocation revenue by Y5.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 65% | AI demand sustains; APLD wins enterprise contracts |
| Year 5 Revenue | $1.47B | $144M × 1.65⁵ |
| Net Margin (Yr 5) | 10% | AI HPC colocation margin benchmark |
| Exit P/E | 18x | Infrastructure with recurring revenue |
| Quality Multiplier | 1.00 | No named structural moat |
| Share Change | +1%/yr | Moderate dilution from capex financing |
| **Year 5 EPS** | **$0.59** | — |
| **Year 5 Price** | **$10.56** | — |
| **Present Value** | **$6.56** | — |

### 🚀 Bull (20% weight): APLD becomes top-tier AI cloud provider
Wins 10+ hyperscaler contracts; $4.6B Y5 revenue with 18% margin as dedicated AI infrastructure commands cloud-tier premium.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 95% | APLD captures 5%+ of AI HPC addressable market |
| Year 5 Revenue | $4.61B | $144M × 2.0⁵ |
| Net Margin (Yr 5) | 18% | Premium AI cloud margin (CoreWeave analogue) |
| Exit P/E | 28x | High-growth AI infrastructure premium |
| Quality Multiplier | 1.05 | Nascent scale advantage if hyperscaler depth achieved |
| Share Change | +1%/yr | Moderate dilution |
| **Year 5 EPS** | **$2.44** | — |
| **Year 5 Price** | **$71.64** | — |
| **Present Value** | **$44.48** | — |

## Valuation Math
- Bear: $0.23 × 35% = $0.08
- Base: $6.56 × 45% = $2.95
- Bull: $44.48 × 20% = $8.90
- **Weighted Fair Value: $11.93** vs $33.55 current → **SELL −64.4%**

## Key Risks
1. **Execution risk** — Data center buildouts face power procurement, permitting, and capex overruns
2. **Hyperscaler disintermediation** — AWS, Azure, GCP can build their own HPC clusters, reducing demand for APLD
3. **Dilution** — Capex-intensive business requires ongoing equity raises; share count dilution compounds losses
4. **BTC mining legacy** — Prior crypto exposure and pivot narrative may mask fundamental business model weakness
5. **AI capex cycle normalization** — Speculative AI infrastructure premium will compress when hyperscaler capex plateaus

## What to Watch
- Quarterly revenue growth rate sustaining above 100%
- Any analyst coverage initiation with price target anchors
- Operating cash flow turning positive (critical valuation gating event)
- Hyperscaler contract announcements with named customers

## Data Quality & Confidence: 0.55/1.0
- No historical financial data available in API (early-stage company)
- No analyst estimates available
- Negative earnings makes margin modeling speculative
- P/S 66.5x = extreme speculative premium; DCF fundamentally disagrees with market

## Prior Analysis
**Gemini 3 Pro** (2026-05-02): SELL $15.35 at $33.55 — directionally aligned; both analyses agree SELL. Current analysis more bearish ($11.93) due to independent derivation.

## Discussion Log
*(empty — append Q&A here)*

