---
name: tv-onboarding
plugin: tradingview
description: >
  Deep-dive TradingView Desktop setup and CDP diagnostic guide.
  Walks users through installing TradingView Desktop, connecting their broker,
  and establishing remote debugging port 9222.
  Trigger on /tv-onboarding, "set up tradingview", or "connect tradingview".
allowed-tools: Bash, Read
---

# TradingView Desktop Onboarding Guide

**Trigger:** `/tv-onboarding` or `connect tradingview`

---

## Purpose
TradingView Desktop with remote debugging port `9222` is the primary data and execution layer for InvestmentToolkit. It enables live portfolio sync, real-time prices, and automated order execution.

---

## Step 1 — Check Installation
Check if TradingView Desktop is installed:
```bash
ls /Applications/TradingView.app 2>/dev/null && echo "Installed" || echo "Not found"
```

If not found, download and install TradingView Desktop:
`https://www.tradingview.com/desktop/`

---

## Step 2 — Launch with Remote Debugging Port 9222
Launch TradingView Desktop with CDP debugging enabled:
```bash
open -a "TradingView" --args --remote-debugging-port=9222
```

---

## Step 3 — Confirm CDP Port Reachability
Verify port 9222 is active:
```bash
curl -s http://localhost:9222/json/version | head -n 5
```

---

## Step 4 — Run Live Health Check
Run the CDP engine health check:
```bash
node tradingview-cdp/cli.js health
```
