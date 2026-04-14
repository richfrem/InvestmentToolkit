# InvestmentToolkit

A premium, "Luxury Dark Mode" investment analysis suite built for sophisticated retail investors. This toolkit provides deep fundamental analysis, valuation modeling, and comparative screening without the need for expensive terminal subscriptions.

## 🌟 Core Components

### 1. Investment Screener (`investment_screener`)
A web-based financial analysis dashboard featuring:
-   **Luxury Dark Mode**: Professional Black/Gold aesthetic.
-   **Expert Metrics**: Instant access to PEG Ratio, Piotroski F-Score, and Insider Ownership.
-   **Valuation Modeler**: Interactive Bear/Base/Bull scenario modeling to project 5-year price targets.
-   **Comparative Analysis**: Side-by-side ticker comparison.

### 2. Questrade Portfolio Integration
A professional-grade brokerage sync engine featuring:
-   **Dynamic Sync**: Real-time retrieval of account positions and balances.
-   **Secure Token Bridge**: AES-256-GCM encryption with hardware-backed master keys (macOS Keychain).
-   **Metadata Enrichment**: Intelligent fallback to `yfinance` for sector/industry categorization of broker holdings.
-   **Onboarding Flow**: Guided UI for secure account linking and rotation management.

### Stock Analysis & Metrics
![Analysis Metrics](investment_screener/assets/images/analysis_metrics.png)
*(15+ Premium metrics including Rule of 40, Piotroski F-Score, and Analyst Targets)*

### Historical Performance
![Performance Charts](investment_screener/assets/images/analysis_charts.png)

### Valuation Modeler
![Valuation Modeler](investment_screener/assets/images/valuation_modeler.png)
*(Interactive DCF modeling with sensitivity matrices)*

### Market Heatmap
![Market Heatmap](investment_screener/assets/images/heatmap.png)
*(Real-time sector performance visualization)*

## 🛠️ Tech Stack
-   **Frontend**: React 19, Vite, Tailwind CSS.
-   **Backend**: Node.js (Express), Python 3.11 (Bridge to `yfinance`).
-   **Data**: `yfinance` & Questrade API (Dynamic Aggregation).

## 🧠 AI Capabilities

Autonomous AI agents perform valuation and portfolio analysis, powered by the Plugin Architecture and Spec Kitty framework.

### 1. Stock Valuation Analyst (`plugins/stock-valuation`)
An autonomous agent that acts as a buy-side analyst. It fetches real-time financial data, performs cognitive analysis, and generates a 3-scenario valuation model (Bear/Base/Bull) with a final "Buy/Sell/Hold" recommendation.

-   **Trigger**: `/stock-valuation_evaluate-stock {TICKER}`
-   **Plugin**: [`plugins/stock-valuation/`](plugins/stock-valuation/README.md)
-   **Capabilities**:
    -   Fetches live financials via `yfinance`.
    -   Projects 5-year revenue, margins, and PE ratios.
    -   Calculates fair value and upside/downside.
    -   Generates deep-dive research reports.
    -   Persists results to the Valuation Modeler.
    -   Interactive Q&A for assumption challenges and sensitivity analysis.

### 2. Strategic Thesis Balancer (`plugins/thesis-balancer`)
A "Strategic Guardian" agent that monitors your portfolio's alignment with your core investment thesis. It detects drift, checks "Thesis Breakers", and recommends rebalancing trades.

-   **Trigger**: `/thesis-balancer_review-portfolio`
-   **Plugin**: [`plugins/thesis-balancer/`](plugins/thesis-balancer/README.md)
-   **Capabilities**:
    -   **Drift Analysis**: Calculates deviation from target weights (Pillar & Holding level).
    -   **Strategic Review**: Classifies drift as passive or active, confirms intent before optimizing.
    -   **Conflict Detection**: Flags when Tool A (valuation) and thesis disagree on a holding.
    -   **Thesis Evolution**: Supports updating thesis targets when conviction changes.

## 🔌 Plugin Architecture

All agent tooling is organized as portable plugins in `plugins/`. Each plugin contains commands, skills, scripts, and documentation.

### Plugin Installation

To install the plugins and skills for this project, use `uvx` (part of the [Astral `uv`](https://github.com/astral-sh/uv) toolkit):

**1. Install Project-Specific Plugins (Local):**
```bash
uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add /Users/richardfremmerlid/Projects/InvestmentToolkit/plugins
```

**2. Install Core Library Plugins (Remote):**
```bash
uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add richfrem/agent-plugins-skills
```

## 🚀 Getting Started

### Prerequisites
-   Node.js 18+
-   Python 3.11+
-   Access to this repository

### Quick Start
The project includes a managed startup script for the entire suite:

```bash
python3 manage.py
```

This will automatically handle port conflicts, launch the backend API, and start the frontend dashboard.

### Individual Service Management
If you prefer to run or debug the servers separately, use the following commands from the root directory:

**1. Start Backend Server (Port 3001):**
```bash
npm --prefix investment_screener run dev -w backend
```

**2. Start Frontend Dashboard (Port 5173):**
```bash
npm --prefix investment_screener run dev -w frontend
```

*Note: Ensure the backend is running first so the frontend can fetch data.*

## 🤖 AI Development Framework
This project utilizes the **Spec Kitty** framework to systematize AI agent workflows.
-   **Specs**: Located in `kitty-specs/`.
-   **Plugins**: Located in `plugins/` — each plugin provides commands, skills, and scripts.
-   **Harness**: Extension of superpowers harness for AI agent workflows. exploration-cycle-plugin. see [.agents/agents/exploration-cycle-plugin-intake-agent.md](.agents/agents/exploration-cycle-plugin-intake-agent.md)
-   **Migration Guide**: See [`plugins/MIGRATION_GUIDE.md`](plugins/MIGRATION_GUIDE.md) for onboarding new repos.