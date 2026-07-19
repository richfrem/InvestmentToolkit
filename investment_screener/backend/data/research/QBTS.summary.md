---
schemaVersion: 1
documentType: generated-research-summary
ticker: "QBTS"
generatedAt: "2026-07-19T03:27:19Z"
---

# QBTS Canonical Research Summary

*This file is a generated view. Do not edit directly. Authoritative observations are stored in the JSONL event ledger and indexed in `intelligence.sqlite`.*

# QBTS (D-Wave Quantum) — AI Deep Dive Research Report — 2026-05-04

## TL;DR
**SELL on a 5-year DCF basis (FV $0.90 vs $21.60, -96%).** D-Wave has the best gross margin in the quantum sector (82.6%) and is the only near-term commercial quantum solution, but quantum annealing has a fundamentally limited addressable market vs gate-based QC. At 325x revenue and $8B market cap, the valuation prices in an outcome (broad NP-hard problem dominance) that faces severe competition from rapidly improving classical ML optimization. The weakest risk/reward of the three quantum names.

---

## Company Snapshot

| Metric | Value |
|--------|-------|
| Ticker | QBTS (NYSE) |
| Price | $21.60 |
| Market Cap | $8.0B |
| TTM Revenue | $24.6M |
| Revenue Growth | +19% YoY |
| Gross Margin | 82.6% (improving) |
| Net Loss TTM | -$355M |
| Net Margin | ~-1,444% |
| Beta | 1.95 |
| Technology | Quantum annealing (NOT gate-based QC) |

---

## Investment Thesis

D-Wave is the odd one out among quantum computing companies — it builds quantum annealers, not gate-based quantum computers. Quantum annealing is specifically designed for combinatorial optimization problems (traveling salesman, scheduling, drug discovery). D-Wave has paying enterprise customers today (Volkswagen, Mastercard, Lockheed Martin, government agencies), which gives it the most near-term commercial revenue outside of IonQ.

The standout metric is an 82.6% gross margin — dramatically better than IONQ (40.4%) or any other quantum hardware company. This reflects a cloud/SaaS delivery model where customers access quantum optimization via API, and the marginal cost of an additional cloud query is near-zero.

The fundamental risk is TAM. Gate-based quantum computing (IBM, Google, IonQ) can in principle solve any problem that quantum annealing solves, plus many more. As gate-based QC matures, it will erode D-Wave's niche. In parallel, classical ML optimization (reinforcement learning, graph neural networks) continues improving on exactly the optimization problems D-Wave targets, from below. D-Wave is being squeezed from above (gate-based QC) and below (classical ML) simultaneously.

Revenue growth decelerated sharply — flat for two years ($8.8M FY22 and FY23) before a 2.8x jump to $24.6M. The sustainability of this jump is uncertain. Net losses of $355M on $24.6M revenue represent extreme R&D intensity with no near-term profitability path.

---

## Scenario Analysis

### Bear (55% probability) — Classical ML wins, annealing niche contracts
Classical optimization methods (ML, simulated annealing, heuristics) close the advantage gap. Enterprise customers don't renew or expand contracts. Revenue grows only 10% CAGR to ~$40M by year 5. Cash burn requires extreme dilution (+5%/yr).

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 10% | Near-stagnation as classical alternatives compete |
| Year 5 Revenue | $40M | From $24.6M base |
| Net Margin (Yr 5) | 0% | Zero-profit (modeled floor) |
| Exit P/E | 10x | Distressed niche platform |
| Quality Multiplier | 0.75 | Limited TAM, technology squeeze |
| Share Change | +5.0%/yr | Heavy dilution |
| **Year 5 EPS** | **$0.00** | |
| **Year 5 Price** | **$0.00** | |
| **Present Value** | **$0.00** | |

### Base (30% probability) — Optimization niche holds, SaaS economics kick in
D-Wave maintains its optimization niche and the 82.6% gross margin converts to operating profitability as opex scales sub-linearly. Revenue reaches ~$110M by year 5 with first meaningful profitability.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 35% | Niche market development |
| Year 5 Revenue | $110M | From $24.6M base |
| Net Margin (Yr 5) | 8% | Operating leverage on 82.6% gross margin |
| Exit P/E | 35x | Profitable niche SaaS platform |
| Quality Multiplier | 1.00 | Average — niche viable but limited |
| Share Change | +2.0%/yr | Moderate dilution |
| **Year 5 EPS** | **$0.02** | Barely positive |
| **Year 5 Price** | **$0.76** | |
| **Present Value** | **$0.47** | |

### Bull (15% probability) — Quantum annealing proves decisive for NP-hard problems
A landmark proof-of-value for pharmaceutical drug discovery or financial portfolio optimization establishes quantum annealing superiority over classical methods. D-Wave becomes optimization infrastructure for Fortune 500.

| Assumption | Value | Rationale |
|-----------|-------|-----------|
| 5-yr Revenue CAGR | 65% | Broad NP-hard problem adoption |
| Year 5 Revenue | $301M | From $24.6M base |
| Net Margin (Yr 5) | 18% | SaaS operating leverage |
| Exit P/E | 55x | High-growth niche dominant |
| Quality Multiplier | 1.05 | Annealing architecture has no direct quantum-native competitor |
| Share Change | +1.0%/yr | Minimal dilution at scale |
| **Year 5 EPS** | **$0.14** | |
| **Year 5 Price** | **$8.10** | |
| **Present Value** | **$5.03** | |

---

## Valuation Math

| Scenario | Weight | Present Value | Contribution |
|----------|--------|--------------|--------------|
| Bear | 55% | $0.00 | $0.00 |
| Base | 30% | $0.47 | $0.14 |
| Bull | 15% | $5.03 | $0.75 |
| **Weighted Fair Value** | | | **$0.90** |

**Current Price:** $21.60 → **Implied upside: -95.8%** → **Action: SELL**

---

## Key Risks
1. **Technology squeeze**: Gate-based QC (IBM/Google/IonQ) can replace annealing for all its use cases as it matures. D-Wave has no moat against the general-purpose solution.
2. **Classical ML competition**: Graph neural networks, reinforcement learning, and heuristic solvers are improving rapidly on exactly the same optimization problems D-Wave targets.
3. **Revenue flat periods**: Two consecutive flat revenue years ($8.8M each) before the recent jump raise questions about the sustainability of current growth.
4. **Extreme cash burn**: Net loss $355M on $24.6M revenue is extreme. Cash runway requires monitoring — the company will need additional raises.
5. **Limited TAM**: Quantum annealing's total addressable market is a subset of the quantum computing market. The ceiling is lower than gate-based QC.

---

## Quantum Sector Comparison

| Metric | QBTS | IONQ | RGTI |
|--------|------|------|------|
| Technology | Quantum annealing | Trapped-ion | Superconducting |
| Revenue TTM | $24.6M | $130M | ~$12M est. |
| Rev Multiple | 325x | 135x | ~500x |
| Gross Margin | **82.6%** | 40.4% | ~50% est. |
| DCF Fair Value | $0.90 | $8.54 | $1.05 |
| DCF Action | SELL | SELL | SELL |
| Near-term Commercial | **Strongest** | Strong | Weak |
| Long-term TAM | Weakest | **Strongest** | Weak |
| **Relative Rank** | **#3** | **#1** | **#2*** |

*RGTI has a differentiated technology but competes directly against vastly better-resourced IBM/Google.

---

## Data Quality & Confidence Score
**Score: 0.48/1.0**
- -0.15: No analyst estimates available
- -0.12: Two flat revenue years before recent jump — sustainability uncertain
- -0.10: Quantum annealing niche limits long-term TAM modeling
- -0.10: 5-yr DCF systematically understates optionality
- -0.05: Extreme loss ratio (-1444% margin) makes near-term modeling unreliable

---

## Discussion Log
*Appended during Q&A sessions*

