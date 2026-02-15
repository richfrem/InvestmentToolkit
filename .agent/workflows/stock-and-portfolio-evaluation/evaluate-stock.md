---
description: "Perform AI-driven stock valuation (Bear-Base-Bull) and persist result as AI_AGENT projection. Executing agent operates as autonomous analyst."
trigger: /evaluate-stock
args:
  - name: ticker
    required: true
    description: "Stock ticker symbol (e.g. NVDA, AAPL)"
  - name: model
    required: false
    default: "self"
    description: "Agent acting as analyst (default: self)"
---

# Evaluate Stock

## Execution Workflow

When triggered with `/perform-stock-valuation {TICKER}`:

### Phase 1: Preparation
1.  **Read Skill Instructions**: Load `.agent/skills/stock_valuation/SKILL.md` to understand the schema, constraints, and analysis framework.
2.  **Verify Backend**: Ensure the backend is reachable.
    ```bash
    curl -sf http://localhost:3001/health || echo "FAIL: Start backend with: python3 tools/manage_servers.py"
    ```

### Phase 2: Data Acquisition
3.  **Fetch Financial Data**: Execute the backend script to get raw data (Skill Step 1).
    ```bash
    # Script takes TICKER as a positional arg and outputs JSON to stdout
    python3 tools/investment-screener/backend/py_services/fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json
    ```
    *   **IF FAIL**: Stop and report error. Do not hallucinate data.

### Phase 3: Cognitive Analysis
4.  **Python Environment**: `yfinance` installed in current environment.
5.  **Build Snapshot**: Extract `price`, `currency`, `shares`, `revenue`, `fiscalPeriod` (Skill Step 2).
6.  **Analyze & Value**: (Skill Step 3). You are the expert analyst. Using `references/analysis_prompt.md`, generate Bear/Base/Bull scenarios.
    *   *Constraint Check*: Ensure `bear.growth < base.growth < bull.growth`.
    *   *Sanity Check*: Verify no >50% growth for mega-caps.

### Phase 4: Validation & Repair
7.  **Self-Correction**: (Skill Step 3b). Before saving, validate your JSON:
    *   [ ] Weights sum to exactly **1.0** (±0.01). Rescale if needed.
    *   [ ] All numeric fields are `number` type (not strings).
    *   [ ] Values are within Zod schema bounds (e.g., max P/E 1000).

### Phase 5: Persistence
8.  **Persist**: (Skill Step 6). POST the valid JSON to the backend.
8.  **Persist**: (Skill Step 6). Persist the valid JSON to the backend using the CLI script.
    ```bash
    cat /tmp/{TICKER}_projection.json | python3 tools/investment-screener/backend/py_services/persist_projection.py
    ```
    *   **Success**: Script outputs "Success" or "Updated existing...".
    *   **Error**: Script logs error to stderr and exits with non-zero code. Fix payload and retry ONCE.

### Phase 6: Reporting
9.  **Report Findings**: Summarize the analysis to the user in this format:

| Scenario | Weight | Growth | Net Margin | Exit PE | Fair Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bear** | {w} | {g}% | {m}% | {pe}x | ${sv} |
| **Base** | {w} | {g}% | {m}% | {pe}x | ${sv} |
| **Bull** | {w} | {g}% | {m}% | {pe}x | ${sv} |

*   **Current Price**: ${price}
*   **Fair Value**: ${fv} ({upside/downside}%)
*   **Action**: **{BUY/HOLD/SELL}**
*   **Model**: {your model name, e.g. "Claude Opus 4.6"}
*   **Thesis**: {1-2 sentence summary}

## Error Handling Matrix

| Error Condition | Action |
| :--- | :--- |
| **Data Fetch Fail** | **STOP**. Report error. |
| **Validation (400)** | Log error, fix payload constraints, retry once. |
| **Conflict (409)** | Get latest version from API, increment `version`, retry. |
| **Server Error** | Check logs. If transient, retry. |
| **Backend Offline** | Not an issue for persistence (CLI uses direct file IO). Fetching data still requires internet. |

## Reference Files

| Artifact | Path | Access |
| :--- | :--- | :--- |
| **Skill Definition** | `.agent/skills/stock_valuation/SKILL.md` | Read |
| **Analysis Prompt** | `.agent/skills/stock_valuation/references/analysis_prompt.md` | Read |
| **Fetch Script** | `tools/investment-screener/backend/py_services/fetch_financials.py` | Execute |
| **API Endpoint** | `http://localhost:3001/api/projections` | POST |
