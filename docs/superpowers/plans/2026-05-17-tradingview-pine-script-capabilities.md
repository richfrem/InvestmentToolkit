```markdown
# TradingView Pine Script Capabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Node CLI commands, Python wrappers, and an AI skill to autonomously generate, inject, and read Pine Script indicators via TradingView CDP.

**Architecture:** Extend the existing TradingView Node CLI (`plugins/tradingview/node/cli.js`) with a new `pine` router namespace. Implement CDP DOM automation in `core/pine.js` to interact directly with the Pine Editor and Data Window (Approach A). Create a Python service wrapper (`plugins/tradingview/scripts/tv_pine_manager.py`) to interface with the Node CLI and handle file I/O. Finally, scaffold the AI Agent Skill (`.agents/skills/tv_pine_advisor/SKILL.md`) that will orchestrate the end-to-end indicator generation, injection, read, and removal lifecycle.

**Tech Stack:** Node.js, Python 3, CDP (Chrome DevTools Protocol), Jest, pytest, Pine Script v5.

---

### Task 1: Node CLI Pine Editor Automation Tests and Stubbing

**Files:**
- Create: `plugins/tradingview/node/tests/pine.test.js`
- Create: `plugins/tradingview/node/core/pine.js`

- [x] **Step 1: Write the failing test**

```javascript
// plugins/tradingview/node/tests/pine.test.js
const { injectPineScript, removePineScript } = require('../core/pine');

describe('Pine Script Injection', () => {
    it('fails gracefully if Pine Editor tab is missing', async () => {
        // Mock CDP client failing to find selector
        const mockClient = { DOM: { querySelector: jest.fn().mockRejectedValue(new Error('Node not found')) } };
        const result = await injectPineScript(mockClient, 'plot(close)');
        expect(result.success).toBe(false);
        expect(result.error).toMatch(/Pine Editor not found/);
    });

    it('injects script and adds to chart successfully', async () => {
        // Mock successful CDP interaction
        const mockClient = { DOM: { querySelector: jest.fn().mockResolvedValue({ nodeId: 1 }) }, Input: { insertText: jest.fn() } };
        const result = await injectPineScript(mockClient, 'plot(close)');
        expect(result.success).toBe(true);
    });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npx jest plugins/tradingview/node/tests/pine.test.js`
Expected: FAIL because `core/pine.js` does not exist.

- [x] **Step 3: Write minimal implementation**

```javascript
// plugins/tradingview/node/core/pine.js
async function injectPineScript(client, scriptContent) {
    try {
        const editorTab = await client.DOM.querySelector({ selector: '.js-pine-editor-tab', nodeId: 1 });
        if (!editorTab || !editorTab.nodeId) throw new Error('Pine Editor not found');
        return { success: true };
    } catch (e) {
        return { success: false, error: e.message || 'Pine Editor not found' };
    }
}
async function removePineScript(client, indicatorName) {
    return { success: true };
}
module.exports = { injectPineScript, removePineScript };
```

- [x] **Step 4: Run test to verify it passes**

Run: `npx jest plugins/tradingview/node/tests/pine.test.js`
Expected: PASS

- [x] **Step 5: Commit**

### Task 2: Node CLI Data Window Extraction

**Files:**
- Modify: `plugins/tradingview/node/tests/pine.test.js`
- Modify: `plugins/tradingview/node/core/pine.js`

- [ ] **Step 1: Write the failing test**

```javascript
// plugins/tradingview/node/tests/pine.test.js
const { readIndicatorValues } = require('../core/pine');

describe('Data Window Extraction', () => {
    it('reads indicator values from Data Window', async () => {
        const mockClient = { Runtime: { evaluate: jest.fn().mockResolvedValue({ result: { value: { MACD: 1.25, Signal: 'BUY' } } }) } };
        const result = await readIndicatorValues(mockClient, 'AI_Custom_TA');
        expect(result.success).toBe(true);
        expect(result.data.MACD).toBe(1.25);
    });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npx jest plugins/tradingview/node/tests/pine.test.js`
Expected: FAIL (`readIndicatorValues` is not defined).

- [x] **Step 3: Write minimal implementation**

```javascript
// plugins/tradingview/node/core/pine.js
async function readIndicatorValues(client, indicatorName) {
    try {
        const evalResult = await client.Runtime.evaluate({
            expression: `({ MACD: 1.25, Signal: 'BUY' })`, // Mock scraping logic for now
            returnByValue: true
        });
        return { success: true, data: evalResult.result.value };
    } catch (e) {
        return { success: false, error: e.message };
    }
}
// export readIndicatorValues as well
module.exports = { injectPineScript, removePineScript, readIndicatorValues };
```

- [x] **Step 4: Run test to verify it passes**

Run: `npx jest plugins/tradingview/node/tests/pine.test.js`
Expected: PASS

- [x] **Step 5: Commit**

### Task 3: Python Service Wrapper and CLI Router Integration

**Files:**
- Modify: `plugins/tradingview/node/cli.js`
- Modify: `plugins/tradingview/node/router.js`
- Create: `plugins/tradingview/tests/test_tv_pine_manager.py`
- Create: `plugins/tradingview/scripts/tv_pine_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# plugins/tradingview/tests/test_tv_pine_manager.py
import pytest
import json
from unittest.mock import patch
from plugins.tradingview.scripts.tv_pine_manager import inject_pine, read_pine, remove_pine

def test_inject_pine(tmp_path):
    script_path = tmp_path / "ai_indicator.pine"
    script_path.write_text("plot(close)")
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = json.dumps({"success": True}).encode()
        mock_run.return_value.returncode = 0
        
        result = inject_pine(str(script_path))
        assert result['success'] is True
        mock_run.assert_called_once()
        assert "pine inject" in " ".join(mock_run.call_args[0][0])
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest plugins/tradingview/tests/test_tv_pine_manager.py`
Expected: FAIL (Module `plugins.tradingview.scripts.tv_pine_manager` not found).

- [x] **Step 3: Write minimal implementation**

```python
# plugins/tradingview/scripts/tv_pine_manager.py
import subprocess
import json
import argparse

def run_node_cli(*args):
    cmd = ["node", "plugins/tradingview/node/cli.js", "pine"] + list(args)
    res = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(res.stdout)

def inject_pine(file_path):
    return run_node_cli("inject", "--file", file_path)

def read_pine(indicator_name):
    return run_node_cli("read", "--indicator", indicator_name)

def remove_pine(indicator_name):
    return run_node_cli("remove", "--indicator", indicator_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inject", "read", "remove"])
    parser.add_argument("--file", help="Path to pine script")
    parser.add_argument("--indicator", help="Name of indicator")
    args = parser.parse_args()
    
    if args.action == "inject":
        print(json.dumps(inject_pine(args.file)))
    elif args.action == "read":
        print(json.dumps(read_pine(args.indicator)))
    elif args.action == "remove":
        print(json.dumps(remove_pine(args.indicator)))
```
*(Also wire up `pine inject`, `pine read`, and `pine remove` commands inside `router.js` and `cli.js` to map to `core/pine.js` functions).*

- [x] **Step 4: Run test to verify it passes**

Run: `pytest plugins/tradingview/tests/test_tv_pine_manager.py`
Expected: PASS

- [x] **Step 5: Commit**

### Task 4: Real CDP Implementation and Live Test Harness

**Files:**
- Modify: `plugins/tradingview/tests/tv_test_harness.py`
- Modify: `plugins/tradingview/node/core/pine.js`

- [ ] **Step 1: Write the failing test**

```python
# plugins/tradingview/tests/tv_test_harness.py
# (Add this to the existing test harness file)

def test_live_pine_cycle():
    from plugins.tradingview.scripts.tv_pine_manager import inject_pine, read_pine, remove_pine
    
    # 1. Inject
    with open("/tmp/test_indicator.pine", "w") as f:
        f.write('//@version=5\nindicator("Test_Indicator")\nplot(close)')
    
    res = inject_pine("/tmp/test_indicator.pine")
    assert res.get('success') is True, f"Injection failed: {res}"
    
    # 2. Read
    res_data = read_pine("Test_Indicator")
    assert res_data.get('success') is True, f"Read failed: {res_data}"
    
    # 3. Remove
    res_rm = remove_pine("Test_Indicator")
    assert res_rm.get('success') is True, f"Remove failed: {res_rm}"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest plugins/tradingview/tests/tv_test_harness.py` (ensure TV Desktop is running on port 9222).
Expected: FAIL (because the Node logic currently returns hardcoded mock values instead of actually parsing the real TV DOM).

- [x] **Step 3: Write minimal implementation**

Update `plugins/tradingview/node/core/pine.js` to perform the actual CDP DOM traversal.

**Critical — React fiber traversal for Monaco (from tradesdontlie/tradingview-mcp code review):**
CSS class selectors like `.js-pine-editor-tab` are fragile and change with TV deployments. Use React fiber tree traversal instead:
```javascript
// Find Monaco editor via React fiber — scan for __reactFiber prefix on DOM nodes
const monacoNode = await client.Runtime.evaluate({
    expression: `(function() {
        const nodes = document.querySelectorAll('*');
        for (const node of nodes) {
            const fiberKey = Object.keys(node).find(k => k.startsWith('__reactFiber'));
            if (fiberKey) {
                // Walk fiber to find Monaco editor instance
                let fiber = node[fiberKey];
                // ... traverse to Monaco props
            }
        }
    })()`,
    returnByValue: true
});
```
Confirm actual selectors via CDP Section 0.5 pattern in `tv_test_harness.py` before hardcoding.

- `injectPineScript`: Click Pine Editor tab (confirm selector live), focus Monaco via fiber traversal, send CDP `Input.insertText` with script content, click "Add to chart".
- `readIndicatorValues`: Open Data Window via CDP, evaluate script in context to scrape current values for the given indicator name.
- `removePineScript`: Find indicator in chart legend, click remove icon.

**All Node snippets MUST end with `process.exit(0)` / `process.exit(1)`** — without it the CDP WebSocket holds the event loop open indefinitely and the Python subprocess call never returns. This was the root cause of all Section 0 timeout failures during Phase 1.

**Temp files**: Write to `InvestmentToolkit/temp/` subfolder, not `/tmp/` root (see Task 0003).

- [x] **Step 4: Run test to verify it passes**

Run: `pytest plugins/tradingview/tests/tv_test_harness.py`
Expected: PASS (Successfully injects, reads, and removes from the live TV chart).

- [x] **Step 5: Commit**

### Task 5: AI Agent Skill Scaffold

**Files:**
- Create: `tests/test_pine_advisor_skill.py`
- Create: `.agents/skills/tv_pine_advisor/SKILL.md`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pine_advisor_skill.py
import os

def test_pine_advisor_skill_exists_and_configured():
    skill_path = ".agents/skills/tv_pine_advisor/SKILL.md"
    assert os.path.exists(skill_path)
    
    with open(skill_path, "r") as f:
        content = f.read()
        assert "/pine-analyze" in content
        assert "tv_pine_manager.py" in content
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pine_advisor_skill.py`
Expected: FAIL (File does not exist).

- [x] **Step 3: Write minimal implementation**

Create `.agents/skills/tv_pine_advisor/SKILL.md`:

```markdown
---
name: tv_pine_advisor
plugin: tradingview
description: Run custom TA on {TICKER} using AI-generated Pine Script
---
# tv_pine_advisor

**Trigger:** `/pine-analyze {TICKER}` or "Run custom TA on {TICKER}"

**Workflow:**
1. Generate valid Pine Script (v5) logic suited for the asset class.
2. Save the generated text to a temporary file `/tmp/ai_indicator.pine`.
3. Execute: `python3 plugins/tradingview/scripts/tv_pine_manager.py inject --file /tmp/ai_indicator.pine`
4. Execute: `python3 plugins/tradingview/scripts/tv_pine_manager.py read --indicator "AI_Custom_TA"`
5. Execute: `python3 plugins/tradingview/scripts/tv_pine_manager.py remove --indicator "AI_Custom_TA"`
6. Evaluate the extracted JSON signals against the portfolio thesis and output an actionable advisory rating (Initiate/Accumulate/Trim/Exit).
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pine_advisor_skill.py`
Expected: PASS

- [x] **Step 5: Commit**
```
