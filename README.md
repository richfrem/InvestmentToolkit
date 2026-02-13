# InvestmentToolkit

A premium, "Luxury Dark Mode" investment analysis suite built for sophisticated retail investors. This toolkit provides deep fundamental analysis, valuation modeling, and comparative screening without the need for expensive terminal subscriptions.

## 🌟 Core Components

### 1. Investment Screener (`tools/investment-screener`)
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
![Analysis Metrics](tools/investment-screener/assets/images/analysis_metrics.png)
*(15+ Premium metrics including Rule of 40, Piotroski F-Score, and Analyst Targets)*

### Historical Performance
![Performance Charts](tools/investment-screener/assets/images/analysis_charts.png)

### Valuation Modeler
![Valuation Modeler](tools/investment-screener/assets/images/valuation_modeler.png)
*(Interactive DCF modeling with sensitivity matrices)*

### Market Heatmap
![Market Heatmap](tools/investment-screener/assets/images/heatmap.png)
*(Real-time sector performance visualization)*

## 🛠️ Tech Stack
-   **Frontend**: React 19, Vite, Tailwind CSS.
-   **Backend**: Node.js (Express), Python 3.11 (Bridge to `yfinance`).
-   **Data**: `yfinance` & Questrade API (Dynamic Aggregation).

## 🚀 Getting Started

### Prerequisites
-   Node.js 18+
-   Python 3.11+
-   Access to this repository

### Quick Start
The project includes a managed startup script for the entire suite:

```bash
python3 tools/manage_servers.py
```

This will automatically handle port conflicts, launch the backend API, and start the frontend dashboard.

## 🤖 AI Development Framework
This project utilizes the **Spec Kitty** framework to systematize AI agent workflows.
-   **Specs**: Located in `kitty-specs/`.
-   **Agents**: Supports Gemini, Copilot, and Claude via the `tools/bridge/speckit_system_bridge.py` sync tool.