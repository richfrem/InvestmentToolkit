---
ticker: AMD
name: AI Deep Dive — AMD — 2026-05-02
lastUpdated: 2026-05-02T23:05:00Z
fairValue: 352.63
priceAtAnalysis: 360.54
action: MAINTAIN
---

# AMD Canonical Research History

## Research Sweep — 2026-05-02
**Date**: 2026-05-02 | **Analyst**: Claude Sonnet 4.6 | **Action**: SELL | **Fair Value**: $320.12 | **Price at Analysis**: $360.54

---

## TL;DR
AMD is one of the best-executed semiconductor turnarounds in history — EPYC now holds ~25% server CPU share and MI300 AI GPUs generated $5B+ in 2024. But at $360 (32x forward P/E), the stock is pricing in a scenario that sits between our base and bull cases. Our weighted fair value is **$320.12 (-11%)** — a SELL, not because the company is failing, but because the risk/reward at current prices is slightly unfavorable. Watch for re-entry below $280.

---

## Prior Analysis Review
**Prior model**: Gemini 3 Pro (UNVALIDATED) | **Date**: 2026-05-02 | **Same day replacement**

Prior BUY FV $443 contained a critical flaw: **bear case used 18% net margin when TTM was 12.52%** — the bear scenario modeled margin *expansion*, not downside risk. This single error inflated bear PV and dragged the weighted average higher. Additionally, bull QM 1.2 = "exceptional durable pricing power across cycles" — that tier belongs to NVIDIA (CUDA monopoly), not AMD. All assumptions re-derived from scratch.

---

## Company Snapshot

| Metric | Value |
|--------|-------|
| Price | $360.54 |
| Market Cap | $587.8B |
| TTM Revenue | $34.64B |
| TTM Net Margin | 12.52% |
| TTM FCF | $6.74B |
| Gross Margin | 49.5% |
| Forward P/E | 32.4x |
| Analyst Data | Unavailable (API gap) |
| YoY Revenue Growth | +34.1% |
| Shares (Diluted) | 1.630B |

---

## Investment Thesis

AMD has earned its premium multiple through exceptional execution. CEO Lisa Su led one of the most successful semiconductor turnarounds ever: EPYC went from 0% to ~25% server CPU share in 7 years, and MI300X achieved $5B+ annual revenue in its first full year. These are real competitive wins backed by genuine architectural advantages (chiplet design, power efficiency leadership).

The bear case is not about AMD failing — it's about NVIDIA succeeding. CUDA's software ecosystem has a decade-long head start and the switching costs are massive: every AI researcher knows PyTorch/CUDA, every cloud provider has CUDA-optimized infrastructure, and NVIDIA's NVLink fabric has no equivalent. ROCm is improving, but "improving" is not "parity." The bear case (30% weight) assumes AMD remains largely locked out of AI training workloads and faces Intel recapturing some EPYC share with 18A process improvements.

The base case (45% weight) is AMD continuing to execute — EPYC crossing 30%+ server share, MI300 and successors capturing 15-20% of the AI inference/cost-sensitive training market, and net margins improving from 12.5% TTM toward 20% as the data center revenue mix rises. FCF of $6.7B confirms the unit economics are already working. The base case fair value of $254 is 30% below the current price.

The bull case (25% weight) requires ROCm software parity with CUDA — specifically the ability to run large-scale AI training workloads with comparable developer experience. If this materializes (and AMD's roadmap suggests Q3-Q4 2026 is a plausible target), AMD could capture meaningful AI training share and re-rate toward 38x+ multiples. Fair value in that scenario: $776.

At $360, the stock is essentially pricing in ~70% of the bull case probability, which is not justified at 25% weight. Re-entry below $280 provides a better risk/reward.

---

## Scenario Analysis

### 🐻 Bear Case (30% weight) — $39.90

CUDA lock-in proves insurmountable for AI training workloads. MI-series GPUs remain an inference niche while NVIDIA Blackwell/Rubin dominates training. Intel's 18A process node recovers enough to slow EPYC's share gains. AI capex normalizes by 2027-2028, reducing total addressable market for data center GPUs. Revenue decelerates to 15% CAGR. Net margin compresses to **10%** — below current TTM 12.52% — as AMD spends heavily on R&D to chase NVIDIA without commensurate revenue share. Exit at 18x P/E (below median) with 0.90 QM.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 15% | Deceleration; AI GPU niche, EPYC growth slows |
| Year 5 Revenue | $69.7B | From $34.6B TTM at 15% |
| Net Margin (Yr 5) | 10% | Below TTM — R&D spend without share gains |
| Exit P/E | 18x | Below median; NVIDIA dominance structural |
| Quality Multiplier | 0.90 | Weakening competitive position in AI |
| Share Change | +1.5%/yr | RSU grants, no buyback capacity |
| **Year 5 EPS** | **$3.97** | $6.97B NI / 1,756M shares |
| **Year 5 Price** | **$64.26** | 18x × 0.90 QM |
| **Present Value** | **$39.90** | 10% discount rate, 5yr |

### ⚖️ Base Case (45% weight) — $253.84

AMD continues executing: EPYC reaches 30%+ server share, MI300 successors capture inference market and cost-sensitive training workloads. ROCm improves but CUDA parity remains elusive. Revenue grows at 28% CAGR as data center revenue mix expands. Net margins improve from 12.5% TTM to 20% via product mix shift to higher-ASP data center GPUs and operating leverage on fixed R&D. Exit at semiconductor median 28x.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 28% | Deceleration from 34%; AI ramp continuation |
| Year 5 Revenue | $119.0B | From $34.6B TTM at 28% |
| Net Margin (Yr 5) | 20% | +7.5pp from TTM via data center mix shift |
| Exit P/E | 28x | Semiconductor median; consistent execution |
| Quality Multiplier | 1.0 | Average quality; EPYC moat limited across cycles |
| Share Change | 0%/yr | Buybacks offset RSU grants |
| **Year 5 EPS** | **$14.60** | $23.8B NI / 1,630M shares |
| **Year 5 Price** | **$408.81** | 28x × 1.0 QM |
| **Present Value** | **$253.84** | 10% discount rate, 5yr |

### 🚀 Bull Case (25% weight) — $775.67

**Catalyst**: ROCm software ecosystem reaches CUDA parity for AI inference and training workloads (Q3-Q4 2026 roadmap target), enabling AMD MI400 to win 2+ major hyperscaler training contracts away from NVIDIA. EPYC Turin (Zen 5) crosses 35% server CPU market share. Data center revenue mix reaches 60%+ of total. Net margins approach 28% (fabless-optimized, Qualcomm-comparable). AMD re-rates toward 38x as it becomes a credible #2 AI accelerator platform.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 38% | ROCm parity + EPYC dominance + MI400 wins |
| Year 5 Revenue | $173.4B | From $34.6B TTM at 38% |
| Net Margin (Yr 5) | 28% | Fabless optimization; data center-dominant mix |
| Exit P/E | 38x | Premium; approaching NVIDIA-tier for AI platform |
| Quality Multiplier | 1.05 | Limited emerging moat via ROCm ecosystem |
| Share Change | -1%/yr | Buybacks as FCF expands |
| **Year 5 EPS** | **$31.31** | $48.5B NI / 1,550M shares |
| **Year 5 Price** | **$1,249.22** | 38x × 1.05 QM |
| **Present Value** | **$775.67** | 10% discount rate, 5yr |

---

## Valuation Math

| Scenario | PV | Weight | Contribution |
|----------|-----|--------|-------------|
| Bear | $39.90 | 30% | $11.97 |
| Base | $253.84 | 45% | $114.23 |
| Bull | $775.67 | 25% | $193.92 |
| **Weighted FV** | | **100%** | **$320.12** |

**Current price**: $360.54
**Upside/Downside**: **-11.2%**
**Action**: **SELL**
**Re-entry target**: ~$280 (base case entry with 10% margin of safety)

---

## Key Risks

1. **CUDA moat**: NVIDIA's software ecosystem is the strongest moat in semiconductors. Every AI engineer, every cloud provider, every MLOps tool is optimized for CUDA. ROCm closing this gap requires not just performance parity but ecosystem equivalence — a much harder problem.

2. **NVIDIA Rubin (2026-2027)**: NVIDIA's next-gen architecture will likely maintain a 2-generation performance lead. AMD would need MI400+ to match Blackwell's throughput before Rubin launches.

3. **Valuation compression risk**: At 32x forward P/E, any guidance miss — even modest — could cause a 15-20% multiple compression. AMD is priced for perfect execution.

4. **Intel 18A wildcard**: If Intel's foundry transition succeeds, a revitalized Intel could slow AMD's EPYC share gains in server CPU from 2027 onward.

5. **No analyst estimates in API**: Growth anchored to TTM 34.1% YoY with internal deceleration model. If consensus is materially different, base case CAGR may need revision.

---

## What To Watch

- **ROCm adoption metrics**: Developer downloads, GitHub stars, cloud provider support pages — leading indicators of CUDA gap closure
- **MI300/MI400 revenue quarterly run rate**: Need to see $6B+ quarterly to justify bull case multiple re-rating
- **EPYC server CPU share** (next IDC/Mercury report): 30%+ is bull territory; any reversal below 22% is bear
- **Gross margin trend**: Holding above 49% indicates favorable data center product mix; dipping below 47% is a warning
- **Re-entry price**: Below $280 gives sufficient margin of safety for the base case

---

## Comparables

| Company | Forward P/E | Net Margin | Rev Growth | CUDA equivalent | Notes |
|---------|-------------|------------|------------|----------------|-------|
| **AMD** | 32x | 12.5% | +34% | ROCm (improving) | SELL FV $320 |
| NVDA | ~32x | 55% | +78% | CUDA (dominant) | Different tier entirely |
| QCOM | 14x | 23% | +12% | N/A | Better value, less upside |
| INTC | 67x | -0.5% | -1.8% | N/A | SELL — worse fundamentals |
| Broadcom | 28x | 35% | +22% | N/A | Better margin quality |

AMD trades at parity with NVIDIA on forward P/E despite massively inferior margins (12.5% vs 55%) and inferior AI GPU market position. The premium is forward-looking — and largely priced in.

---

## Data Quality & Confidence Score

**Confidence**: 0.65/1.0

**Flags**:
- ⚠️ No API analyst estimates (yfinance gap for AMD — unusual for large-cap; growth anchored to TTM YoY only)
- ⚠️ FY2023 margin outlier (3.77%) — cyclical PC crash; excluded from trend analysis
- ⚠️ Historical revenue has a leading zero (FY2021 unavailable in API)
- ⚠️ Prior Gemini 3 Pro analysis: critical bear margin error (18% > 12.5% TTM), QM 1.2 unjustified — UNVALIDATED
- ✅ FCF positive and growing ($6.7B TTM) — strong fundamental signal
- ✅ Gross margin consistent improvement (44.9% → 49.5%) — 4yr trend
- ✅ Business quality is high — uncertainty is about valuation, not company

---

## Discussion Log
*Session: 2026-05-02 — Initial Sonnet 4.6 analysis. Replaced same-day Gemini 3 Pro analysis (v3). No Q&A appended.*

---

## Sources Checked
- Financial data: ✅ fetch_financials.py (yfinance)
- Analyst estimates: ⚠️ Empty (API gap — unusual for AMD)
- Projection persistence: ✅ Saved to backend/data/projections/AMD.json (v4)
- Research report: ✅ Saved to backend/data/research/AMD_2026-05-02.md
- Valuation benchmarks: ✅ references/valuation-benchmarks.md
- Prior projection: ✅ Read AMD.json v3 (Gemini 3 Pro, same day) — UNVALIDATED, critical errors documented

