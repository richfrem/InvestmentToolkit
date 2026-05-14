# Investment Thesis v9.4

| Field | Value |
| :--- | :--- |
| **Current Theme** | ASI Buildout (Primary) + Sovereign Finance (Secondary) |
| **Edition** | "The Compute Sovereign" |
| **Status** | ACTIVE |
| **Last Updated** | 2026-05-13 |
| **Portfolio Data** | Live — synced from Questrade via app or `python3 investment_screener/backend/src/QuestradeDataEngine.py` |
| **Latest Review** | `PortfolioAnalysis/strategic-reviews/2026-05-05-PortfolioAnalysisRecommendations.md` |

> **Living document.** The framework and sub-strategies persist across versions. Holdings, weights, and conviction details evolve. Only update this doc when conviction, structure, or macro narrative materially shifts.

---

## Version History

| Version | Date | Edition | Key Change |
| :--- | :--- | :--- | :--- |
| 9.4 | 2026-05-13 | The Compute Sovereign | Grok sweep: PSIX 0.5%→1.71% (user doubled on 40% earnings selloff; SA LP intact; H2 ramp thesis); BE 4.95%→5.23% (Oracle 2.8GW confirmed + equity warrants); NBIS 2.55%→2.85% (AI cloud momentum); IREN 1.90%→2.09% (NVIDIA deal); INTC trimmed 8.19%→7.81% (Q1 beat, still DCF SELL); IONQ catalyst: Q1 +755% YoY + SkyWater merger shareholder approval. SA LP 13F expected 2026-05-14/15. |
| 9.3 | 2026-05-08 | The Compute Sovereign | IREN MAINTAIN→ACCUMULATE: NVIDIA $3.4B 5-year AI cloud contract + 5GW partnership; COIN Q1 miss (-$394M GAAP loss) — FV $185, MAINTAIN confirmed. IREN DCF snapshot stale — fresh eval warranted. |
| 9.2 | 2026-05-07 | The Compute Sovereign | Exit reversals: COHR/EQT/IREN returned to MAINTAIN (~1% each) on fresh AI tailwinds; NVDA target reduced 7.8%→3% (conviction trim); COIN SELL→MAINTAIN (FV $162→$193, subscription/services maturation); 7 catalyst updates: INTC/AMD/MSFT earnings beats, BE/CORZ major contracts, OKLO NRC regulatory, CRWV RPO $99.4B backlog. |
| 9.1 | 2026-05-06 | The Compute Sovereign | Re-ranked sub-strategies: ASI/Compute (Primary: Immediate Growth, 75% ceiling) vs Sovereign Finance (Secondary: Strategic Infrastructure, 15% cap). Finalized liquidation of IREN, EQT, and COHR. Updated Finance rationale to reflect AI-agent autonomous settlement. |
| 9.0 | 2026-05-05 | The Sovereign Manufacturer | Major restructure after 4-model adversarial red team review: exited all Sovereign Finance crypto (COIN/CRCL/ETHA/IBIT); exited POET/CRWD/SOLZ/EQT/TEM; reduced INTC (~11%→9%), CRWV; 39% cash freed for redeployment into DCF BUY names |
| 8.5 | 2026-05-04 | The Sovereign Manufacturer | Healthcare AI / Life Science pillar added; TEM promoted from EXIT to speculative MAINTAIN (Pelosi conviction, AI-healthcare thesis) |
| 8.4 | 2026-05-04 | The Sovereign Manufacturer | Quantum Computing pillar added; IONQ initiated (trapped-ion moat, ACCUMULATE→MAINTAIN at actual weight); RGTI exited; COIN regulatory catalyst (SEC case dismissed, FV $124→$162); apply_catalyst.py tooling added |
| 8.3 | 2026-05-03 | The Sovereign Manufacturer | Third Grok sweep: CRWV→6%, CORZ→4.9%, BE→4%; NVDA/META/PSIX/WYFI/BTDR buys synced; Questrade float(None) crash fixed |

---

## I. Core Premise

This strategy is built on a single macro conviction: **the 2020s will be defined by two simultaneous civilisational-scale competitions**, and losing either front means losing strategic dominance for a generation.

**The ASI Race (Primary: Immediate Growth)** — Control of intelligence and technological supremacy. This is a high-velocity, **~$700 billion sprint** driven by Hyperscaler Capex. No longer a commercial competition — it is a national security priority analogous to the Manhattan Project. This forces a structural shift from *"most efficient"* to *"most sovereign"*, mandating onshoring of critical technology and resilient supply chains.

**The Sovereign Finance Race (Secondary: Strategic Infrastructure Maturity)** — Control of value, monetary systems, and debt monetisation via digital assets. Currently in a foundational maturity phase (**~$29 billion RWA market**). The US counter-strategy (GENIUS Act of 2025) establishes federal stablecoin rails. The primary users of this infrastructure will be **AI Agents** needing autonomous settlement rails to conduct business at machine speed.

**The Feedback Loop** — Both fronts are self-reinforcing. Winning ASI requires capital; winning Sovereign Finance provides it.

> **Investment Philosophy:** *"Builder-First, Empire-Second."* Own the foundational, physically-constrained, sovereign-critical **infrastructure** required to dominate both fronts — not the application layer built on top of it.

---

## II. Sub-Strategies

*Five named conviction frameworks. Every holding maps to exactly one. The skill assesses each sub-strategy as a unit — conviction intact, weakening, or broken.*

---

### Sub-Strategy 1 — SA / ASI Race (Primary: Immediate Growth)

**Conviction:** Aschenbrenner's *Situational Awareness* thesis is playing out. The transition from narrow AI to AGI/ASI is a national security emergency. The US government has designated AI compute a strategic resource — creating a durable, state-backed tailwind that runs through two distinct investment layers. **Target Ceiling: 75%**.

- **Direct Plays** — The silicon, software, and EDA tooling that produces and runs AI models. These are the companies whose revenue is directly denominated in AI compute demand: chip designers, foundries, GPU clouds, hyperscalers, and the EDA duopoly every chip must pass through.
- **Infrastructure Plays** — The physical facilities, power supply, cooling, networking, and hosting that AI data centres require. These are scarce, capital-intensive real assets with multi-year construction backlogs. Demand is model-agnostic — regardless of who wins the AI application layer, the infrastructure must be built and powered. Bitcoin mining companies converting to AI hosting are a high-beta play on this transition.

Both layers derive from the same root conviction. They are not separate theses.

**Conviction Intact When:** US-China AI competition continues. CHIPS Act funding flows. Pentagon treats compute as strategic. Hyperscalers keep accelerating **~$700B capex**. Data centre construction backlogs remain multi-year. AI compute demand continues to exceed power and cooling supply.

**Thesis Breaker:** US-China technological de-escalation removes national security urgency for sovereign compute. Algorithmic efficiency breakthrough (Chinchilla-scale) collapses compute demand. Room-temperature superconductors eliminate cooling bottlenecks.

**Key Validators:** Aschenbrenner SA LP 13F positions (Q4 2025: INTC $746M calls, CRWV $1.21B). Pentagon AI executive orders. Hyperscaler capex reports. IEA data centre power demand forecasts.

---

### Sub-Strategy 3 — Sovereign Finance (Secondary: Strategic Maturity)

**Conviction:** The global financial system is being tokenised. This is a foundational maturity phase (**~$29B RWA market**) that will eventually settle the value AI creates. The primary users of these rails will be **AI Agents** requiring autonomous, 24/7 settlement without human intermediaries. Coinbase and Circle are the regulated picks-and-shovels plays on this transition. **Target Cap: 15% for 2026**.

**Conviction Intact When:** GENIUS Act framework is intact. Stablecoin adoption growing. RWA tokenisation expanding. AI agents begin autonomous transaction pilots.

**Thesis Breaker:** GENIUS Act repealed or SEC court victory classifies ETH as security. USDC de-peg sustained beyond 48 hours.

---

### Sub-Strategy 1 — SA / ASI Race

#### Direct Plays — Silicon, Software & EDA

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **NVDA** | 🔵 ACCUMULATE | 2.06% | 2.80% | Core | AI Compute Incumbent: CUDA ecosystem moat and dominant GPU supply chain. |
| **AMD** | 🟡 TRIM | 4.00% | 3.36% | Core | Fortified #2: only credible US-based GPU competitor to NVIDIA |
| **INTC** | 🟡 TRIM | 9.25% | 7.54% | Core | Sovereign Foundry: US national champion for onshored compute. |
| **AVGO** | 👁️ WATCHLIST | — | — | Core | Networking + custom silicon moat: irreplaceable in hyperscaler AI buildout. |
| **CRWV** | 🔵 ACCUMULATE | 4.03% | 5.77% | Core | Pure-play GPU cloud. SA #1 position. |
| **GOOG** | ⚪ MAINTAIN | 4.81% | 4.60% | Core | Foundational AI research leader. |
| **MSFT** | ⚪ MAINTAIN | 2.43% | 2.33% | Core | Sovereign distribution channel: dominant enterprise AI via Azure + Copilot |
| **META** | ⚪ MAINTAIN | 1.85% | 1.87% | Core | Consumer AI Leader: open-source Llama models. |
| **NBIS** | ⚪ MAINTAIN | 2.50% | 2.83% | Speculative | Nebius AI infrastructure — early stage conviction. |
| **COHR** | 🟡 TRIM | 1.22% | 0.93% | EXIT | Liquidation finalized. Capital better deployed in higher conviction ASI names. |
| **LITE** | ⚪ MAINTAIN | 2.31% | 2.10% | Speculative | Lumentum optical interconnects: photonic layer of AI networking. |
| **HUMN** | ⚪ MAINTAIN | 3.12% | 2.90% | Thematic ETF | Humanoid robotics ETF — physical embodiment of ASI |
| **KOID** | ⚪ MAINTAIN | 2.72% | 2.63% | Thematic ETF | Automation and robotics revolution. |

#### Infrastructure Plays — Power, Cooling, Hosting & Networking

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **VST** | 🔥 REVIEW | 2.15% | 1.20% | Core | Largest independent US power producer. |
| **CEG** | ⚪ MAINTAIN | 2.73% | 3.04% | Core | Nuclear renaissance — clean, carbon-free baseload. |
| **VRT** | 🟡 TRIM | 1.12% | 0.97% | Core | Thermal management — liquid cooling bottleneck solver. |
| **OKLO** | ⚪ MAINTAIN | 2.05% | 2.26% | Speculative | Next-gen SMRs. |
| **BE** | 🔵 ACCUMULATE | 2.17% | 5.18% | Speculative | Bloom Energy fuel cells — clean distributed power. |
| **CORZ** | 🔵 ACCUMULATE | 3.64% | 5.13% | High-beta | Bitcoin mining converting to AI data centres. |
| **IREN** | 🔵 ACCUMULATE | 1.66% | 2.07% | EXIT | Liquidation finalized. |
| **EQT** | ⚪ MAINTAIN | 1.01% | 0.98% | EXIT | Liquidation finalized. |

---

### Sub-Strategy 2 — AI-Native Cybersecurity

**Conviction:** As AI capabilities advance, the attack surface expands. More AI = more attack surface = more security spend.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **PANW** | ⚪ MAINTAIN | 5.46% | 4.78% | Core | AI-native platform leader. |
| **ZS** | 🔥 REVIEW | 3.67% | 3.00% | Core | Zero Trust access gateway. |

---

### Sub-Strategy 3 — Sovereign Finance (Secondary: Strategic Maturity)

**Conviction:** The global financial system is being tokenised for **AI Agents**. Bitcoin (store of value), Ethereum (settlement layer), Coinbase/Circle (infrastructure).

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **IBIT** | 👁️ WATCHLIST | — | — | Core | Digital gold: neutral, un-inflatable store of value. |
| **ETHA** | 👁️ WATCHLIST | — | — | Core | Global settlement layer. |
| **COIN** | ⚪ MAINTAIN | 3.04% | 2.96% | Core | Regulated app store for sovereign finance. |
| **CRCL** | ⚪ MAINTAIN | 3.79% | 3.65% | Core | Sovereign stablecoin manufacturer for AI agents. |

---

### Sub-Strategy 4 — Quality SaaS Resilience

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **CRM** | 🔥 REVIEW | 2.00% | 1.20% | Core | Salesforce — Agentforce AI platform. |
| **NOW** | ⚪ MAINTAIN | 1.32% | 1.20% | Core | ServiceNow — AI workflow automation. |

---

## III. Portfolio Weights

*Holdings and actual weights are maintained in `target-portfolio.json`.*

---

## IV. Portfolio Blueprint

*Generated 2026-05-13 · Source: `validate_weights.py` × `target-portfolio.json` × `portfolio.json` (Questrade live)*
*Portfolio value: $33,228. Refresh: `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write`*

### Sub-Strategy 1 — SA / ASI Race (Aschenbrenner Framework)

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **INTC** | 🟡 TRIM | — | 9.25% | 7.54% | — | The Sovereign Foundry: designated US National Champion for onshored compute manufacturing. |
| **GOOG** | ⚪ MAINTAIN | — | 4.81% | 4.60% | — | Hyperscaler with vertically integrated AI stack. |
| **CRWV** | 🔵 ACCUMULATE | — | 4.03% | 5.77% | — | GPU cloud provider. |
| **AMD** | 🟡 TRIM | — | 4.00% | 3.36% | — | Hedge against NVDA dominance. |
| **CORZ** | 🔵 ACCUMULATE | — | 3.64% | 5.13% | — | BTC→AI data center conversion thesis. |
| **HUMN** | ⚪ MAINTAIN | — | 3.12% | 2.90% | — | Physical embodiment of ASI thesis. |
| **CEG** | ⚪ MAINTAIN | — | 2.73% | 3.04% | — | Largest US nuclear operator. |
| **KOID** | ⚪ MAINTAIN | — | 2.72% | 2.63% | — | Automation and robotics revolution. |
| **NBIS** | ⚪ MAINTAIN | — | 2.50% | 2.83% | — | European AI infrastructure. |
| **MSFT** | ⚪ MAINTAIN | — | 2.43% | 2.33% | — | Azure + OpenAI partnership. |
| **LITE** | ⚪ MAINTAIN | — | 2.31% | 2.10% | — | Lumentum optical interconnects. |
| **BE** | 🔵 ACCUMULATE | — | 2.17% | 5.18% | — | Bloom Energy fuel cells. |
| **VST** | 🔥 REVIEW | — | 2.15% | 1.20% | — | Nuclear + natgas power merchant. |
| **NVDA** | 🔵 ACCUMULATE | — | 2.06% | 2.80% | — | Highest-conviction BUY. Target increased to absorb freed capital from IREN, COHR, and EQT exits. |
| **OKLO** | ⚪ MAINTAIN | — | 2.05% | 2.26% | — | Micro-nuclear reactor commercialization. |
| **BTDR** | 🔥 REVIEW | — | 1.98% | 1.50% | — | Proprietary Sealminer ASIC chip design. |
| **META** | ⚪ MAINTAIN | — | 1.85% | 1.87% | — | Social monopoly + AI ad flywheel. |
| **IREN** | 🔵 ACCUMULATE | — | 1.66% | 2.07% | — | EXIT: Liquidation finalized. |
| **TEAM** | ⚪ MAINTAIN | — | 1.46% | 1.30% | — | Human-agentic collaboration platform. |
| **WYFI** | 🔥 REVIEW | — | 1.29% | 0.91% | — | AI GPU cloud + HPC data center. |
| **COHR** | 🟡 TRIM | — | 1.22% | 0.93% | — | EXIT: Liquidation finalized. |
| **VRT** | 🟡 TRIM | — | 1.12% | 0.97% | — | Data center thermal management. |
| **PSIX** | 🔵 ACCUMULATE | — | 1.06% | 1.70% | — | AI power infrastructure. |
| **EQT** | ⚪ MAINTAIN | — | 1.01% | 0.98% | — | EXIT: Liquidation finalized. |
| **AVGO** | 👁️ WATCHLIST | — | — | — | — | Custom ASIC + networking moat. |
| **EQIX** | 👁️ WATCHLIST | — | — | — | — | Digital Geneva. |
| **ANET** | 👁️ WATCHLIST | — | — | — | — | AI networking switching fabric. |
| **SNDK** | 🟢 INITIATE | — | — | 0.71% | — | NAND storage infrastructure play. |
| **TSM** | 🟢 INITIATE | — | — | 2.20% | — | The foundry backbone of the AI compute stack. |
| **ASML** | 🟢 INITIATE | — | — | 1.76% | — | Absolute monopoly on EUV lithography. |
| **MU** | 🟢 INITIATE | — | — | 1.32% | — | HBM3E memory bandwidth bottleneck. |
| **Subtotal** | | **62.62%** | **71.86%** | +9.24pp | |

### Sub-Strategy 2 — AI-Native Cybersecurity

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **PANW** | ⚪ MAINTAIN | — | 5.46% | 4.78% | — | AI-native platform consolidation leader. |
| **ZS** | 🔥 REVIEW | — | 3.67% | 3.00% | — | Zero-trust SASE leader. |
| **CRWD** | 👁️ WATCHLIST | — | — | — | — | EXIT: DCF -66% downside. |
| **Subtotal** | | **9.13%** | **7.78%** | -1.34pp | |

### Sub-Strategy 3 — Sovereign Finance

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **CRCL** | ⚪ MAINTAIN | — | 3.79% | 3.65% | — | USDC issuer and stablecoin infrastructure for AI agents. |
| **COIN** | ⚪ MAINTAIN | — | 3.04% | 2.96% | — | Regulated crypto exchange + Base L2 growth. Settlement rail for AI Agents. |
| **ETHA** | 👁️ WATCHLIST | — | — | — | — | Ethereum as programmable settlement layer. |
| **IBIT** | 👁️ WATCHLIST | — | — | — | — | Bitcoin as sovereign reserve asset. |
| **SOLZ** | 👁️ WATCHLIST | — | — | — | — | EXIT: Solana ETF. |
| **Subtotal** | | **6.83%** | **6.61%** | -0.22pp | |

### Sub-Strategy 4 — Quality SaaS Resilience

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **CRM** | 🔥 REVIEW | — | 2.00% | 1.20% | — | Agentforce AI platform. |
| **NOW** | ⚪ MAINTAIN | — | 1.32% | 1.20% | — | AI workflow automation. |
| **Subtotal** | | **3.32%** | **2.40%** | -0.92pp | |

### Sub-Strategy 5 — Applied AI / Frontier Bets

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **RGTI** | 👁️ WATCHLIST | — | — | — | — | EXIT: Rigetti Computing. |
| **POET** | 👁️ WATCHLIST | — | — | — | — | EXIT: POET Technologies. |
| **Subtotal** | | **0.00%** | **0.00%** | — | |

### Strategic Reserve

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **PSU-U.TO** | 🟢 INITIATE | — | — | 9.41% | — | USD cash reserve (Purpose US Cash Fund) — holds short-term USD treasuries on TSX. Primary purpose: USD currency exposure + interest income while awaiting deployment into thesis positions. Monthly dividend ~$0.31-0.33/share (~$3.68-3.90 USD annualized). ENTRY RULE: always buy 1-2 days AFTER the ex-dividend date (typically last Tuesday of month) to get the cycle-low reset price and capture the full next month of accrual. Buying mid-cycle or just before ex-date overpays for already-accrued dividend. Ex-dates: ~Jan 28, Feb 25, Mar 31, Apr 28, May 28, Jun 30 pattern. Next planned entry: May 29, 2026 (post May 28 ex-date). |
| **Subtotal** | | **0.00%** | **9.41%** | +9.41pp | |

### Portfolio Totals

| | Actual % | Target % | Delta |
| :--- | ---: | ---: | ---: |
| **All holdings** | **81.90%** | **98.07%** | +16.16pp |
| *Validate* | `python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode both` | | |


---


## V. Risk Factors

| Risk | Trigger Condition | Hedge / Mitigation |
| :--- | :--- | :--- |
| INTC execution failure | 18A delay past Q4 2026 | NVDA/AMD long |
| Crypto regulatory reversal | GENIUS Act repealed | Position caps: COIN, CRCL ≤5% each |

---

## VII. Supporting Research

| Source | Relevance |
| :--- | :--- |
| Aschenbrenner (2024) *Situational Awareness* | Core ASI Race thesis framework |
| GENIUS Act (H.R. 5150, enacted 2025) | Sovereign Finance legal framework |
