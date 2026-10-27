---
name: analyzing-charts
plugin: tradingview
description: Technical analysis on live TradingView charts. Covers the batch daily sweep across all holdings, a single-ticker snapshot with visual analysis cross-referenced to DCF fair value, the adversarial red-team review of a technical thesis, and the senior technical-analyst workflow that reads the Data Window and synthesizes support, trim and entry levels. Trigger on /tv-ta-daily-sweep, /tv-ta, /tv-ta-red-team, /tv-ta-expert, "run ta sweep", "ta snapshot [TICKER]", "red team ta thesis" or "expert technical analysis".
allowed-tools: Bash, Read, Write
---

# Analyzing Charts

Technical-analysis workflows built on the TradingView chart: a portfolio-wide sweep, a single-ticker deep look, an adversarial review and the expert synthesis. They read indicators from the chart's Data Window rather than guessing from the picture.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

Check the connection, then read the mode:

```bash
python3 investment_screener/backend/py_services/tv_health_check.py
python3 scripts/ta_sweep_single.py {TICKER}
```

Paths starting with `scripts/` or `assets/` are relative to this skill's folder.

## Workflow

1. Match the request to a mode and read its mode file.
2. Run the health check (port 9222 must be open); use the `setup` mode of the `operating-tradingview-charts` skill if it is not.
3. Read indicator values from the Data Window, then cross-reference DCF fair value and stored levels from `domain_model.sqlite`.
4. Every price-level thesis passes the red-team review before it is presented.

## Constraints

- **Data Window authority**: levels come from actual Data Window values (21/50/200 EMAs, RSI, volume), not visual guesswork.
- **Multi-timeframe**: 1W for the macro trend, 1D for tactical execution.
- **Red-team before finalizing**: the reviewer answers `[APPROVED]` or `[REJECTED]` with at least three falsifiable counter-arguments and never proposes or places trades.
- **Screenshots** are saved under `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [ta-daily-sweep](references/modes/ta-daily-sweep.md) | `/tv-ta-daily-sweep` | Sequential TA sweep of every active holding with a Bullish/Neutral/Bearish/At Key Support posture |
| [ta-snapshot](references/modes/ta-snapshot.md) | `/tv-ta` | One ticker: screenshot, Data Window read, entry/accumulate/trim/stop levels |
| [ta-red-team](references/modes/ta-red-team.md) | `/tv-ta-red-team` | Skeptical senior risk manager verdict on a TA thesis |
| [technical-analysis-expert](references/modes/technical-analysis-expert.md) | `/tv-ta-expert` | Full workflow: chart setup, AI TA Levels, Data Window, levels, red team, thesis |

## Scripts

- `scripts/ta_sweep_batch.py` (portfolio sweep), `scripts/ta_sweep_single.py` (one ticker).
- `assets/templates/ta_thesis_template.md`: the thesis format shared by `ta-red-team` and `technical-analysis-expert`.
- Shared engine (`py_services/`): `tv_client.py`, `tv_health_check.py`. Tests: `tests/` (pass the path explicitly).
- The `ta-guide` agent (plugin `.apm/agents/`) is the interactive tutor that drives these modes.

## Verification

- A sweep report exists for every active holding; a snapshot report links its screenshot.
- The technical report cites Data Window values, and the red-team verdict addresses specific indicator levels and volume.
- Routing cases for every mode are in `evals/evals.json`.

## References

- [TA thesis template](assets/templates/ta_thesis_template.md).
- The `operating-tradingview-charts` skill: chart setup, indicators, AI TA Levels overlay, Pine Script.
