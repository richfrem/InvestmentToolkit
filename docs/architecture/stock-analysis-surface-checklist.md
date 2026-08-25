# Comprehensive Stock Analysis UI Surface & Metric Mapping

## Overview
To fulfill **Self-Evolution Rule 12** ("Modular Validation Functions for Every UI Analytical Metric"), every tab, card, multiple, metric, and modal across the Stock Analysis screen is mapped to a discrete, test-backed function and database table. When an anomaly is spotted on any UI card, agents fix the corresponding modular Python/TypeScript function and add a regression test.

---

## 🗂️ Complete Screen-by-Screen UI Component & Metric Inventory

### 1. Global Header & Action Bar (All Tabs)
| UI Element | Visual Output | Data Source | Calculation / Retrieval Function | Validator / Persistence Script |
|---|---|---|---|---|
| **Price Tag & Period Chips** | `$88.90` (+1.9% 1D, -4.2% 1W, +125% YTD) | `yfinance` & historical prices | `fetch_financials.py::fetch_financial_data()` | `validate_stock_metrics.py` |
| **TV Overlay Button** | Injects dynamic Pine script to TV Desktop | `domain_model.sqlite` (`price_level_tier`) | `tv_thesis_overlay.py::generate_pine_script()` | `tv_pine_inject.py` |
| **Buy / Sell Action Buttons** | Quick modal triggers | `domain_model.sqlite` (`investment`) | `TradeButtons.tsx` | HITL Advisory Rule #17 |

---

### 2. Tab 1 — Overview (`Dashboard.tsx`)
| UI Section | Card / Metric Name | Data Source | Calculation Function | Underlying Function File |
|---|---|---|---|---|
| **Target Portfolio Thesis** | Strategic Intent / Rationale | `domain_model.sqlite` (`investment.agent_rationale`) | `InvestmentRepository.getInvestment()` | `stock_intake_persist.py` |
| | Target Allocation (`2%`) & Role | `domain_model.sqlite` (`target_weight`, `lifecycle_status`) | `InvestmentRepository.getInvestment()` | `stock_intake_persist.py` |
| | Conviction Score (`/10`) | `domain_model.sqlite` (`conviction_score`) | `compute_conviction_scores.py` | `stock_intake_persist.py` |
| **Action Tiers Grid** | Buy / Accumulate Tiers | `domain_model.sqlite` (`price_level_tier` WHERE tier_kind='BUY') | `PriceLevelRepository.get_price_levels()` | `price_level_repository.py` |
| | Trim / Profit Tiers (1, 2, 3) | `domain_model.sqlite` (`price_level_tier` WHERE tier_kind='SELL') | `PriceLevelRepository.get_price_levels()` | `price_level_repository.py` |
| | Risk Management / Stop Loss | `domain_model.sqlite` (`price_level_tier` WHERE tier_kind='STOP_LOSS') | `PriceLevelRepository.get_price_levels()` | `price_level_repository.py` |
| **AI Expert Thesis Card** | Thesis Summary & Action Badge | `projection_version.snapshot_json` / `/api/projections` | `ProjectionRepository.findByTicker()` | `stock_intake_persist.py` |
| | AI Target Price (`$115`) | `projection_version.fair_value` | `dcf_scenarios.py` | `stock_intake_persist.py` |
| **Financial Metrics Grid** | Revenue Growth (`25.4%`) | `yfinance` financial statements | `fetch_financials.py` | `validate_stock_metrics.py` |
| | Free Cash Flow (`$-15.7B`) & Yield | `yfinance` cash flow statement | `fetch_financials.py` | `validate_stock_metrics.py` |
| | Operating Margin (`-0.0%`) | `yfinance` income statement | `fetch_financials.py` | `validate_stock_metrics.py` |
| | P/E Ratio (`0.0x`) & Forward P/E (`43.6x`) | `yfinance` quote summary | `fetch_financials.py` | `validate_stock_metrics.py` |
| | PEG Ratio (`N/A`) | P/E divided by 1Y Growth Est | `MetricsGrid.tsx` / `fetch_financials.py` | `validate_stock_metrics.py` |
| | Analyst Mean Target (`$115` +29%) | Consensus target price | `fetch_financials.py` | `validate_stock_metrics.py` |
| | Gross Margin (`34.8%`) & Net Margin (`-0.5%`) | Historical financial statements | `fetch_financials.py` | `validate_stock_metrics.py` |
| | Rule of 40 (`52.6%`) | Rev Growth + EBITDA Margin | `fetch_financials.py::expert_metrics` | `validate_stock_metrics.py` |
| | EPS (TTM) & Prior Year EPS | Historical Basic/Diluted EPS | `fetch_financials.py` | `validate_stock_metrics.py` |
| | Piotroski F-Score (`5/9`) | 9-point fundamental accounting test | `fetch_financials.py::piotroski_f_score` | `validate_stock_metrics.py` |

---

### 3. Tab 2 — Technicals (`TechnicalAnalysisSummaryCard.tsx`)
| UI Section | Card / Metric Name | Data Source | Calculation Function | Underlying Function File |
|---|---|---|---|---|
| **Header Badge** | Technical Action (`WATCHLIST` / `INITIATE` / `ACCUMULATE` / `TRIM`) | Joined `intelligence.sqlite` + `domain_model.sqlite` | `routes/stock.ts` (Strict Non-Holding Safety Guard) | `routes/stock.ts` |
| **Executive Setup** | Regime Analysis & Setup Summary | TV Live Telemetry / Sweep | `ta_sweep_single.py` | `routes/stock.ts` |
| **Accumulation & Support** | 21 EMA ($88.72) & 50 EMA ($85.57) | Multi-EMA indicators | `ta_sweep_single.py` | `intelligence_event` |
| **Staged Take-Profit Tiers** | Tier 1 (1.5x ATR), Tier 2 (Base DCF), Tier 3 (Bull FV) | Dynamic confluence calculation | `routes/stock.ts::profitTiers` | `stock_intake_persist.py` |
| **Stop Loss & ATR** | Stop Loss Limit & Expected Daily ATR | 14-period ATR from TV chart | `ta_sweep_single.py` | `intelligence_event` |
| **Momentum Indicators** | ADX (Trend Strength), Vol Bias (%), RSI (14D), Squeeze | Pine Script indicator outputs | `ta_sweep_single.py` | `intelligence.sqlite` |
| **Thesis Evolution Ledger** | Fair Value History Timeline (Aug 25 $115, May 02 $62, etc.) | `projection_version` chronological log | `ProjectionRepository.findByTicker()` | `ProjectionRepository.ts` |

---

### 4. Tab 3 — Historical & Projected Analysis Charts (`FinancialChart.tsx`)
| UI Chart Mode | Line / Bar Metrics Rendered | Data Source | Calculation Function | Underlying Function File |
|---|---|---|---|---|
| **Revenue & Earnings** | Historical Revenue, Net Income, + 2Y Forward Consensus Forecast Range | Historical Statements + Analyst Estimates | `fetch_financials.py` | `FinancialChart.tsx` |
| **Margins** | Gross Margin (%), Operating Margin (%), Net Margin (%) 5-year trend lines | Income Statement Margins | `fetch_financials.py` | `FinancialChart.tsx` |
| **Free Cash Flow** | Operating Cash Flow - CAPEX bar chart | Cashflow Statement | `fetch_financials.py` | `FinancialChart.tsx` |
| **EPS Trend** | Historical EPS vs Forward EPS Consensus trajectory | Earnings / Balance Sheet | `fetch_financials.py` | `FinancialChart.tsx` |

---

### 5. Tab 4 — Valuation Modeler (`ValuationModeler.tsx`)
| UI Section | Parameter / Slider | Data Source | Calculation Function | Underlying Function File |
|---|---|---|---|---|
| **AI Thesis Banner** | Markdown Research Rationale, Action, Model Author | `projection_version` / `/api/projections` | `ProjectionRepository.ts` | `stock_intake_persist.py` |
| **Weighted Fair Value** | Blended Fair Value & Upside % | Bear (20%) + Base (50%) + Bull (30%) Present Values | `dcf_scenarios.py` | `dcf_scenarios.py` |
| **Scenario Drivers** | Growth Rate (%), Net Margin (%), Exit P/E, Quality Multiplier, Share Change | 5-Year DCF Scenario Model | `dcf_scenarios.py` | `ProjectionRepository.ts` |
| **Global Settings** | Discount Rate (WACC 10%), Time Horizon (5 Yrs) | Portfolio Policy / DCF Engine | `dcf_scenarios.py` | `ProjectionRepository.ts` |

---

### 6. Modals & Popups
| Modal Name | Trigger | Content Rendered | Persistence / Source File |
|---|---|---|---|
| **AI Deep-Dive Research Modal** | "View Full Report" button | Complete markdown research report with TL;DR, Moat, Peer Comps, Risks | `intelligence_event` / `data/research/{T}_{D}.md` |
| **TradingView Pine Script Viewer** | `<> TV Overlay` button | Dynamic auto-generated Pine Script with live SQLite levels | `tv_thesis_overlay.py` |
| **Metric Definition Help Modal** | Info `(?)` icons on cards | Educational benchmark guide (e.g. Piotroski rules, Rule of 40 thresholds) | `HelpModal.tsx` |

---

## 🔄 Self-Evolution Continuous Improvement Loop

```
  ┌────────────────────────────────────────────────────────┐
  │         AGENT DETECTS OR RECEIVES UI ANOMALY           │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │ 1. Locate specific function in the matrix table above  │
  │ 2. Reproduce failure via pytest in backend/tests/      │
  │ 3. Fix underlying Python or TypeScript function        │
  │ 4. Run `python3 run_tests.py` to confirm 100% pass     │
  │ 5. Execute unified refresh: all 5 surfaces sync        │
  └────────────────────────────────────────────────────────┘
```
