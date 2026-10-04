---
name: tv-setup
plugin: tradingview
description: Diagnoses and guides setup of TradingView CDP dependency and debugging port. Trigger on /tv-setup or 'diagnose tradingview connection'.
allowed-tools: Bash, Read, Write
---

# TradingView Setup

Diagnoses and guides setup of TradingView CDP dependency and debugging port.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Port 9222 check: Verifies HTTP connectivity to `http://localhost:9222/json/version`.
- Node CDP dependency: Ensures `tradingview-cdp/` has node modules installed.
- Read-only diagnostic: Does not alter system network configuration.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_health_check.py
```

## Workflow

1. Check if Node.js runtime and `tradingview-cdp/` packages exist.
2. Test HTTP response on `http://localhost:9222`.
3. Provide actionable remediation steps if connection fails:
   - Launch TradingView with `--remote-debugging-port=9222`.
   - Run `npm ci` in `tradingview-cdp/`.
4. Report diagnostic status.

## Verification

- Confirm `tv_health_check.py` returns OK.
- Validate routing cases against `evals/evals.json`.
