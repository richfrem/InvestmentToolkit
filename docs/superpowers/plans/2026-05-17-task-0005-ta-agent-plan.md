# Task 0005 Implementation Plan: TA Expert Agent & CDP Chart Controls

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a Technical Analysis Expert sub-agent and the Node.js CDP functions to manipulate TradingView charts (timeframes, reading data window).

**Architecture:** A new skill (`technical-analysis-expert`) will orchestrate the TA analysis. New Node.js functions in `plugins/tradingview/node/core/chart.js` will handle CDP interactions.

**Tech Stack:** Node.js (CDP), Claude/Gemini CLI (Markdown skills).

---

### Task 1: Node.js CDP Chart Controls

**Files:**
- Create: `plugins/tradingview/node/core/chart.js`
- Modify: `plugins/tradingview/node/cli.js`

- [ ] **Step 1: Create chart.js with CDP functions**
Implement `changeTimeframe` and `readDataWindow`.
*(Note: Use `client.Runtime.evaluate` to interact with the DOM.)*

```javascript
export async function changeTimeframe(client, resolution) {
  // Simulates typing the resolution on the chart to open the interval dialog
  // ... DOM manipulation via CDP
}

export async function readDataWindow(client) {
  // Scrapes the data window for indicator values
  // ... DOM manipulation via CDP
}
```

- [ ] **Step 2: Expose via CLI**
Update `cli.js` to add `chart` command group with `timeframe` and `read` actions.

- [ ] **Step 3: Commit**
```bash
git add plugins/tradingview/node/core/chart.js plugins/tradingview/node/cli.js
git commit -m "feat(tradingview): add CDP chart manipulation and data reading"
```

### Task 2: Create the TA Expert Skill

**Files:**
- Create: `.agents/skills/technical-analysis-expert/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

```markdown
# technical-analysis-expert

**Description:** Acts as a seasoned Technical Analyst, manipulating TradingView charts and evaluating indicators to advise on price levels.

**Trigger:** `/tv-ta-deep {TICKER}`

**Instructions:**
1. You are an Expert Technical Analyst.
2. When asked to evaluate a ticker:
   - Use the Node CLI to set the ticker and timeframe: `<Bash> node plugins/tradingview/node/cli.js chart timeframe 1D </Bash>`
   - Use the Node CLI to read the data window: `<Bash> node plugins/tradingview/node/cli.js chart read </Bash>`
3. If necessary, use `/pine-inject` to load a custom indicator first.
4. Analyze the returned data (MAs, RSI, MACD, etc.).
5. Provide actionable entry, trim, and exit price levels based on technical support/resistance and momentum.
```

- [ ] **Step 2: Commit**
```bash
git add .agents/skills/technical-analysis-expert/SKILL.md
git commit -m "feat(agents): add technical analysis expert skill"
```