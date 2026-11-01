# Mode: batch-price-levels (`/tv-batch-levels`, `/tv-draw-levels`)

Batch recalculates, persists, and synchronizes structured price levels across all watchlist and portfolio investments in TradingView. 

Trigger on `/tv-batch-levels`, `/tv-draw-levels`, "update target buy sell levels on charts", "refresh chart levels", "clear and redraw chart levels", "redraw price level lines", "batch update price levels", or "update every chart".
Allowed tools: Bash, Read, Write.

## Architecture & How It Works

TradingView Desktop operates with a single active chart canvas per tab. Study inputs on indicators belong to the **layout**, meaning indicator inputs can only display levels for whichever ticker was drawn last.

To solve this permanently across the entire watchlist without running background follower daemons:
1. **Per-Symbol Horizontal Line Drawings**: In TradingView, drawings (`createShape({shape: 'horizontal_line'})`) belong to the **specific symbol**, not the layout. A line drawn on `SMCI` stays on `SMCI`; when you switch to `SOFI`, `SMCI`'s lines vanish and `SOFI`'s lines appear.
2. **Deterministic Clearing**: Each drawn line is tagged with the label prefix `AI-L: ` (e.g. `AI-L: Buy 1 $14.20`, `AI-L: DCF Fair Value $18.60`, `AI-L: Stop $10.40`). When refreshing levels, the clear step removes only existing `AI-L:` lines, preserving any manual discretionary drawings or alert markers the user created. If `--all-lines` is passed, all line drawings on that ticker are cleared.
3. **Indicator Input Blanking**: After the per-symbol line drawings are placed, the batch process blanks the `AI TA Levels` indicator's level inputs (`Levels for ticker = ""`, levels = 0.0). This prevents duplicate lines on the chart and completely eliminates the red mismatch banner (`⚠ Levels are for X, not Y`).

## Quick Start

```bash
# 1. Recalculate SQLite levels and sweep all charts (clear old AI-L lines + draw fresh lines + blank indicator):
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --recalculate --sweep

# 2. Redraw lines on all charts AND synchronize matching audible price alerts:
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep --sync-alerts

# 3. Clean foundation: wipe all existing alerts first, draw lines, and set fresh matching alerts:
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep --sync-alerts --clear-alerts

# 4. Dry run: verify what would be removed and drawn across all charts without modifying them:
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep --dry-run

# 5. Single ticker: recalculate, draw lines, and sync alerts for one stock (e.g. SOFI):
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --ticker SOFI --sync-alerts

# 6. Full reset: clear ALL lines (including non-AI drawings) on every chart and reapply from SQLite:
python3 plugins/tradingview/.apm/skills/operating-tradingview-charts/scripts/batch_update_price_levels.py --sweep --all-lines
```

## Level Line Styling Reference

| Level Tier | Label Format | Default Hex Color |
|---|---|---|
| Trim Tier 3 | `AI-L: Trim 3 $X.XX` | `#ab47bc` (Purple) |
| Trim Tier 2 | `AI-L: Trim 2 $X.XX` | `#fb8c00` (Orange) |
| Trim Tier 1 | `AI-L: Trim 1 $X.XX` | `#fdd835` (Yellow) |
| DCF Fair Value | `AI-L: DCF Fair Value $X.XX` | `#00bcd4` (Cyan) |
| Buy Tier 1 | `AI-L: Buy 1 $X.XX` | `#26a69a` (Teal) |
| Buy Tier 2 | `AI-L: Buy 2 $X.XX` | `#00e676` (Bright Green) |
| Buy Tier 3 | `AI-L: Buy 3 $X.XX` | `#2962ff` (Blue) |
| Stop Loss / Breaker | `AI-L: Stop $X.XX` | `#f44336` (Red) |

## Verification

1. Switch between test stocks in TradingView (e.g. `SMCI` and `SOFI`).
2. Verify that each stock displays its own labelled levels in the right-hand price axis.
3. Verify that switching between tickers produces zero warning banners.
4. Confirm `tv_health_check.py` reports OK.
