---
ticker: PUMP
name: AI Deep Dive — PUMP — 2026-05-02
lastUpdated: 2026-05-02T22:20:00Z
fairValue: 4.92
priceAtAnalysis: 16.62
action: SELL
---

# PUMP Canonical Research History

## Research Sweep — 2026-05-02
**Analyst**: Claude Sonnet 4.6 | **Date**: 2026-05-02 | **Confidence**: 0.73/1.0

---

## TL;DR
**SELL — Fair Value $4.92 vs $16.62 (-70.4%).** ProPetro Holding is a small-cap hydraulic fracturing company with revenue declining 24.7% YoY, near-zero margins, and analyst target ($15.45) already below current price. The bull case present value of $17.15 barely covers current price — there is almost no upside scenario in which PUMP is worth what it currently trades at. Note: the raw API data contained a critical share count error (shares_diluted < shares_outstanding — impossible) that was corrected using mktcap-implied count before the DCF was run.

---

## Company Snapshot

| Metric | Value |
|--------|-------|
| Ticker | PUMP |
| Price | $16.62 |
| Market Cap | $2.04B |
| Revenue (TTM) | $1,274.1M (down 24.7% YoY) |
| Net Margin (TTM) | ~0% (near breakeven) |
| EPS (TTM) | $0.18 |
| Forward EPS (Y1) | -$0.155 (negative) |
| Forward PE | N/M (negative earnings) |
| Piotroski | 4/9 |
| Analyst Target | $15.45 (4 analysts) — BELOW current price |
| DCF Fair Value | **$4.92** |
| Recommendation | **SELL** |

---

## ⚠️ Data Quality Alert: Share Count Correction

The financial data API returned `shares_diluted = 82,400,000` and `shares_outstanding = 122,616,976`. This is mathematically impossible — diluted shares must always be ≥ outstanding shares (diluted includes options, warrants, convertibles on top of outstanding). The raw API data was incorrect.

**Correction methodology**: Market cap $2.04B / price $16.62 = 122.7M shares implied. Used 122.6M (aligning with shares_outstanding, which appears correct).

**Impact**: Using the erroneous 82.4M diluted share count would have given a fair value of $7.32. Correct count gives $4.92. The error makes the company appear 49% more valuable than it is on a per-share basis. This data quality issue is flagged and corrected in the projection JSON.

---

## Investment Thesis

ProPetro Holding provides hydraulic fracturing, wireline, cementing, and other completion services to E&P companies, primarily in the Permian Basin. The company was founded in 2012 and has benefited from two oil price cycles — but the current down-cycle is impacting it more severely than larger competitors like Liberty Oilfield Services (LBRT).

The fundamental problem is multi-dimensional:
1. **Revenue decline**: $1,690M (FY2023) → $1,274M (TTM) — a 24.7% collapse driven by E&P capex cuts
2. **Near-zero profitability**: Net income of approximately $22M on $1.27B revenue = 1.7% margin, producing just $0.18 EPS on 122.6M shares
3. **Negative forward earnings**: Analysts project Y1 EPS of -$0.155 — the business is expected to swing into a loss as revenue declines continue and fixed costs remain elevated
4. **Analyst target below market**: $15.45 consensus target vs $16.62 current price — a rare case where even bullish sell-side analysts believe the stock is overvalued at current prices

The competitive position of PUMP vs LBRT is relevant context. LBRT is approximately 3x larger ($4B revenue vs $1.27B), has better cost structure through scale, and has been able to sustain slightly better margins. PUMP's smaller scale means it faces more pricing pressure and has less negotiating leverage with E&P customers.

The only bull scenario that partially justifies current prices requires oil $85+, meaningful E&P activity recovery, and PUMP winning market share — all of which together give $17.15, barely above the current $16.62. This is not an investment with an appropriate risk/reward profile.

---

## Scenario Analysis

### 🐻 Bear (40%) — $0.19

E&P capex continues to decline. PUMP revenue falls further, near-breakeven margins deteriorate below zero, requiring dilutive equity issuance.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | -5% | Continued E&P budget cuts |
| Year 5 Revenue | $998M | From $1,274M |
| Net Margin (Yr 5) | 1% | Near-breakeven compression |
| Exit P/E | 6x | Distressed commodity service |
| Quality Multiplier | 0.80 | — |
| **Year 5 EPS** | **$0.08** | — |
| **Present Value** | **$0.19** | — |

### ⚖️ Base (40%) — $3.54

Oil demand stabilizes. PUMP revenue troughs and modestly recovers. Margins recover slightly from near-zero to 4%.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 5% | Modest recovery |
| Year 5 Revenue | $1,626.5M | From $1,274M |
| Net Margin (Yr 5) | 4% | Recovery from near-zero |
| Exit P/E | 12x | Commodity services, still below cycle |
| Quality Multiplier | 0.90 | — |
| **Year 5 EPS** | **$0.47** | — |
| **Present Value** | **$3.54** | — |

### 🚀 Bull (20%) — $17.15

**Catalyst**: Oil to $90+, Permian activity surge, PUMP captures share from smaller competitors exiting the market in the down cycle.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 12% | Oil price recovery + activity surge |
| Year 5 Revenue | $2,245.5M | From $1,274M |
| Net Margin (Yr 5) | 8% | Peak-cycle restoration |
| Exit P/E | 18x | — |
| Quality Multiplier | 1.00 | — |
| **Year 5 EPS** | **$1.29** | — |
| **Present Value** | **$17.15** | — |

---

## Valuation Math

| Scenario | PV | Weight | Contribution |
|----------|-----|--------|--------------|
| Bear | $0.19 | 40% | $0.08 |
| Base | $3.54 | 40% | $1.42 |
| Bull | $17.15 | 20% | $3.43 |
| **Weighted Fair Value** | | | **$4.92** |

**Current Price**: $16.62 | **Downside**: -70.4% | **Recommendation**: **SELL**

**Note**: Bull PV $17.15 ≈ current price. Even in the optimistic scenario, the stock is approximately fairly valued. The asymmetry is strongly negative.

---

## Key Risks

1. **Oil price shock** — Only a sharp, sustained oil price recovery (>$85/bbl) can materially change this thesis. This is a binary commodity macro risk.
2. **Share count data error** — The corrected 122.6M share count may itself be slightly off if there are recent buybacks or issuances not reflected in market cap calculation.
3. **Analyst Y1 negative EPS** — If the company does swing to negative earnings, there is potential for a forced dividend cut or balance sheet deterioration that could accelerate the decline.

---

## Data Quality & Confidence Score

**Confidence**: 0.73/1.0 — SELL thesis is highly supported. Main uncertainty is commodity price. The share count correction is clearly right (diluted < outstanding is impossible), but the corrected figure itself relies on market cap imputation. Analyst target already below market price confirms SELL signal independently.

---

## Discussion Log
*No Q&A logged yet.*

