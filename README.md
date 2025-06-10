# Quick Stock Screener Framework

A robust, extensible toolkit for fundamental stock analysis, peer benchmarking, and visualization. This project combines a structured qualitative/quantitative screener, an LLM prompt for structured analysis, and a Python CLI tool for live data visualization.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Dependencies & Installation](#dependencies--installation)
3. [File Overview](#file-overview)
    - [quick-stock-screener.md](#quick-stock-screenermd)
    - [LLM-Prompt.md](#llm-promptmd)
    - [stock_charts_cli.py](#stock_charts_clipypy)
4. [Usage](#usage)
5. [Planned Improvements](#planned-improvements)

---

## Project Overview

This project provides a comprehensive framework and toolkit for quick, repeatable, and insightful stock analysis. It includes:
- **A detailed screener framework** for both qualitative and quantitative metrics.
- **A prompt for LLMs** to generate structured, sectioned stock analysis.
- **A Python CLI tool** to fetch, compare, and visualize key financial metrics and peer comparisons using live data from Yahoo Finance and Finnhub APIs.

---

## Dependencies & Installation

### Python Dependencies

- Python 3.8+
- [yfinance](https://pypi.org/project/yfinance/)
- [finnhub-python](https://pypi.org/project/finnhub-python/)
- [matplotlib](https://pypi.org/project/matplotlib/)
- [numpy](https://pypi.org/project/numpy/)
- [questionary](https://pypi.org/project/questionary/)

### Installation

1. **Clone the repository** (if not already):
   ```sh
   git clone <repo-url>
   cd QuickStockScreener
   ```
2. **(Recommended) Create a virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Upgrade pip:**
   ```sh
   pip install --upgrade pip
   ```
4. **Install dependencies:**
   ```sh
   pip install yfinance finnhub-python matplotlib numpy questionary
   ```

5. **(Optional) Set your Finnhub API key:**
   - The script includes a demo key, but you can get your own free API key at [Finnhub.io](https://finnhub.io/).
   - Replace the `FINNHUB_API_KEY` in `stock_charts_cli.py` if desired.

---

## File Overview

### 1. `quick-stock-screener.md`
- **Purpose:**
  - The main framework for stock analysis, covering revenue, profitability, valuation, balance sheet, competitive advantage, risk, peer benchmarking, scoring, and visualization.
- **Contents:**
  - Key metrics, formulas, and qualitative factors for each analysis section.
  - Scoring system and quick reference summary for investment decisions.
  - Guidance on data sources and best practices for each metric.

### 2. `LLM-Prompt.md`
- **Purpose:**
  - A ready-to-use prompt for LLMs (e.g., GPT-4) to generate structured, sectioned stock analysis using the screener framework.
- **Contents:**
  - Instructions for the LLM, analysis framework outline, and a detailed example (NVIDIA).
  - Guidance on how to provide data and interpret results.
  - Usage instructions for the CLI visualization tool.

### 3. `stock_charts_cli.py`
- **Purpose:**
  - Python CLI tool for fetching, comparing, and visualizing stock metrics and peer comparisons.
- **Features:**
  - Fetches live data from Yahoo Finance (yfinance) and Finnhub APIs.
  - Handles missing/invalid data gracefully (annotates N/A in charts).
  - Plots revenue and margin trends, and peer metric bar charts.
  - Interactive prompts for ticker, peers, and metric selection (via `questionary`).
  - Extensible for future interactive features (dropdowns, industry median, etc.).

---

## Usage

Run the CLI tool to visualize a company's financials and compare with peers:

```sh
python3 stock_charts_cli.py --ticker <TICKER> --peers <PEER1> <PEER2> ...
```

- If arguments are omitted, the tool will prompt interactively.
- Select the metric for peer comparison when prompted.

**Example:**
```sh
python3 stock_charts_cli.py --ticker NVDA --peers AMD INTC QCOM
```

---

## Planned Improvements

- Add dropdowns for selecting analysis category and metric in the CLI tool.
- Add industry median calculation for peer comparisons.
- Further automate peer selection and metric fetching.
- Expand documentation and add more usage examples.

---

## License

This project is for educational and research purposes. See individual data provider terms for API/data usage.
