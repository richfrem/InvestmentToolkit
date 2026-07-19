---
schemaVersion: 1
documentType: generated-research-summary
ticker: "TEM"
generatedAt: "2026-07-19T03:27:19Z"
---

# TEM Canonical Research Summary

*This file is a generated view. Do not edit directly. Authoritative observations are stored in the JSONL event ledger and indexed in `intelligence.sqlite`.*

# Tempus AI (TEM) — Deep-Dive Research Report
**Date**: 2026-05-02 | **Analyst**: Claude Sonnet 4.6 | **Action**: HOLD | **Fair Value**: $53.88 | **Price at Analysis**: $55.00

---

## TL;DR
Tempus AI is a healthcare AI + genomics company growing +83% YoY at P/S 7.76x — the market is pricing this fairly. The prior GPT-5 mini SELL $7.70 was caused by a critical decimal error (growth rates entered as 0.24% instead of 24%), completely invalidating that analysis. With corrected inputs, weighted fair value is **$53.88 HOLD (-2%)**. Great company, right price — wait for a pullback to $40 before buying.

---

## ⚠️ Prior Analysis Correction (Critical)

**Prior model**: GPT-5 mini | **Same day** | **Prior FV**: $7.70 SELL

**Root cause of error**: GPT-5 mini passed `growthRate: 0.24` to the DCF calculator where `0.24` was interpreted as **0.24% CAGR** (not 24%). This caused near-flat revenue ($1.29B → $1.29B) in all scenarios, making every forward EPS near-zero. The $7.70 output is entirely an artifact of this data entry bug — it does not reflect any analytical judgment about TEM's business.

| Parameter | GPT-5 mini (broken) | Sonnet 4.6 (corrected) |
|-----------|--------------------|-----------------------|
| Bear CAGR | 0.08% | 20% |
| Base CAGR | 0.24% | 28% |
| Bull CAGR | 0.40% | 38% |
| **Fair Value** | **$7.70 SELL** | **$53.88 HOLD** |

---

## Company Snapshot

| Metric | Value |
|--------|-------|
| Price | $55.00 |
| Market Cap | $9.87B |
| TTM Revenue | $1.27B |
| Revenue Growth YoY | **+83%** |
| TTM Net Margin | -19.27% |
| Forward P/E | -608x (expected ongoing losses) |
| P/S Ratio | **7.76x** |
| Shares Diluted | 174.4M |
| Sector | Healthcare — Health Information Services |

**Peer P/S benchmarks at comparable growth stage**:
| Company | P/S | Revenue Growth |
|---------|-----|----------------|
| Veeva Systems (early stage) | ~10x | ~35% |
| Doximity | ~8x | ~25% |
| **TEM current** | **7.76x** | **83%** |

TEM is actually *inexpensive* on P/S relative to growth rate. The market isn't paying a premium — it's paying fair value.

---

## Investment Thesis

Tempus AI has built something genuinely hard to replicate: the largest proprietary dataset of de-identified genomic and clinical records (7M+ patients), developed over 10+ years through partnerships with major cancer centers, cardiology practices, and health systems. This dataset underlies two distinct business lines:

**1. Genomics Testing**: Next-generation sequencing for oncology, cardiology, and psychiatry. This is a volume-driven diagnostics business with improving reimbursement dynamics and high switching costs (oncologists don't change their genomic testing partner often — data continuity and clinical workflow integration create inertia).

**2. AI/Data Licensing**: Licensing de-identified clinical data to pharmaceutical companies for drug development, trial design, and patient matching. This is the structurally higher-margin business and the primary driver of the bull case. Pharma companies pay premium prices for real-world clinical data at this scale.

The 83% YoY growth is impressive but requires context: a meaningful portion is acquisition-driven. The question for the base case is what organic growth looks like — which we can't precisely determine from available data, but $1.27B revenue at this growth rate suggests real commercial momentum beyond just inorganic M&A.

At $55 with P/S 7.76x, the market is pricing in a 28% 5-year CAGR that normalizes margins to ~10% over time. This is achievable if pharma data licensing continues growing. The stock is not a compelling buy at this price (only -2% margin of safety) but neither is it a sell.

**Re-entry thesis**: The stock is worth buying on a pullback to $38-42 (bear case provides real margin of safety at that level) or on a bull catalyst (pharma data licensing ARR disclosure, FDA clearance for additional AI diagnostic applications, or major health system partnership announcement).

---

## Scenario Analysis

### 🐻 Bear Case (30% weight) — $2.97

Healthcare AI investment cycle reverses. Epic Systems, Oracle Health, and Microsoft's Azure healthcare AI push commoditize TEM's data advantage by providing comparable analytics capabilities bundled into existing EHR contracts. CMS introduces reimbursement caps on genomic testing for non-oncology indications. M&A-driven revenue growth normalizes to 20% CAGR. GAAP margins reach only 2% by Y5 due to competitive pricing pressure.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 20% | Rapid deceleration from 83%; M&A cycle ends |
| Year 5 Revenue | $3.16B | From $1.27B at 20% CAGR |
| Net Margin (Yr 5) | 2% | Minimal profitability; pricing pressure limits expansion |
| Exit P/E | 18x | Healthcare tech at slow growth; conservative multiple |
| Quality Multiplier | 0.85 | Data moat eroded by EHR incumbents |
| Share Change | +3%/yr | Ongoing dilution for operations and M&A |
| **Year 5 EPS** | **$0.31** | $63.3M NI / 202.1M shares |
| **Year 5 Price** | **$4.79** | — |
| **Present Value** | **$2.97** | — |

### ⚖️ Base Case (45% weight) — $42.28

TEM's clinical data moat delivers sustained platform monetization. Pharma data licensing grows to $500M+ ARR by Y5, becoming the dominant segment with ~60% gross margins. Genomics testing scale delivers operating leverage. Revenue $1.27B → $4.37B at 28% CAGR (deceleration path: 83% → 45% → 30% → 20% → 12%). GAAP margins improve to 10% as software-like data licensing mix increases.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 28% | Realistic deceleration from 83%; pharma licensing drives midpoint |
| Year 5 Revenue | $4.37B | From $1.27B at 28% CAGR |
| Net Margin (Yr 5) | 10% | Data licensing mix + operating leverage |
| Exit P/E | 30x | Healthcare tech with recurring revenue, proven at scale |
| Quality Multiplier | 1.0 | Clinical data moat acknowledged but not exceptional-tier |
| Share Change | +2%/yr | Moderate dilution for ongoing investment |
| **Year 5 EPS** | **$2.27** | $437M NI / 192.5M shares |
| **Year 5 Price** | **$68.10** | — |
| **Present Value** | **$42.28** | — |

### 🚀 Bull Case (25% weight) — $135.87

**Catalyst**: TEM's AI diagnostics platform achieves FDA clearance for cardiology and psychiatry in addition to oncology, creating a new high-margin revenue stream with CMS reimbursement. Pharma data licensing expands to include real-world evidence for regulatory submissions (FDA Real-World Evidence program). TEM becomes the clinical AI OS for major health systems, generating $200M+ ARR in software licensing separate from testing. Revenue scales to $6.37B at 38% CAGR. QM 1.05 citing structural moat: **7M+ de-identified patient records across genomics and longitudinal clinical data is a 10+ year accumulation asset that cannot be replicated by new entrants under current HIPAA frameworks**.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 38% | Sustained by AI diagnostics + pharma + health system SaaS |
| Year 5 Revenue | $6.37B | Three-engine growth: genomics + pharma data + AI platform |
| Net Margin (Yr 5) | 15% | Platform economics + high-margin AI software layer |
| Exit P/E | 40x | Healthcare AI platform premium (Veeva at scale: 40x+) |
| Quality Multiplier | 1.05 | Proprietary data moat: 7M+ patient records, structural barrier |
| Share Change | +1%/yr | Dilution moderates as cash generation improves |
| **Year 5 EPS** | **$5.21** | $954.8M NI / 183.3M shares |
| **Year 5 Price** | **$218.82** | — |
| **Present Value** | **$135.87** | — |

---

## Valuation Math

| Scenario | PV | Weight | Contribution |
|----------|-----|--------|-------------|
| Bear | $2.97 | 30% | $0.89 |
| Base | $42.28 | 45% | $19.03 |
| Bull | $135.87 | 25% | $33.97 |
| **Weighted FV** | | **100%** | **$53.88** |

**Current price**: $55.00 | **Upside/(Downside)**: **-2.0%** | **Action**: **HOLD**
**Buy target**: ~$40 (bear provides margin of safety; -27% from here)

---

## Key Risks

1. **Organic vs. inorganic growth opacity**: The 83% YoY growth rate is likely partially M&A-driven. Without segment-level disclosure of organic revenue growth, the base case deceleration model has meaningful uncertainty. If organic growth is 30-40% and M&A inflated the number, future growth will decelerate faster than modeled.
2. **Healthcare data regulation**: HIPAA amendments, CMS data-sharing rules, or state-level privacy laws could restrict TEM's ability to license de-identified patient data to pharma companies — the highest-margin segment and key to the bull case.
3. **Reimbursement risk**: Genomic testing reimbursement depends on CMS coverage decisions. CMS has historically been cautious about expanding genomic testing coverage, particularly for non-oncology indications. Adverse rulings would compress the testing segment margin.
4. **EHR incumbent response**: Epic and Oracle Health have the existing clinical relationships and data to build competing analytics capabilities. While they lack TEM's AI specialization, a strategic decision by either to prioritize this market would compress TEM's pricing power.
5. **Profitability timeline**: With -19.27% net margin and no analyst estimates, the path to GAAP profitability is unclear. If the company requires ongoing dilutive equity raises to fund losses, the per-share value compounds more slowly than modeled.

---

## What To Watch
- **Pharma data licensing ARR**: Any disclosure of data licensing contract sizes or ARR is the primary bull signal
- **FDA clearance announcements**: Additional AI diagnostic applications beyond oncology are the bull catalyst
- **Organic vs. total growth disclosure**: Management commentary on M&A contribution to growth is key to validating base case
- **Gross margin by segment**: If data licensing gross margins exceed 60%+ it validates premium exit multiple
- **Re-entry level**: $38-42 is the sweet spot where even bear provides reasonable return (vs. current fair valuation)

---

## Data Quality & Confidence Score

**Confidence**: 0.55/1.0

**Flags**:
- 🔴 Prior GPT-5 mini analysis INVALIDATED — decimal/percentage error on growth rates. FV $7.70 SELL was completely wrong.
- ⚠️ No historical financial data from API (arrays null — recent IPO)
- ⚠️ No analyst estimates available
- ⚠️ Organic vs. M&A growth split unknown
- ✅ 83% YoY growth confirmed (not a small-cap speculation)
- ✅ P/S 7.76x — not overvalued on growth-adjusted basis
- ✅ Clinical data moat is real and well-documented (7M+ patients, major health system partnerships)

---

## Discussion Log
*Session: 2026-05-02 — Replaced same-day GPT-5 mini (v1, $7.70 SELL — INVALID). No Q&A appended.*

---

## Sources Checked
- Financial data: ✅ fetch_financials.py | Historical arrays: ❌ Null (recent IPO limitation)
- Analyst estimates: ❌ Unavailable
- Projection: ✅ TEM.json v2 | Research: ✅ TEM_2026-05-02.md
- Benchmarks: ✅ references/valuation-benchmarks.md
- Prior: ✅ v1 GPT-5 mini — REPLACED (decimal error invalidated entire analysis)

