---
name: forward-valuation-challenge
description: >
  Challenge and stress-test AI-generated investment thesis valuations that are overly anchored on historical financials. Force the valuation engine to incorporate forward-looking demand signals, contract pipelines, and secular growth drivers — particularly for companies positioned in the AI infrastructure and data center buildout.
has_tools: false
allowed-tools: Read, Write
---

# Forward-Looking Valuation Challenge Skill

## Purpose
Challenge and stress-test AI-generated investment thesis valuations that are overly anchored on historical financials. Force the valuation engine to incorporate forward-looking demand signals, contract pipelines, and secular growth drivers — particularly for companies positioned in the AI infrastructure and data center buildout.

## Problem Statement
The current valuation model tends to produce bear/base/bull scenarios that are excessively backward-looking:
- Growth rates derived from trailing revenue CAGR rather than forward contract visibility
- Margins based on historical averages rather than operating leverage at scale
- Terminal multiples anchored to legacy comps rather than the structural repricing of AI infrastructure assets
- No incorporation of signed contracts, backlog, or LOIs into revenue visibility
- No recognition of the unprecedented scale of the AI infrastructure capex cycle

This produces scenarios where:
- Bear cases collapse to near-zero despite visible contracted revenue
- Base cases assume modest growth while the company sits on billions in backlog
- Bull cases are the only ones that reflect the actual demand environment
- The probability-weighted fair value becomes artificially depressed

## When This Skill Activates
This skill MUST activate when analyzing any company operating in:
- AI data center power (fuel cells, gas turbines, SMRs, behind-the-meter generation)
- AI data center infrastructure (cooling, electrical, construction, MEP)
- AI compute hardware (GPUs, custom silicon, networking, memory)
- AI data center REITs and developers
- Grid infrastructure, transmission, and utility companies with AI data center exposure

## Required Context: The AI Infrastructure Buildout (2025–2030)

The valuation engine MUST incorporate the following verified demand signals into scenario construction:

### Hyperscaler Capital Expenditure (verified, public filings)
| Year | Combined Hyperscaler Capex (Big 5) | YoY Growth |
|------|-------------------------------------|------------|
| 2024 | ~$256B | +63% |
| 2025 | ~$443B | +73% |
| 2026 (projected) | $660–770B | +36–73% |
| 2025–2027 cumulative | ~$1.15 trillion (Goldman Sachs est.) | — |

- ~75% of 2026 capex (~$450–500B) is AI-specific infrastructure
- Capital intensity has reached 45–57% of revenue for hyperscalers — historically unprecedented
- All hyperscalers report demand is supply-constrained, not demand-constrained

### Individual Hyperscaler Commitments (2026)
| Company | 2026 Capex Guidance | Notes |
|---------|---------------------|-------|
| Amazon/AWS | ~$200B | Majority to AI data centers |
| Alphabet/Google | $175–185B | 2× prior year |
| Meta | $125–145B | Highest ever |
| Microsoft | $120B+ | Azure AI infrastructure |
| Oracle | ~$50B | Cloud + AI factories |

### Power Demand Projections
- US data center power demand: **61.8 GW (2025) → 134.4 GW (2030)** (S&P Global 451 Research)
- Global data center electricity: **448 TWh (2025) → 980 TWh (2030)** (Gartner)
- AI-optimized servers: **21% of DC power (2025) → 44% by 2030** (Gartner)
- Goldman Sachs: **+165% increase in data center power demand by 2030** vs 2023
- Grid infrastructure investment to support AI: **$700B+ by 2030**
- Behind-the-meter (off-grid) power is now the critical enabler — grid interconnection timelines are 3–7 years; BTM deploys in months

### Construction Pipeline
- **23+ GW** of data center capacity under construction globally (BloombergNEF, Sep 2025)
- **831 active construction sites** worldwide
- 75% of construction is in the US
- 40% of announced projects face delays due to **power infrastructure bottlenecks** (not chip supply)

## Valuation Challenge Rules

### Rule 1: Revenue Visibility Must Reflect Contracted Backlog
If the company has disclosed:
- Signed contracts or framework agreements
- Product/service backlog ($ value)
- Letters of intent (LOIs)
- Named customer commitments

Then the BASE case revenue trajectory MUST reflect at minimum the contracted/backlog revenue, appropriately phased over the delivery timeline.

**Example (Bloom Energy):**
- Product backlog: ~$6B (as of Q4 2025)
- Service backlog: ~$14B
- Named deals: $5B Brookfield, $2.65B AEP, 2.8GW Oracle
- TTM revenue: ~$2B
- Therefore: base case CANNOT assume revenue grows at only 35% CAGR if $6B+ in product backlog exists against $2B TTM revenue

### Rule 2: Growth Rates Must Be Calibrated to Addressable Demand
The scenario growth rates must be benchmarked against:
- Total addressable market (TAM) growth for the specific segment
- The company's current market share and trajectory
- The rate of industry capex deployment (which sets the demand ceiling)

**Sanity check formula:**
```
If industry_capex_growth > 50% YoY
AND company_backlog_growth > 100% YoY
AND company_revenue_growth_ttm > 30%
THEN base_case_CAGR should be >= company_revenue_growth_ttm
```

Do NOT default to "regression to mean" growth rates when the industry is in a structural acceleration phase.

### Rule 3: Margin Assumptions Must Reflect Operating Leverage
For companies with:
- High fixed-cost manufacturing (fuel cells, hardware, infrastructure)
- Recurring service revenue streams
- Increasing scale of deployments

Margins should IMPROVE as revenue scales, not remain flat at historical averages.

**Challenge test:**
```
If base_case_CAGR > 30%
AND current_gross_margin is improving QoQ
AND company has recurring service revenue
THEN base_case_terminal_margin should be HIGHER than trailing margin
```

### Rule 4: Bear Case Must Have a Floor Based on Contracted Revenue
The bear case should NOT produce near-zero target prices when the company has:
- Billions in signed contracts
- Diversified customer base (utilities, hyperscalers, enterprises)
- Deployed installed base generating recurring service revenue

**Bear case floor formula:**
```
bear_floor = (contracted_backlog * delivery_probability * margin) / shares_outstanding
```

A bear case of $0.23 on a company with $6B backlog and $14B service backlog is not a "bear case" — it's a bankruptcy/fraud scenario that should be labeled as such and assigned < 10% probability.

### Rule 5: Exit Multiples Must Reflect Sector Re-Rating
AI infrastructure companies have structurally re-rated vs. legacy energy/industrial comps:
- Traditional power generation: 8–15x P/E
- AI infrastructure enablers: 25–50x P/E (or higher for high-growth)
- Data center REITs: 30–50x FFO

The exit multiple in the BASE case should reflect where the company is heading (AI infrastructure), not where it came from (legacy fuel cells / traditional power).

### Rule 6: Explicitly State Forward vs. Backward Assumptions
Every scenario MUST include a "Forward Signals" section that lists:
- Relevant macro demand data (hyperscaler capex, power demand growth)
- Company-specific forward indicators (backlog, contracts, partnerships, LOIs)
- Industry tailwinds or headwinds specific to the 5-year horizon

If the model ignores these signals, it must explicitly state WHY and justify the omission.

### Rule 7: Scenario Spread Sanity Check
After computing bear/base/bull:

```
spread_ratio = bull_target / bear_target
```

If `spread_ratio > 50x`, flag for review. This typically indicates:
- A units/scale bug in the valuation math
- An implicit bankruptcy assumption in bear that isn't labeled
- Inconsistent discount rates or share counts across scenarios

Acceptable spread ratios for speculative growth companies: **5x–20x**
Acceptable spread ratios for established companies: **2x–5x**

### Rule 8: Cross-Validate Against Market Implied Expectations
Before finalizing scenarios, check:
```
current_market_cap = share_price × shares_outstanding
implied_growth = reverse_DCF(current_market_cap, discount_rate, horizon)
```

If the BASE case implies the market is > 50% overvalued, the model must:
1. Explicitly state what the market is "pricing in" that the model rejects
2. Identify which specific assumption drives the divergence
3. Assign appropriate probability to the possibility that the MARKET is right

## Output Requirements

When this skill activates, the valuation output MUST include:

### 1. Forward Context Box
A brief section (3–5 bullets) summarizing:
- Current industry capex cycle stage
- Key demand signals for the company's segment
- Notable contracts/backlog/partnerships

### 2. Assumption Transparency Table
For each scenario (bear/base/bull):
| Input | Value | Source | Forward or Backward |
|-------|-------|--------|---------------------|
| Rev CAGR | X% | [source] | Forward / Backward |
| Net Margin | X% | [source] | Forward / Backward |
| Exit P/E | Xx | [source] | Forward / Backward |

### 3. Sanity Check Log
- Spread ratio: X (pass/fail)
- Bear floor check: pass/fail
- Backlog incorporation: yes/no
- Market implied growth comparison: X%

### 4. Confidence Qualifier
Rate the overall thesis confidence:
- **HIGH**: Strong forward signals, contracted revenue, clear TAM expansion
- **MEDIUM**: Mixed signals, some forward visibility, execution risk
- **LOW**: Highly speculative, limited forward visibility, binary outcome

## Example Application: Bloom Energy (BE)

### What the model currently produces (problematic):
- Bear: $4 (near-zero, ignores $6B backlog)
- Base: $48 (assumes 35% CAGR despite 37% actual + accelerating backlog)
- Bull: $323 (only scenario reflecting AI demand reality)

### What the model SHOULD produce (forward-calibrated):
- Bear: $80–120 (contracted revenue floor + margin compression + multiple contraction)
- Base: $180–250 (backlog-supported growth + margin expansion at scale + sector-appropriate multiple)
- Bull: $350–500 (full TAM capture + margin leadership + premium multiple)

### Why:
- $6B product backlog + $14B service backlog = multi-year revenue visibility
- $5B Brookfield partnership = institutional validation of technology
- $2.65B AEP utility deal = grid-scale adoption beyond data centers
- 2.8GW Oracle expansion = hyperscaler repeat commitment
- Behind-the-meter power is the #1 bottleneck for AI data center deployment
- Grid interconnection delays (3–7 years) make Bloom's rapid-deploy model structurally advantaged

## Maintenance
This skill should be updated quarterly with:
- Latest hyperscaler capex guidance
- Updated power demand forecasts
- Company-specific contract/backlog updates
- Any material changes to the AI infrastructure investment cycle

---
*Last updated: May 2026*
*Data sources: Goldman Sachs Research, S&P Global 451 Research, Gartner, BloombergNEF, McKinsey, Moody's Ratings, SEC filings, company earnings reports*
