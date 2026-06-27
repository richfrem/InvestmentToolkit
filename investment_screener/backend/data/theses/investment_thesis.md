# Investment Thesis v9.4

| Field | Value |
| :--- | :--- |
| **Current Theme** | ASI Buildout (Primary) + Sovereign Finance (Secondary) |
| **Edition** | "The Compute Sovereign" |
| **Status** | ACTIVE |
| **Last Updated** | 2026-06-26 |
| **Thesis Last Analyzed** | 2026-05-22 (Full strategic review post-13F chip exits) |
| **13F Last Refactored** | 2026-05-22 (Refactored SA LP Q1 2026 13F filed 2026-05-18 into target-portfolio.json) |
| **Portfolio Data** | Live — synced from Questrade via app or `python3 investment_screener/backend/src/QuestradeDataEngine.py` |
| **Latest Review** | SA LP Q1 2026 13F filed 2026-05-18 — **BARBELL STRATEGY**: ~62% semiconductor puts (SHORT chip sector) + ~25% AI infrastructure equity longs (BE, CRWV, IREN, CORZ, APLD). Portfolio nearly tripled $5.5B→$13.7B. Full filing: `investment_screener/backend/data/13f/000204572426000008.json` |

> **Living document.** The framework and sub-strategies persist across versions. Holdings, weights, and conviction details evolve. Only update this doc when conviction, structure, or macro narrative materially shifts.

---

## Version History

| Version | Date | Edition | Key Change |
| :--- | :--- | :--- | :--- |
| 9.7 | 2026-06-05 | The Compute Sovereign | Grok sweep: OKLO target 2.82%→1.75% (development-stage DCF -91%); CEG target 3.84%→2.5% (no fresh catalyst, DCF -43%); GOOG re-locked to actual 4.47% (MAINTAIN). Catalyst updates: CORZ Q1 colo beat + $3.3B bond (FV $14.72→$16.08); CRWV $8.5B IG GPU financing (FV $179→$202); NBIS SA LP new 5.6% stake May 2026 (FV $516→$570); PANW Q3 beat/raise June 2 (FV $155→$168). |
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

*Detailed narratives, risk factors, and conviction frameworks for each pillar have been extracted to individual files to avoid duplication.*

- **[SA / ASI Race](../../../investment_screener/backend/data/theses/sub_strategies/asi_race.md)** (Primary: Immediate Growth)
- **[AI-Native Cybersecurity](../../../investment_screener/backend/data/theses/sub_strategies/cybersecurity.md)**
- **[Ontological AI & Operating Systems](../../../investment_screener/backend/data/theses/sub_strategies/ontological_os.md)**
- **[Sovereign Finance](../../../investment_screener/backend/data/theses/sub_strategies/sovereign_finance.md)** (Secondary: Strategic Maturity)
- **[Quality SaaS — Oversold Leaders](../../../investment_screener/backend/data/theses/sub_strategies/quality_saas.md)**
- **[Strategic Reserve](../../../investment_screener/backend/data/theses/sub_strategies/strategic_reserve.md)**
- **[Space Data Centers & Defense](../../../investment_screener/backend/data/theses/sub_strategies/space_defense.md)** (Proposed)
- **[Photonics & Optical Interconnect](../../../investment_screener/backend/data/theses/sub_strategies/photonics_optical.md)** (Proposed — Watchlist Only)
- **[Quantum Computing](../../../investment_screener/backend/data/theses/sub_strategies/quantum_computing.md)** (Partial)
- **[Robotics & Physical AI](../../../investment_screener/backend/data/theses/sub_strategies/robotics_automation.md)** (Approved — ETF Only)

Every holding in the portfolio maps to exactly one of these strategies. The skill assesses each sub-strategy as a unit — conviction intact, weakening, or broken.

---

## III. Portfolio Weights

*Holdings and actual weights are maintained in `target-portfolio.json`.*

---

## IV. Portfolio Blueprint

<!-- AUTO_UPDATE_START: portfolio_blueprint -->
*Generated 2026-06-26 · Source: `validate_weights.py` × `target-portfolio.json` × `portfolio.json` (Questrade live)*
*Portfolio value: $33,516. Refresh: `python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py --write`*

### Sub-Strategy 1 — SA / ASI Race (Aschenbrenner Framework)

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **CRWV** | ⚪ MAINTAIN | — | 5.26% | 5.23% | — | GPU cloud provider. |
| **SNDK** | 🟡 TRIM | — | 4.84% | 4.00% | — | NAND storage infrastructure play. |
| **DRAM** | ⚪ MAINTAIN | — | 4.78% | 4.45% | — | Only US-listed vehicle for SK Hynix (25.9%) and Samsung (21.6%) HBM exposure — Nvidia's #1 and #2 HBM suppliers, not tradeable directly on US exchanges. Strategic memory play: HBM is the critical scarcity resource in AI compute scaling. Korean/Japanese memory consolidation thesis. Wait for pullback from current levels (+94.6% in 6mo) before initiating. |
| **GOOG** | ⚪ MAINTAIN | — | 4.05% | 3.95% | — | Hyperscaler with vertically integrated AI stack. |
| **CORZ** | ⚪ MAINTAIN | — | 3.71% | 3.71% | — | BTC→AI data center conversion thesis. |
| **IREN** | ⚪ MAINTAIN | — | 3.11% | 3.26% | — | AI GPU cloud pivot — 800MW Australia campus + Blackwell GPU deployment + $4.4B ARR target. IREN converted from BTC mining to AI data center infrastructure. HOLD at target weight; reduce only if AI capex thesis deteriorates. |
| **BE** | ⚪ MAINTAIN | — | 2.75% | 2.97% | — | Bloom Energy fuel cells. |
| **CEG** | ⚪ MAINTAIN | — | 2.63% | 2.47% | — | Largest US nuclear operator. |
| **APLD** | ⚪ MAINTAIN | — | 2.43% | 2.47% | — | Situational Awareness LP core holding. AI data center infrastructure play aligned with SA fund thesis on ASI race build-out. |
| **NBIS** | ⚪ MAINTAIN | — | 2.28% | 2.47% | — | European AI infrastructure. |
| **CBRS** | ⚪ MAINTAIN | — | 2.25% | 2.47% | — | Monolithic Wafer-Scale AI compute engine delivering 21 PB/s memory bandwidth for ultra-high-speed reasoning and real-time agentic inference. |
| **BTDR** | 🟡 TRIM | — | 2.18% | 1.90% | — | Proprietary Sealminer ASIC chip design. |
| **VST** | ⚪ MAINTAIN | — | 1.99% | 1.88% | — | Nuclear + natgas power merchant. |
| **TEAM** | ⚪ MAINTAIN | — | 1.77% | 1.88% | — | Human-agentic collaboration platform. |
| **OKLO** | ⚪ MAINTAIN | — | 1.51% | 1.48% | — | Micro-nuclear reactor commercialization. Power pillar speculative play — same theme as BE and CEG. AI data center power demand requires diverse nuclear supply; OKLO's micro-reactor model targets co-location with data centers. |
| **PSIX** | 🔵 ACCUMULATE | — | 1.38% | 1.98% | — | AI power infrastructure. |
| **INTC** | 👁️ WATCHLIST | — | — | — | — | EXIT: Position closed 2026-06. Semis sector overextended — waiting for pullback before re-entry. Terafab JV (Intel + Tesla + SpaceX/xAI) thesis intact long-term but valuation stretched. |
| **AVGO** | 👁️ WATCHLIST | — | — | — | — | Custom ASIC + networking moat. |
| **NVDA** | 👁️ WATCHLIST | — | — | — | — | Highest-conviction BUY. Target increased to absorb freed capital from IREN, COHR, and EQT exits. |
| **AMD** | 👁️ WATCHLIST | — | — | — | — | Hedge against NVDA dominance. |
| **META** | 👁️ WATCHLIST | — | — | — | — | Social monopoly + AI ad flywheel. |
| **EQIX** | 👁️ WATCHLIST | — | — | — | — | Digital Geneva. |
| **ANET** | 👁️ WATCHLIST | — | — | — | — | AI networking switching fabric. |
| **VRT** | 👁️ WATCHLIST | — | — | — | — | Data center thermal management. |
| **EQT** | 👁️ WATCHLIST | — | — | — | — | EXIT: Position closed. Not held. |
| **WYFI** | 👁️ WATCHLIST | — | — | — | — | AI GPU cloud + HPC data center. |
| **TSM** | 👁️ WATCHLIST | — | — | — | — | The foundry backbone of the AI compute stack. |
| **ASML** | 👁️ WATCHLIST | — | — | — | — | Absolute monopoly on EUV lithography. |
| **MU** | 👁️ WATCHLIST | — | — | — | — | HBM3E memory bandwidth bottleneck. |
| **Subtotal** | | **46.92%** | **46.56%** | -0.35pp | |

### Sub-Strategy 2 — AI-Native Cybersecurity

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **ZS** | ⚪ MAINTAIN | — | 4.40% | 4.45% | — | Zero-trust SASE leader. |
| **PANW** | ⚪ MAINTAIN | — | 4.34% | 4.45% | — | AI-native platform consolidation leader. |
| **CRWD** | 👁️ WATCHLIST | — | — | — | — | EXIT: DCF -66% downside. |
| **Subtotal** | | **8.74%** | **8.90%** | +0.16pp | |

### Sub-Strategy 3 — Sovereign Finance

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **COIN** | ⚪ MAINTAIN | — | 2.74% | 2.97% | — | Regulated crypto exchange + Base L2 growth. Settlement rail for AI Agents. |
| **CRCL** | ⚪ MAINTAIN | — | 2.65% | 2.72% | — | USDC issuer and stablecoin infrastructure for AI agents. |
| **ETHA** | 👁️ WATCHLIST | — | — | — | — | Ethereum as programmable settlement layer. |
| **IBIT** | 👁️ WATCHLIST | — | — | — | — | Bitcoin as sovereign reserve asset. |
| **SOLZ** | 👁️ WATCHLIST | — | — | — | — | EXIT: Solana ETF. |
| **Subtotal** | | **5.39%** | **5.68%** | +0.29pp | |

### Sub-Strategy 4 — Quality SaaS Resilience

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **CRM** | ⚪ MAINTAIN | — | 1.78% | 1.88% | — | Agentforce AI platform. |
| **NOW** | 🔵 ACCUMULATE | — | 1.59% | 1.88% | — | AI workflow automation. |
| **Subtotal** | | **3.37%** | **3.76%** | +0.39pp | |

### Sub-Strategy 5 — Applied AI / Frontier Bets

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **POET** | 👁️ WATCHLIST | — | — | — | — | EXIT: POET Technologies. |
| **DXYZ** | 👁️ WATCHLIST | — | — | — | — | Only public vehicle for pre-IPO AI basket: SpaceX, Anthropic, OpenAI, xAI, Databricks. Scarcity premium play — not a value play. |
| **Subtotal** | | **0.00%** | **0.00%** | — | |

### Strategic Reserve

| Ticker | Thesis Action | AI Signal | Actual % | Target % | Upside | Conviction |
| :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **PSU-U.TO** | 🔵 ACCUMULATE | — | 15.74% | 18.65% | — | USD cash reserve (Purpose US Cash Fund) — holds short-term USD treasuries on TSX. Primary purpose: USD currency exposure + interest income while awaiting deployment into thesis positions. Monthly dividend ~$0.31-0.33/share (~$3.68-3.90 USD annualized). ENTRY RULE: always buy 1-2 days AFTER the ex-dividend date (typically last Tuesday of month) to get the cycle-low reset price and capture the full next month of accrual. Buying mid-cycle or just before ex-date overpays for already-accrued dividend. Ex-dates: ~Jan 28, Feb 25, Mar 31, Apr 28, May 28, Jun 30 pattern. Next planned entry: May 29, 2026 (post May 28 ex-date). |
| **Subtotal** | | **15.74%** | **18.65%** | +2.91pp | |

### Portfolio Totals

| | Actual % | Target % | Delta |
| :--- | ---: | ---: | ---: |
| **All holdings** | **80.16%** | **83.55%** | +3.39pp |
| *Validate* | `python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode both` | | |
<!-- AUTO_UPDATE_END: portfolio_blueprint -->

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
