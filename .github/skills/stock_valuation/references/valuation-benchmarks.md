# Valuation Benchmarks — Category-Calibrated Reference Table

> **L4 Pattern**: Category-Calibrated Benchmark Anchoring  
> Purpose: Provide hardcoded industry-standard P/E and margin benchmarks. The agent's task is to **look up** the category from this table — not to generate benchmark values from prior knowledge, which risks hallucination.

---

## Sector Median P/E Benchmarks

| Sector | Conservative P/E | Median P/E | Growth P/E | Notes |
|--------|-----------------|------------|------------|-------|
| Technology — Software (SaaS) | 20 | 30 | 50+ | Revenue-multiple often more meaningful |
| Technology — Semiconductors | 15 | 25 | 40 | Highly cyclical; use through-cycle avg |
| Technology — Hardware / Consumer Electronics | 12 | 18 | 25 | Lower multiple; commodity risk |
| Technology — Internet / Platforms | 18 | 28 | 45 | Network effects justify premium |
| Healthcare — Biotech (profitable) | 18 | 28 | 50 | Pipeline optionality adds variance |
| Healthcare — Pharma (large cap) | 12 | 18 | 25 | Patent cliff discounts apply |
| Healthcare — Medical Devices | 20 | 28 | 38 | |
| Financials — Banks | 8 | 12 | 16 | Use P/Book as supplement |
| Financials — Insurance | 9 | 13 | 18 | |
| Financials — Fintech | 20 | 35 | 60+ | |
| Consumer Discretionary | 14 | 20 | 28 | |
| Consumer Staples | 15 | 20 | 25 | Stable; lower beta |
| Energy — Integrated Oil | 8 | 12 | 16 | Commodity-dependent |
| Energy — Renewables | 20 | 35 | 55 | Growth premium justified |
| Industrials | 14 | 18 | 24 | |
| Materials | 10 | 14 | 20 | |
| Telecommunications | 8 | 13 | 18 | High capex, low growth |
| Utilities | 12 | 16 | 20 | Bond-proxy; discount rate sensitive |
| Real Estate (REITs) | 15 | 20 | 28 | Use P/FFO preferred |

**Usage Rule**: When selecting `exitPE`, locate the company's sector in this table. Deviations of more than ±30% from the `Median P/E` column require explicit justification in the scenario `rationale` field citing moat, growth profile, or comparable multiples.

---

## Net Margin Benchmarks by Sector

| Sector | Bear Trough | Typical Range | Best-in-Class |
|--------|-------------|---------------|---------------|
| Technology — Software (SaaS) | 0% | 15–25% | 30%+ |
| Technology — Semiconductors | 5% | 15–30% | 40%+ (fabless) |
| Technology — Hardware | -5% | 5–15% | 20% |
| Technology — Platforms | 10% | 20–30% | 35%+ |
| Healthcare — Pharma | 5% | 15–25% | 30%+ |
| Healthcare — Biotech | neg. | 10–20% | 25%+ |
| Financials — Banks | 15% | 20–30% | 35%+ (ROE metric preferred) |
| Consumer Staples | 3% | 6–12% | 15% |
| Consumer Discretionary | -5% | 4–10% | 15% |
| Energy | -10% | 5–15% | 20% |
| Industrials | 2% | 6–12% | 15% |

**Usage Rule**: `base.netMargin` must not exceed the `Best-in-Class` column for the sector without a specific thesis. `bear.netMargin` should reference the `Bear Trough` as a floor data point.

---

## Quality Multiplier Guide

| Score | Description | Criteria |
|-------|-------------|----------|
| 0.8 | Structurally challenged | Commoditised product, pricing power declining, management issues |
| 0.9 | Below average | No clear moat, competition intensifying |
| 1.0 | Average quality | Normal business economics |
| 1.1 | Above average | One identifiable moat source (e.g. brand, incumbency) |
| 1.2 | High quality | Two+ moat sources (e.g. network effects + switching costs) |
| 1.3+ | Exceptional | Rare — requires evidence of durable pricing power across cycles |

> **Negative Constraint**: ❌ Do NOT set `qualityMultiplier > 1.1` purely because the company is well-known or has a high current P/E. The multiplier must be anchored to a specific structural advantage in the rationale.
