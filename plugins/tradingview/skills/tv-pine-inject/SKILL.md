---
name: tv-pine-inject
plugin: tradingview
description: Injects custom Pine Script v6 indicators directly into TradingView Pine Editor via CDP with auto-compilation error checking. Trigger on /tv-pine-inject or 'inject pine script'.
allowed-tools: Bash, Read, Write
---

# TradingView Pine Inject

Injects custom Pine Script v6 indicators directly into TradingView Pine Editor via CDP with auto-compilation error checking.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- Pine Script v6 only: Scripts must begin with `//@version=6`.
- Content passing: Pass script content directly via `--content` parameter, not relative file path.
- Compilation safety: Check editor output for compilation errors and self-correct on failure.

## Quick start

```bash
node tradingview-cdp/cli.js pine inject --content "//@version=6\nindicator('Test')\nplot(close)"
```

## Workflow

1. Lint Pine Script via `pine_linter.py`.
2. Open Pine Editor dialog in TradingView via CDP.
3. Inject code into Monaco editor instance using `--content`.
4. Click 'Add to chart' / 'Update on chart'.
5. Verify absence of compilation errors in Pine console.

## Verification

- Confirm indicator plots on chart layout.
- Validate routing cases against `evals/evals.json`.
