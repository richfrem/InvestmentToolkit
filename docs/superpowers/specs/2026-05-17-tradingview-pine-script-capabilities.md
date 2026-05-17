# Design Spec: TradingView Pine Script Capabilities

## 1. Context and Problem Statement
Task 0002 requires empowering the AI agent to autonomously generate, inject, and analyze custom Pine Script indicators within TradingView. Currently, the `tradingview` plugin supports health checks, quotes, alerts, screenshots, and basic order management via CDP (Chrome DevTools Protocol) automation. However, it lacks the ability to programmatically interact with the Pine Editor, add generated scripts to the chart, and extract the resulting technical analysis signals (e.g., MACD crosses, RSI levels) to inform portfolio actions (initiate, accumulate, trim, exit).

The goal is to build a robust, TDD-compliant pipeline that allows the agent to:
1. Generate valid Pine Script (v5).
2. Inject and apply the script to the active TradingView chart.
3. Read the calculated indicator values back from the UI.
4. Synthesize these signals into actionable portfolio advice.

## 2. Proposed Approaches

### Approach A: Full CDP DOM Automation (Recommended)
**Mechanism:** Use CDP to interact directly with the Pine Editor DOM elements. The script clicks the "Pine Editor" tab, clears the editor, pastes the AI-generated script, clicks "Add to chart", and then reads the resulting values from the "Data Window" or indicator legend on the chart.
**Trade-offs:** 
- *Pros:* Fully headless-capable, reliable DOM selectors, integrates perfectly with our existing `tv_client.py` and Node CLI architecture.
- *Cons:* Susceptible to TradingView DOM structure changes.

### Approach B: OS-Level Keyboard/Mouse Automation (PyAutoGUI/RobotJS)
**Mechanism:** Use OS-level macros to send keyboard shortcuts (e.g., `Ctrl+E` or `Cmd+E` to open Pine Editor, `Ctrl+A`, `Ctrl+V` to paste, `Tab` navigation).
**Trade-offs:** 
- *Pros:* Immune to deep DOM obfuscation.
- *Cons:* Extremely brittle. Requires TradingView to have OS focus. Fails if screen resolution changes or toolbars are collapsed. Not suitable for background execution.

### Approach C: Chrome Extension Bridge
**Mechanism:** Build a custom Chrome extension injected via CDP that exposes a global `window.TradingViewBridge` object, bridging Pine Script injection directly into TradingView's internal JS state.
**Trade-offs:** 
- *Pros:* Cleanest data extraction if internal APIs are successfully hooked.
- *Cons:* High reverse-engineering overhead. Violates the principle of minimal intervention. Highly likely to break upon TV platform updates.

**Decision:** **Approach A** is selected. It aligns with our existing CDP infrastructure, is robust enough for background execution, and leverages the reliable Data Window for value extraction.

## 3. Architecture and Component Design

The solution will be implemented as an extension to the existing `tradingview` plugin, adding new CLI commands and Python wrappers.

### 3.1. Node CLI Extensions (`plugins/tradingview/node/cli.js`)
We will add a new command namespace `pine` to the router:
- `pine inject --file <path>`: Reads a Pine Script from a file, opens the Pine Editor via CDP, clears it, pastes the code, and clicks "Add to chart".
- `pine read --indicator <name>`: Opens the Data Window via CDP, scrapes the DOM for the specified indicator's current values, and returns JSON.
- `pine remove --indicator <name>`: Cleans up the chart by removing the injected indicator to prevent chart pollution over multiple runs.

### 3.2. Python Service Wrappers (`plugins/tradingview/scripts/`)
- `tv_pine_manager.py`: Python wrapper around the Node CLI `pine` commands. Handles the temporary file creation for script injection and parses the JSON output.

### 3.3. AI Agent Skill (`.agents/skills/tv_pine_advisor/SKILL.md`)
A new AI skill will be scaffolded. 
**Trigger:** `/pine-analyze {TICKER}` or "Run custom TA on {TICKER}"
**Workflow:**
1. LLM generates a custom Pine Script based on the asset class and current market conditions.
2. Agent calls `tv_pine_manager.py inject`.
3. Agent calls `tv_pine_manager.py read`.
4. Agent calls `tv_pine_manager.py remove`.
5. Agent evaluates the extracted signals against the portfolio thesis and outputs an action (Initiate/Accumulate/Trim/Exit).

## 4. Data Flow

1. **Generation:** AI Agent generates Pine Script text and writes it to a temporary file `/tmp/ai_indicator.pine`.
2. **Injection:** Agent executes `python3 tv_pine_manager.py inject /tmp/ai_indicator.pine`.
3. **CDP Execution:** Node CLI finds the `.js-pine-editor-tab` button, clicks it, focuses the Monaco editor canvas, sends CDP `Input.insertText` to inject the code, and clicks the "Add to chart" button.
4. **Signal Extraction:** Agent executes `python3 tv_pine_manager.py read "AI_Custom_TA"`. Node CLI ensures the Data Window is open, parses the key-value pairs for the indicator, and returns JSON: `{"MACD": 1.25, "Signal": "BUY"}`.
5. **Synthesis:** Agent parses the JSON, formulates the portfolio advisory response, and completes the workflow.

## 5. Testing Strategy (TDD Iron Law)

Following the project's strict TDD mandate, no production code will be written before failing tests are established.

### 5.1. Test Harness Preparation
We will utilize `plugins/tradingview/tests/tv_test_harness.py` (and corresponding Jest tests for the Node CLI). Tests will be executed against a local TradingView instance running with `--remote-debugging-port=9222`.

### 5.2. Test Cases (RED -> GREEN -> REFACTOR)

**Test 1: Node CLI `pine inject` fails gracefully if Pine Editor is missing**
- *RED:* Write a test asserting that `pine inject` returns exit code 1 with a specific error message if the Pine Editor DOM node cannot be found.
- *GREEN:* Implement the CDP selector check and error handling.

**Test 2: Node CLI successfully injects code and adds to chart**
- *RED:* Write a test that injects a basic `plot(close)` script and verifies the success response.
- *GREEN:* Implement the Monaco editor CDP interaction (focus, clear, `Input.insertText`, click "Add to chart").

**Test 3: Node CLI reads indicator values from Data Window**
- *RED:* Write a test that calls `pine read` and expects a JSON object containing the injected indicator's values.
- *GREEN:* Implement Data Window CDP scraping logic.

**Test 4: Python Wrapper Integration**
- *RED:* Write `tests/test_tv_pine_manager.py` to ensure the Python wrapper correctly parses the Node CLI JSON output and handles temporary file cleanup.
- *GREEN:* Implement `tv_pine_manager.py`.

## 6. Next Steps
1. The user will review this spec.
2. Upon approval, invoke the `writing-plans` skill to generate a detailed implementation plan.
3. Begin execution strictly adhering to the Red-Green-Refactor loop.
