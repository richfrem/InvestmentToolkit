# Chart levels belong to a stock, not to the chart

How the buy, trim and stop levels reach a TradingView chart, why a chart can show another stock's levels, and the ways to prevent it. Read this before drawing, trusting or changing levels on a chart.

## Contents

- [How levels get on a chart](#how-levels-get-on-a-chart) · [The failure](#the-failure) · [Check before trusting a level](#check-before-trusting-a-level) · [Designs and trade-offs](#designs-and-trade-offs) · [Rules](#rules)

## How levels get on a chart

- The levels live in `domain_model.sqlite` (`price_level_set`, `price_level_tier`): numbered buy tiers, trim tiers, a stop, and the DCF fair value from the latest projection.
- The **AI TA Levels** indicator draws them from its *inputs* (fair value, buy 1 to 3, trim 1 to 3, stop). `update_price_levels.py --ticker T --source combined --write --draw` switches the chart to `T` and sets those inputs through the chart API. A level left at 0 draws nothing.
- The inputs belong to the indicator on the chart, not to a symbol.

## The failure

- Inputs stay as they are when the chart symbol changes. A chart switched from stock A to stock B keeps A's levels until someone redraws for B, so B shows A's buy tiers, often far above or below B's price.
- A chart is therefore right only for the ticker it was last drawn for.
- Indicator v4.0.0 adds a "Levels for ticker" input: levels are drawn only when it matches the chart symbol, and the indicator shows a red warning otherwise. The guard is live only once the indicator is re-saved in TradingView; a chart still running an older saved copy keeps the old behaviour.
- The indicator's own plausibility check (a level must be between 0.2 and 5 times the close) does not catch it: another stock's levels fall inside that range often.
- Drawing levels for every stock in the database does not fix it. It writes the database; the chart still shows one set of inputs.

## Check before trusting a level

1. Read the stored levels for the ticker (`price_level_tier`), not the chart.
2. Buy tiers sit below the current price and at or below DCF base fair value. A buy tier above the price, or a stop above the price, means the levels belong to another stock or are stale.
3. Compare the numbers on the chart with the stored ones. A mismatch means the chart was not redrawn for this ticker.

## Designs and trade-offs

| Design | How it works | Cost |
|---|---|---|
| Inputs only (before v4.0.0) | One set of inputs, redrawn per ticker | Right for one ticker at a time; silently wrong after any symbol change |
| Ticker-tagged inputs with a follower (current) | The inputs carry the ticker they were drawn for; the indicator draws nothing, and warns, on any other ticker. `pine_level_inputs.py --draw TICKER` redraws one stock; `pine_level_inputs.py --follow` redraws whichever stock the chart shows each time the symbol changes | A wrong chart is visible, not misleading; still one ticker at a time, and the indicator must be re-saved in TradingView |
| Per-symbol drawings | Horizontal lines drawn on each stock's own chart (drawings belong to the symbol they were drawn on; confirm on the layout first) | Static: every level refresh means clearing and redrawing each chart; clearing must remove only the lines this tool drew, never the owner's own drawings or alert markers |
| Embedded table | The indicator holds every stock's levels and picks the rows for the chart's ticker | Every chart right with no redraw; Pine cannot read SQLite, so each refresh regenerates and re-injects the script |

## Rules

- Quote levels only from the stored tiers, never from what a chart shows.
- Do not remove or replace an indicator, clear drawings, or save a layout without the owner's yes. A "clear all" is destructive and not reversible.
- A script saved in TradingView is the owner's: changing its source in the repo does not change the saved copy until it is re-saved there.
- After switching a chart to a ticker, redraw that ticker's levels before reading any level off the chart.
