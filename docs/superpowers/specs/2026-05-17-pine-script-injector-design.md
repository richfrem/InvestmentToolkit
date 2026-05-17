# Pine Script v6 CDP Injector Design

## 1. Overview
The goal is to extend the existing `tradingview` plugin with a new skill (`pine-inject`) capable of generating Pine Script v6 code and seamlessly injecting it into the TradingView Desktop application via Chrome DevTools Protocol (CDP).

*Note: This skill focuses strictly on code generation and injection (Task #0004). It acts as a foundational capability for the future "Technical Analysis Expert" sub-agent (Task #0005), which will use this injector to load custom scripts, read the resulting data from the TradingView Data Window, and then clear the chart.*

## 2. Architecture & Components

### 2.1 Agent Skill (`pine-inject`)
- **Location:** `plugins/tradingview/skills/pine-inject/SKILL.md`
- **Trigger:** `/pine-inject {description}`
- **Responsibility:**
  - Formulate a strict prompt enforcing Pine Script v6 rules.
  - Generate the indicator or strategy logic.
  - Call the underlying Node.js CDP script.
  - Handle the error-correction loop if the CDP script reports a compilation error.

### 2.2 CDP Execution Script (`pine_injector.js`)
- **Location:** `plugins/tradingview/node/pine_injector.js`
- **Responsibility:**
  - Connect to TradingView Desktop via CDP (port 9222).
  - Open the Pine Editor panel.
  - Use React fiber traversal (`__reactFiber`) to locate the Monaco editor instance (bypassing brittle CSS selectors).
  - Clear existing code and inject the generated Pine Script code.
  - Click the "Add to chart" button.
  - Wait for compilation. If an error dialog or console error appears, extract the error message and exit with a non-zero code.
  - Ensure the Node process exits gracefully on completion (`process.exit(0)`).

## 3. Data Flow & Error Handling
1. **User Request:** `Agent` -> "Generate a moving average crossover strategy"
2. **Generation:** `Skill` -> Produces Pine Script v6 string.
3. **Execution:** `Skill` -> Executes `node plugins/tradingview/node/pine_injector.js --script "..."`
4. **Success Path:** Script injected, added to chart, Node exits `0`.
5. **Error Path:** TradingView compiler rejects the script. Node extracts the error text (e.g., "Undeclared identifier 'foo' at line 4"), prints it as JSON, and exits `1`.
6. **Self-Correction:** `Skill` parses the error, prompts the LLM with the error and the faulty code, generates a fix, and loops back to Step 3.

## 4. Testing Strategy
- Create a test harness in `plugins/tradingview/tests/tv_test_pine_injector.py`.
- The test will verify that a valid script is successfully added to the chart.
- The test will also verify that an intentionally invalid script correctly returns a parseable error message to the Python caller.