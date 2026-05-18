# Pine Script v6 CDP Injector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a new AI Agent skill (`pine-inject`) inside the `tradingview` plugin that generates Pine Script v6 code and calls the existing Node.js CDP automation to inject it into TradingView.

**Architecture:** The Node.js CDP layer (`core/pine.js`) and its CLI wrapper (`cli.js`) already exist. This plan focuses on creating the Agent Skill (`SKILL.md`), adding a Python wrapper for standardized agent execution (if needed, though we can call Node directly), and ensuring the LLM prompt enforces Pine Script v6 standards and handles error correction.

**Tech Stack:** Claude/Gemini CLI (Markdown prompt), Node.js (existing CDP CLI).

---

### Task 1: Create the Pine Inject Skill Definition

**Files:**
- Create: `plugins/tradingview/skills/pine-inject/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

```markdown
# pine-inject

**Description:** Generates custom Pine Script v6 indicators and strategies and injects them directly into the TradingView Pine Editor via CDP.

**Trigger:** `/pine-inject {description}`

**Instructions:**
1. You are a Pine Script v6 expert.
2. Given the user's description, write a complete, valid Pine Script v6 `indicator` or `strategy`.
3. Use built-in `ta.*` functions where possible. Enforce v6 syntax (e.g., proper tuple unpacking `[macd, signal, hist] = ta.macd(...)`).
4. Save the generated script to `InvestmentToolkit/temp/generated_script.pine`.
5. Execute the injection using the Node.js CLI:
   `<Bash> node plugins/tradingview/node/cli.js pine inject -f InvestmentToolkit/temp/generated_script.pine </Bash>`
6. If the command succeeds, inform the user the script is on their chart.
7. If the command fails (compilation error extracted from TV), read the error output. Correct your `.pine` file and try injecting again.

**Available Resources:**
- Pine Script v6 User/Reference Manual knowledge.
```

- [ ] **Step 2: Commit**

```bash
git add plugins/tradingview/skills/pine-inject/SKILL.md
git commit -m "feat(tradingview): add pine-inject skill definition"
```

### Task 2: Fix CLI argument passing in `cli.js` (if necessary)

**Files:**
- Modify: `plugins/tradingview/node/cli.js`

*Note: The existing `cli.js` passes `opts.file` to `pine.injectPineScript(client, opts.file)`. But `injectPineScript` expects the script content, not the file path.*

- [ ] **Step 1: Write the failing test or verify current behavior**

Run: `node plugins/tradingview/node/cli.js pine inject -f nonexistent.pine`
Observe the behavior. It currently probably sends the string `"nonexistent.pine"` to TradingView instead of reading the file.

- [ ] **Step 2: Update `cli.js` to read the file content**

```javascript
// In plugins/tradingview/node/cli.js around line 90:
      handler: async (opts) => {
        const fs = await import('fs');
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        
        let scriptContent = opts.file;
        if (opts.file && fs.existsSync(opts.file)) {
            scriptContent = fs.readFileSync(opts.file, 'utf8');
        }
        
        const pine = await import('./core/pine.js');
        return pine.injectPineScript(client, scriptContent);
      },
```

- [ ] **Step 3: Test the Node injection locally**

```bash
echo "//@version=6\nindicator('Test')\nplot(close)" > /tmp/test.pine
node plugins/tradingview/node/cli.js pine inject -f /tmp/test.pine
```

- [ ] **Step 4: Commit**

```bash
git add plugins/tradingview/node/cli.js
git commit -m "fix(tradingview): read pine script content from file in cli"
```

### Task 3: Update `plugin.json` to register the new skill

**Files:**
- Modify: `plugins/tradingview/plugin.json`

- [ ] **Step 1: Add the skill to `plugin.json`**

Open `plugins/tradingview/plugin.json` and add `pine-inject` to the `skills` array.

```json
    "skills": [
      // ... existing skills
      "pine-inject"
    ]
```

- [ ] **Step 2: Commit**

```bash
git add plugins/tradingview/plugin.json
git commit -m "feat(tradingview): register pine-inject skill in plugin.json"
```