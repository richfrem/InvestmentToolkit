# Agent Quick Reference — Portfolio Advisor

This guide explains how to trigger AI agent skills directly in the Copilot CLI chat to analyse your portfolio, research stocks, and manage your investment thesis.

---

## How to Use Agent Skills

Open the **GitHub Copilot CLI** (or Claude Code) in the project terminal and type any command below. The agent reads your live portfolio data, investment thesis, and AI valuations — then responds with structured analysis.

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

## Stock Research & Valuation Commands

### `/evaluate-stock {TICKER}`
**Full DCF valuation.** Fetches live financials, runs Bear / Base / Bull scenario modelling, produces a weighted fair value, and saves a projection JSON. Updates the AI rating (BUY / HOLD / SELL) and price target on the Portfolio Advisor table.

```
/evaluate-stock NVDA
/evaluate-stock INTC
/evaluate-stock CRWV
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

### `/setup-questrade`
**Interactive Questrade token setup.** Guides you through seeding a new one-week app token into the encrypted local cache. Required once per machine or when the token expires.

> Token expired? Visit [apphub.questrade.com](https://apphub.questrade.com/UI/UserApps.aspx), generate a new one-week token, then run `/setup-questrade`.

---

### `/start-screener`
**Launch the full suite.** Starts backend (port 3001) and frontend (port 5173).

---

## Typical Workflows

| Cadence | Command | Follow-up |
|---|---|---|
| Weekly | `/review-portfolio` | `/rebalance` if pillar >5pp off target |
| Monthly | `/evaluate-stock {TICKER}` | Re-run for stale or missing AI projections |
| Quarterly | `/strategic-review` | Review MD, approve, apply formula patch |
| Before buying | `/research-stock {TICKER}` then `/evaluate-stock {TICKER}` | Class C/D findings block buy recommendations |

---

## Key Files

| File | Purpose |
|---|---|
| `investment_screener/backend/data/theses/target_portfolio.json` | Live thesis — pillar targets and holding weights |
| `plugins/portfolio-advisor/references/investment_thesis.md` | Thesis narrative — strategy, pillars, conviction logic |
| `PortfolioAnalysis/strategic-reviews/` | Historical reviews (MD + JSON + patch) |
| `investment_screener/backend/data/projections/` | AI DCF valuations per stock |

