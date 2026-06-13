---
name: tv_setup
plugin: tradingview
description: Diagnoses and guides setup of the TradingView CDP dependency and debugging port.
allowed-tools: Bash, Read
---

# TradingView CDP Setup & Diagnostic Skill

## What This Skill Does

1. **Checks** if the `tradingview-cdp` dependency folder exists.
2. **Checks** if `npm ci` has been run inside it (validates `node_modules`).
3. **Checks** if TradingView Desktop is running on debug port `9222`.
4. **Guides** the user to automatically resolve any issues.

---

## Diagnostics Check

To run the full suite of programmatic diagnostics:

```bash
python3 "$(find plugins/tradingview/scripts ~/.claude/plugins/cache -name tv_health_check.py -path "*/tradingview/*" 2>/dev/null | sort | tail -1)"
```

---

## Action Plan for Common Issues

### 1. Missing `tradingview-cdp` folder or `node_modules`
If the folder is missing or dependencies are not installed, run:
```bash
cd tradingview-cdp && npm ci
```

### 2. TradingView Desktop not running on Port 9222
If the health check fails due to the port not being reachable:
- On macOS:
  ```bash
  python3 tools/launch_tradingview_with_debugport.py
  ```
- Or run manually:
  - Close all instances of TradingView Desktop.
  - Launch from command line:
    ```bash
    open -a TradingView --args --remote-debugging-port=9222
    ```
