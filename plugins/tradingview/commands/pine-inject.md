---
description: Inject a Pine Script v6 file into TradingView via CDP — lint, inject, and optionally save to personal library
argument-hint: "<path to .pine file>"
---

# /pine-inject

Invoke the `pine-inject` skill.

**Usage:** `/pine-inject {path}` or `/pine-inject {description of indicator to generate}`

**Examples:**
- `/pine-inject plugins/tradingview/assets/pinescript-indicators/ai-ta-levels.pine` — lint and inject an existing file
- `/pine-inject a volume profile indicator` — generate from description, lint, inject

**Workflow:**
1. Lint: `python3 plugins/tradingview/skills/author-pine-script/scripts/pine_linter.py <file>`
2. Inject: `node tradingview-cdp/cli.js pine inject --file <file>`
3. Optional save: `node tradingview-cdp/cli.js pine save "Name"`
4. Add to chart: `node tradingview-cdp/cli.js chart addIndicator "Name"` (close Pine Editor first)

**Preflight checks:**
- Must start with `//@version=6` (no space after `//`)
- Must contain `indicator()` declaration
- Close Pine Editor before running `addIndicator` after inject

**Personal library scripts ready to inject:**
- `plugins/tradingview/assets/pinescript-indicators/ai-ta-levels.pine` — Multi-EMA + volume bias (already saved as "AI TA Levels")
