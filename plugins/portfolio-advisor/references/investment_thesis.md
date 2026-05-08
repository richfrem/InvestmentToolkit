# Investment Thesis v9.2

| Field | Value |
| :--- | :--- |
| **Current Theme** | ASI Buildout (Primary) + Sovereign Finance (Secondary) |
| **Edition** | "The Compute Sovereign" |
| **Status** | ACTIVE |
| **Last Updated** | 2026-05-07 |
| **Portfolio Data** | Live — synced from Questrade via app or `python3 investment_screener/backend/src/QuestradeDataEngine.py` |
| **Latest Review** | `PortfolioAnalysis/strategic-reviews/2026-05-07-PortfolioAnalysisRecommendations.json` |

> **Living document.** The framework and sub-strategies persist across versions. Holdings, weights, and conviction details evolve. Only update this doc when conviction, structure, or macro narrative materially shifts.

---

## Version History

| Version | Date | Edition | Key Change |
| :--- | :--- | :--- | :--- |
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
| **NVDA** | 🔵 ACCUMULATE | 1.90% | 3.72% | Core | AI Compute Incumbent: CUDA ecosystem moat and dominant GPU supply chain. |
| **AMD** | ⚪ MAINTAIN | 3.84% | 3.60% | Core | Fortified #2: only credible US-based GPU competitor to NVIDIA |
| **INTC** | ⚪ MAINTAIN | 8.85% | 8.27% | Core | Sovereign Foundry: US national champion for onshored compute. |
| **AVGO** | 👁️ WATCHLIST | — | — | Core | Networking + custom silicon moat: irreplaceable in hyperscaler AI buildout. |
| **CRWV** | 🔵 ACCUMULATE | 4.21% | 6.18% | Core | Pure-play GPU cloud. SA #1 position. |
| **GOOG** | ⚪ MAINTAIN | 4.86% | 4.51% | Core | Foundational AI research leader. |
| **MSFT** | 🔥 REVIEW | 2.56% | 2.00% | Core | Sovereign distribution channel: dominant enterprise AI via Azure + Copilot |
| **META** | ⚪ MAINTAIN | 1.89% | 2.00% | Core | Consumer AI Leader: open-source Llama models. |
| **NBIS** | ⚪ MAINTAIN | 2.22% | 2.57% | Speculative | Nebius AI infrastructure — early stage conviction. |
| **COHR** | 🔴 EXIT | 1.05% | 0.00% | EXIT | Liquidation finalized. Capital better deployed in higher conviction ASI names. |
| **LITE** | 🔵 ACCUMULATE | 1.46% | 2.25% | Speculative | Lumentum optical interconnects: photonic layer of AI networking. |
| **HUMN** | ⚪ MAINTAIN | 2.78% | 2.59% | Thematic ETF | Humanoid robotics ETF — physical embodiment of ASI |
| **KOID** | ⚪ MAINTAIN | 2.63% | 2.44% | Thematic ETF | Automation and robotics revolution. |

#### Infrastructure Plays — Power, Cooling, Hosting & Networking

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **VST** | 🔥 REVIEW | 2.46% | 1.29% | Core | Largest independent US power producer. |
| **CEG** | ⚪ MAINTAIN | 2.96% | 3.26% | Core | Nuclear renaissance — clean, carbon-free baseload. |
| **VRT** | ⚪ MAINTAIN | 1.09% | 1.04% | Core | Thermal management — liquid cooling bottleneck solver. |
| **OKLO** | ⚪ MAINTAIN | 2.19% | 2.42% | Speculative | Next-gen SMRs. |
| **BE** | 🔵 ACCUMULATE | 1.78% | 4.12% | Speculative | Bloom Energy fuel cells — clean distributed power. |
| **CORZ** | 🔵 ACCUMULATE | 2.96% | 5.05% | High-beta | Bitcoin mining converting to AI data centres. |
| **IREN** | 🔴 EXIT | 1.79% | 0.00% | EXIT | Liquidation finalized. |
| **EQT** | 🔴 EXIT | 1.08% | 0.00% | EXIT | Liquidation finalized. |

---

### Sub-Strategy 2 — AI-Native Cybersecurity

**Conviction:** As AI capabilities advance, the attack surface expands. More AI = more attack surface = more security spend.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **PANW** | ⚪ MAINTAIN | 4.53% | 5.13% | Core | AI-native platform leader. |
| **ZS** | ⚪ MAINTAIN | 3.39% | 3.22% | Core | Zero Trust access gateway. |

---

### Sub-Strategy 3 — Sovereign Finance (Secondary: Strategic Maturity)

**Conviction:** The global financial system is being tokenised for **AI Agents**. Bitcoin (store of value), Ethereum (settlement layer), Coinbase/Circle (infrastructure).

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **IBIT** | 👁️ WATCHLIST | — | — | Core | Digital gold: neutral, un-inflatable store of value. |
| **ETHA** | 👁️ WATCHLIST | — | — | Core | Global settlement layer. |
| **COIN** | ⚪ MAINTAIN | 3.02% | 2.63% | Core | Regulated app store for sovereign finance. |
| **CRCL** | ⚪  TRIM | 3.56% | 3.07% | Core | Sovereign stablecoin manufacturer for AI agents. |

---

### Sub-Strategy 4 — Quality SaaS Resilience

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **CRM** | 🔵 ACCUMULATE | 0.86% | 1.29% | Core | Salesforce — Agentforce AI platform. |
| **NOW** | 🔵 ACCUMULATE | 0.83% | 1.29% | Core | ServiceNow — AI workflow automation. |

---

## III. Portfolio Weights

*Holdings and actual weights are maintained in `target-portfolio.json`.*

---

## IV. Portfolio Blueprint

### Sub-Strategy 1 — SA / ASI Race (Primary: Immediate Growth)

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **INTC** | ⚪ MAINTAIN | — | 8.85% | 8.27% | — | The Sovereign Foundry: designated US National Champion. |
| **GOOG** | ⚪ MAINTAIN | — | 4.86% | 4.51% | — | Vertically integrated AI stack. |
| **CRWV** | 🔵 ACCUMULATE | — | 4.21% | 6.18% | — | GPU cloud provider. |
| **AMD** | ⚪ MAINTAIN | — | 3.84% | 3.60% | — | Hedge against NVDA dominance. |
| **CORZ** | 🔵 ACCUMULATE | — | 2.96% | 5.05% | — | BTC→AI data center conversion. |
| **CEG** | ⚪ MAINTAIN | — | 2.96% | 3.26% | — | Nuclear operator. |
| **HUMN** | ⚪ MAINTAIN | — | 2.78% | 2.59% | — | Humanoid robotics ETF. |
| **KOID** | ⚪ MAINTAIN | — | 2.63% | 2.44% | — | Automation and robotics revolution. |
| **MSFT** | 🔥 REVIEW | — | 2.56% | 2.00% | — | Azure + OpenAI partnership. |
| **VST** | 🔥 REVIEW | — | 2.46% | 1.29% | — | Nuclear + natgas power. |
| **NBIS** | ⚪ MAINTAIN | — | 2.22% | 2.57% | — | European AI infrastructure. |
| **OKLO** | ⚪ MAINTAIN | — | 2.19% | 2.42% | — | Micro-nuclear reactor commercialization. |
| **NVDA** | 🔵 ACCUMULATE | — | 1.90% | 3.72% | — | Highest-conviction BUY. GPU monopoly. |
| **META** | ⚪ MAINTAIN | — | 1.89% | 2.00% | — | Social monopoly + AI ad flywheel. |
| **IREN** | 🔴 EXIT | — | 1.79% | 0.00% | — | EXIT: Liquidation finalized. |
| **BE** | 🔵 ACCUMULATE | — | 1.78% | 4.12% | — | Bloom Energy fuel cells. |
| **LITE** | 🔵 ACCUMULATE | — | 1.46% | 2.25% | — | Optical interconnects. |
| **VRT** | ⚪ MAINTAIN | — | 1.09% | 1.04% | — | Data center thermal management. |
| **EQT** | 🔴 EXIT | — | 1.08% | 0.00% | — | EXIT: Liquidation finalized. |
| **COHR** | 🔴 EXIT | — | 1.05% | 0.00% | — | EXIT: Liquidation finalized. |
| **Subtotal** | | **59.26%** | **68.19%** | | |

---

### Sub-Strategy 3 — Sovereign Finance (Secondary: Strategic Infrastructure)

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **CRCL** | 🟡 TRIM | — | 3.56% | 3.07% | — | Sovereign stablecoin manufacturer for AI agents. |
| **COIN** | ⚪ MAINTAIN | — | 3.02% | 2.63% | — | Regulated gateway for tokenized finance. |
| **Subtotal** | | **6.59%** | **5.70%** | | |

### Strategic Reserve

| Ticker | Thesis Action | Actual % | Target % | Conviction |
| :--- | :--- | ---: | ---: | :--- |
| **PSU-U.TO** | 🟢 INITIATE | — | 10.08% | Strategic reserve for opportunistic deployment. |

### Portfolio Totals

| | Actual % | Target % | Delta |
| :--- | ---: | ---: | ---: |
| **All holdings** | **75.45%** | **94.89%** | +19.44pp |

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
