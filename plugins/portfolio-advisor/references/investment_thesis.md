# Investment Thesis v8.4

| Field | Value |
| :--- | :--- |
| **Current Theme** | ASI Buildout + Sovereign Finance + AI-Native Defence |
| **Edition** | "The Sovereign Manufacturer" |
| **Status** | ACTIVE |
| **Last Updated** | 2026-05-04 |
| **Portfolio Data** | Live — synced from Questrade via app or `python3 investment_screener/backend/src/QuestradeDataEngine.py` |
| **Latest Review** | `PortfolioAnalysis/strategic-reviews/2026-05-03-PortfolioAnalysisRecommendations.md` |

> **Living document.** The framework and sub-strategies persist across versions. Holdings, weights, and conviction details evolve. Only update this doc when conviction, structure, or macro narrative materially shifts.

---

## Version History

| Version | Date | Edition | Key Change |
| :--- | :--- | :--- | :--- |
| 8.2 | 2026-05-03 | The Sovereign Manufacturer | Exhaustive SA LP Q4 2025 13F cross-reference; EXIT AVGO/EQIX/ANET (price > FV, no SA LP); add SNDK/PSIX (SA LP + DCF BUY); USD_CASH and PSU-U.TO decoupled; hard gates added to agent skill |
| 8.1 | 2026-05-03 | The Sovereign Manufacturer | First-pass AI target recommendations from DCF corpus; INTC/CRWV conviction raised; NVDA/META capped at 3%; no-change positions locked (GOOG/crypto/ETFs) |
| 7.5 | 2026-05-02 | The Sovereign Manufacturer | Cybersecurity elevated to standalone sub-strategy; datacenter-infra merged into SA/ASI Race as infrastructure plays; 5 named sub-strategies |
| 7.4 | 2026-05-02 | The Sovereign Manufacturer | Refactored from pillars to sub-strategies; 5 named conviction frameworks |
| 7.3 | 2026-05-02 | The Sovereign Manufacturer | INTC Terafab/14A validated, SA 13F conviction confirmed, CRWV elevated |
| 7.2 | 2026-04-13 | The Sovereign Manufacturer | GENIUS Act enacted; CRCL added; cash position optimised |
| 7.1 | 2026-02-14 | The Fortified Barbell | Security restructured; ZS added; CRWD conviction reviewed |
| 7.0 | 2025-11-01 | The Twin Revolutions | Initial formalisation of dual-front thesis framework |

---

## I. Core Premise

This strategy is built on a single macro conviction: **the 2020s will be defined by two simultaneous civilisational-scale competitions**, and losing either front means losing strategic dominance for a generation.

**The ASI Race** — Control of intelligence, decision-making, and technological supremacy. No longer a commercial competition — it is a national security priority analogous to the Manhattan Project. This forces a structural shift from *"most efficient"* to *"most sovereign"*, mandating onshoring of critical technology and resilient supply chains. The CHIPS Act and executive AI orders create a powerful, state-sponsored tailwind for designated domestic champions.

**The Sovereign Finance Race** — Control of value, monetary systems, and debt monetisation via digital assets. The global financial system is being tokenised. The US counter-strategy (GENIUS Act of 2025) establishes federal stablecoin rails built on Bitcoin (store of value) and Ethereum (global settlement layer), creating a perpetual structural bid for US Treasuries.

**The Feedback Loop** — Both fronts are self-reinforcing. Winning ASI requires capital; winning Sovereign Finance provides it.

> **Investment Philosophy:** *"Builder-First, Empire-Second."* Own the foundational, physically-constrained, sovereign-critical **infrastructure** required to dominate both fronts — not the application layer built on top of it.

---

## II. Sub-Strategies

*Five named conviction frameworks. Every holding maps to exactly one. The skill assesses each sub-strategy as a unit — conviction intact, weakening, or broken.*

---

### Sub-Strategy 1 — SA / ASI Race (Aschenbrenner Framework)

**Conviction:** Aschenbrenner's *Situational Awareness* thesis is playing out. The transition from narrow AI to AGI/ASI is a national security emergency. The US government has designated AI compute a strategic resource — creating a durable, state-backed tailwind that runs through two distinct investment layers:

- **Direct Plays** — The silicon, software, and EDA tooling that produces and runs AI models. These are the companies whose revenue is directly denominated in AI compute demand: chip designers, foundries, GPU clouds, hyperscalers, and the EDA duopoly every chip must pass through.
- **Infrastructure Plays** — The physical facilities, power supply, cooling, networking, and hosting that AI data centres require. These are scarce, capital-intensive real assets with multi-year construction backlogs. Demand is model-agnostic — regardless of who wins the AI application layer, the infrastructure must be built and powered. Bitcoin mining companies converting to AI hosting are a high-beta play on this transition.

Both layers derive from the same root conviction. They are not separate theses.

**Conviction Intact When:** US-China AI competition continues. CHIPS Act funding flows. Pentagon treats compute as strategic. Hyperscalers keep accelerating capex. Data centre construction backlogs remain multi-year. AI compute demand continues to exceed power and cooling supply.

**Thesis Breaker:** US-China technological de-escalation removes national security urgency for sovereign compute. Algorithmic efficiency breakthrough (Chinchilla-scale) collapses compute demand. Room-temperature superconductors eliminate cooling bottlenecks.

**Key Validators:** Aschenbrenner SA LP 13F positions (Q4 2025: INTC $746M calls, CRWV $1.21B). Pentagon AI executive orders. Hyperscaler capex reports. IEA data centre power demand forecasts.

#### Direct Plays — Silicon, Software & EDA

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **NVDA** | 🔵 ACCUMULATE | 0.94% | 3.45% | Core | AI Compute Incumbent: CUDA ecosystem moat and dominant GPU supply chain. Holds regardless of who wins the application layer. |
| **AMD** | ⚪ MAINTAIN | 3.29% | 3.33% | Core | Fortified #2: only credible US-based GPU competitor to NVIDIA |
| **INTC** | ⚪ MAINTAIN | 11.30% | 10.73% | Core | Sovereign Foundry: US national champion for onshored compute. 14A/Terafab catalyst. SA 13F $746M. |
| **AVGO** | 👁️ WATCHLIST | — | — | Core | Networking + custom silicon moat: irreplaceable in hyperscaler AI buildout. SA Q2 2025 $1.1B position. |
| **CRWV** | 🔵 ACCUMULATE | 4.48% | 5.72% | Core | Pure-play GPU cloud. SA #1 position $1.21B combined. Accumulate urgently. |
| **GOOG** | ⚪ MAINTAIN | 4.81% | 4.79% | Core | Foundational AI research leader — DeepMind, Gemini. Algorithmic breakthrough hedge. |
| **MSFT** | ⚪ MAINTAIN | 2.66% | 2.98% | Core | Sovereign distribution channel: dominant enterprise AI via Azure + Copilot |
| **META** | 🔵 ACCUMULATE | 0.97% | 3.45% | Core | Consumer AI Leader: open-source Llama models + massive consumer distribution |
| **ANET** | 👁️ WATCHLIST | — | — | Core | Networking spine: backbone of hyperscaler AI buildout |
| **NBIS** | 🔵 ACCUMULATE | 1.10% | 2.38% | Speculative | Nebius AI infrastructure — early stage conviction, former Yandex Cloud |
| **COHR** | 🔵 ACCUMULATE | 1.05% | 1.49% | Speculative | Optical networking components: coherent optics for AI compute interconnect |
| **LITE** | 🔵 ACCUMULATE | 0.77% | 2.08% | Speculative | Lumentum optical interconnects: photonic layer of AI networking. SA LP holding. |
| **HUMN** | ⚪ MAINTAIN | 2.77% | 2.76% | Thematic ETF | Humanoid robotics ETF — physical embodiment of ASI |
| **KOID** | ⚪ MAINTAIN | 2.62% | 2.61% | Thematic ETF | KraneShares humanoid ETF — automation and robotics revolution |

#### Infrastructure Plays — Power, Cooling, Hosting & Networking

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **VST** | 🔥 REVIEW | 3.57% | 1.19% | Core | Largest independent US power producer — reliable baseload for AI compute at scale |
| **CEG** | ⚪ MAINTAIN | 3.08% | 3.02% | Core | Nuclear renaissance — clean, carbon-free baseload for data centre energy demand |
| **EQIX** | 👁️ WATCHLIST | — | — | Core | Digital Geneva: critical physical nexus where compute and sovereign finance interconnect |
| **VRT** | ⚪ MAINTAIN | 1.04% | 0.96% | Core | Thermal management — liquid cooling bottleneck solver for high-density AI clusters |
| **OKLO** | ⚪ MAINTAIN | 2.27% | 2.24% | Speculative | Next-gen SMRs — binary NRC outcome, capped position. Fission future bet. |
| **BE** | 🔵 ACCUMULATE | 0.90% | 3.81% | Speculative | Bloom Energy fuel cells — clean distributed power for data centre edge. SA LP holding. |
| **CORZ** | 🔵 ACCUMULATE | 1.99% | 4.67% | High-beta | Bitcoin mining converting to AI data centres — pure infrastructure play |
| **IREN** | 🔴 EXIT | 1.61% | — | High-beta | AI data centre and Bitcoin mining — high-beta infrastructure bet |
| **EQT** | ⚪ MAINTAIN | 1.13% | 1.19% | Macro hedge | Natural gas infrastructure — energy security + structural AI power demand floor |

---

### Sub-Strategy 2 — AI-Native Cybersecurity

**Conviction:** As AI capabilities advance, the attack surface expands and the sophistication of threats scales proportionally. AI agents now autonomously discover zero-days, craft spear-phishing at scale, and probe infrastructure 24/7. The *Claude* model family and frontier AI labs have publicly demonstrated AI-assisted vulnerability discovery — validating that AI-powered offence is already operational. The SaaSocalypse narrative (AI eating SaaS growth) does **not** apply here: cybersecurity demand is *structurally coupled to AI adoption*, not threatened by it. More AI = more attack surface = more security spend. AI-native platforms that embed intelligence into detection, response, and zero-trust access are the clear beneficiaries. This is a sovereign-critical layer — the onshored AI supply chain and the new financial system both require it.

**Conviction Intact When:** Cyber attack frequency and sophistication keep rising with AI model capability. Enterprise zero-trust adoption accelerating. AI-native security platforms taking share from legacy SIEM/endpoint. No single AI-native disruptor captures >20% of PANW's or ZS's addressable market.

**Thesis Breaker:** A single AI-native security platform achieves commoditisation across detection, response, and access — eliminating the platform premium for PANW/ZS. Quantum decryption makes current security architectures obsolete without a viable post-quantum replacement.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **PANW** | ⚪ MAINTAIN | 4.74% | 4.74% | Core | AI-native platform leader: Cortex XSIAM unifies SOC, endpoint, and network. Secures the sovereign AI supply chain. |
| **ZS** | ⚪ MAINTAIN | 3.18% | 2.98% | Core | Zero Trust access gateway: AI-native SASE for distributed AI workforce. BUY-rated. |
| **CRWD** | 🔴 EXIT | 2.98% | — | EXIT | Endpoint leader structurally damaged by July 2024 global outage. Route weight to ZS. |

---

### Sub-Strategy 3 — Sovereign Finance

**Conviction:** The global financial system is being tokenised. The GENIUS Act (enacted 2025) establishes regulated stablecoin rails requiring every dollar of new stablecoins to be backed by US Treasuries — a perpetual structural bid for US government debt. Bitcoin is the neutral reserve asset. Ethereum is the programmable settlement layer for RWAs. Coinbase and Circle are the regulated picks-and-shovels plays on this transition.

**Conviction Intact When:** GENIUS Act framework is intact. Stablecoin adoption growing. RWA tokenisation expanding. Bitcoin holds monetary reserve narrative.

**Thesis Breaker:** GENIUS Act repealed or SEC court victory classifies ETH as security. USDC de-peg sustained beyond 48 hours.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **IBIT** | ⚪ MAINTAIN | 2.60% | 2.59% | Core | Digital gold: neutral, un-inflatable store of value and pristine digital reserve asset |
| **ETHA** | ⚪ MAINTAIN | 3.81% | 3.79% | Core | Global settlement layer: Ethereum as programmable rail for RWA tokenisation |
| **COIN** | ⚪ MAINTAIN | 3.28% | 3.26% | Core | Regulated app store for sovereign finance: primary US gateway and picks-and-shovels |
| **CRCL** | ⚪ MAINTAIN | 2.59% | 2.58% | Core | Sovereign stablecoin manufacturer: pure-play builder of the regulated digital dollar (USDC) |
| **SOLZ** | 🔴 EXIT | 1.36% | — | Speculative | Solana ecosystem ETF — high-throughput payments layer, speculative allocation |

---

### Sub-Strategy 4 — Quality SaaS Resilience

**Conviction:** The AI boom has indiscriminately oversold high-quality SaaS companies with strong bottom-line profit, durable growth, and mission-critical enterprise relationships. These companies will not be displaced by AI — they will embed it into their platforms and compound through the cycle. The market is pricing them as AI casualties; the reality is they are AI beneficiaries with a moat. This thesis is **distinct from the SaaSocalypse risk** — only companies with genuine platform lock-in, high net retention, and active AI product integration qualify.

**Conviction Intact When:** Revenue growth stays positive. Net retention above 110%. AI product integration (Agentforce, Now Assist) progressing. Operating margins expanding.

**Thesis Breaker:** An AI-native replacement captures >20% of the addressable market. Revenue growth decelerates below 10% YoY on a sustained basis.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **CRM** | 🔵 ACCUMULATE | 0.90% | 1.19% | Core | Salesforce — Agentforce AI platform built on the world's largest CRM dataset |
| **NOW** | 🔵 ACCUMULATE | 0.90% | 1.19% | Core | ServiceNow — AI workflow automation embedded in enterprise IT infrastructure |

---

### Sub-Strategy 5 — Applied AI / Frontier Bets

**Conviction:** Small, asymmetric positions in early-stage or speculative AI-adjacent themes. These are binary bets — sized accordingly (≤2% each). The thesis is optionality, not certainty. Each requires its own catalyst for conviction to increase.

**Sizing Rule:** No single frontier bet exceeds 2% of portfolio. Aggregate frontier exposure capped at 8%.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **TEM** | 🔴 EXIT | 1.76% | — | Applied AI | Tempus AI — AI-native healthcare data platform, applied AI in regulated industry |

| RGTI | Quantum | Rigetti Computing — quantum compute exposure, binary milestone outcome |
| POET | Photonics | POET Technologies — photonic integrated circuits, optical compute interconnect bet |

---

## III. Portfolio Weights

Portfolio holdings and actual weights are maintained in `target-portfolio.json` and updated live from Questrade.

**To refresh portfolio from broker:**
```bash
# Option 1: Via the app (recommended)
python3 run_investment_toolkit.py
# Then: POST http://localhost:3001/api/portfolio/sync-questrade

# Option 2: Direct Python call
python3 investment_screener/backend/src/QuestradeDataEngine.py --sync
```

**To view current health vs targets:**
```bash
curl -s http://localhost:3001/api/theses/target-portfolio/health | python3 -m json.tool
```

Each holding in `target-portfolio.json` carries a `subStrategyId` field mapping it to one of the five sub-strategies above. The strategic review skill uses this to assess sub-strategy-level health, not just individual holding drift.

**Sub-strategy IDs** (used in `target-portfolio.json`):

| subStrategyId | Sub-Strategy |
| :--- | :--- |
| `sa-asi-race` | Sub-Strategy 1 — SA / ASI Race |
| `cybersecurity` | Sub-Strategy 2 — AI-Native Cybersecurity |
| `sovereign-finance` | Sub-Strategy 3 — Sovereign Finance |
| `quality-saas` | Sub-Strategy 4 — Quality SaaS Resilience |
| `frontier-bets` | Sub-Strategy 5 — Applied AI / Frontier Bets |
| `cash` | Strategic Reserve |

**Strategic Reserve (Cash):**

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **PSU-U.TO** | 🟢 INITIATE | — | 9.33% | Reserve | Purpose US Cash Fund — high-yield USD cash providing tactical optionality for market dislocations |

---

## IV. Scenario Framework

### Base Case
- US-China strategic competition continues in technology and finance
- CHIPS Act investment flows sustain domestic semiconductor expansion
- GENIUS Act framework drives regulated stablecoin adoption
- AI compute demand continues to exceed supply
- Cyber threat sophistication rises in lockstep with frontier model capability

### Upside
- US achieves decisive ASI lead; allied nations adopt US sovereign finance rails
- INTC 14A/Terafab executes ahead of schedule; tier-1 design win announced
- Stablecoin adoption accelerates, creating structural Treasury demand overshoot
- AI-native security platforms achieve platform consolidation (PANW wins the SOC)

### Downside
- Rapid geopolitical de-escalation removes national security tailwind for onshored compute
- Chinchilla-scale efficiency breakthrough dramatically reduces compute demand
- Hostile regulatory reversal of GENIUS Act
- SaaSocalypse accelerates beyond CRM/NOW platform moat

---


## IV. Portfolio Blueprint

*Generated 2026-05-04 · Source: `validate_weights.py` × `target-portfolio.json` × `portfolio.json` (Questrade live)*
*Portfolio value: $31,425. Refresh: `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write`*

### Sub-Strategy 1 — SA / ASI Race (Aschenbrenner Framework)

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **INTC** | ⚪ MAINTAIN | — | 11.30% | 10.73% | — | The Sovereign Foundry: designated US National Champion for onshored compute manufacturing. Core contrarian bet on 18A node. Target restored to 11.04% (2026-05-03): Terafab manufacturing partnership (Tesla/SpaceX/xAI AI compute) confirms first tier-1 hyperscaler-class design win on 18A — the thesis catalyst. 18A yield improvements reported. Do not trim before HVM data. |
| **GOOG** | ⚪ MAINTAIN | — | 4.81% | 4.79% | — | Hyperscaler with vertically integrated AI stack: TPUs, Gemini models, Search, YouTube, GCP. Increased from 6% — underweight given AI monetization runway. |
| **CRWV** | 🔵 ACCUMULATE | — | 4.48% | 5.72% | — | GPU cloud provider with hyperscaler-grade infrastructure. Microsoft/OpenAI anchor customer. Meta $21B+ contract expansion (2026-05-03) confirms hyperscaler demand; $8.5B investment-grade financing is the first IG credit for any GPU cloud company. |
| **VST** | 🔥 REVIEW | — | 3.57% | 1.19% | — | Nuclear + natgas power merchant for data center load growth. Trimmed from 4.43% — power thesis still valid but reduce overweight. |
| **AMD** | ⚪ MAINTAIN | — | 3.29% | 3.33% | — | Hedge against NVDA dominance. MI300X gaining traction in inference. Slight increase from 2.7%. |
| **CEG** | ⚪ MAINTAIN | — | 3.08% | 3.02% | — | Largest US nuclear operator. Microsoft data center deal secured. DCF TRIM -35% — reduced from 4.42% on regulatory compression risk. Maintain small core. |
| **HUMN** | ⚪ MAINTAIN | — | 2.77% | 2.76% | — | Physical embodiment of ASI thesis — humanoid robotics ETF. Increased from 2.88%. |
| **MSFT** | ⚪ MAINTAIN | — | 2.66% | 2.98% | — | Azure + OpenAI partnership. Copilot monetization slower than expected — reduced from 3.7%. Maintain as infrastructure hedge. |
| **KOID** | ⚪ MAINTAIN | — | 2.62% | 2.61% | — | Automation and robotics revolution — China + global exposure. Increased from 2.49%. |
| **OKLO** | ⚪ MAINTAIN | — | 2.27% | 2.24% | — | Micro-nuclear reactor commercialization. Binary bet on NRC licensing. Increased from 1.35% — conviction on data center power timeline. |
| **CORZ** | 🔵 ACCUMULATE | — | 1.99% | 4.67% | — | BTC→AI data center conversion thesis. Pecos campus expanding to 1.5 GW for AI (2026-05-03); $3.3B bond raise funds hyperscale data center buildout; ongoing CoreWeave partnership anchor. Execution is materially ahead of DCF assumptions. |
| **IREN** | 🔴 EXIT | — | 1.61% | — | — | EXIT: IREN AI data centre + Bitcoin mining — high-beta physical infra bet. DCF SELL -15%. |
| **EQT** | ⚪ MAINTAIN | — | 1.13% | 1.19% | — | EXIT: EQT natural gas infrastructure — gas commodity, near breakeven. DCF SELL -18%. |
| **NBIS** | 🔵 ACCUMULATE | — | 1.10% | 2.38% | — | DCF BUY +186% upside. Former Yandex Cloud team building European AI infrastructure. INITIATE — DCF conviction overrides thesis EXIT flag. |
| **COHR** | 🔵 ACCUMULATE | — | 1.05% | 1.49% | — | EXIT: Coherent optics — near fair value. Capital better deployed elsewhere. |
| **VRT** | ⚪ MAINTAIN | — | 1.04% | 0.96% | — | Data center thermal management. AI cooling bottleneck play. DCF SELL -32% — maintain small position, thesis is real but valuation stretched. |
| **META** | 🔵 ACCUMULATE | — | 0.97% | 3.45% | — | Social monopoly + AI ad flywheel. DCF BUY +82% upside. Llama open-source creating massive ecosystem leverage. Increased from 3% — strong conviction. |
| **NVDA** | 🔵 ACCUMULATE | — | 0.94% | 3.45% | — | Highest-conviction BUY in corpus (+124% DCF upside). GPU monopoly for AI training. Increased from 4.4% — needs to be a core position. |
| **BE** | 🔵 ACCUMULATE | — | 0.90% | 3.81% | — | Bloom Energy fuel cells — clean distributed power for data centre edge. Oracle AI data center fuel cell deal up to 2.8 GW (2026-05-03); strong Q1 results. SA LP top power holding. |
| **WYFI** | ⚪ MAINTAIN | — | 0.85% | 0.90% | — | AI GPU cloud + HPC data center. DCF BUY +92%. SA LP Q4 2025 NEW position. BTBT subsidiary. Speculative — monitor Q2 2026 revenue >M. |
| **LITE** | 🔵 ACCUMULATE | — | 0.77% | 2.08% | — | Lumentum optical interconnects — photonic layer of AI networking. SA LP holding. |
| **BTDR** | 🔵 ACCUMULATE | — | 0.71% | 1.49% | — | Proprietary Sealminer ASIC chip design — structural cost moat over pure BTC miners. DCF BUY +103%. SA LP Q4 2025 increased 92%. ASIC capability aligns with compute thesis. |
| **PSIX** | ⚪ MAINTAIN | — | 0.45% | 0.47% | — | SA LP NEW position Q4. DCF BUY +51.9%. AI power infrastructure — industrial engine/generator systems. |
| **AVGO** | 👁️ WATCHLIST | — | — | — | — | Custom ASIC + networking moat. Google TPU and Meta MTIA are multi-year engagements. DCF shows -22% short-term but the thesis is multi-year platform lock-in. |
| **EQIX** | 👁️ WATCHLIST | — | — | — | — | Digital Geneva — carrier-neutral colocation in every major financial market. Increased from 2.88%. Not yet owned — INITIATE. |
| **ANET** | 👁️ WATCHLIST | — | — | — | — | AI networking switching fabric. Hyperscaler capex flows through ANET. Near fair value — hold and accumulate on pullbacks. |
| **SNDK** | 🟢 INITIATE | — | — | 0.70% | — | SA LP +1839% Q4. DCF BUY +26.4%. AI-era NAND storage infrastructure play. |
| **Subtotal** | | **54.37%** | **66.40%** | +12.03pp | |

### Sub-Strategy 2 — AI-Native Cybersecurity

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **PANW** | ⚪ MAINTAIN | — | 4.74% | 4.74% | — | AI-native platform consolidation leader. Platformization model winning enterprise. Increased from 3.85% — cybersecurity pillar was underweight. |
| **ZS** | ⚪ MAINTAIN | — | 3.18% | 2.98% | — | Zero-trust SASE leader. Network security moving to cloud-native model. Increased from 2.04%. |
| **CRWD** | 🔴 EXIT | — | 2.98% | — | — | EXIT: DCF -66% downside. Structural outage damage (July 2024) confirmed ongoing customer attrition. Reputational capital permanently impaired at the enterprise level. |
| **Subtotal** | | **10.91%** | **7.72%** | -3.19pp | |

### Sub-Strategy 3 — Sovereign Finance

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **ETHA** | ⚪ MAINTAIN | — | 3.81% | 3.79% | — | Ethereum as programmable settlement layer. Staking yield embedded in ETF. Slight increase from 3.77%. |
| **COIN** | ⚪ MAINTAIN | — | 3.28% | 3.26% | — | Regulated crypto exchange + Base L2 growth. Increased from 3.48%. |
| **IBIT** | ⚪ MAINTAIN | — | 2.60% | 2.59% | — | Bitcoin as sovereign reserve asset. US strategic reserve narrative accelerating. Increased from 3.2%. |
| **CRCL** | ⚪ MAINTAIN | — | 2.59% | 2.58% | — | USDC issuer and stablecoin infrastructure. GENIUS Act tailwind. |
| **SOLZ** | 🔴 EXIT | — | 1.36% | — | — | EXIT: Solana ETF — high-throughput payments layer. Speculative, no clear catalyst for re-entry. |
| **Subtotal** | | **13.65%** | **12.22%** | -1.43pp | |

### Sub-Strategy 4 — Quality SaaS Resilience

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **NOW** | 🔵 ACCUMULATE | — | 0.90% | 1.19% | — | DCF BUY +45% upside. AI workflow automation embedded in enterprise IT infrastructure. Small position — thesis EXIT overridden by DCF valuation gap. |
| **CRM** | 🔵 ACCUMULATE | — | 0.90% | 1.19% | — | DCF BUY +53% upside. Agentforce AI platform on world's largest CRM dataset. Small position — thesis EXIT overridden by DCF valuation gap. |
| **Subtotal** | | **1.80%** | **2.38%** | +0.58pp | |

### Sub-Strategy 5 — Applied AI / Frontier Bets

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **POET** | 🔴 EXIT | — | 1.98% | — | — | EXIT: POET Technologies — photonic integrated circuits. DCF STRONG SELL -86%. Pre-commercial. |
| **TEM** | 🔴 EXIT | — | 1.76% | — | — | EXIT: Tempus AI — AI-native healthcare data platform. DCF HOLD -2%. Not core to thesis. |
| **RGTI** | 👁️ WATCHLIST | — | — | — | — | EXIT: Rigetti Computing — quantum compute exposure. DCF STRONG SELL -94%. Pre-commercial. |
| **Subtotal** | | **3.74%** | **0.00%** | -3.74pp | |

### Strategic Reserve

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **PSU-U.TO** | 🟢 INITIATE | — | — | 9.33% | — | Strategic reserve for opportunistic deployment. Reduced from 13% to fund NVDA, META, and NBIS initiations. |
| **Subtotal** | | **0.00%** | **9.33%** | +9.33pp | |

### Portfolio Totals

| | Actual % | Target % | Delta |
| :--- | ---: | ---: | ---: |
| **All holdings** | **84.46%** | **98.05%** | +13.59pp |
| *Validate* | `python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode both` | | |


---


## V. Risk Factors

| Risk | Trigger Condition | Hedge / Mitigation |
| :--- | :--- | :--- |
| INTC execution failure | 18A delay past Q4 2026 or no tier-1 customer | NVDA/AMD long; AVBO position |
| Algorithmic efficiency breakthrough | Compute demand falls despite model growth | GOOG long (research leader) |
| TSMC moat insurmountable | Intel IFS commercially non-viable | NVDA direct position |
| Crypto regulatory reversal | GENIUS Act repealed or ETH classified as security | Position caps: COIN, CRCL ≤5% each |
| Geopolitical de-escalation | Taiwan resolution removes urgency | Power/energy positions valid regardless |
| Monetary shock | Fed pivot + dollar stress | IBIT as uncorrelated reserve asset |
| SaaS AI displacement | AI-native replacement >20% TAM capture | Position capped, monitor net retention |
| Cyber AI arms race backfire | Offensive AI outpaces defensive AI by >2 model generations | PANW + ZS platform consolidation hedge |

---

## VI. Thesis Breakers & Sell Discipline

| Holding | Breaker Conditions |
| :--- | :--- |
| **INTC** | 18A HVM delay past Q4 2026 · No tier-1 design win by EOY 2026 · CEO departure without IFS-committed successor |
| **COIN** | GENIUS Act repealed · Base L2 fails top-3 by volume · Major hack impairing brand trust |
| **CRCL** | Failure to secure federal charter · USDC de-peg >48hrs · Sustained market share loss |
| **OKLO** | Definitive NRC rejection without remediation path |
| **CRWD** | Already EXIT — structural damage from July 2024 outage |
| **CRM / NOW** | AI-native replacement >20% TAM · Net retention falls below 105% for 2 consecutive quarters |

**General Discipline:**
- Holding where thesis-for-inclusion is no longer true → full review within 30 days
- Any holding at 2× target weight without conviction reaffirmation → trim to target
- TRIM/EXIT-rated position deferred >90 days → escalate to `/strategic-review`

---

## VII. Supporting Research

| Source | Relevance |
| :--- | :--- |
| Aschenbrenner (2024) *Situational Awareness* — [situational-awareness.ai](https://situational-awareness.ai) | Core ASI Race thesis framework |
| SA LP Q4 2025 13F — [13f.info](https://13f.info/13f/000204572426000002-situational-awareness-lp-q4-2025) | INTC $746M calls, CRWV $1.21B |
| Intel 18A Platform Brief (Mar 2025) — [intel.com](https://www.intel.com/content/dam/www/central-libraries/us/en/documents/2025-03/foundry-18a-platform-brief.pdf) | INTC execution evidence |
| GENIUS Act (H.R. 5150, enacted 2025) — [congress.gov](https://www.congress.gov/bill/118/hr5150) | Sovereign Finance legal framework |
| IEA Electricity 2024 — [iea.org](https://www.iea.org/reports/electricity-2024) | Data centre power demand evidence |
| Anthropic (2025) *Claude frontier security research* | AI-native cyber offence validates security sub-strategy |

---

## VIII. Red Team Reviews

| Date | Reviewer | Score | Key Finding |
| :--- | :--- | :--- | :--- |
| Nov 2025 | Grok AI | 8/10 | Core framework valid. Primary risk: Intel execution (~11% position). Hedges appropriate. |
| 2026-05-02 | Claude Sonnet 4.6 | — | INTC breakers resolved. CRWV elevated to URGENT ACCUMULATE. Thesis refactored to 5 sub-strategies. |
| 2026-05-02 | Claude Sonnet 4.6 | — | Cybersecurity elevated to standalone sub-strategy. Datacenter-infra merged into SA/ASI Race as infrastructure plays. v7.5. |
