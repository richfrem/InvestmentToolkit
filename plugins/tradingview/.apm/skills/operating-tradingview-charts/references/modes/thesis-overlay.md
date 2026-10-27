# Mode: thesis-overlay (`/tv-thesis-overlay`)

Generates a dynamic Pine Script indicator containing Fair Value, Target Entry, Breaker, and DCF Bear/Base/Bull scenario levels from SQLite and injects it onto the chart. Trigger on /tv-thesis-overlay or 'inject thesis overlay'.
Allowed tools: Bash, Read, Write.

Generates a dynamic Pine Script indicator containing Fair Value, Target Entry, Breaker, and DCF Bear/Base/Bull scenario levels from SQLite and injects it onto the chart.


## Constraints

- Dynamic compilation: Generates indicator dynamically from latest SQLite projection rows.
- Single active overlay: Removes prior 'AI Thesis' indicator before injecting fresh levels.
- Same levels as the page: buy/trim tiers and stop come from `price_level_tier`. To refresh and redraw them use `python3 investment_screener/backend/py_services/update_price_levels.py --ticker T --source combined --write --draw`; `--draw` sets the inputs of the saved **AI TA Levels** script on the chart (add it once from Indicators -> My scripts; it stays across symbols) through the chart API, without touching the Pine Editor; an unstored level is set to 0 and draws nothing. The source lives in `assets/pinescript-indicators/ai-ta-levels.pine` (versions under `versions/ai-ta-levels/`); edit it there and re-save the script in TradingView.
- Lint gate: Must pass `pine_linter.py` before injection.

## Quick start

```bash
python3 scripts/tv_thesis_overlay.py --ticker {TICKER}
```

## Workflow

1. Query latest projection and price levels from `domain_model.sqlite`.
2. Switch chart to target ticker via CDP.
3. Generate Pine Script v6 overlay containing Fair Value, Target Entry, and DCF levels.
4. Lint generated script via `pine_linter.py`.
5. Inject onto chart via [pine-inject mode](pine-inject.md)`.

## Verification

- Confirm indicator plots on active TradingView chart.
- Validate routing cases against `evals/evals.json`.
