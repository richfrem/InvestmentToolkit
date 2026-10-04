---
name: tv-author-pine-script
plugin: tradingview
description: Master workflow for authoring, researching, and linting custom Pine Script v6 indicators. Trigger on /tv-author-pine-script or 'author pine script'.
allowed-tools: Bash, Read, Write
---

# TradingView Author Pine Script

Master workflow for authoring, researching, and linting custom Pine Script v6 indicators.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Pine Script v6 only: All generated scripts must specify `//@version=6`.
- Mandatory lint gate: Must pass `plugins/tradingview/scripts/pine_linter.py` before injection.
- No repainting: Forbidden to use lookahead on unconfirmed historical bars or future data leakage.
- Standalone self-contained code: Never import non-existent external libraries.

## Quick start

```bash
python3 plugins/tradingview/scripts/pine_linter.py <script.pine>
```

## Workflow

1. Research existing indicator references in `plugins/tradingview/assets/pinescript-indicators/`.
2. Author indicator logic conforming strictly to Pine Script v6 syntax.
3. Run automated linter: `python3 plugins/tradingview/scripts/pine_linter.py <file.pine>`.
4. Inject onto chart via `tv-pine-inject`.
5. Monitor Pine Editor console for compilation errors and self-heal if warnings occur.

## Verification

- Confirm `pine_linter.py` returns exit code 0.
- Confirm chart compiles without runtime errors in TradingView.
- Validate routing cases against `evals/evals.json`.
