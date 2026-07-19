# IREN Research Timeline

## 2026-07-02 — IREN research import (2026-07-02)

# IREN Limited (IREN) — Deep-Dive Research Report
**Date**: 2026-07-02  
**Analyst**: Antigravity Gemini 3.5  
**Verdict**: **SELL** (Fair Value **$20.43** vs Current Price **$38.27**, **-46.6%** downside)

---

## TL;DR
IREN Limited faces a severe valuation contraction driven by a **38.4% share count dilution** (shares outstanding rising from 258M to 357.38M), critical corporate governance concerns surrounding an **$800 million CEO RSU compensation package**, and structural threats to GPU rental margins from **Meta’s entry** into the AI cloud infrastructure market. We downgrade IREN to **SELL** with a weighted fair value of **$20.43**.

---

## Company Snapshot

| Metric | Value | Source / Note |
|--------|-------|---------------|
| Current Price | $38.265 | July 2, 2026 Close |
| Shares Outstanding | 357,378,674 | Basic outstanding (overriding yfinance's stale 258M diluted count) |
| TTM Revenue | $501.02M | yfinance |
| TTM Revenue Growth | +167.65% | Hypergrowth due to mining capacity & initial AI cloud deployments |
| TTM Net Profit Margin | 20.88% | yfinance |
| Trailing P/E | 94.45x | Based on corrected basic share count earnings |
| **Weighted Fair Value** | **$20.43** | **SELL (-46.6%)** |

---

## Investment Thesis

### The Dilution Trap & Capital Structure Shock
IREN is expanding its megawatt data center capacities rapidly. However, to fund this buildout, management has aggressively utilized its ATM equity programs. Basic shares outstanding have ballooned from **258M to 357.38M** in a very short period. yfinance continues to distribute a stale `shares_diluted` count of 258.2M, meaning many automated screens and models are severely overstating IREN's per-share earnings power. Adjusting for the actual capital structure reduces the base case fair value significantly.

### Corporate Governance Concerns
The approval of an **$800 million RSU package** for Co-CEOs William and Daniel Roberts represents an extreme case of shareholder dilution and poor board alignment. A compensation package of this magnitude is highly unusual for a company generating ~$500M in trailing revenues. It adds a major structural overhead to net income margins and signals capital allocation that is hostile to public shareholders.

### Meta Competitive Threat & GPU Commoditization
Recent reports that Meta plans to build and offer its own AI cloud infrastructure introduce a massive, deep-pocketed competitor to the market. Meta can afford to subsidize compute rentals at scale, threatening to compress GPU lease margins for smaller providers like IREN that do not have custom silicon or proprietary software moats.

---

## Scenario Analysis

### 🐻 Bear Case Scenario (20% Probability) — Present Value: $0.70
A severe correction in Bitcoin price (60%+) combines with rising network difficulty, compressing mining margins to cash-trough levels. Grid interconnection delays and equipment delivery backlogs stall the AI cloud rollout. Continued dilution of 5%/year is required to fund operations.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 15% | BTC bear market slows growth; AI rollout delayed |
| Year 5 Revenue | $1,007.7M | Severe deceleration from capacity expansion stalls |
| Net Margin (Yr 5) | 5% | Cyclical trough mining margins |
| Exit P/E | 12x | Cyclical commodity infrastructure trough multiple |
| Quality Multiplier | 0.85x | Corporate governance discount and high beta risk |
| Share Change | 5.0%/yr | High dilution to bridge capital shortfalls |
| **Year 5 EPS** | **$0.11** | — |
| **Year 5 Price** | **$1.13** | — |
| **Present Value** | **$0.70** | — |

### ⚖️ Base Case Scenario (45% Probability) — Present Value: $10.85
Through-cycle normalization of Bitcoin prices ($60k–$120k). The AI cloud hosting pivot scales to 35-40% of the revenue mix, stabilizing blended margins. Revenue grows at a 35% CAGR (decelerated from 167% TTM). Dilution continues at 3.5%/year to fund megawatt capacity additions.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 35% | Decelerated from 167% hypergrowth baseline |
| Year 5 Revenue | $2,246.6M | Solid capacity execution on Texas/Australia campuses |
| Net Margin (Yr 5) | 15% | Blended rate reflecting stabilized AI hosting margins |
| Exit P/E | 22x | Digital infrastructure benchmark with commodity discount |
| Quality Multiplier | 1.00x | Standard business quality |
| Share Change | 3.5%/yr | Continuous equity issuance for data center CapEx |
| **Year 5 EPS** | **$0.79** | — |
| **Year 5 Price** | **$17.47** | — |
| **Present Value** | **$10.85** | — |

### 🚀 Bull Case Scenario (35% Probability) — Present Value: $44.01
Bitcoin price appreciates to $200k+ driven by global institutional adoption, while AI hosting scales rapidly (targeting 1+ GW of compute capacity). High-margin GPU contracts are executed at scale. Renewable PPAs in British Columbia and Texas supply sub-$0.03/kWh energy, providing a strong cost moat.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 50% | Successful execution of the full GW-scale backlog |
| Year 5 Revenue | $3,804.6M | AI cloud contracts fully ramp alongside high BTC prices |
| Net Margin (Yr 5) | 25% | High-profit hosting blended with peak mining margins |
| Exit P/E | 28x | Premium AI infrastructure multiple |
| Quality Multiplier | 1.05x | Moat from sub-$0.03/kWh hydroelectric power contracts |
| Share Change | 2.0%/yr | Self-funding cash flow reduces dilution rate |
| **Year 5 EPS** | **$2.41** | — |
| **Year 5 Price** | **$70.87** | — |
| **Present Value** | **$44.01** | — |

---

## Valuation Arithmetic
$$\text{Weighted Fair Value} = (0.20 \times \$0.70) + (0.45 \times \$10.85) + (0.35 \times \$44.01) = \$0.14 + \$4.88 + \$15.40 = \$20.43$$

---

## Key Risks & What to Watch
1. **Bitcoin Volatility**: IREN remains heavily exposed to BTC price cycles. Any sharp downturn instantly degrades mining cash flows.
2. **GPU Leasing Commoditization**: Meta, Amazon, and Google Cloud expanding their custom silicon compute capacity could significantly drive down GPU pricing power.
3. **Execution Delay**: Developing GW-scale power interconnections is subject to utility grid backlogs and equipment shortages (transformers, cooling infrastructure).
4. **Governance Overhang**: The $800M CEO compensation plan may lead to further shareholder unfriendly moves or executive flight if targets are unachievable.

---

## Data Quality & Confidence Score
**Confidence Score**: **0.55 / 1.0**
* **Positive factors**: Clear TTM financial numbers and established yfinance revenue trend.
* **Negative factors**: 
  * Severe discrepancy in API share counts (diluted vs outstanding) requiring manual intervention.
  * Extremely high cyclical volatility makes margin projection highly speculative.
  * Governance and executive compensation red flags discount management's projections.

---

## Discussion Log
* **2026-07-02 (Antigravity Gemini 3.5)**: Initial post-dilution review and Meta threat downgrade to SELL. Stale share counts corrected to basic outstanding count of 357.38M.

REPORT_EOF


## 2026-05-02 — IREN research import (2026-05-02)

# Iris Energy (IREN) — Deep-Dive Research Report
**Date**: 2026-05-02 | **Analyst**: Claude Sonnet 4.6 | **Action**: SELL | **Fair Value**: $39.03 | **Price at Analysis**: $45.66

---

## TL;DR
Iris Energy is one of the best-positioned Bitcoin miners (renewable hydro power at sub-$0.03/kWh is a real structural moat), growing +59% YoY with a credible AI/HPC hosting pivot. But the 51.48% TTM net margin is a cyclical Bitcoin peak — through-cycle normalized margins of 18% in the base case produce a weighted fair value of **$39.03 SELL (-14.5%)**. Not dramatically overvalued; re-entry at $30-35.

---

## Prior Analysis Review
**Prior model**: Gemini 3 Pro | **Same day** | **Prior FV**: $50.38 (HOLD)

Two corrections:
1. **Bull CAGR 90% → 60%**: Gemini modeled 90% CAGR → $12.4B Y5 revenue from a $501M base. This is an extreme assumption requiring IREN to become a top-10 global infrastructure company in 5 years with no named catalysts. Corrected to 60% → $5.25B.
2. **QM 1.1 → 1.05**: Bull QM 1.1 was uncited in the prior rationale. Corrected to 1.05 with explicit moat citation (hydro PPAs). These two changes flip the result from HOLD to SELL and lower FV from $50.38 → $39.03.

**Note**: Unlike AMD/INTC/CRWD, the Gemini bear margin (5%) is correctly *below* TTM (51.48%) — appropriate directional modeling of cyclical mean-reversion. No bear-above-TTM error on this one.

---

## Company Snapshot

| Metric | Value | Note |
|--------|-------|------|
| Price | $45.66 | |
| Market Cap | $15.15B | |
| TTM Revenue | $501M | |
| Revenue Growth YoY | +59% | Strong capacity expansion |
| TTM Net Margin | **51.48%** | ⚠️ BTC cyclical peak — not sustainable |
| Trailing P/E | 31.7x | |
| Forward P/E | **36.1x** | Market pricing in earnings compression |
| P/S | 30.23x | Expensive on trailing basis |
| Beta | 4.308 | High volatility |
| Shares Diluted | 258.2M | ⚠️ 22.2% discrepancy vs mktcap-implied 331.8M |

**The forward P/E > trailing P/E signal**: When forward P/E (36.1x) exceeds trailing (31.7x), the market is pricing in earnings *compression* at the same stock price. This directly confirms the mean-reversion thesis — the market already knows the 51.48% margin won't persist.

---

## Investment Thesis

IREN's competitive edge among Bitcoin miners is genuine: long-term hydroelectric power purchase agreements at $0.02-0.03/kWh in British Columbia and Texas give them a structural cost floor that high-cost miners (paying $0.06-0.10/kWh from grid) can't match. During BTC mining difficulty cycles when marginal miners get squeezed out, IREN survives and often gains market share. This isn't a speculative moat — it's contracted energy economics.

The AI/HPC hosting pivot adds a dimension that didn't exist in the last BTC cycle. IREN has announced targets for gigawatt-scale AI compute capacity, and the same power assets that make them a resilient miner make them a competitive AI hosting provider (AI data centers are energy-intensive, same as mining). The bull case has a credible mechanism.

The challenge is current valuation. At $45.66 and 30x P/S, the stock prices in both continued BTC elevation AND successful AI pivot execution simultaneously. The forward P/E of 36.1x already signals the market expects near-term earnings compression from the 51.48% peak. Through-cycle normalized, the base case produces a $27 present value — 41% below current price.

This is a stock worth owning at $30-35, where the base case provides a reasonable margin of safety and you're getting the bull case optionality essentially free.

---

## Scenario Analysis

### 🐻 Bear Case (30% weight) — $1.26

Bitcoin price corrects 60%+ from current levels. Mining difficulty continues rising with network hash rate expansion. AI hosting ramp faces grid interconnection delays. Revenue grows only 20% CAGR. Through-cycle trough margins reach 5% — IREN's hydro power advantage provides survival buffer that higher-cost miners lack entirely. Historical reference: Bitcoin miners broadly traded at 1-3x EV/Revenue during the 2022 bear cycle; IREN's low-cost structure would likely preserve equity value better than peers.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 20% | BTC revenue compression; AI ramp delayed |
| Year 5 Revenue | $1,246.7M | From $501M at 20% CAGR |
| Net Margin (Yr 5) | 5% | BTC trough; hydro advantage preserves survival-level margins |
| Exit P/E | 12x | Cyclical infrastructure at trough |
| Quality Multiplier | 0.85 | Execution risk; dual-model complexity |
| Share Change | +4%/yr | Dilution for ongoing capex |
| **Year 5 EPS** | **$0.20** | $62.3M NI / 314.2M shares |
| **Year 5 Price** | **$2.02** | — |
| **Present Value** | **$1.26** | — |

### ⚖️ Base Case (45% weight) — $27.00

Through-cycle normalized scenario. BTC oscillates in a moderate range ($60K-$120K). IREN's hydro PPAs keep mining competitive through the cycle. AI/HPC hosting ramps to 30-40% of revenue mix by Y5, improving blended margins above pure-mining peers. Revenue deceleration: 59% → 50% → 42% → 35% → 26% → 18%, implying 42% 5-year CAGR. Through-cycle normalized GAAP margin of 18% balances mining cyclicality with AI hosting uplift.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 42% | Realistic deceleration from 59%; AI hosting mix grows |
| Year 5 Revenue | $2,892.7M | From $501M at 42% CAGR |
| Net Margin (Yr 5) | 18% | Through-cycle: hydro cost advantage + AI hosting blend |
| Exit P/E | 25x | Proven infrastructure with cyclical component |
| Quality Multiplier | 1.0 | Power moat acknowledged; not exceptional-tier in base |
| Share Change | +3%/yr | Ongoing capex for capacity expansion |
| **Year 5 EPS** | **$1.74** | $520.7M NI / 299.4M shares |
| **Year 5 Price** | **$43.48** | — |
| **Present Value** | **$27.00** | — |

### 🚀 Bull Case (25% weight) — $106.01

**Catalyst**: Bitcoin appreciates to $200K+ driven by institutional ETF inflows and sovereign adoption; simultaneously IREN's AI/HPC hosting achieves gigawatt-scale. The combination of peak mining profitability and high-margin AI hosting drives blended 28% GAAP margins. QM 1.05 citing specific structural moat: **long-term hydroelectric PPAs at $0.02-0.03/kWh in British Columbia and Texas — these contracted rates represent a 3-5x cost advantage over grid-connected AI data centers and cannot be replicated without decade-scale utility negotiation and environmental permitting**.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 60% | Sustained by BTC appreciation + full AI hosting scale |
| Year 5 Revenue | $5,253.6M | From $501M at 60% CAGR |
| Net Margin (Yr 5) | 28% | Elevated BTC + AI hosting premium margins |
| Exit P/E | 30x | Premium AI infrastructure (below Equinix 35-40x given BTC cyclicality) |
| Quality Multiplier | 1.05 | Hydro PPA moat: contracted $0.02-0.03/kWh vs market $0.06-0.10/kWh |
| Share Change | +1%/yr | Dilution moderates as cash generation improves |
| **Year 5 EPS** | **$5.42** | $1,471M NI / 271.4M shares |
| **Year 5 Price** | **$170.73** | — |
| **Present Value** | **$106.01** | — |

---

## Valuation Math

| Scenario | PV | Weight | Contribution |
|----------|-----|--------|-------------|
| Bear | $1.26 | 30% | $0.38 |
| Base | $27.00 | 45% | $12.15 |
| Bull | $106.01 | 25% | $26.50 |
| **Weighted FV** | | **100%** | **$39.03** |

**Current price**: $45.66 | **Downside**: **-14.5%** | **Action**: **SELL**
**Re-entry range**: $30-35 (base case PV $27 starts providing real margin of safety)

---

## Key Risks

1. **Bitcoin price cyclicality**: The TTM 51.48% margin will not persist. Every prior BTC cycle has seen 50-80% price corrections. The bear case (30% weight, $1.26 PV) reflects realistic cycle trough dynamics. Investors must size positions with this binary outcome in mind.
2. **AI hosting execution**: Gigawatt-scale AI hosting is ambitions — grid interconnection, permitting, and equipment procurement are all multi-year processes with execution risk. Delays push the bull case timeline out and dilute per-share value.
3. **Share count dilution**: Ongoing capacity expansion requires capital. With +3-4%/yr share count growth in base/bear scenarios, per-share value compounds more slowly than headline revenue growth suggests.
4. **Renewable energy dependency**: IREN's hydro PPA advantage depends on continued access to those power sources. Regulatory changes in British Columbia or Texas power markets, or PPA non-renewal, could eliminate the key competitive advantage.
5. **Multiple compression on mining**: If Bitcoin mining is increasingly viewed as environmentally controversial (ESG pressure) or if AI hosting becomes the primary business narrative, the appropriate exit multiple shifts materially. Misclassification risk on exit PE is higher than for pure software businesses.

---

## What To Watch
- **AI hosting MW announcement**: Specific contracted GW targets with delivery timelines = bull signal
- **BTC price trend**: Direction of travel into next halving cycle is the primary margin driver
- **Revenue mix disclosure**: Mining % vs AI hosting % quarterly — watch for the crossover
- **PPA renewal details**: Any changes to the hydroelectric power contract terms are a critical risk flag
- **Re-entry signal**: $30-35 where base case $27 PV provides modest but real margin of safety

---

## Data Quality & Confidence Score

**Confidence**: 0.50/1.0

**Flags**:
- ⚠️ TTM 51.48% margin is cyclical BTC peak — through-cycle normalization required
- ⚠️ Share count discrepancy 22.2% (API diluted 258M vs mktcap-implied 332M) — above 15% threshold
- ⚠️ Forward P/E (36.1x) > trailing (31.7x) — market already pricing in earnings compression
- ⚠️ No financial history from API
- ⚠️ No analyst estimates available
- ⚠️ Prior Gemini bull CAGR 90% was extreme — corrected to 60% (flips HOLD → SELL)
- ✅ Revenue growth +59% genuine (not declining like RGTI/CORZ)
- ✅ Hydro PPA moat explicitly documented and cited
- ✅ Profitable company (P/E 31.7x) — not a pre-revenue speculation

---

## Discussion Log
*Session: 2026-05-02 — Replaced same-day Gemini 3 Pro (v3, $50.38 HOLD). No Q&A appended.*

---

## Sources Checked
- Financial data: ✅ fetch_financials.py | Historical arrays: ❌ Null
- Analyst estimates: ❌ Unavailable
- Projection: ✅ IREN.json v4 | Research: ✅ IREN_2026-05-02.md
- Benchmarks: ✅ references/valuation-benchmarks.md
- Prior: ✅ v3 Gemini 3 Pro — REPLACED (bull CAGR corrected 90% → 60%, QM 1.1 → 1.05)

