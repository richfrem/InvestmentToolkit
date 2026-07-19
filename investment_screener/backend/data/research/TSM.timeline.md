# TSM Research Timeline

## 2026-05-02 — TSM research import (2026-05-02)

# Taiwan Semiconductor Manufacturing (TSM) — Deep-Dive Research Report
**Date**: 2026-05-02 | **Analyst**: Claude Sonnet 4.6 | **Action**: HOLD | **Fair Value**: $453.72 | **Price**: $397.67

---

## TL;DR
TSMC is the world's only volume manufacturer of sub-3nm chips — every AI accelerator from NVIDIA, AMD, and Apple runs through its fabs, creating an unmatched structural moat. At $397.67, the stock is fairly valued against a $453.72 weighted fair value (+14%). Great business, full price — HOLD until $320-350 range for a compelling entry.

---

## Prior Analysis Review
**Prior model**: Gemini 1.5 Pro | **Same day** | **Prior FV**: $671.68 (BUY)

Three corrections vs Gemini:
1. **QM inflated**: Base QM 1.2, bull QM 1.25 were uncited. "Near-absolute monopoly" is one moat source, not two+. Corrected to 1.1 (base: process monopoly cited) and 1.15 (bull: process monopoly + ecosystem lock-in cited). This alone cuts ~$100 from FV.
2. **Growth rates too aggressive**: Base 25% and bull 32% on $119B revenue would require Y5 revenues of $366B and $470B respectively. Corrected to 18%/25% with explicit catalyst for bull.
3. **Currency correction**: Raw yfinance revenue was NT$3.81T TWD — patched to $119B USD for valid DCF math.

Result flips from BUY $671 → HOLD $453.

---

## Company Snapshot

| Metric | Value | Note |
|--------|-------|------|
| Price (ADR) | $397.67 | 1 ADR = 5 ordinary shares |
| Market Cap | $2.062T | |
| TTM Revenue | ~$119B USD | NT$3.81T / 32 TWD/USD |
| Revenue Growth YoY | +35.1% | AI chip demand surge |
| Trailing P/E | 34.1x | |
| Forward P/E | **20.6x** | Implies 65.6% Y+1 EPS growth |
| TTM Net Margin | ~42-50% | P/E-implied 50.7%; historical range 38-45% |
| Shares (ADR basis) | 5.186B | 25.93B ordinary / 5 per ADR |

**Key signal — forward P/E 20.6x vs trailing 34.1x**: Market expects Y+1 EPS to grow 65.6% — consistent with continued AI chip demand and N2 node ramp with premium pricing.

---

## Investment Thesis

TSMC occupies the most defensible position in the global semiconductor supply chain. As the world's only volume manufacturer of sub-3nm logic chips, TSMC is the sole source for every AI GPU and accelerator that matters: NVIDIA H100/H200/B100/B200, AMD MI300X/MI350, and Apple Silicon. This is not a competitive advantage — it's a structural monopoly protected by a $50B+ annual capital expenditure wall that took decades to build and cannot be replicated quickly even with sovereign backing.

The AI infrastructure buildout is TSMC's most powerful demand driver in its 38-year history. Each NVIDIA GB200 NVL72 rack contains 72 Blackwell GPUs — all TSMC N3/N4. As data center operators race to deploy AI compute, TSMC runs at near-100% utilization on leading-edge nodes with pricing power it has never previously exercised. TTM revenue $119B grew 35.1% YoY — the fastest growth since the smartphone super-cycle.

The margin story is structural, not cyclical. TSMC's net margin has expanded from 38.8% (FY2023 downcycle) to an estimated 42-50% TTM, driven by: (1) N3/N2 process nodes commanding 40-60% price premiums over mature nodes; (2) CoWoS advanced packaging revenue growing from negligible to multi-billion; (3) operating leverage on a fixed-cost-heavy fab model. Unlike IREN (BTC mining margins), TSMC's margin expansion has fundamental roots.

The geopolitical discount is the single most important variable in the model. A Taiwan Strait military confrontation — while not our base case — would be catastrophic: TSMC's fabs cannot be moved and represent irreplaceable global infrastructure. This risk warrants a permanent valuation discount vs a US-based peer with identical fundamentals.

---

## Scenario Analysis

### 🐻 Bear Case (25% weight) — $144.59

Geopolitical escalation (Taiwan Strait tensions escalate to naval blockade or military conflict) or AI capex cycle peak triggers demand shock. Revenue decelerates to 10% CAGR as hyperscalers pause orders. Net margin compresses to 35% as utilization falls and capex commitments create fixed cost drag. Historical trough reference: TSMC FY2023 saw revenue decline -3.8% in the PC/smartphone downcycle; AI cycle could follow a similar pattern 2027-2028.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 10% | Demand shock + AI capex moderation |
| Year 5 Revenue | $191.7B | From $119B at 10% CAGR |
| Net Margin (Yr 5) | 35% | Below-TTM; utilization compression |
| Exit P/E | 18x | Below semiconductor median; cycle trough |
| Quality Multiplier | 1.0 | Geopolitical discount normalizes moat value |
| Share Change | 0%/yr | Stable share count |
| **Year 5 EPS** | **$12.94** | — |
| **Year 5 Price** | **$232.86** | — |
| **Present Value** | **$144.59** | — |

### ⚖️ Base Case (45% weight) — $394.48

AI infrastructure demand sustains at moderated pace. TSMC ramps N2 and A16 nodes 2026-2028, maintaining 90%+ leading-edge market share. Revenue CAGR decelerates naturally from 35% to 18% as base grows. Net margin 44% sustained by N2 pricing power, partly offset by CoWoS capacity capex amortization. No major geopolitical disruption.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 18% | Deceleration from 35% peak; AI sustains |
| Year 5 Revenue | $272.3B | From $119B at 18% CAGR |
| Net Margin (Yr 5) | 44% | Near TTM; N2 pricing partially offset by capex |
| Exit P/E | 25x | Semiconductor median for secular growth leader |
| Quality Multiplier | 1.1 | Process monopoly: sole volume sub-3nm manufacturer |
| Share Change | 0%/yr | Minimal dilution/buyback activity |
| **Year 5 EPS** | **$23.10** | — |
| **Year 5 Price** | **$635.31** | — |
| **Present Value** | **$394.48** | — |

### 🚀 Bull Case (30% weight) — $800.19

**Catalyst**: Sovereign AI buildout — US CHIPs Act fab construction, EU AI infrastructure mandates, Japan/Middle East government AI programs — drives TSMC to extraordinary multi-year utilization with advance purchase agreements. Advanced packaging (CoWoS, SoIC) becomes a profit center rivaling foundry margins. TSMC Arizona/Japan fabs begin contributing to diversified revenue while maintaining monopoly status.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 25% | Sovereign AI + sustained hyperscaler demand |
| Year 5 Revenue | $363.3B | From $119B at 25% CAGR |
| Net Margin (Yr 5) | 50% | Full-utilization pricing power on advanced nodes |
| Exit P/E | 32x | Growth semiconductor premium; near benchmark growth P/E |
| Quality Multiplier | 1.15 | Two moats: (1) sub-3nm process monopoly; (2) hyperscaler lock-in (NVIDIA/AMD/Apple multi-year sole-source commitments) |
| Share Change | 0%/yr | — |
| **Year 5 EPS** | **$35.02** | — |
| **Year 5 Price** | **$1,288.72** | — |
| **Present Value** | **$800.19** | — |

---

## Valuation Math

| Scenario | PV | Weight | Contribution |
|----------|-----|--------|-------------|
| Bear | $144.59 | 25% | $36.15 |
| Base | $394.48 | 45% | $177.52 |
| Bull | $800.19 | 30% | $240.06 |
| **Weighted FV** | | **100%** | **$453.72** |

**Current price**: $397.67 | **Upside**: **+14.1%** | **Action**: **HOLD**
**Buy target**: ~$320-350 (base case provides 13-23% margin of safety)

---

## Key Risks

1. **Geopolitical tail risk (Taiwan Strait)**: A military confrontation would make TSMC's fabs inaccessible regardless of fundamentals. This is an uninsurable, unquantifiable tail risk that justifies holding less than full position sizing for non-Taiwan-resident investors.
2. **AI capex cycle peak**: The current extraordinary AI infrastructure buildout is partly competitive/FOMO-driven among hyperscalers. A pause or cutback in AI capex (as happened with telecom capex in 2001) would hit TSMC utilization hard given front-loaded capacity investments.
3. **Intel Foundry/Samsung resurgence**: Both competitors are investing tens of billions to close the process gap. While 3+ years behind on yield and throughput, government subsidies (US CHIPS Act, EU Chips Act, Samsung's Korea subsidies) could accelerate catch-up on 2nm tier by 2028-2029.
4. **Customer concentration**: NVIDIA, Apple, AMD likely represent 60%+ of N3/N2 revenue. A NVIDIA demand shock (export controls deepening, competitive disruption from Google TPU/Amazon Trainium) would disproportionately impact TSMC.
5. **Currency / data quality**: All financial data in NT$ with currency conversion creating uncertainty. No analyst estimates or historical arrays available from API — confidence in DCF inputs is lower than typical.

---

## What To Watch
- **Quarterly revenue guidance**: Each quarter TSMC guides to ±2% — above-consensus guides are the primary re-rating catalyst
- **CoWoS capacity expansion announcements**: Advanced packaging is becoming as important as foundry margin-wise
- **Intel 18A yield updates**: If Intel achieves competitive yields by 2027, market share risk becomes real
- **Taiwan Strait military developments**: Any escalation is an immediate SELL trigger for risk management
- **N2 customer qualification**: Apple iPhone 18 will be first major N2 device — successful qualification = bull catalyst

---

## Comparables

| Company | P/E | P/S | Net Margin | Notes |
|---------|-----|-----|------------|-------|
| TSM (TSMC) | 34x | 17x | ~42-50% | Process monopoly premium |
| ASML | 35x | 12x | ~27% | EUV monopoly; equipment not foundry |
| Samsung Foundry | N/A | ~2x | ~5% | Bundled in Samsung conglomerate; yield issues |
| Intel Foundry | N/A | ~1x | Negative | Pre-revenue external fab; heavily subsidized |
| GlobalFoundries | ~25x | ~3x | ~12% | Mature nodes only; not leading-edge |

TSMC's P/S of 17x reflects its monopoly status on leading-edge manufacturing — no pure-play comparable justifies this multiple except TSMC's unique structural position.

---

## Data Quality & Confidence Score

**Confidence**: 0.58/1.0

**Flags**:
- 🔴 Revenue in raw data was NT$3.81T TWD — patched to $119B USD
- 🔴 No financial history arrays available (revenue/margin/EPS) — yfinance gap for Taiwanese ADRs
- 🔴 No analyst estimates available — growth derivation based on YoY growth + forward P/E trajectory
- ⚠️ P/E-implied net margin (50.7%) exceeds historical GAAP range (38-45%) — used 42% conservative anchor
- ✅ Trailing P/E 34.1x and forward P/E 20.6x are reliable signals for scenario calibration
- ✅ Revenue growth 35.1% YoY is consistent with known TSMC AI demand data
- ✅ Process technology moat is well-documented industry knowledge (no hallucination risk)

---

## Discussion Log
*Session: 2026-05-02 — Replaced same-day Gemini 1.5 Pro (v1, $671.68 BUY). Key corrections: QM recalibrated, growth rates de-risked, currency patched.*

---

## Sources Checked
- Financial data: ✅ fetch_financials.py | Revenue: ⚠️ Currency-patched (TWD→USD) | Net margin: ⚠️ P/E-derived
- Historical arrays: ❌ Unavailable (yfinance ADR gap)
- Analyst estimates: ❌ Unavailable
- Projection: ✅ TSM.json v2 | Research: ✅ TSM_2026-05-02.md
- Benchmarks: ✅ references/valuation-benchmarks.md
- Prior: ✅ v1 Gemini 1.5 Pro — REPLACED (QM, growth rates, currency corrected)

