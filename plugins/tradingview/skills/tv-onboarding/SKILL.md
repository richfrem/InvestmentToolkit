---
name: tv-onboarding
plugin: tradingview
description: Setup and diagnostic guide for TradingView Desktop and remote debugging port 9222. Trigger on /tv-onboarding or 'connect tradingview'.
allowed-tools: Bash, Read, Write
---

# TradingView Onboarding

Setup and diagnostic guide for TradingView Desktop and remote debugging port 9222.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Port 9222 requirement: TradingView Desktop must launch with `--remote-debugging-port=9222`.
- Broker login prerequisite: Broker panel must be connected to enable portfolio sync.
- Read-only diagnostic: Health checks do not mutate user settings.

## Quick start

```bash
python3 plugins/tradingview/scripts/tv_health_check.py
```

## Workflow

1. Check if TradingView Desktop is installed.
2. Launch TradingView with debugging enabled:
   `open -a 'TradingView' --args --remote-debugging-port=9222`
3. Run automated health check:
   `python3 plugins/tradingview/scripts/tv_health_check.py`
4. Report connectivity status across chart engine and broker panel.

## Verification

- Confirm `tv_health_check.py` outputs 'OK (port 9222 open)'.
- Validate routing cases against `evals/evals.json`.
