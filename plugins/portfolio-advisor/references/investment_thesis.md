# Investment Thesis v9.4

| Field | Value |
| :--- | :--- |
| **Current Theme** | ASI Buildout (Primary) + Sovereign Finance (Secondary) |
| **Edition** | "The Compute Sovereign" |
| **Status** | ACTIVE |
| **Last Updated** | 2026-05-21 |
| **Portfolio Data** | Live — synced from Questrade via app or `python3 investment_screener/backend/src/QuestradeDataEngine.py` |
| **Latest Review** | SA LP Q1 2026 13F filed 2026-05-18 — **BARBELL STRATEGY**: ~62% semiconductor puts (SHORT chip sector) + ~25% AI infrastructure equity longs (BE, CRWV, IREN, CORZ, APLD). Portfolio nearly tripled $5.5B→$13.7B. Full filing: `investment_screener/backend/data/13f/000204572426000008.json` |

> **Living document.** The framework and sub-strategies persist across versions. Holdings, weights, and conviction details evolve. Only update this doc when conviction, structure, or macro narrative materially shifts.

---

## Version History

| Version | Date | Edition | Key Change |
| :--- | :--- | :--- | :--- |
| 9.6 | 2026-05-21 | The Compute Sovereign | Initiated CBRS (Cerebras Systems) post-IPO valuation ($342.80 weighted fair value, BUY) under Compute direct plays. |
| 9.5 | 2026-05-18 | The Compute Sovereign | SA LP Q1 2026 13F filed: **MAJOR SIGNAL SHIFT** — portfolio nearly tripled ($5.5B→$13.7B). Barbell strategy: ~62% puts on semiconductor sector (SMH $2.04B, NVDA $1.57B, ORCL $1.07B, AVGO $1.01B, AMD $969M, MU $584M, TSM $535M, ASML $494M, INTC $159M) + ~25% AI infrastructure equity longs (BE $878M #1 long, CRWV $697M, IREN $401M, CORZ $389M, APLD $320M). SNDK: $1.11B total ($724M shares + $388M calls — NOT puts). Key Validators updated. Exchange rate fallback corrected (1.0→1.38). |
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

**Key Validators:** Aschenbrenner SA LP 13F positions — Q1 2026 (filed 2026-05-18): **BARBELL SHIFT** — portfolio tripled to $13.7B. SA LP is now net SHORT the chip sector via massive puts (SMH $2.04B 14.94%, NVDA $1.57B 11.47%, ORCL $1.07B 7.84%, AVGO $1.01B 7.36%, AMD $969M 7.09%, MU $584M 4.27%, TSM $535M 3.91%, ASML $494M 3.61%, INTC $159M 1.16%) and net LONG AI infrastructure equity (BE $878M #1 long, CRWV $697M, IREN $401M, CORZ $389M, APLD $320M). SNDK $1.11B is equity long (shares + calls, NOT puts). Q4 2025 reference: INTC $746M calls, CRWV $1.21B. Pentagon AI executive orders. Hyperscaler capex reports. IEA data centre power demand forecasts.

> ⚠️ **SA LP Divergence Signal (Q1 2026):** SA LP holds puts against NVDA, AMD, INTC, AVGO, MU, TSM, and ASML — all chips in this thesis. Their longs (BE, IREN, CORZ, APLD, CRWV) align with our AI infrastructure sub-strategy. Interpretation: SA LP is NOT bearish on AI buildout — they are bearish on near-term chip sector valuations while maintaining maximum conviction in the physical infrastructure layer. This is a valuation hedge, not a thesis reversal. INTC puts ($159M) alongside their prior INTC calls ($746M Q4) suggests they see valuation risk even in sovereign foundry plays at current prices.

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
| **NVDA** | 🟢 INITIATE | — | 2.84% | Core | AI Compute Incumbent: CUDA ecosystem moat and dominant GPU supply chain. |
| **AMD** | 🟢 INITIATE | — | 3.41% | Core | Fortified #2: only credible US-based GPU competitor to NVIDIA |
| **INTC** | 🟢 INITIATE | — | 7.65% | Core | Sovereign Foundry: US national champion for onshored compute. |
| **AVGO** | 👁️ WATCHLIST | — | — | Core | Networking + custom silicon moat: irreplaceable in hyperscaler AI buildout. |
| **CRWV** | 🔵 ACCUMULATE | 4.72% | 5.86% | Core | Pure-play GPU cloud. SA #1 position. |
| **GOOG** | ⚪ MAINTAIN | 4.54% | 4.67% | Core | Foundational AI research leader. |
| **MSFT** | 🔴 EXIT | 2.47% | — | Core | Sovereign distribution channel: dominant enterprise AI via Azure + Copilot |
| **META** | 🟢 INITIATE | — | 1.89% | Core | Consumer AI Leader: open-source Llama models. |
| **NBIS** | ⚪ MAINTAIN | 2.65% | 2.87% | Speculative | Nebius AI infrastructure — early stage conviction. |
| **COHR** | 🟢 INITIATE | — | 0.95% | EXIT | Liquidation finalized. Capital better deployed in higher conviction ASI names. |
| **LITE** | 🟢 INITIATE | — | 2.13% | Speculative | Lumentum optical interconnects: photonic layer of AI networking. |
| **HUMN** | ⚪ MAINTAIN | 2.78% | 2.95% | Thematic ETF | Humanoid robotics ETF — physical embodiment of ASI |
| **KOID** | ⚪ MAINTAIN | 2.63% | 2.67% | Thematic ETF | Automation and robotics revolution. |
| **CBRS** | 👁️ WATCHLIST | — | — | Core | Monolithic Wafer-Scale AI compute engine delivering 21 PB/s memory bandwidth for ultra-high-speed reasoning and real-time agentic inference. |

#### Infrastructure Plays — Power, Cooling, Hosting & Networking

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **VST** | ⚪ MAINTAIN | 1.75% | 1.73% | Core | Largest independent US power producer. |
| **CEG** | ⚪ MAINTAIN | 2.79% | 3.09% | Core | Nuclear renaissance — clean, carbon-free baseload. |
| **VRT** | ⚪ MAINTAIN | 0.97% | 0.98% | Core | Thermal management — liquid cooling bottleneck solver. |
| **OKLO** | 🔵 ACCUMULATE | 1.84% | 2.29% | Speculative | Next-gen SMRs. |
| **BE** | 🟡 TRIM | 7.49% | 5.26% | Speculative | Bloom Energy fuel cells — clean distributed power. |
| **CORZ** | 🔵 ACCUMULATE | 4.28% | 5.21% | High-beta | Bitcoin mining converting to AI data centres. |
| **CLSK** | 🔴 EXIT | 2.77% | — | Watchlist | Bitcoin mining infrastructure watchlist. |
| **IREN** | 🟡 TRIM | 3.48% | 2.10% | EXIT | Liquidation finalized. |
| **EQT** | 🟢 INITIATE | — | 0.99% | EXIT | Liquidation finalized. |

---

### Sub-Strategy 2 — AI-Native Cybersecurity

**Conviction:** As AI capabilities advance, the attack surface expands. More AI = more attack surface = more security spend.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **PANW** | ⚪ MAINTAIN | 4.42% | 4.37% | Core | AI-native platform leader. |
| **ZS** | 🟡 TRIM | 4.05% | 3.05% | Core | Zero Trust access gateway. |

---

### Sub-Strategy 3 — Sovereign Finance (Secondary: Strategic Maturity)

**Conviction:** The global financial system is being tokenised for **AI Agents**. Bitcoin (store of value), Ethereum (settlement layer), Coinbase/Circle (infrastructure).

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **IBIT** | 👁️ WATCHLIST | — | — | Core | Digital gold: neutral, un-inflatable store of value. |
| **ETHA** | 👁️ WATCHLIST | — | — | Core | Global settlement layer. |
| **COIN** | ⚪ MAINTAIN | 2.79% | 3.00% | Core | Regulated app store for sovereign finance. |
| **CRCL** | ⚪ MAINTAIN | 3.34% | 3.71% | Core | Sovereign stablecoin manufacturer for AI agents. |

---

### Sub-Strategy 4 — Quality SaaS Resilience

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **CRM** | ⚪ MAINTAIN | 1.56% | 1.52% | Core | Salesforce — Agentforce AI platform. |
| **NOW** | 🟡 TRIM | 1.49% | 1.22% | Core | ServiceNow — AI workflow automation. |

---

### Sub-Strategy 5 — Applied AI / Frontier Bets

**Conviction:** Pre-IPO access and quantum computing represent the absolute bleeding edge of technology. These are highly speculative, asymmetric bets on hardware breakthroughs and private-market titan valuations.

| Ticker | Action | Current % | Target % | Role | Conviction Note |
| :--- | :--- | ---: | ---: | :--- | :--- |
| **DXYZ** | 🟢 INITIATE | — | 1.01% | Speculative | Only public vehicle for pre-IPO AI basket: SpaceX, Anthropic, OpenAI, xAI, Databricks. Scarcity premium play — not a value play. |
| **IONQ** | ⚪ MAINTAIN | 1.03% | 0.96% | Speculative | Quantum computing leader. |
| **RGTI** | 👁️ WATCHLIST | — | — | Speculative | Quantum hardware competitor (EXIT/Watchlist). |
| **POET** | 👁️ WATCHLIST | — | — | Speculative | Photonic packaging (EXIT/Watchlist). |

---

## III. Portfolio Weights

*Holdings and actual weights are maintained in `target-portfolio.json`.*

---

## IV. Portfolio Blueprint

*Generated 2026-05-21 · Source: `validate_weights.py` × `target-portfolio.json` × `portfolio.json` (Questrade live)*
*Portfolio value: $33,818. Refresh: `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write`*

### Sub-Strategy 1 — SA / ASI Race (Aschenbrenner Framework)

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **BE** | 🟡 TRIM | — | 7.49% | 5.26% | — | Bloom Energy fuel cells. |
| **SNDK** | 🟡 TRIM | — | 6.54% | 0.72% | — | NAND storage infrastructure play. |
| **DRAM** | 🟡 TRIM | — | 5.02% | 0.51% | — | Only US-listed vehicle for SK Hynix (25.9%) and Samsung (21.6%) HBM exposure — Nvidia's #1 and #2 HBM suppliers, not tradeable directly on US exchanges. Strategic memory play: HBM is the critical scarcity resource in AI compute scaling. Korean/Japanese memory consolidation thesis. Wait for pullback from current levels (+94.6% in 6mo) before initiating. |
| **CRWV** | 🔵 ACCUMULATE | — | 4.72% | 5.86% | — | GPU cloud provider. |
| **GOOG** | ⚪ MAINTAIN | — | 4.54% | 4.67% | — | Hyperscaler with vertically integrated AI stack. |
| **CORZ** | 🔵 ACCUMULATE | — | 4.28% | 5.21% | — | BTC→AI data center conversion thesis. |
| **IREN** | 🟡 TRIM | — | 3.48% | 2.10% | — | EXIT: Liquidation finalized. |
| **CEG** | ⚪ MAINTAIN | — | 2.79% | 3.09% | — | Largest US nuclear operator. |
| **HUMN** | ⚪ MAINTAIN | — | 2.78% | 2.95% | — | Physical embodiment of ASI thesis. |
| **NBIS** | ⚪ MAINTAIN | — | 2.65% | 2.87% | — | European AI infrastructure. |
| **KOID** | ⚪ MAINTAIN | — | 2.63% | 2.67% | — | Automation and robotics revolution. |
| **BTDR** | 🟡 TRIM | — | 2.03% | 1.52% | — | Proprietary Sealminer ASIC chip design. |
| **OKLO** | 🔵 ACCUMULATE | — | 1.84% | 2.29% | — | Micro-nuclear reactor commercialization. |
| **VST** | ⚪ MAINTAIN | — | 1.75% | 1.73% | — | Nuclear + natgas power merchant. |
| **TEAM** | ⚪ MAINTAIN | — | 1.47% | 1.32% | — | Human-agentic collaboration platform. |
| **WYFI** | 🟡 TRIM | — | 1.30% | 0.92% | — | AI GPU cloud + HPC data center. |
| **PSIX** | 🔵 ACCUMULATE | — | 1.01% | 1.72% | — | AI power infrastructure. |
| **VRT** | ⚪ MAINTAIN | — | 0.97% | 0.98% | — | Data center thermal management. |
| **INTC** | 🟢 INITIATE | — | — | 7.65% | — | The Sovereign Foundry: designated US National Champion for onshored compute manufacturing. |
| **AVGO** | 👁️ WATCHLIST | — | — | — | — | Custom ASIC + networking moat. |
| **NVDA** | 🟢 INITIATE | — | — | 2.84% | — | Highest-conviction BUY. Target increased to absorb freed capital from IREN, COHR, and EQT exits. |
| **AMD** | 🟢 INITIATE | — | — | 3.41% | — | Hedge against NVDA dominance. |
| **META** | 🟢 INITIATE | — | — | 1.89% | — | Social monopoly + AI ad flywheel. |
| **EQIX** | 👁️ WATCHLIST | — | — | — | — | Digital Geneva. |
| **ANET** | 👁️ WATCHLIST | — | — | — | — | AI networking switching fabric. |
| **LITE** | 🟢 INITIATE | — | — | 2.13% | — | Lumentum optical interconnects. |
| **COHR** | 🟢 INITIATE | — | — | 0.95% | — | EXIT: Liquidation finalized. |
| **EQT** | 🟢 INITIATE | — | — | 0.99% | — | EXIT: Liquidation finalized. |
| **TSM** | 🟢 INITIATE | — | — | 2.23% | — | The foundry backbone of the AI compute stack. |
| **ASML** | 🟢 INITIATE | — | — | 1.78% | — | Absolute monopoly on EUV lithography. |
| **MU** | 🟢 INITIATE | — | — | 1.34% | — | HBM3E memory bandwidth bottleneck. |
| **CBRS** | 👁️ WATCHLIST | — | — | — | — | Monolithic Wafer-Scale AI compute engine delivering 21 PB/s memory bandwidth for ultra-high-speed reasoning and real-time agentic inference. |
| **Subtotal** | | **57.30%** | **71.62%** | +14.32pp | |

### Sub-Strategy 2 — AI-Native Cybersecurity

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **PANW** | ⚪ MAINTAIN | — | 4.42% | 4.37% | — | AI-native platform consolidation leader. |
| **ZS** | 🟡 TRIM | — | 4.05% | 3.05% | — | Zero-trust SASE leader. |
| **CRWD** | 👁️ WATCHLIST | — | — | — | — | EXIT: DCF -66% downside. |
| **Subtotal** | | **8.46%** | **7.41%** | -1.05pp | |

### Sub-Strategy 3 — Sovereign Finance

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **CRCL** | ⚪ MAINTAIN | — | 3.34% | 3.71% | — | USDC issuer and stablecoin infrastructure for AI agents. |
| **COIN** | ⚪ MAINTAIN | — | 2.79% | 3.00% | — | Regulated crypto exchange + Base L2 growth. Settlement rail for AI Agents. |
| **ETHA** | 👁️ WATCHLIST | — | — | — | — | Ethereum as programmable settlement layer. |
| **IBIT** | 👁️ WATCHLIST | — | — | — | — | Bitcoin as sovereign reserve asset. |
| **SOLZ** | 👁️ WATCHLIST | — | — | — | — | EXIT: Solana ETF. |
| **Subtotal** | | **6.13%** | **6.72%** | +0.59pp | |

### Sub-Strategy 4 — Quality SaaS Resilience

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **CRM** | ⚪ MAINTAIN | — | 1.56% | 1.52% | — | Agentforce AI platform. |
| **NOW** | 🟡 TRIM | — | 1.49% | 1.22% | — | AI workflow automation. |
| **Subtotal** | | **3.05%** | **2.74%** | -0.31pp | |

### Sub-Strategy 5 — Applied AI / Frontier Bets

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **IONQ** | ⚪ MAINTAIN | — | 1.03% | 0.96% | — | IONQ |
| **RGTI** | 👁️ WATCHLIST | — | — | — | — | EXIT: Rigetti Computing. |
| **POET** | 👁️ WATCHLIST | — | — | — | — | EXIT: POET Technologies. |
| **DXYZ** | 🟢 INITIATE | — | — | 1.01% | — | Only public vehicle for pre-IPO AI basket: SpaceX, Anthropic, OpenAI, xAI, Databricks. Scarcity premium play — not a value play. |
| **Subtotal** | | **1.03%** | **1.96%** | +0.93pp | |

### Strategic Reserve

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **PSU-U.TO** | 🟢 INITIATE | — | — | 9.55% | — | USD cash reserve (Purpose US Cash Fund) — holds short-term USD treasuries on TSX. Primary purpose: USD currency exposure + interest income while awaiting deployment into thesis positions. Monthly dividend ~$0.31-0.33/share (~$3.68-3.90 USD annualized). ENTRY RULE: always buy 1-2 days AFTER the ex-dividend date (typically last Tuesday of month) to get the cycle-low reset price and capture the full next month of accrual. Buying mid-cycle or just before ex-date overpays for already-accrued dividend. Ex-dates: ~Jan 28, Feb 25, Mar 31, Apr 28, May 28, Jun 30 pattern. Next planned entry: May 29, 2026 (post May 28 ex-date). |
| **Subtotal** | | **0.00%** | **9.55%** | +9.55pp | |

### Untracked / Thesis Pending

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **APLD** | 🔴 EXIT | — | 3.34% | — | — | Applied Digital Corporation |
| **CLSK** | 🔴 EXIT | — | 2.77% | — | — | CLSK |
| **MSFT** | 🔴 EXIT | — | 2.47% | — | — | MSFT |
| **Subtotal** | | **8.58%** | **0.00%** | -8.58pp | |

### Portfolio Totals

| | Actual % | Target % | Delta |
| :--- | ---: | ---: | ---: |
| **All holdings** | **84.55%** | **100.00%** | +15.45pp |
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
