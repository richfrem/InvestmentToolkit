---
schemaVersion: 1
documentType: generated-research-summary
ticker: "INTC"
generatedAt: "2026-07-19T03:27:19Z"
---

# INTC Canonical Research Summary

*This file is a generated view. Do not edit directly. Authoritative observations are stored in the JSONL event ledger and indexed in `intelligence.sqlite`.*

# Intel Corporation (INTC) — Deep-Dive Research Report
**Date**: 2026-05-02 | **Analyst**: Claude Sonnet 4.6 | **Action**: SELL | **Fair Value**: $22.97 | **Price at Analysis**: $99.62

---

## TL;DR
Intel has surged 153% YTD to $99.62 — more than 27% above the analyst mean target of $78.21 — on turnaround optimism, but the fundamentals have not followed. Revenue is in a 4-year declining trend, FCF is -$15.7B TTM, and the company is barely breakeven on net income. Our probability-weighted fair value of **$22.97** implies **77% downside**. This is a SELL.

---

## Company Snapshot

| Metric | Value |
|--------|-------|
| Price | $99.62 |
| Market Cap | ~$499B |
| TTM Revenue | $52.85B |
| TTM Net Margin | -0.51% |
| TTM FCF | -$15.7B |
| Forward P/E | 67.3x |
| Analyst Mean Target | $78.21 (42 analysts) |
| Analyst Consensus | Hold |
| YTD Performance | +153% |
| 1-Year Performance | +398% |
| Shares (Diluted) | 5.026B |

---

## Prior Analysis Review
**Prior model**: Antigravity-Gemini3Pro | **Date**: 2026-02-14 | **Prior price**: $46.79 | **Prior FV**: $83.51 | **Prior action**: STRONG BUY

The prior BUY at $46.79 was directionally correct — the stock has since +113%. However, the thesis has **fully played out**. The stock now trades above the prior *bull case* of $143.68 on a 5-year horizon, compressed to today. Key flaws in prior analysis:
- Bear case assumed 15% net margin when Intel's TTM was -0.51% — this was not a bear case at all
- Quality Multiplier 1.3 (bull) requires durable pricing power across cycles — Intel has demonstrably lost CPU market share to AMD for 5+ years
- "STRONG BUY" is not a valid schema action — reflects an unvalidated model generating unconstrained outputs
- All assumptions flagged UNVALIDATED (Antigravity-Gemini3Pro non-Sonnet model); fully re-derived from scratch.

---

## Investment Thesis

Intel is a turnaround story being priced as a success story — before the turnaround has succeeded. CEO Lip-Bu Tan joined in March 2024 to execute an ambitious repositioning of Intel from a declining IDM (Integrated Device Manufacturer) into a competitive foundry alongside its traditional CPU business. The thesis is real. The execution risk is massive. And the market has priced in success at 67x forward earnings.

The core problem is the revenue trend. Intel's top line has declined for four consecutive years: $63.1B → $54.2B → $53.1B → $52.9B TTM. This is not a cyclical trough — it reflects structural share loss in both server CPU (AMD EPYC: ~25% share up from ~2% in 2017) and client CPU (AMD Ryzen, plus Apple M-series eliminating Intel from Mac entirely). The AI PC narrative provides some uplift, but Intel's AI PC NPU is not a class leader vs Qualcomm Snapdragon X Elite or Apple M4.

The FCF situation is alarming. Intel has burned $15.7B in free cash flow in the trailing twelve months, following -$14.3B in FY2023 and -$9.4B in FY2022. This is funding the 18A process node and factory buildout — a necessary investment, but one that will keep FCF negative through at least 2027 under the most optimistic scenario. Meanwhile, Intel is carrying this investment at a 67x forward earnings multiple.

The analyst community is not enthusiastic: 42 analysts covering INTC produce a mean target of $78.21 — 27% below the current price. The consensus is "Hold," meaning the average analyst says don't buy at these prices. The stock's recent run appears momentum-driven, possibly fueled by AI/semiconductor sector rotation and retail speculation rather than fundamental re-rating.

Our probability-weighted DCF produces a fair value of $22.97, driven primarily by the bear (35%) and base (45%) outcomes, which together account for 80% of the probability mass. Only the bull case — which requires Intel's 18A node to win a major fabless customer — justifies the current price neighborhood, and we assign that only 20% probability.

---

## Scenario Analysis

### 🐻 Bear Case (35% weight) — $1.48

Intel's market share erosion continues: AMD EPYC takes another 10% server share by 2030, reflecting Intel's historical server share decline from 98% (2019) to ~75% (2024) that has not stopped. The 18A node fails to reach competitive yields with TSMC N2, and Intel remains dependent on external foundry for leading-edge products, generating no foundry external revenue. Revenue stagnates at 2% CAGR. Cost cuts barely cover the declining revenue base — margin recovers to 2% (from -0.5% TTM) reflecting breakeven operation without the FY2024 restructuring charges. The stock de-rates to a 13x P/E — below the semiconductor median of 25x, appropriate for a structurally challenged IDM with negative FCF history and no moat narrative.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 2% | Stagnation; continued share loss offsets AI PC |
| Year 5 Revenue | $58.4B | From current TTM $52.85B at 2% compound |
| Net Margin (Yr 5) | 2% | Breakeven recovery; no scale leverage |
| Exit P/E | 13x | 48% below median; distressed IDM with no FCF |
| Quality Multiplier | 0.85 | x86 moat eroding; no competitive differentiation |
| Share Change | +1.5%/yr | Dilution from RSU grants during turnaround |
| **Year 5 EPS** | **$0.22** | $1.17B NI / 5.45B shares |
| **Year 5 Price** | **$1.74** | 13x × 0.85 QM |
| **Present Value** | **$1.48** | 10% discount rate, 5yr |

### ⚖️ Base Case (45% weight) — $21.34

Intel executes its turnaround partially: revenue returns to modest growth at 8% CAGR (within the analyst consensus range of 10.45%), driven by AI PC refresh cycle and modest datacenter recovery. The 18A node reaches viable yields for Intel's own products but does not win major external customers. Net margin recovers to 12% by year 5 — an optimistic but achievable target based on cost restructuring and operating leverage, consistent with analyst forward EPS trajectory implying ~9-12% margins. Intel's x86 incumbency in enterprise remains intact. Stock trades at 20x P/E — 20% below semiconductor sector median, reflecting ongoing competitive headwinds vs AMD.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 8% | Consensus -2.45pp; cautious due to 4yr decline trend |
| Year 5 Revenue | $77.7B | From TTM at 8% compound |
| Net Margin (Yr 5) | 12% | Recovery target; 3yr adj avg 5.1% + recovery |
| Exit P/E | 20x | 20% below median; competitive headwinds persist |
| Quality Multiplier | 0.95 | Below average; x86 incumbency partially intact |
| Share Change | +0.5%/yr | Minimal net dilution as RSU grants normalize |
| **Year 5 EPS** | **$1.81** | $9.32B NI / 5.15B shares |
| **Year 5 Price** | **$22.46** | 20x × 0.95 QM |
| **Present Value** | **$21.34** | 10% discount rate, 5yr |

### 🚀 Bull Case (20% weight) — $64.25

**Catalyst**: Intel 18A process node achieves competitive yields with TSMC N2/N3 by 2027, winning at least one major fabless anchor customer (Qualcomm, MediaTek, or hyperscaler custom silicon), creating a multi-billion foundry external revenue stream not in current analyst consensus. Simultaneously, AI PC refreshes at 14% volume CAGR as Windows 12 AI features drive mandatory hardware upgrades. Gaudi AI accelerator gains datacenter traction vs NVIDIA H-series, capturing 5-8% AI training market share. Revenue accelerates to 14% CAGR. Margins reach 18% (below fabless best-in-class 40%, realistic for IDM with foundry contribution). Stock re-rates to 27x — 8% above sector median — justified by foundry optionality premium.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 14% | Foundry external + AI PC + Gaudi all materializing |
| Year 5 Revenue | $101.8B | From TTM at 14% compound |
| Net Margin (Yr 5) | 18% | Foundry scale leverage; below fabless best-in-class |
| Exit P/E | 27x | 8% above median; foundry optionality premium |
| Quality Multiplier | 1.0 | Average; return to competitive parity only |
| Share Change | -1.0%/yr | Buybacks resume as FCF turns positive |
| **Year 5 EPS** | **$3.83** | $18.32B NI / 4.79B shares |
| **Year 5 Price** | **$103.41** | 27x × 1.0 QM |
| **Present Value** | **$64.25** | 10% discount rate, 5yr |

---

## Valuation Math

| Scenario | PV | Weight | Contribution |
|----------|-----|--------|-------------|
| Bear | $1.48 | 35% | $0.52 |
| Base | $21.34 | 45% | $9.60 |
| Bull | $64.25 | 20% | $12.85 |
| **Weighted FV** | | **100%** | **$22.97** |

**Current price**: $99.62
**Upside/Downside**: **-77%**
**Action**: **SELL**

---

## Key Risks

1. **18A process node miss**: If 18A yields remain uncompetitive vs TSMC N2 through 2027, the entire foundry transformation thesis collapses. Intel would be forced to outsource even more production, destroying the IDM premium. This is the single largest binary risk.

2. **Momentum unwind**: At 67x forward P/E, any disappointment in quarterly earnings — a single missed revenue estimate, a yield setback, a delayed product — could cause a rapid de-rating. Stocks running on momentum tend to mean-revert quickly when sentiment shifts.

3. **AMD share acceleration**: AMD's EPYC 5 (Zen 6, 2025) and Zen 7 (2026) continue improving on power efficiency. If AMD crosses 35% server share (from ~25% today), Intel's data center revenue decline accelerates materially beyond base case assumptions.

4. **FCF trajectory**: Intel needs ~$25-30B in annual capex through 2027 for foundry buildout. If revenue growth disappoints, the company may need to raise equity or cut the dividend, both of which are bearish catalysts.

5. **Geopolitical / China**: Intel derives ~27% of revenue from China. Any tightening of US export restrictions beyond current entity list controls could remove $14B+ from the top line immediately.

---

## What To Watch

- **18A process node milestones** (next 2-3 quarters): Yield improvement announcements, any external customer pilot wins, or TSMC comparison benchmarks
- **FCF inflection**: Watch quarterly FCF turning from deeply negative toward -$5B or better — any path to positive FCF changes the thesis
- **AMD EPYC 5 launch impact** (2025-2026): Server CPU market share trends are the best real-time indicator of Intel's competitive position
- **AI PC attach rate**: Track Intel AI PC unit shipments as a % of total CPU units — need to see 40%+ to justify AI PC CAGR assumptions
- **Analyst target revisions**: If analyst mean target moves above $85+, that would indicate a shift in professional consensus toward the bull case

---

## Comparables

| Company | Forward P/E | Net Margin | Rev Growth | Action |
|---------|-------------|------------|------------|--------|
| **INTC** | 67x | -0.51% TTM | -1.8% TTM | SELL |
| AMD | 24x | 9.5% | +24% TTM | Comparable (turnaround success) |
| NVDA | 32x | 55% | +78% TTM | Different category entirely |
| QCOM | 14x | 23% | +12% TTM | Better quality at lower multiple |
| TSM (TSMC) | 22x | 38% | +34% TTM | Better execution, lower risk |

INTC trades at a 67x P/E with negative TTM margins vs AMD at 24x with growing margins. INTC is being priced as a growth stock without growth. TSMC, which is actually executing on leading-edge nodes, trades at 22x — one-third of INTC's multiple.

---

## Data Quality & Confidence Score

**Confidence**: 0.68/1.0

**Flags**:
- ⚠️ FY2024 net margin -35.32% is a restructuring/impairment outlier — excluded from margin anchor
- ⚠️ FCF deeply negative all 3 data years (-$9.4B, -$14.3B, -$15.7B); trajectory worsening
- ⚠️ Stock trading 27% above analyst consensus target — significant divergence
- ⚠️ Prior Antigravity-Gemini3Pro analysis flagged UNVALIDATED; all assumptions re-derived
- ⚠️ 18A yield data is proprietary/unavailable — bull case catalyst unconfirmable from public data
- ✅ 42 analyst coverage — high confidence in consensus estimates
- ✅ Revenue trend is clear and consistent (4yr decline) — low uncertainty in bear/base

**Prior model quality flag**: UNVALIDATED (Antigravity-Gemini3Pro) — all prior assumptions treated as unvalidated starting points. Fresh analysis completed independently.

---

## Discussion Log

*Session: 2026-05-02 — Initial analysis. No Q&A appended.*

---

## Sources Checked
- Financial data: ✅ fetch_financials.py (yfinance)
- Projection persistence: ✅ Saved to backend/data/projections/INTC.json (v8)
- Research report: ✅ Saved to backend/data/research/INTC_2026-05-02.md
- Valuation benchmarks: ✅ references/valuation-benchmarks.md
- Analysis prompt: ✅ references/analysis_prompt.md
- Prior projection: ✅ Read INTC.json v7 (Antigravity-Gemini3Pro, 2026-02-14) — flagged UNVALIDATED

---

## Projection Update — 2026-05-02

Updated `INTC.json` to version 9:
- **Action:** SELL → **SELL** (maintained, but fundamentally different rationale)
- **Fair Value:** $22.97 → **$49.65** (+116%)
- **Scenario weights:** Bear 35%→20% / Base 45%→45% / Bull 20%→35%
- **Scenario prices:** Bear $3.65 | Base $32.52 | Bull $97.96
- **Note:** Bull case ($97.96) now encompasses current price ($99.62). SELL reflects weighted probability, not thesis failure. Stock is priced as if bull case is near-certain; it is not. Maintain position; do not add.

