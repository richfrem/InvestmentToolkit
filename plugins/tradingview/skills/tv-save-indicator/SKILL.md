---
name: tv-save-indicator
plugin: tradingview
description: Saves current Pine Script in editor to TradingView personal script library. Trigger on /tv-save-indicator or 'save pine script to library'.
allowed-tools: Bash, Read, Write
---

# TradingView Save Indicator

Saves current Pine Script in editor to TradingView personal script library.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Editor state: Pine Editor must contain valid compiled script code.
- Modal handling: Handle first-save 'Save Script As' dialog automatically.
- Library availability: Saved script appears under 'My scripts' in Indicators dialog.

## Quick start

```bash
node tradingview-cdp/cli.js pine save --name "AI TA Levels"
```

## Workflow

1. Verify Pine Script is compiled without errors in editor.
2. Dispatch save command via CDP: `node tradingview-cdp/cli.js pine save --name "{NAME}"`.
3. Confirm script name is registered in personal library.

## Verification

- Confirm script appears in Indicators dialog under 'My scripts'.
- Validate routing cases against `evals/evals.json`.
