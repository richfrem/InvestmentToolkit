# Agent Quick Reference — Portfolio Advisor

This guide explains how to trigger AI agent skills directly in the Copilot CLI chat (or Claude Code) to analyse your portfolio, research stocks, evaluate ETFs, and manage your investment thesis.

---

## How to Use Agent Skills

Open **Claude Code** or **GitHub Copilot CLI** in the project terminal and type any command below. The agent reads your live portfolio data, investment thesis, and AI valuations — then responds with structured analysis.

---

## Data Architecture

`domain_model.sqlite` (`account` / `investment` / `account_investment` / `price_level_set` /
`price_level_tier` / `portfolio_policy` tables, among others) is the sole source of truth for
portfolio holdings, thesis targets, pillars, price levels, and standing decisions. `portfolio.json`
and `theses/target-portfolio.json` were both retired (Waves 7/8) and are archived under
`ARCHIVE/investment_screener/backend/data/` — commands below now read/write SQLite via
`investment_screener/backend/py_services/portfolio_io.py`'s `load_portfolio_state()`/
`load_thesis_holdings()`/`load_target_weights()` (Python) or `InvestmentRepository`/
`ThesisService`/`PriceLevelRepository` (TypeScript backend). A small number of other JSON files
remain as deliberate, still-current exceptions (`cash_flows.json`, `trade-log.json`,
`thesis_breaker_state.json`, `projections/*.json`) — see `data-architecture/domain-data-model.md`
for the current schema (entities, ERD, rationale) and `data-architecture/sql/` for the DDL.

---

## Portfolio Commands

### `/strategic-review`
**Full quarterly portfolio review.** Evaluates every holding against your investment thesis, cross-references AI fair-value scores, and produces a structured `PortfolioAnalysisRecommendations.md` + companion JSON saved to `PortfolioAnalysis/strategic-reviews/`.

Outputs:
- Pillar drift summary (over/underweight vs targets)
- Per-holding action: ACCUMULATE / MAINTAIN / TRIM / EXIT / WATCHLIST
- Urgency rating and rationale for each change
- Formula health score (0–100)
- Ready-to-apply `formula-patch.json` for weight updates

---

### `/review-portfolio`
**Lightweight drift monitor.** Faster than a full strategic review — checks pillar-level drift and conviction alignment. Good for a weekly check.

---

### `/rebalance`
**Valuation-gated trade optimizer.** Calculates specific buy/sell trades to restore pillar drift to targets. Skips any holding rated SELL/EXIT by AI valuation — won't buy into a falling knife to fix drift.

---

### `/x-news-sweep`
**Daily Grok/X.com news sweep.** Generates a structured prompt from your live thesis, posts it to Grok, and gates every recommendation against DCF fair values + 8 hard gates before applying changes. Run at the start of each trading day.

---

### `/13f-tracker`
**SEC 13F filing monitor.** Polls SEC EDGAR for new 13F filings from tracked institutions. Downloads the latest holdings JSON and diffs it quarter-over-quarter to surface new positions, exits, and sizing changes.

---

### `/13f-analyze`
**Surgical 13F analysis.** Cross-references an institution's 13F holdings against your thesis targets. Outputs gated INITIATE / ACCUMULATE / TRIM / EXIT recommendations and applies approved changes to `domain_model.sqlite` (via `update_targets.py`).

---

### `/place-order {ACTION} {N} {TICKER} in {ACCOUNT}`
**Live order execution via TradingView.** Places buy or sell orders through TradingView's built-in TradingView connected broker integration using CDP automation. Three-step HITL flow: preflight card (broker check + buying power) → CONFIRM → form filled + submitted → portfolio.json synced.

Requires: TradingView Desktop running with connected broker connected (the broker panel visible at the bottom of TradingView).

```
/place-order buy 1 WYFI in TFSA
/place-order sell 5 NVDA in RRSP
/place-order buy 10 INTC at $18.50 limit in TFSA
```

Pre-flight checks every time:
- connected broker connected in TradingView
- Correct account (TFSA / RRSP / Margin)
- Sufficient buying power (USD or CAD matched to ticker exchange)

---

### `/run-advisor`
**Full lifecycle orchestrator.** Runs the complete Portfolio Advisor loop: drift review → target calibration → rebalance. Good for a full session when you have time to act on recommendations.

---

### `/calibrate-targets`
**Interactive target-weight calibration.** Guides you through adjusting pillar and holding target weights interactively.

---

## Stock Research & Valuation Commands

### `/update-stock-analysis {TICKER}`
**Full DCF valuation.** Fetches live financials (yfinance), runs Bear / Base / Bull scenario modelling, produces a weighted fair value, and saves a projection JSON. Uses live price from TradingView Desktop (active chart via CDP) when connected, otherwise yfinance.

Updates the AI rating (BUY / HOLD / SELL) and price target on the Portfolio Advisor table.

```
/update-stock-analysis NVDA
/update-stock-analysis INTC
/update-stock-analysis CRWV
```

---

### `/research-stock {TICKER}`
**Qualitative research sweep.** Deep-dives into recent news, earnings calls, analyst reports, and thesis alignment for a single stock. Classifies each finding:
- **Class A** — Confirms thesis (no action needed)
- **Class B** — Thesis evolution (update conviction)
- **Class C** — Thesis breach (triggers re-valuation gate)
- **Class D** — Thesis breaker (immediate review required)

```
/research-stock INTC
/research-stock CRCL
```

---

### `/analyze-etf {TICKER}`
**Thematic ETF analysis.** For ETFs that don't fit a standard DCF model. Analyses holdings alignment against your investment thesis, expense ratio, fund type, and produces a BUY / HOLD / AVOID action with entry strategy.

Automatically writes the result to:
- `data/etf_analysis/{TICKER}.json` — full analysis
- `data/projections/{TICKER}.json` — so the AI Expert Thesis panel appears in the Dashboard

```
/analyze-etf DXYZ
/analyze-etf KOID
/analyze-etf HUMN
/analyze-etf DRAM
```

---

### `/bundle-thesis-review`
**Package thesis for external LLM.** Bundles your full thesis + DCF projections into a pasteable format for Grok, ChatGPT, or Gemini when you want a second opinion.

---

## Thesis Management

### Update target weights after a strategic review

Once a `formula-patch.json` is approved:

```bash
python3 investment_screener/backend/py_services/update_thesis.py \
  --patch PortfolioAnalysis/strategic-reviews/YYYY-MM-DD-formula-patch.json \
  --note "Strategic review YYYY-MM-DD approved"
```

Update a single holding target directly:

```bash
python3 investment_screener/backend/py_services/update_thesis.py \
  --pillar "ASI / Compute" --holding NVDA --target 8.5 \
  --note "Elevated after earnings beat"

# List all current targets and weights
python3 investment_screener/backend/py_services/update_thesis.py --list
```

---

## Setup & Infrastructure

### `/start-screener`
**Launch the full suite.** Starts backend (port 3001) and frontend (port 5173). TradingView Desktop is auto-launched with `--remote-debugging-port=9222` if installed.

To relaunch TradingView independently:
```bash
python3 plugins/tradingview/scripts/tv_launch.py
```

---

## Typical Workflows

| Cadence | Command | Follow-up |
|---|---|---|
| Daily | `/x-news-sweep` | Gate recs against DCF + 8 hard gates |
| Weekly | `/review-portfolio` | `/rebalance` if pillar >5pp off target |
| Monthly | `/update-stock-analysis {TICKER}` | Re-run for stale or missing AI projections |
| Quarterly | `/strategic-review` | Review MD, approve, apply formula patch |
| Before buying | `/research-stock {TICKER}` then `/update-stock-analysis {TICKER}` | Class C/D findings block buy recommendations |
| Execute trade | `/place-order buy N {TICKER} in {ACCOUNT}` | Preflight → CONFIRM → TV dialog filled + submitted → portfolio synced |
| New ETF | `/analyze-etf {TICKER}` | Appears in Dashboard AI Expert Thesis panel automatically |

---

## Key Files

| File | Purpose |
|---|---|
| `investment_screener/backend/data/domain_model.sqlite` | Live thesis — pillar targets and holding weights (sole source of truth, Wave 8) |
| `investment_screener/backend/data/theses/investment_thesis.md` | Thesis narrative — strategy, pillars, conviction logic |
| `PortfolioAnalysis/strategic-reviews/` | Historical reviews (MD + JSON + patch) |
| `investment_screener/backend/data/projections/` | AI DCF valuations per stock |
| `investment_screener/backend/data/etf_analysis/` | ETF analysis results (versioned per ticker) |
