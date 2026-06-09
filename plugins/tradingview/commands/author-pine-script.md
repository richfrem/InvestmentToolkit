---
description: Full Pine Script v6 authoring workflow — source research, lint, inject, and save to TradingView personal library
argument-hint: "<description of indicator to build>"
---

# /author-pine-script

Invoke the `author-pine-script` skill.

**Usage:** `/author-pine-script {description}`

**Examples:**
- `/author-pine-script a multi-timeframe momentum indicator with RSI divergence` — research community indicators, author a v6 script, lint, inject, and save
- `/author-pine-script order blocks with liquidity sweeps` — study PA Toolkit patterns, author custom equivalent

**Workflow:**
1. Phase 0: Research — reads source of top community indicators via `pine_source_reader.py`; checks `community-reference/` for saved local references
2. Phase 1: Draft — writes Pine Script v6 with `indicator()`, proper `var` state, and `display=display.data_window` for Data Window visibility
3. Phase 2.5: Lint gate — `pine_linter.py` must pass (0 errors) before injection
4. Phase 3: Inject — `node tradingview-cdp/cli.js pine inject --file <path>` with up to 3 self-heal attempts
5. Phase 4: Save — `node tradingview-cdp/cli.js pine save "Name"` to TV personal library

Scripts are saved to `plugins/tradingview/assets/pinescript-indicators/` for reuse across sessions.

**References:**
- `plugins/tradingview/references/Top_TradingView_Indicators_Reference.md`
- `plugins/tradingview/references/pinescript_overview.md`
- `plugins/tradingview/references/PineScript_Agent_Skill_Rules.md`
- `plugins/tradingview/assets/pinescript-indicators/community-reference/pa-toolkit-lite-ualgo.pine` — order block + liquidity sweep patterns
