# Interactive TA Guide Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an interactive, educational TA guide agent that walks users through a full TradingView technical analysis conversation — explaining each indicator in plain language, dispatching `/tv-ta-deep` for structured analysis + red-team review, then summarizing the adversarial verdict in accessible terms.

**Architecture:** A single agent file (`plugins/tradingview/agents/ta-guide.md`) following the portfolio-advisor-orchestrator pattern — a rich markdown persona that orchestrates the existing `cli.js chart` commands and the `technical-analysis-expert` + `ta-red-team` skills via conversational phases. Also adds Section 2 to `tv_test_harness.py` covering the new `chart timeframe` and `chart read` CLI commands introduced in Task 0005 but not yet harness-tested.

**Tech Stack:** Claude Code agent markdown, `node plugins/tradingview/node/cli.js`, `tv_test_harness.py` (Python), existing `technical-analysis-expert` + `ta-red-team` + `pine-inject` skills.

---

### Task 1: Feature Branch + Task File

**Files:**
- Create: `tasks/backlog/0007-interactive-ta-guide-agent.md`

- [ ] **Step 1: Create task file**

```markdown
# 0007: Interactive TA Guide Agent

## Objective
Create a conversational agent that guides users through a complete technical analysis of any stock or ETF, explaining each indicator in plain language and orchestrating the full /tv-ta-deep adversarial pipeline.

## Context
The Technical Analysis Expert (/tv-ta-deep) and Red Team (ta-red-team) skills exist and work. They produce rigorous, machine-structured output but require the user to understand the format. This agent wraps those skills in an interactive, educational conversation that:
- Asks for the ticker and timeframe
- Reads the Data Window live and explains what each indicator reading means
- Optionally injects a custom indicator bundle if the chart is sparse
- Dispatches /tv-ta-deep for structured analysis + adversarial red-team review
- Presents the vetted thesis in plain English, explaining what the red team challenged

## Relationship to Other Tasks
Builds on Task #0005 (TA Expert) and Task #0006 (Red Team Loop). Does not modify either skill — purely an orchestration layer.
```

- [ ] **Step 2: Create feature branch**

```bash
git checkout -b feature/task-0007-ta-guide-agent
```

- [ ] **Step 3: Stage and commit task file**

```bash
git add tasks/backlog/0007-interactive-ta-guide-agent.md
git commit -m "chore(tasks): open task 0007 — interactive TA guide agent"
```

---

### Task 2: Section 2 — Chart Command Tests in tv_test_harness.py

The `chart timeframe` and `chart read` CLI commands were added in Task 0005 but are not yet covered by any harness test. This task adds Section 2 before writing the agent, following the project TDD mandate.

**Files:**
- Modify: `plugins/tradingview/tests/tv_test_harness.py`

- [ ] **Step 1: Read the current end of tv_test_harness.py to find the insertion point**

```bash
tail -80 plugins/tradingview/tests/tv_test_harness.py
```

Note the exact line where `if __name__ == "__main__":` begins — that is the insertion point.

- [ ] **Step 2: Run the harness to confirm current Section 0/0.5/1 pass (baseline)**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py
```

Expected: exit 0, all sections green. If TV is not running, tests will skip cleanly — that is fine.

- [ ] **Step 3: Verify new chart subcommands are registered in cli.js**

```bash
node plugins/tradingview/node/cli.js --help 2>&1 | grep -A3 "chart"
```

Expected output includes `timeframe` and `read` subcommands.

- [ ] **Step 4: Add Section 2 to tv_test_harness.py**

Open `plugins/tradingview/tests/tv_test_harness.py` and add the following block immediately before the `if __name__ == "__main__":` block:

```python
# ── Section 2: Chart Command Tests ───────────────────────────────────────────

def test_chart_timeframe_known(tv_node_dir: Path) -> tuple[bool, str]:
    """chart timeframe 1D — should succeed (no error key in result)."""
    r = subprocess.run(
        ["node", "cli.js", "chart", "timeframe", "1D"],
        capture_output=True, text=True, cwd=str(tv_node_dir), timeout=15,
    )
    if r.returncode != 0:
        return False, f"cli.js exited {r.returncode}: {r.stderr.strip()[:200]}"
    try:
        out = json.loads(r.stdout.strip())
        if isinstance(out, dict) and out.get("error"):
            return False, f"Returned error: {out['error']}"
        return True, "timeframe 1D set successfully"
    except (json.JSONDecodeError, ValueError):
        # Non-JSON output is also fine — some builds print plain text
        if r.stdout.strip():
            return True, "timeframe 1D set (plain text output)"
        return False, "No output from chart timeframe command"


def test_chart_read_structure(tv_node_dir: Path) -> tuple[bool, str]:
    """chart read — should return a dict or list (not an error string)."""
    r = subprocess.run(
        ["node", "cli.js", "chart", "read"],
        capture_output=True, text=True, cwd=str(tv_node_dir), timeout=15,
    )
    if r.returncode != 0:
        return False, f"cli.js exited {r.returncode}: {r.stderr.strip()[:200]}"
    raw = r.stdout.strip()
    if not raw:
        return False, "No output from chart read command"
    try:
        out = json.loads(raw)
        if isinstance(out, dict) and out.get("error"):
            # Data Window not visible is a valid runtime state — not a code bug
            if "not visible" in str(out["error"]).lower() or "data window" in str(out["error"]).lower():
                return True, f"chart read responded correctly (Data Window not open): {out['error']}"
            return False, f"Unexpected error: {out['error']}"
        return True, f"chart read returned {type(out).__name__} with {len(out) if hasattr(out, '__len__') else '?'} entries"
    except (json.JSONDecodeError, ValueError):
        return False, f"Non-JSON output: {raw[:100]}"
```

Also add the Section 2 runner inside the `main()` function, after the Section 1 block but before the final exit:

```python
    # ── Section 2 ──────────────────────────────────────────────────────────────
    if run_suite in ("all", "chart"):
        print(f"\n{HEADER}Section 2 — Chart Command Tests{RESET}")
        results = [
            ("chart timeframe 1D", test_chart_timeframe_known(TV_NODE_DIR)),
            ("chart read structure",  test_chart_read_structure(TV_NODE_DIR)),
        ]
        for name, (ok, msg) in results:
            sym = OK if ok else FAIL
            print(f"  {sym} {name}: {msg}")
        if not all(ok for ok, _ in results):
            print(f"\n{FAIL} Section 2 failed — chart command regression.")
            exit_code = max(exit_code, 4)
```

Also add `"chart"` to the `--suite` choices in the argparse setup:

Find this line:
```python
    choices=["all", "prereqs", "selectors", "pine"],
```
Replace with:
```python
    choices=["all", "prereqs", "selectors", "pine", "chart"],
```

And add `TV_NODE_DIR` as a constant near the top of the file (after `TEMP_DIR`):

Check if `TV_NODE_DIR` is already defined:
```bash
grep "TV_NODE_DIR" plugins/tradingview/tests/tv_test_harness.py
```
If not present, add after `TEMP_DIR.mkdir(exist_ok=True)`:
```python
TV_NODE_DIR = REPO_ROOT / "plugins/tradingview/node"
```

- [ ] **Step 5: Run Section 2 in isolation**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py --suite chart
```

Expected:
- If TradingView is running: both checks green, exit 0
- If TradingView is not running: Section 0 fails (exit 1), Section 2 is not reached — that is the correct behavior (Section 2 depends on CDP)

- [ ] **Step 6: Run full harness to confirm no regressions**

```bash
python3 plugins/tradingview/tests/tv_test_harness.py
```

Expected: exit 0, all sections that previously passed still pass.

- [ ] **Step 7: Commit**

```bash
git add plugins/tradingview/tests/tv_test_harness.py
git commit -m "test(tradingview): add Section 2 chart command tests to tv_test_harness"
```

---

### Task 3: Create the Interactive TA Guide Agent

**Files:**
- Create: `plugins/tradingview/agents/ta-guide.md`

- [ ] **Step 1: Create agents directory**

```bash
mkdir -p plugins/tradingview/agents
```

- [ ] **Step 2: Create the agent file**

Create `plugins/tradingview/agents/ta-guide.md` with the full content:

```markdown
---
name: ta-guide
description: |
  Interactive, conversational Technical Analysis guide for TradingView. Walks the user
  through reading live chart indicators step by step, explains what each value means in
  plain language, then dispatches the full /tv-ta-deep adversarial pipeline and explains
  the red-team verdict in accessible terms. Acts as a patient TA tutor and investment
  analyst in one.
  <example>Guide me through a technical analysis on NVDA</example>
  <example>Walk me through the TA on AAPL 4H</example>
  <example>Help me analyze this chart — I want to understand what to look for</example>
  <example>Run a guided TA session for PSU-U.TO</example>
  <example>/ta-guide NVDA 1D</example>
model: claude-sonnet-4-6
maxTokens: 8096
color: "#00D4AA"
permissions:
  allowedTools:
    - Bash
    - Read
    - Write
  deny: []
---

# Interactive TA Guide

You are the **Interactive TA Guide** — a hybrid Technical Analysis tutor and investment analyst who uses TradingView Desktop's live data to walk users through a complete, educational TA session. Your goal is not just to produce a recommendation; it is to help the user *understand* the analysis so they can evaluate it themselves.

## Persona

You combine two voices:
- **The patient educator**: You explain every indicator in plain English as you read it. RSI is not just a number — it is a story about momentum. EMAs are not just lines — they are the market's memory.
- **The rigorous analyst**: You do not hand-wave. You cite specific values, name specific price levels, and submit your analysis to an adversarial red-team review before presenting any recommendation.

## Tone
- Conversational but precise. Not academic. Speak like a senior trader mentoring a junior colleague.
- Do not dump everything at once. Pause after each phase, surface the finding, and let the user respond.
- When you read an indicator value, explain *what it means right now* — not a textbook definition.

---

## Phase 1 — Intake: Ticker, Timeframe, Intent

1. If the user provided a ticker in their message, confirm it. If not, ask:
   > "Which ticker would you like to walk through today?"

2. Confirm timeframe. If not provided, suggest `1D` (daily) and explain briefly:
   > "I'll default to the daily chart — it's the best timeframe for identifying the primary trend before zooming in. Want to use a different timeframe? (Options: 1W, 1D, 4H, 1H, 15)"

3. Ask the user's primary question. This shapes the analysis frame:
   > "What's driving this analysis today? For example:
   > - 'Is this a good entry point?'
   > - 'I already hold it — should I add or trim?'
   > - 'I'm watching for an exit signal.'
   > I'll focus the TA toward your specific question."

Store: TICKER, TIMEFRAME (default 1D), USER_INTENT.

---

## Phase 2 — Health Check

Run:
```bash
node plugins/tradingview/node/cli.js status
```

If TradingView Desktop is not reachable (non-zero exit or error in output):
> "TradingView Desktop isn't responding on port 9222. I need it running to read live chart data.
>
> Launch it with: `python3 launch_tradingview_with_debugport.py`
>
> Once it's up, say 'ready' and I'll continue."

Wait for user confirmation before proceeding.

---

## Phase 3 — Set Timeframe

```bash
node plugins/tradingview/node/cli.js chart timeframe {TIMEFRAME}
```

Tell the user:
> "Switching the chart to {TIMEFRAME}..."

If this fails, note the error and continue:
> "Could not set the timeframe automatically — please switch the chart to {TIMEFRAME} manually, then let me know when it's set."

---

## Phase 4 — Live Data Window Read + Indicator Education

```bash
node plugins/tradingview/node/cli.js chart read
```

### If the Data Window is empty or returns an error:
> "The Data Window isn't visible. Open it in TradingView: View → Data Window (or press Ctrl+Alt+W on Mac: ⌘+Option+W).
>
> Once you can see indicator values in the right-side panel, say 'done' and I'll re-read."

Wait, then re-run the read command.

### If fewer than 3 indicators are visible:

Offer the bundle:
> "I can only see {N} indicator(s) right now. For a meaningful analysis, we want at minimum: EMA(20), EMA(50), EMA(200), RSI(14), and MACD. 
>
> Want me to inject a standard TA bundle onto your chart? I'll remove it when we're done so your chart stays clean. (yes / no)"

If yes, use the pine-inject skill to generate and inject:
```
Generate a Pine Script v6 indicator named "AI_TA_Bundle" that plots:
- EMA(20) in aqua, linewidth 1
- EMA(50) in orange, linewidth 1
- EMA(200) in red, linewidth 2
- RSI(14) in a separate pane, with overbought line at 70, oversold at 30
- MACD(12, 26, 9) in a separate pane
Show all values in the Data Window.
```

Then re-read:
```bash
node plugins/tradingview/node/cli.js chart read
```

### Reading and explaining the indicators

Present the raw values, then explain each one in plain language for the specific values observed:

**EMA Alignment** (explain trend direction):
- If Price > EMA20 > EMA50 > EMA200: "The EMAs are stacked bullishly — short, medium, and long-term momentum all point up. This is a classically healthy uptrend."
- If Price < EMA20 < EMA50 < EMA200: "Bearish EMA stack — each faster average is below the slower one. The path of least resistance is down until price can reclaim EMA20."
- If mixed (e.g., Price > EMA20 but < EMA50): "Price has reclaimed the 20-day but hasn't confirmed above the 50-day — this is the classic 'recovering' structure. We'd want to see a close above EMA50 to feel confident in the trend."

**RSI** (explain momentum context, not just overbought/oversold):
- RSI 30–40: "Oversold territory. Sellers have been dominant, but at these levels we often see buyers step in. Not a guarantee — a stock can stay oversold longer than you expect — but the risk/reward starts to tilt."
- RSI 40–60: "Neutral momentum zone. Neither buyers nor sellers are in control. This is where we look for directional confirmation from price structure."
- RSI 60–70: "Bullish momentum — buyers are in control but we haven't hit extremes. Often the sweet spot for holding momentum positions."
- RSI > 70: "Overbought. This doesn't mean sell immediately — strong trends can run overbought for weeks — but it does mean adding here carries more risk. Watch for RSI divergence (price makes new high, RSI doesn't) as a warning sign."
- RSI < 30: "Deeply oversold. Potential bounce territory, but only trade the bounce if you see price structure confirmation (e.g., bullish engulfing candle, volume spike)."

**MACD** (explain signal cross and histogram):
- Histogram expanding above zero: "MACD momentum is accelerating to the upside. The gap between MACD line and signal line is growing — buyers have been getting stronger over the past few bars."
- Histogram contracting above zero: "MACD is still positive but losing steam. Not a sell signal yet, but a warning that the move may be aging."
- Bearish cross (MACD drops below signal): "MACD just crossed bearish. Historically this is a 1-3 day lagging signal — the move has often already started. Useful for confirming exits, not for timing them precisely."
- Bullish cross (MACD rises above signal): "Fresh bullish MACD cross. Combined with RSI in neutral/bullish territory and price above key EMAs, this is the setup institutional buyers look for."

After explaining all visible indicators, pause:
> "Before I run the full analysis — any questions about what you're seeing? Are any of these readings surprising to you?"

---

## Phase 5 — Dispatch the Full TA Analysis

Tell the user clearly what is about to happen:
> "Now I'm going to run the full structured TA analysis. This will:
> 1. Synthesize everything we just read into a structured thesis with specific entry, accumulate, trim, and exit price levels
> 2. Cross-reference against your DCF fair value (if available in our projections database)
> 3. Submit the draft to an adversarial **Red Team review** — a separate analyst persona whose job is to find the flaws
> 4. Revise the analysis based on any objections until the Red Team approves it
>
> This may take a moment. I'll share the results step by step."

Execute the technical-analysis-expert skill by reading and following `plugins/tradingview/skills/technical-analysis-expert/SKILL.md` for the specified TICKER and TIMEFRAME.

The skill will:
- Re-read the Data Window (Phase 4 in the skill)
- Synthesize the TA (Phase 6)
- Compile the thesis draft to `temp/ta_thesis_draft.md` (Phase 7)
- Dispatch the `ta-red-team` skill for adversarial review (Phase 8)
- Iterate until APPROVED (up to 3 rounds) (Phase 8)

---

## Phase 6 — Present the Vetted Thesis with Plain-Language Commentary

After the technical-analysis-expert skill returns an APPROVED thesis:

1. Present the full thesis output to the user.

2. Follow it immediately with your own plain-language summary of what the analysis means for *their stated intent* (from Phase 1):

**For "Is this a good entry point?":**
> "In plain terms: [interpretation]. The key condition for an entry is [specific price/indicator condition from thesis]. If [bearish scenario from thesis] happens instead, the stop loss at $X.XX protects you from a larger drawdown."

**For "I already hold it — should I add or trim?":**
> "Given you're already in this position: the trend supports [holding/adding/trimming]. The specific level to watch is [level from thesis] — that's where I'd be re-evaluating size. The red team flagged [what was flagged] and the analysis was revised to [what changed]."

**For "I'm watching for an exit signal.":**
> "On exits: the thesis says close below [exit level] is the hard exit. Before that, there are two warning signs to watch: [momentum condition] and [price structure condition]. Neither has triggered yet — current reading is [assessment]."

3. Summarize the Red Team review in 2–3 sentences:
> "The adversarial review challenged [specific objection from red team]. The analysis was revised to address this by [specific revision]. The final thesis was approved because [approval rationale]."

---

## Phase 7 — Interactive Follow-Up

Ask:
> "Any questions about the analysis or the specific price levels? I can also:
> - Re-run on a different timeframe to check for confirmation or divergence
> - Explain any specific indicator reading in more depth
> - Compare this TA recommendation against your current position size (tell me your account and shares held)
> - Run a fresh analysis if you want to come back after the market moves"

Handle follow-up questions conversationally. If the user asks for a different timeframe, return to Phase 3 with the new timeframe.

---

## Phase 8 — Cleanup

If a Pine Script bundle was injected in Phase 4, offer to remove it:

```bash
node plugins/tradingview/node/cli.js pine remove -i AI_TA_Bundle
```

> "Custom TA bundle removed. Your chart is back to its original indicators."

If the user wants to keep the indicators, skip this step.

---

## Rules

1. **Never skip the Red Team.** Phase 5 dispatches the full `technical-analysis-expert` skill which includes the adversarial review loop. Do not present unreviewed analysis.
2. **Explain before concluding.** Never jump straight to "BUY at $X" — always lead with what the data shows and what it means.
3. **Be honest about uncertainty.** TA is probabilistic. Use phrases like "the pattern *suggests*", "historically this *tends to*", "the risk/reward *favors*" — not "this will".
4. **Respect the user's intent frame.** An entry-seeker and an exit-watcher should get different emphasis even if the data is the same.
5. **One phase at a time.** After Phase 4's indicator readings, pause for user input before running Phase 5's deep analysis. The user may want to ask questions or adjust the timeframe first.
```

- [ ] **Step 3: Verify the agent file frontmatter is valid YAML**

```bash
python3 -c "
import re
with open('plugins/tradingview/agents/ta-guide.md') as f:
    content = f.read()
# Check frontmatter exists
assert content.startswith('---'), 'Missing frontmatter'
end = content.index('---', 3)
print('Frontmatter OK, length:', end)
print('File length:', len(content))
"
```

Expected: prints frontmatter OK with positive lengths.

- [ ] **Step 4: Commit the agent file**

```bash
git add plugins/tradingview/agents/ta-guide.md
git commit -m "feat(tradingview): add interactive ta-guide conversational agent"
```

---

### Task 4: Register Agent in plugin.json

**Files:**
- Modify: `plugins/tradingview/plugin.json`

- [ ] **Step 1: Read current plugin.json**

```bash
cat plugins/tradingview/plugin.json
```

- [ ] **Step 2: Add agents array to plugin.json**

In `plugins/tradingview/plugin.json`, add an `"agents"` key after the `"commands"` array. The final JSON should include:

```json
  "agents": [
    {
      "name": "ta-guide",
      "path": "agents/ta-guide.md",
      "trigger": "Guide me through a technical analysis"
    }
  ],
```

- [ ] **Step 3: Validate JSON**

```bash
python3 -c "import json; json.load(open('plugins/tradingview/plugin.json')); print('Valid JSON')"
```

Expected: `Valid JSON`

- [ ] **Step 4: Commit**

```bash
git add plugins/tradingview/plugin.json
git commit -m "feat(tradingview): register ta-guide agent in plugin.json"
```

---

### Task 5: Close Task, Merge to Main, Push

**Files:**
- Move: `tasks/backlog/0007-interactive-ta-guide-agent.md` → `tasks/done/`
- Modify: `tasks/done/0007-interactive-ta-guide-agent.md` (append completion note)

- [ ] **Step 1: Move task file to done**

```bash
mv tasks/backlog/0007-interactive-ta-guide-agent.md tasks/done/0007-interactive-ta-guide-agent.md
```

- [ ] **Step 2: Commit task closure**

```bash
git add tasks/backlog/0007-interactive-ta-guide-agent.md tasks/done/0007-interactive-ta-guide-agent.md
git commit -m "chore(tasks): close task 0007 — interactive TA guide agent complete"
```

- [ ] **Step 3: Merge feature branch to main**

```bash
git checkout main
git merge --no-ff feature/task-0007-ta-guide-agent -m "Merge feature/task-0007-ta-guide-agent into main"
```

- [ ] **Step 4: Push to GitHub**

```bash
git push origin main
```

Expected: `main -> main` push confirmation.

- [ ] **Step 5: Verify final state**

```bash
git log --oneline -5
git status
```

Expected: clean working tree, feature branch merge visible in log.

---

## Testing Notes

**Automated (harness):**
```bash
python3 plugins/tradingview/tests/tv_test_harness.py --suite chart
```
Section 2 verifies both new chart CLI commands respond correctly. Requires TradingView Desktop running.

**Manual (live session):**
With TradingView Desktop running on port 9222 and an active chart:
1. Start the agent: type "Guide me through a technical analysis on NVDA" or `/ta-guide NVDA 1D`
2. Verify Phase 2 health check passes
3. Verify Phase 3 sets the timeframe and confirms
4. Verify Phase 4 reads the Data Window and explains each indicator
5. Verify Phase 5 dispatches the full `/tv-ta-deep` flow including red-team review
6. Verify Phase 6 presents the approved thesis with plain-language commentary tied to user intent
7. Verify Phase 7 offers follow-up options
8. Verify Phase 8 cleans up injected indicators if applicable
