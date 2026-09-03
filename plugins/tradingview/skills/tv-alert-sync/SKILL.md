---
name: tv-alert-sync
plugin: tradingview
description: >
  Creates TradingView price alerts at DCF bear/base/bull scenarioPrice targets
  for all (or one) portfolio holdings that have projection JSONs. Requires
  TradingView Desktop running with --remote-debugging-port=9222.
  Trigger on /tv-alert-sync, "sync tradingview alerts", or "create dcf alerts".
allowed-tools: Bash, Read
---

# TradingView Alert Sync Skill

## What This Skill Does

1. **Checks** TradingView Desktop is reachable (port 9222)
2. **Accepts** an optional `--ticker TICKER` argument for single-ticker mode
3. **Reads** DCF projection JSONs from `investment_screener/backend/data/projections/`
4. **Creates** price alerts at bear / base / bull / fair-value levels in TradingView
5. **Reports** a results table: ticker | alerts created | alerts failed | status
6. **Suggests** next steps

---

## Phase 1 — Health Check

```bash
python3 "$(find plugins/tradingview/scripts ~/.claude/plugins/cache -name tv_health_check.py -path "*/tradingview/*" 2>/dev/null | sort | tail -1)" --json
```

If TradingView is **not** running, print the following and stop:

```
TradingView Desktop not detected on port 9222.
Launch it with: python3 plugins/tradingview/scripts/tv_launch.py
Or manually:    open -a TradingView --args --remote-debugging-port=9222

Once TradingView is running, re-run /tv-alert-sync.
```

If npm node_modules are missing, print:

```
TradingView CLI dependencies not installed.
Run: cd tradingview-cdp && npm ci
Then re-run /tv-alert-sync.
```

---

## Phase 2 — Create Alerts

### All holdings mode (default):
```bash
python3 plugins/tradingview/scripts/tv_create_alerts.py
```

### Single ticker mode:
```bash
python3 plugins/tradingview/scripts/tv_create_alerts.py --ticker CRWV
```

### Dry-run (preview without creating):
```bash
python3 plugins/tradingview/scripts/tv_create_alerts.py --dry-run
```

---

## Phase 3 — Report Results

Parse the JSON output and display a formatted table:

```
╔══════════════════════════════════════════════════════════════════╗
║              TRADINGVIEW ALERT SYNC RESULTS                      ║
╚══════════════════════════════════════════════════════════════════╝

Ticker       Bear Alert    Base Alert    Bull Alert    Fair Value    Status
----------   ----------    ----------    ----------    ----------    ------
CRWV         $14            $134          $393          $163         ✅ Created
NVDA         —              —             —             $374         ✅ Created (no scenarioPrice)
INTC         $8             $22           $35           $18          ✅ Created
ALAB         —              —             —             —            ⚠️  Skipped (no projection)

Summary: 3 tickers, 11 alerts created, 0 failed, 1 skipped
```

---

## Phase 4 — Suggest Next Steps

After a successful sync:

```
✅ Alerts synced to TradingView.

Tip: Run /tv-alert-sync after each /update-stock-analysis to keep alerts current
     with your latest DCF projections.

To view alerts in TradingView: Alerts panel (bell icon, top-right toolbar).
```

---

## Error Handling

| Situation | Response |
|-----------|----------|
| TradingView not running | Print launch instructions, exit |
| npm not installed | Print install command, exit |
| No projection file for ticker | Skip silently, note in table |
| No scenarioPrice in projection | Skip scenario-level alerts, still create fairValue alert |
| TradingView CLI error for one ticker | Mark as failed, continue with others |

---

## Hard Rules

1. **Never create alerts** without running the health check first
2. **Always report** skipped tickers with the reason
3. **Dry-run by default** if the user says "preview" or "what would be created"
