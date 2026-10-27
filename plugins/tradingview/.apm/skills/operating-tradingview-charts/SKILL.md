---
name: operating-tradingview-charts
plugin: tradingview
description: Drives TradingView Desktop through its remote debugging port. Covers connection setup and diagnostics, chart control (symbol, chart type, workspace layout, screenshots, drawings), indicator management, Pine Script authoring, injection, saving and the thesis overlay, and price alerts (list, reconcile against SQLite targets, create at DCF scenario levels). Trigger on /tv-setup, /tv-onboarding, /tv-change-symbol, /tv-change-type, /tv-chart-setup, /tv-snapshot, /tv-draw, /tv-add-indicator, /tv-indicators, /tv-save-indicator, /tv-pine-inject, /tv-author-pine-script, /tv-thesis-overlay, /tv-alert-list, /tv-alert-reconcile, /tv-alert-sync, "connect tradingview", "switch chart to [TICKER]", "add indicator [NAME]", "author pine script", "inject pine script", "inject thesis overlay", "list tradingview alerts", "reconcile alerts" or "sync tradingview alerts".
allowed-tools: Bash, Read, Write
---

# Operating TradingView Charts

Everything that drives the TradingView Desktop chart through the Chrome DevTools Protocol (CDP): connection, chart state, indicators, Pine Script and alerts. Orders, portfolio sync and prices are in `trading-via-tradingview`; technical-analysis workflows are in `analyzing-charts`.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

From the repository root, check the connection first:

```bash
python3 investment_screener/backend/py_services/tv_health_check.py
```

Paths starting with `scripts/` or `assets/` are relative to this skill's folder; `node tradingview-cdp/cli.js ...` runs from the repository root.

## Workflow

1. Match the request to a mode in the table below and read its mode file.
2. Run the health check. If port 9222 is not open, use the [setup mode](references/modes/setup.md).
3. Follow the mode; chart commands change the **active chart only**.
4. Verify on the chart (legend, drawing, alert list) before reporting success.

## Constraints

- **Port 9222**: TradingView Desktop must be launched with `--remote-debugging-port=9222`; the Node CDP engine in `tradingview-cdp/` needs its dependencies installed (`npm ci`).
- **Read-only diagnostics**: health checks never change user settings or network configuration.
- **Single chart target**: commands act on the active chart layout; `chart-setup` uses the dedicated `agent-layout` so the owner's own layouts are untouched.
- **Pine Script v6 only**, linted before injection (`scripts/pine_linter.py`), no repainting or lookahead.
- **Database authority**: levels and alert targets come from `domain_model.sqlite`; stored levels are authoritative over alert text.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [setup](references/modes/setup.md) | `/tv-setup`, `/tv-onboarding` | Diagnose and fix the CDP connection and port 9222 (combines the old setup and onboarding skills) |
| [change-symbol](references/modes/change-symbol.md) | `/tv-change-symbol` | Switch the active chart symbol |
| [change-type](references/modes/change-type.md) | `/tv-change-type` | Candlestick, bar, line, area, Heikin Ashi or Renko |
| [chart-setup](references/modes/chart-setup.md) | `/tv-chart-setup` | agent-layout, symbol and timeframe in one step |
| [chart-snapshot](references/modes/chart-snapshot.md) | `/tv-snapshot` | Screenshot of a ticker's chart |
| [draw](references/modes/draw.md) | `/tv-draw` | Level lines, zones and tags on the chart |
| [add-indicator](references/modes/add-indicator.md) | `/tv-add-indicator` | Add a built-in or personal indicator |
| [manage-indicators](references/modes/manage-indicators.md) | `/tv-indicators` | List, add or remove loaded indicators |
| [save-indicator](references/modes/save-indicator.md) | `/tv-save-indicator` | Save the editor's script to My scripts |
| [pine-inject](references/modes/pine-inject.md) | `/tv-pine-inject` | Inject Pine v6 into the editor with compile checking |
| [author-pine-script](references/modes/author-pine-script.md) | `/tv-author-pine-script` | Research, write and lint a Pine v6 indicator |
| [thesis-overlay](references/modes/thesis-overlay.md) | `/tv-thesis-overlay` | Fair value, entry, breaker and DCF levels from SQLite as an overlay |
| [alert-list](references/modes/alert-list.md) | `/tv-alert-list` | List active alerts and cache them in SQLite |
| [alert-reconcile](references/modes/alert-reconcile.md) | `/tv-alert-reconcile` | Flag missing or drifted alerts against SQLite levels |
| [alert-sync](references/modes/alert-sync.md) | `/tv-alert-sync` | Create alerts at DCF bear/base/bull levels |

## Scripts

- `scripts/`: `tv_draw`, `tv_manage_indicators`, `tv_pine_inject`, `tv_pine_manager`, `pine_linter`, `pine_source_reader`, `tv_thesis_overlay`, `tv_create_alerts`, `tv_list_alerts`, `tv_quote`.
- Shared engine (backend `py_services/`): `tv_client`, `tv_launch`, `tv_health_check` and the broker/order modules used by `trading-via-tradingview`.
- `assets/pinescript-indicators/`: the indicators (`ai-ta-levels.pine`, `ai-thesis-overlay.pine`, community references, versions). Tests: `tests/` (pass the path explicitly; pytest skips dot-directories).

## Verification

- `tv_health_check.py` reports OK (port 9222 open).
- The change shows on the chart: header symbol, legend entry, drawing, or the alert in `tv_list_alerts.py` output.
- Routing cases for every mode are in `evals/evals.json`.

## References

- [Pine Script overview](references/pinescript_overview.md), [Pine Script agent rules](references/PineScript_Agent_Skill_Rules.md), [Top TradingView indicators](references/Top_TradingView_Indicators_Reference.md), [chart types](references/chart-types-reference.md).
- [Self-evolution profile](references/self-evolution-profile.md) and [evolution log](references/evolution-log.md); [playbooks](references/playbooks/README.md).
- Sibling skills: `trading-via-tradingview` (orders, sync, prices, watchlists) and `analyzing-charts` (technical analysis).
