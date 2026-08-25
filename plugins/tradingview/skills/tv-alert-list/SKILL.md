---
name: tv-alert-list
plugin: tradingview
description: >
  Fetches, analyzes, and lists active TradingView price alerts, saving the snapshot
  to the backend data folder for offline caching and verification.
  Trigger on /tv-alert-list, "list tradingview alerts", or "show active alerts".
allowed-tools: Bash, Read
---

# TradingView Alert List Skill

## What This Skill Does

1. **Checks** if TradingView Desktop is reachable on port 9222.
2. **Runs** the python listing script to scrape all current active alerts.
3. **Persists** the output to `investment_screener/backend/data/tradingview_alerts_actual.json` so that other scripts and agents can read it offline.
4. **Displays** a clean markdown summary table of active alerts to the user.

---

## Execution Step

Run the following Python script to execute the listing and generate the offline snapshot:

```bash
python3 plugins/tradingview/scripts/tv_list_alerts.py
```

---

## Output Location

The list is persisted directly to the web app backend database folder at:
*   [tradingview_alerts_actual.json](investment_screener/backend/data/tradingview_alerts_actual.json)

---

## Expected Results Format

The command output will print a summary of active alerts directly in the console:

```
Active TradingView Alerts Summary:
Ticker       Price        Condition       Label/Message
----------   ----------   -------------   -------------
CRWV         $163.00      crossing        CRWV DCF Fair Value $163
NVDA         $374.00      crossing        NVDA DCF Fair Value $374
INTC         $22.00       crossing        INTC Base Alert $22
```

Use this cached snapshot in downstream deduplication and correlation logic to avoid redundant browser CDP calls.
