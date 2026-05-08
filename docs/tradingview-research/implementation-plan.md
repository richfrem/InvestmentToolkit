# TradingView Plugin — Implementation Plan

**For:** Fresh agent handoff  
**Date:** 2026-05-08  
**Repo root:** `/Users/richardfremmerlid/Projects/InvestmentToolkit`  
**Verification:** After implementation, the spawning agent will run verify steps listed at the bottom.

---

## Context

InvestmentToolkit is an AI-driven portfolio management tool. It has a plugin architecture at `plugins/` with three existing plugins: `portfolio-advisor`, `stock-valuation`, `toolkit-manager`. Each plugin has:
- `plugin.json` (root — skill registry, commands, dependencies)
- `.claude-plugin/plugin.json` (marketplace metadata)
- `commands/*.md` (slash command stubs for autocomplete)
- `skills/*/SKILL.md` (agent skill definitions)
- `scripts/*.py` (Python scripts the skills call)

The goal of this task is to create a **fourth plugin: `tradingview`** that bridges InvestmentToolkit's AI agents and Python backend to TradingView Desktop's real-time market data.

---

## How the Integration Works

There is a community Node.js library at `temp/tradingview-mcp/` that connects to TradingView Desktop via Chrome DevTools Protocol (CDP). It exposes a CLI (`src/cli/index.js`) that outputs JSON to stdout.

**We do NOT run it as an MCP server.** We call its CLI directly from Python via `subprocess`.

```
Python script
  └── subprocess.run(["node", "temp/tradingview-mcp/src/cli/index.js", "quote", "CRWV"])
        └── Node.js CLI → CDP → TradingView Desktop (running with --remote-debugging-port=9222)
              └── Returns JSON: { "price": 115.26, "change": -6.2, "changePercent": -5.1, ... }
```

**Requirement:** TradingView Desktop must be running with `--remote-debugging-port=9222`. A launch script already exists at `temp/tradingview-mcp/scripts/launch_tv_debug_mac.sh`. The Python scripts must gracefully fall back to yfinance if TradingView is unavailable.

**npm install required:** Run `npm install` inside `temp/tradingview-mcp/` before the CLI works. Check by running `node temp/tradingview-mcp/src/cli/index.js --help`.

---

## Existing Codebase to Understand

Before implementing, read these files to understand patterns:

| File | Why |
|------|-----|
| `plugins/portfolio-advisor/plugin.json` | Root plugin.json structure to copy |
| `plugins/portfolio-advisor/.claude-plugin/plugin.json` | Marketplace plugin.json structure |
| `plugins/portfolio-advisor/commands/x-news-sweep.md` | Command file format |
| `plugins/portfolio-advisor/skills/x-news-sweep/SKILL.md` | Skill SKILL.md format |
| `investment_screener/backend/py_services/fetch_portfolio_heatmap.py` | Script to augment with TradingView prices |
| `investment_screener/backend/src/index.ts` | How backend calls the heatmap script (grep for "heatmap") |
| `temp/tradingview-mcp/src/cli/commands/data.js` | CLI command signatures (`quote`, `ohlcv`) |
| `temp/tradingview-mcp/src/cli/commands/alerts.js` | CLI alert commands |
| `temp/tradingview-mcp/src/cli/commands/capture.js` | CLI screenshot commands |
| `temp/tradingview-mcp/src/cli/commands/watchlist.js` | CLI watchlist commands |

---

## File Structure to Create

```
plugins/tradingview/
├── plugin.json                          # Root: skill registry + commands + dependencies
├── .claude-plugin/
│   └── plugin.json                      # Marketplace metadata
├── commands/
│   ├── tv-alert-sync.md                 # /tv-alert-sync command stub
│   ├── tv-price-refresh.md              # /tv-price-refresh command stub
│   └── tv-snapshot.md                   # /tv-snapshot command stub
├── skills/
│   ├── alert-sync/
│   │   └── SKILL.md                     # Skill: create DCF alerts in TradingView
│   ├── price-refresh/
│   │   └── SKILL.md                     # Skill: pull real-time prices for all positions
│   └── chart-snapshot/
│       └── SKILL.md                     # Skill: capture chart screenshot for a ticker
└── scripts/
    ├── tv_client.py                     # Core: subprocess caller + fallback + health check
    ├── tv_quote.py                      # CLI: get real-time quote for one ticker
    ├── tv_batch_quotes.py               # CLI: get quotes for a list of tickers (JSON array arg)
    ├── tv_create_alerts.py              # CLI: create TradingView price alerts from projection JSONs
    ├── tv_health_check.py               # CLI: verify TradingView Desktop is reachable at CDP port
    └── tv_launch.py                     # Helper: launch TradingView Desktop with CDP flag
```

Also modify (do NOT rewrite from scratch):
- `investment_screener/backend/py_services/fetch_portfolio_heatmap.py` — add optional TradingView price injection

---

## Script Specifications

### `scripts/tv_client.py` — Core client

This is the only file that knows the path to the Node.js CLI. All other scripts import from it.

```python
REPO_ROOT = Path(__file__).resolve().parents[3]
TV_CLI = REPO_ROOT / "temp/tradingview-mcp/src/cli/index.js"
TV_PORT = 9222

def is_tv_running() -> bool:
    """Return True if TradingView is reachable at CDP port."""
    # Try: socket.connect(('localhost', TV_PORT)) with 1s timeout
    # Return False on any error

def tv_call(*args, timeout: int = 10) -> dict | list:
    """
    Call TradingView CLI, return parsed JSON.
    Raises RuntimeError with stderr if returncode != 0.
    Raises FileNotFoundError if node or CLI not found.
    """
    # subprocess.run(["node", str(TV_CLI)] + list(args), capture_output=True, text=True, timeout=timeout)
    # json.loads(result.stdout)

def tv_call_or_fallback(*args, fallback_fn, timeout: int = 10):
    """
    Try tv_call(*args). If TradingView unavailable or any error, call fallback_fn() instead.
    Returns (result, source) where source is 'tradingview' or 'fallback'.
    """
```

### `scripts/tv_quote.py` — Single ticker quote

```
Usage: python3 tv_quote.py TICKER [--json]

CLI call: node ... quote TICKER
Output (stdout, JSON):
{
  "ticker": "CRWV",
  "price": 115.26,
  "change": -7.44,
  "changePercent": -6.07,
  "volume": 4521000,
  "source": "tradingview"   # or "yfinance" if fallback
}

Fallback: yfinance Ticker(ticker).fast_info
Exit code 1 with error on stderr if both fail.
```

### `scripts/tv_batch_quotes.py` — Portfolio-wide price pull

```
Usage: python3 tv_batch_quotes.py '["CRWV", "NVDA", "INTC", ...]'

For each ticker: calls tv_quote (TradingView or fallback).
Concurrency: use ThreadPoolExecutor(max_workers=5) to parallelize.

Output (stdout, JSON):
{
  "quotes": {
    "CRWV": { "price": 115.26, "changePercent": -6.07, "source": "tradingview" },
    "NVDA":  { "price": 497.32, "changePercent":  1.23, "source": "tradingview" },
    ...
  },
  "summary": {
    "total": 35,
    "tradingview": 35,
    "fallback": 0,
    "errors": 0
  }
}
```

### `scripts/tv_create_alerts.py` — Create DCF alerts

```
Usage:
  python3 tv_create_alerts.py                        # all holdings with DCF projections
  python3 tv_create_alerts.py --ticker CRWV          # single ticker
  python3 tv_create_alerts.py --dry-run              # print what would be created, don't call CLI

For each ticker:
  1. Load investment_screener/backend/data/projections/{TICKER}.json
  2. Find latest AI_AGENT entry
  3. Extract bear/base/bull scenarioPrice values
  4. Extract aiThesis.fairValue
  5. For each price level, call:
     node ... alert create TICKER {price} --condition crossing --name "{TICKER} {scenario} ${price:.0f}"

CLI call: node ... alert create SYMBOL PRICE [--condition crossing] [--name NAME]
  (Check temp/tradingview-mcp/src/cli/commands/alerts.js for exact syntax)

Requires TradingView to be running — print warning and skip ticker if not.

Output: table of alerts created/skipped per ticker.
```

### `scripts/tv_health_check.py` — Connection health

```
Usage: python3 tv_health_check.py [--json]

Checks:
  1. Is port 9222 reachable? (socket test)
  2. Does `node ... health` return success?
  3. Is npm installed in temp/tradingview-mcp/ (node_modules exists)?

Output (--json): {"status": "ok|error", "port": true|false, "cli": true|false, "npm": true|false, "message": "..."}
Output (default): Human-readable status table

Exit code 0 if all checks pass, 1 otherwise.
```

### `scripts/tv_launch.py` — Launch TradingView

```
Usage: python3 tv_launch.py

On macOS: subprocess.run(["open", "-a", "TradingView", "--args", "--remote-debugging-port=9222"])
Also tries: the launch script at temp/tradingview-mcp/scripts/launch_tv_debug_mac.sh

Prints instructions if launch fails (path not found, etc.).
```

### Modification: `fetch_portfolio_heatmap.py` — Price injection

At the top of the script, after reading the items JSON, add an optional price override:

```python
# Optional: inject real-time prices from TradingView if available
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/tradingview/scripts"))
try:
    from tv_client import is_tv_running, tv_call
    if is_tv_running():
        # For each item, override price with TradingView real-time quote
        # Only override if TradingView call succeeds; keep yfinance as fallback per item
        pass  # implement inline or call tv_batch_quotes
except ImportError:
    pass  # tv plugin not installed, continue with yfinance only
```

**Important:** This is a soft enhancement — the script must still work identically if the TradingView plugin is not present or TradingView is not running. Do not break existing functionality.

---

## Skill Specifications

### `skills/alert-sync/SKILL.md`

**Trigger:** `/tv-alert-sync` or "sync tradingview alerts" or "create dcf alerts"

**What it does:**
1. Runs `tv_health_check.py` — if TradingView not running, instruct user to launch it and stop
2. Optionally accepts a `--ticker` argument for single-ticker mode
3. Runs `tv_create_alerts.py` (or `tv_create_alerts.py --ticker TICKER` if specified)
4. Reports a table: ticker | bear alert | base alert | bull alert | status
5. Suggests: "Run `/tv-alert-sync` after each `/evaluate-stock` to keep alerts current"

**Error handling:** If TradingView not running, print launch instructions:
```
TradingView Desktop not detected on port 9222.
Launch it with: python3 plugins/tradingview/scripts/tv_launch.py
Or manually: open -a TradingView --args --remote-debugging-port=9222
```

### `skills/price-refresh/SKILL.md`

**Trigger:** `/tv-price-refresh` or "refresh prices" or "get live prices"

**What it does:**
1. Runs `tv_health_check.py`
2. Loads all tickers from `investment_screener/backend/data/portfolio.json` + `target-portfolio.json`
3. Runs `tv_batch_quotes.py` with combined ticker list
4. Prints a table: ticker | live price | 1d change% | source (tradingview/yfinance)
5. Reports summary: N tickers, N real-time, N yfinance fallback

**Use case:** Quick "what are my positions doing right now" check during a session.

### `skills/chart-snapshot/SKILL.md`

**Trigger:** `/tv-snapshot TICKER` or "snapshot TICKER" or "chart screenshot TICKER"

**What it does:**
1. Runs `tv_health_check.py`
2. Calls `node ... chart set-symbol TICKER` to switch TradingView to the ticker
3. Calls `node ... screenshot` to capture
4. Saves to `PortfolioAnalysis/screenshots/{YYYY-MM-DD}/{TICKER}.png`
5. Reports the saved path

**CLI calls:**
```bash
node temp/tradingview-mcp/src/cli/index.js chart set-symbol TICKER
node temp/tradingview-mcp/src/cli/index.js screenshot
```

---

## Plugin Metadata

### `plugin.json` (root)

```json
{
  "name": "tradingview",
  "version": "1.0.0",
  "description": "TradingView Desktop integration for real-time prices, DCF price alerts, and chart snapshots. Calls TradingView Desktop CLI via CDP — requires Desktop running with --remote-debugging-port=9222. Falls back to yfinance when unavailable.",
  "author": "InvestmentToolkit",
  "maturity": "L3",
  "architecture": "standard",
  "skills": [
    { "name": "tv_alert_sync", "path": "skills/alert-sync/SKILL.md", "trigger": "/tv-alert-sync" },
    { "name": "tv_price_refresh", "path": "skills/price-refresh/SKILL.md", "trigger": "/tv-price-refresh" },
    { "name": "tv_chart_snapshot", "path": "skills/chart-snapshot/SKILL.md", "trigger": "/tv-snapshot" }
  ],
  "commands": [
    { "name": "tv-alert-sync", "path": "commands/tv-alert-sync.md", "trigger": "/tv-alert-sync" },
    { "name": "tv-price-refresh", "path": "commands/tv-price-refresh.md", "trigger": "/tv-price-refresh" },
    { "name": "tv-snapshot", "path": "commands/tv-snapshot.md", "trigger": "/tv-snapshot" }
  ],
  "external_dependencies": [
    {
      "name": "tradingview-mcp-cli",
      "canonical_path": "temp/tradingview-mcp/src/cli/index.js",
      "owned_by": "community",
      "purpose": "Node.js CLI that connects to TradingView Desktop via CDP"
    },
    {
      "name": "portfolio-json",
      "canonical_path": "investment_screener/backend/data/portfolio.json",
      "owned_by": "investment-screener-app",
      "purpose": "Current portfolio holdings (synced from Questrade)"
    },
    {
      "name": "target-portfolio-json",
      "canonical_path": "investment_screener/backend/data/theses/target-portfolio.json",
      "owned_by": "portfolio-advisor",
      "purpose": "Target weights and thesis for all holdings"
    },
    {
      "name": "projections-dir",
      "canonical_path": "investment_screener/backend/data/projections/",
      "owned_by": "stock-valuation",
      "purpose": "DCF projection JSONs — source of bear/base/bull alert prices"
    }
  ],
  "related_plugins": ["portfolio-advisor", "stock-valuation"],
  "tags": ["finance", "tradingview", "real-time", "alerts", "prices"]
}
```

### `.claude-plugin/plugin.json`

```json
{
  "name": "tradingview",
  "version": "1.0.0",
  "description": "TradingView Desktop integration — real-time prices, DCF alerts, chart snapshots.",
  "author": {
    "name": "richfrem",
    "email": "connect.richfrem@gmail.com"
  },
  "keywords": ["finance", "tradingview", "real-time", "alerts"]
}
```

---

## Command File Format (copy for all three)

```markdown
---
name: tv-alert-sync
description: Create TradingView price alerts at DCF bear/base/bull targets for all portfolio holdings with projections.
type: command
---

# /tv-alert-sync

Invoke the `tradingview:tv_alert_sync` skill.
```

Same pattern for `tv-price-refresh` and `tv-snapshot`.

---

## Important Constraints

1. **Never break existing functionality.** `fetch_portfolio_heatmap.py` must still work identically if the tradingview plugin doesn't exist or TradingView isn't running.

2. **All scripts run from repo root.** Paths should be resolved relative to `REPO_ROOT = Path(__file__).resolve().parents[N]` where N gets to `/Users/richardfremmerlid/Projects/InvestmentToolkit`.

3. **`tv_client.py` REPO_ROOT calculation:**  
   `tv_client.py` is at `plugins/tradingview/scripts/tv_client.py`.  
   `parents[0]` = `scripts/`, `parents[1]` = `tradingview/`, `parents[2]` = `plugins/`, `parents[3]` = repo root.  
   So `REPO_ROOT = Path(__file__).resolve().parents[3]`

4. **Node.js `--input-type` may be needed** because `temp/tradingview-mcp` uses ES modules (`"type": "module"` in package.json). The subprocess call must use `node` directly, not `node -e`.

5. **npm install check:** `tv_health_check.py` should verify that `temp/tradingview-mcp/node_modules` exists and suggest running `npm install` if not.

6. **No new npm packages in the main project.** The Node.js CLI lives entirely in `temp/tradingview-mcp/` and is called via subprocess — no changes to `investment_screener/package.json`.

7. **Python imports:** Scripts in `plugins/tradingview/scripts/` that import from `tv_client.py` should use `sys.path.insert(0, str(Path(__file__).parent))` before the import.

8. **`tv_create_alerts.py` alert CLI syntax:** Before implementing, read `temp/tradingview-mcp/src/cli/commands/alerts.js` to confirm exact argument names for alert creation.

9. **Projections directory:** `investment_screener/backend/data/projections/{TICKER}.json` — each file is a JSON array; get the latest AI_AGENT entry by `max(ai_entries, key=lambda x: x.get("savedAt", ""))`.

---

## Verification Steps (for the reviewing agent after implementation)

Run these checks to confirm everything is correct:

```bash
# 1. Plugin structure correct
ls plugins/tradingview/
ls plugins/tradingview/skills/
ls plugins/tradingview/scripts/

# 2. Plugin JSON valid
python3 -c "import json; json.load(open('plugins/tradingview/plugin.json')); print('OK')"
python3 -c "import json; json.load(open('plugins/tradingview/.claude-plugin/plugin.json')); print('OK')"

# 3. Scripts importable (syntax check)
python3 -m py_compile plugins/tradingview/scripts/tv_client.py && echo "tv_client OK"
python3 -m py_compile plugins/tradingview/scripts/tv_quote.py && echo "tv_quote OK"
python3 -m py_compile plugins/tradingview/scripts/tv_batch_quotes.py && echo "tv_batch OK"
python3 -m py_compile plugins/tradingview/scripts/tv_create_alerts.py && echo "tv_create OK"
python3 -m py_compile plugins/tradingview/scripts/tv_health_check.py && echo "tv_health OK"

# 4. Health check runs (should report TradingView unavailable gracefully)
python3 plugins/tradingview/scripts/tv_health_check.py --json

# 5. fetch_portfolio_heatmap.py still works (fallback path)
cd investment_screener/backend/py_services
python3 fetch_portfolio_heatmap.py '[{"symbol":"NVDA","shares":5}]' | python3 -c "import json,sys; d=json.load(sys.stdin); print('heatmap OK, items:', len(d))"

# 6. Skill files exist and have correct frontmatter
head -5 plugins/tradingview/skills/alert-sync/SKILL.md
head -5 plugins/tradingview/skills/price-refresh/SKILL.md
head -5 plugins/tradingview/skills/chart-snapshot/SKILL.md

# 7. Command files exist
ls plugins/tradingview/commands/
```

All 7 checks must pass. Report results back to the reviewing agent.

---

## Summary: What to Build

| File | Action |
|------|--------|
| `plugins/tradingview/plugin.json` | Create |
| `plugins/tradingview/.claude-plugin/plugin.json` | Create |
| `plugins/tradingview/commands/tv-alert-sync.md` | Create |
| `plugins/tradingview/commands/tv-price-refresh.md` | Create |
| `plugins/tradingview/commands/tv-snapshot.md` | Create |
| `plugins/tradingview/skills/alert-sync/SKILL.md` | Create |
| `plugins/tradingview/skills/price-refresh/SKILL.md` | Create |
| `plugins/tradingview/skills/chart-snapshot/SKILL.md` | Create |
| `plugins/tradingview/scripts/tv_client.py` | Create |
| `plugins/tradingview/scripts/tv_quote.py` | Create |
| `plugins/tradingview/scripts/tv_batch_quotes.py` | Create |
| `plugins/tradingview/scripts/tv_create_alerts.py` | Create |
| `plugins/tradingview/scripts/tv_health_check.py` | Create |
| `plugins/tradingview/scripts/tv_launch.py` | Create |
| `investment_screener/backend/py_services/fetch_portfolio_heatmap.py` | Modify (add optional TV price injection) |

**15 files total: 14 new, 1 modified.**
