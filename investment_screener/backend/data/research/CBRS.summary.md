---
schemaVersion: 1
documentType: generated-research-summary
ticker: "CBRS"
generatedAt: "2026-07-19T03:27:19Z"
---

# CBRS Canonical Research Summary

*This file is a generated view. Do not edit directly. Authoritative observations are stored in the JSONL event ledger and indexed in `intelligence.sqlite`.*

# Cerebras Systems (CBRS) — Deep-Dive Research Report
**Date**: 2026-05-21 | **Analyst**: Antigravity | **Action**: BUY | **Fair Value**: $342.80 | **Price**: $287.30

## TL;DR
Cerebras Systems Inc. (CBRS) has completed its highly anticipated IPO, introducing a paradigm-shifting wafer-scale architecture that addresses the core interconnect and memory bandwidth bottlenecks in modern artificial intelligence clusters. At its current price of $287.30, our multi-scenario DCF model indicates a weighted fair value of **$342.80** (representing 19.3% upside), making it a high-conviction **BUY**. However, this investment is not for the faint of heart: we advise holding-period discipline to navigate extreme customer concentration in the United Arab Emirates (G42/MBZUAI) and upcoming dilutive warrants and lockup expiry overhangs.

---

## Prior Analysis Review
**Prior**: None (Initial Public Coverage post-IPO in May 2026).

---

## Company Snapshot
| Metric | Value | Detail / Notes |
|--------|-------|----------------|
| **Current Price** | $287.30 | |
| **Basic Market Cap** | ~$9.91B | Based on Class A float shares (34.5M) |
| **Fully Diluted Market Cap** | ~$89.7B | Based on fully-converted share structure (~312.2M shares) |
| **TTM Revenue** | $510.0M | Strong growth (+75.7% YoY from $290.3M in FY2024) |
| **GAAP Net Income** | $237.8M | Highly inflated by a **$363M one-time accounting gain** |
| **Adjusted Net Loss** | -$76.0M | Core operations remain cash-burning |
| **Operating Loss** | -$146.0M | Reflects high R&D and scaling costs |
| **Capex Burn** | $400.0M | Large ongoing data center build-outs |
| **War Chest** | ~$1.7B | $700M cash + $1.0B credit facility from OpenAI |
| **Backlog** | ~$24.6B | Anchored by OpenAI ($20.0B through 2029) |
| **Class A Float Shares** | 34.5M | Model anchor for per-share calculations |

> [!CAUTION]
> **The GAAP Earnings Mirage**:
> On paper, Cerebras appears highly profitable in 2025 with $237.8M in net income. However, this includes a **$363M one-time, non-cash financial gain** from unwinding preferred stock contracts during IPO restructuring. Excluding this paper adjustment, Cerebras posted a **core adjusted net loss of -$76M** and an **operating loss of -$146M**. The underlying business continues to burn cash rapidly.

---

## Wafer-Scale Engine: The Strategic Monolithic Bet
For 75 years, the semiconductor industry operated under a single dogma: *chips must be small to optimize yield.* NVIDIA's high-end Blackwell B200 die size is roughly 740 mm² (about the size of a postage stamp). 

Cerebras completely disrupts this by turning a whole silicon disc into a single massive chip: the **Wafer-Scale Engine 3 (WSE-3)**.
* **Plate vs. Stamp**: WSE-3 has a die size of over 46,000 mm²—over 60 times larger than B200.
* **AI Core Density**: Packages 900,000 AI compute cores (44x more than B200).
* **Interconnect Speed**: Eliminates board-level cables and switches, enabling data movement at **21 PB/s** (2,600x faster memory bandwidth than B200).
* **Inference Leadership**: WSE-3 runs Meta's Llama 4 and Llama 3 models at **2,100 to 2,500 tokens per second**, roughly 2.4x faster than B200, making it the premier choice for real-time agentic workflows and multi-step reasoning models.

---

## Scenario Analysis

### 🐻 Bear Scenario (35% Probability) — Present Value: $36.12
**Thesis**: High customer concentration remains unmitigated, yields on wafer-scale packaging at TSMC plateau, and NVIDIA's Blackwell/Rubin architectures combined with hyperscaler in-house ASICs commoditize high-throughput inference. 
* **Quality Multiplier (QM)**: 1.0 (moat eroded by alternatives, high switching costs for legacy CUDA software prevent scaling).
* **Dilution**: 2.0% annual dilution.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| **5-yr CAGR** | 15.0% | Customer churn/concentration risk stalls out sales |
| **Year 5 Revenue** | $1,025.8M | Represents modest scaling to legacy backlog |
| **Net Margin** | 12.0% | Gross margins compress to utility semiconductor levels |
| **Exit P/E** | 18.0x | Standard hardware exit multiple |
| **Year 5 EPS** | $3.23 | Reflected on 38.1M projected shares |
| **Year 5 Price** | $58.17 | Undiscounted terminal price |
| **Present Value** | **$36.12** | Discounted at 10.0% over 5 years |

### ⚖️ Base Scenario (45% Probability) — Present Value: $323.07
**Thesis**: Landmark agreements with OpenAI ($20B backlog) and Amazon Web Services (Amazon Bedrock integration) successfully scale and diversify the customer base away from G42. Decelerates current hypergrowth naturally to a sustainable baseline while WSE-3 margins improve as cloud utilization increases.
* **Quality Multiplier (QM)**: 1.1 (Justified by WSE-3 switching costs—replacing a wafer-scale array requires completely rewriting low-level inference compilers, creating a strong customer lock-in).
* **Dilution**: 1.0% annual dilution.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| **5-yr CAGR** | 35.0% | Deceleration from TTM 75.7% growth as AWS/OpenAI scale |
| **Year 5 Revenue** | $2,286.8M | AWS distribution channels capture massive mid-market inference |
| **Net Margin** | 25.0% | Fabless operational leverage matures as cloud services scale |
| **Exit P/E** | 30.0x | Reflects moderate premium for structural switching costs |
| **Year 5 EPS** | $15.77 | Reflected on 36.3M projected shares |
| **Year 5 Price** | $520.31 | Undiscounted terminal price |
| **Present Value** | **$323.07** | Discounted at 10.0% over 5 years |

### 🚀 Bull Scenario (20% Probability) — Present Value: $923.88
**Thesis**: Cerebras becomes the absolute benchmark for frontier agentic and reasoning models. Monolithic integration is recognized as the only path to bypass the physical scaling limits of traditional GPU clusters. AWS and OpenAI exercise maximum contract capacity, and other hyperscalers are forced to adopt WSE-3 to compete on token-per-second performance.
* **Quality Multiplier (QM)**: 1.15 (Justified by technological monopoly in wafer-scale engineering and significant pricing power).
* **Dilution**: 0.5% annual dilution due to high free cash flow generation.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| **5-yr CAGR** | 45.0% | Hypergrowth sustains through multi-gigawatt cloud expansions |
| **Year 5 Revenue** | $3,268.9M | Maximum backlog realization and new cloud sign-ups |
| **Net Margin** | 35.0% | High-margin cloud software and licensing leverage |
| **Exit P/E** | 40.0x | Awarded premium growth semiconductor multiple |
| **Year 5 EPS** | $32.35 | Reflected on 35.4M projected shares |
| **Year 5 Price** | $1,487.92 | Undiscounted terminal price |
| **Present Value** | **$923.88** | Discounted at 10.0% over 5 years |

---

## Valuation Math & Target Weighting
| Scenario | presentValue | Weight | Contribution |
|----------|--------------|--------|--------------|
| **Bear** | $36.12 | 35% | $12.64 |
| **Base** | $323.07 | 45% | $145.38 |
| **Bull** | $923.88 | 20% | $184.78 |
| **Weighted Fair Value** | | **100%** | **$342.80** |

* **Current Price**: $287.30
* **Upside**: +19.3%
* **Recommendation**: **BUY**

---

## Key Risks & Dilution Overhangs
1. **Severe Customer Concentration**: Two Abu Dhabi-based entities (G42 and MBZUAI) accounted for **86% of total revenue** in 2025 (MBZUAI alone made up 62%). A single geopolitical policy change could wipe out the company's current cash flows.
2. **Dilutive Warrants Overhang**:
   * **OpenAI Deal**: Comes with warrants for OpenAI to purchase up to **10% of the company** at a nominal strike price ($0).
   * **AWS Deal**: AWS holds warrants for **2.7M shares** at a strike price of $100.
   These agreements ensure commercial success but significantly dilute Class A common shareholders.
3. **Lockup Expiry Selling Pressure**: The 180-day post-IPO lockup period for employees and early investors expires in **November 2026**. Insiders are sitting on massive gains (valuation expanded from $8B to $95B in private secondary markets), making heavy selling pressure likely. 
4. **Manufacturing Risk**: Single-source manufacturing at TSMC for the monolithic silicon wafer. Any fabrication line disruptions or wafer defects immediately hit production volume.

---

## Data Quality & Confidence: 0.75/1.0
* **Moat Strength**: Exceptional. The 21 PB/s memory bandwidth and monolithic packaging cannot be easily replicated by standard GPU node architectures.
* **Financial Quality**: Moderate. Revenue growth (+75.7% TTM) is stellar, but the one-time $363M gain masking a cash-burning adjusted net loss demands analytical skepticism.
* **Path to Validation**: High. OpenAI's $20B backlog and AWS Bedrock integration provide clear, auditable milestones over the next 90 days.

---

## Sources Checked
* **Financial statements**: ✅ S-1 post-IPO disclosures (`fetch_financials.py` parsing).
* **Calculations**: ✅ Mathematical confirmation using `dcf_scenarios.py` with Class A float anchors.
* **Projections persistence**: ✅ Saved via POST `/api/projections`.

