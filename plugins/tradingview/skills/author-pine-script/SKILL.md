---
name: author_pine_script
plugin: tradingview
description: >
  The master self-evolving workflow for authoring, research, and managing custom
  Pine Script v6 indicators. Empowers the agent to learn from existing indicators,
  apply strict repainting safeguards, and self-heal by creating new helpers.
allowed-tools: Bash, Read, Write
---

# 🎨 Self-Evolving Pine Script™ v6 Authoring Workflow

**Trigger:** `/author-pine {description}` or "create a pine script for..."

**Role:** Senior Pine Script Architect. You don't just write code; you research, verify, and improve the toolkit's own capabilities as you work.

---

## Phase 0 — Research & Self-Learning (The Browser-Harness Pattern)

Before authoring, determine if you are missing information about the target indicator.

1.  **Check References:** Review `Top_TradingView_Indicators_Reference.md` to see if the core mechanics are already documented.
2.  **Read Source from TradingView:** If the indicator exists as a community script, fetch its Pine Script source directly from the Indicators dialog to study its implementation:
    ```bash
    python3 plugins/tradingview/skills/author-pine-script/scripts/pine_source_reader.py --name "Indicator Name"
    ```
    Source files are saved to `temp/indicator_sources/<Name>.pine`. You can also fetch the top 10 most popular indicators at once with `--top 10`.
3.  **Search & Learn:** Use `/add-indicator` or direct CDP calls to add the indicator and read its Data Window outputs to understand its runtime behavior.
4.  **Fill Gaps:** If you discover a non-obvious pattern, timing quirk, or new indicator logic, **update the references folder** (the "Map, not the Diary" approach) to teach your future self.

---

## Phase 1 — Mandatory Rules Review

You MUST review these two documents before generating code:
- `references/pinescript_overview.md` (Syntax & v6 Migration)
- `references/PineScript_Agent_Skill_Rules.md` (Repainting Safeguards & Determinism)

---

## Phase 2 — Robust Generation & Authoring

Write the script to `temp/generated_script.pine`.

**Strict Iron Rules:**
- **//@version=6** is mandatory.
- **No Repainting:** Use `barstate.isconfirmed` and `[1]` offsets for signal logic.
- **Deterministic Naming:** Use traceable names for plots (e.g., `plot(..., title="AI_Signal_EMA")`).
- **State Optimization:** Use `var` for one-time calcs and `varip` for tick-level tracking.

---

## Phase 2.5 — Pre-Injection Lint Gate

Before injecting, run the linter against the generated file:

```bash
python3 plugins/tradingview/skills/author-pine-script/scripts/pine_linter.py temp/generated_script.pine
```

| Exit code | Meaning | Action |
|-----------|---------|--------|
| `0` (no errors) | Passes — warnings are informational | Proceed to Phase 3 |
| `1` (errors) | Fails — fix before injecting | Read the `[ERROR]` lines, patch `temp/generated_script.pine`, re-lint (max 3 attempts) |

**Linter checks:**
- `//@version=6` present
- Exactly one `indicator()` / `strategy()` / `library()` declaration
- `request.security()` calls include explicit `lookahead=` argument
- Boolean expressions not passed to `na()` or `nz()`
- Drawing objects (`label.new`, `line.new`, etc.) declared with `var` or `varip`

Do **not** inject a script that returns exit code 1.

---

## Phase 3 — Injection & Self-Healing Loop

Push the script to the active chart:
```bash
python3 plugins/tradingview/scripts/tv_pine_inject.py -f temp/generated_script.pine
```

**The Self-Healing Loop:**
- If the JSON response contains `success: false` or a compilation error:
    1. Analyze the error log.
    2. If the failure is due to a **stale DOM selector** or **missing helper**: Stop and **patch the underlying script** (`tradingview-cdp/core/pine.js` or the Python wrapper) before retrying.
    3. If it's a syntax error: Fix `temp/generated_script.pine` and retry (max 3 times).

---

## Phase 4 — Persistence (Library & Layout)

1.  **Save to Library:** `node tradingview-cdp/cli.js pine save --name "Indicator Name"`
2.  **Save Layout:** `node tradingview-cdp/cli.js chart saveLayout --name "agent-layout"`

---

## Phase 5 — Capability Evolution

If this task required you to invent a new logic or workaround that would be useful for other skills:
1.  **Create a new Script:** If you needed a new specialized Python wrapper, write it to `plugins/tradingview/scripts/`.
2.  **Update Manifest:** Add any new files to `symlinks.json` and run the symlink manager.
3.  **Document:** Update the "How It Works" section of this or other `SKILL.md` files.
