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
    python3 tools/investment-screener/backend/scripts/fetch_financials.py --ticker {TICKER} --output /tmp/{TICKER}_raw.json
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
7.  **Persist**: (Skill Step 6). POST the valid JSON to the backend.
    ```bash
    curl -X POST http://localhost:3001/api/projections \
      -H "Content-Type: application/json" \
      -d @/tmp/{TICKER}_projection.json
    ```
    *   **409 Conflict**: Fetch latest version (`GET /api/projections/{TICKER}`), increment version, and retry.
    *   **400 Bad Request**: Read error, fix payload, retry ONCE.

### Phase 6: Reporting
8.  **Report Findings**: Summarize the analysis to the user in this format:

| Scenario | Weight | Growth | Exit PE |
| :--- | :--- | :--- | :--- |
| **Bear** | {w} | {g}% | {pe}x |
| **Base** | {w} | {g}% | {pe}x |
| **Bull** | {w} | {g}% | {pe}x |

*   **Fair Value**: ${fv} ({upside/downside}%)
*   **Action**: **{BUY/HOLD/SELL}**
*   **Thesis**: {1-2 sentence summary}

## Error Handling Matrix

| Error Condition | Action |
| :--- | :--- |
| **Data Fetch Fail** | **STOP**. Report error. |
| **Validation (400)** | Log error, fix payload constraints, retry once. |
| **Conflict (409)** | Get latest version from API, increment `version`, retry. |
| **Server Error (500)** | Report to user: "Backend service error". |
| **Backend Offline** | User instruction: "Run `python3 tools/manage_servers.py`" |

## Reference Files

| Artifact | Path | Access |
| :--- | :--- | :--- |
| **Skill Definition** | `.agent/skills/stock_valuation/SKILL.md` | Read |
| **Analysis Prompt** | `.agent/skills/stock_valuation/references/analysis_prompt.md` | Read |
| **Fetch Script** | `tools/investment-screener/backend/scripts/fetch_financials.py` | Execute |
| **API Endpoint** | `http://localhost:3001/api/projections` | POST |
