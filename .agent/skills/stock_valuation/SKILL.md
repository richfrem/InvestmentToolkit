---
name: stock_valuation
description: Perform autonomous stock valuation. Produces a Projection object saved to backend/data/projections/{TICKER}.json.
has_tools: true
---

# Stock Valuation Skill

## Quick Reference
- **Trigger**: `/perform-stock-valuation {TICKER}`
- **Output**: A valid Projection object (source: AI_AGENT)
- **Output Schema**: See references/projection_schema.json
- **Example**: See references/example_NVDA.json
- **Persistence**: CLI script `persist_projection.py` (direct file IO)

## Step 1: Fetch Financial Data
Execute the backend script to fetch raw financial data from Yahoo Finance.

```bash
# Script takes TICKER as a positional arg and outputs JSON to stdout
python3 tools/investment-screener/backend/py_services/fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json
```
**Expected Output**: A JSON object containing `metrics`, `financials`, `estimates`, and `profile`.
**Action**: If this fails, STOP and report the error to the user.

## Step 2: Build Snapshot Object
Read `/tmp/{TICKER}_raw.json` and extract the following fields to build the `snapshot` object:

```json
{
  "price": <metrics.price>,
  "currency": <metrics.currency>,
  "shares": <metrics.shares_outstanding>,
  "revenue": <metrics.revenue>,
  "lastActualPS": <price * shares / revenue>,
  "fiscalPeriod": "TTM",
  "analystGrowthEstimate": <estimates.revenue_growth (next year) or null>,
  "analystMarginEstimate": <estimates.profit_margin or null>
}
```

## Step 3: Cognitive Analysis — Generate Scenarios
You are the expert analyst. Using the raw data, generate Bear, Base, and Bull scenarios.

### ⚠️ Constraints & Validation Rules
1.  **Weights**: `bear.weight + base.weight + bull.weight` MUST equal **1.0** (± 0.01).
2.  **Growth**: `bear.growthRate` < `base.growthRate` < `bull.growthRate`.
3.  **Margins**: `netMargin` should be realistic (-100% to 100%).
4.  **Limits**:
    *   **Growth > 50%**: For large caps (> $50B revenue), growth > 50% requires explicit justification citing specific catalysts.
    *   `shareChange` limits: -5.0 (buyback) to +5.0 (dilution).

### Analysis Prompt
Use the instructions in `references/analysis_prompt.md` to guide your reasoning.

## Step 4: Validate & Repair
Before saving, YOU must validate your own generated JSON:
1.  **Weights**: If sum ≠ 1.0, normalize them.
2.  **Types**: Ensure all numeric fields are actual numbers, not strings (e.g., `15.5`, not `"15.5%"`).
3.  **Ranges**: Clamp any values outside the schema limits (e.g., max P/E 1000).

## Step 5: Assemble Projection Object
Construct the final JSON payload using this structure:

```json
{
  "ticker": "{TICKER}",
  "id": "<generate a UUID>",
  "source": "AI_AGENT",
  "schemaVersion": "1.1",
  "version": 1,
  "savedAt": "<current ISO timestamp>",
  "updatedAt": "<current ISO timestamp>",
  "name": "AI Deep Dive — {TICKER} — <date>",
  "rationale": "<Your 3-5 sentence thesis>",
  "snapshot": { ... from Step 2 ... },
  "dataPreferences": { "growthBasis": "next", "marginBasis": "ttm" },
  "scenarios": {
    "bear": { ... },
    "base": { ... },
    "bull": { ... }
  },
  "aiThesis": {
    "model": "<your human-readable model name>",
    "rationale": "<Full markdown analysis>",
    "fairValue": <calculated weighted value>,
    "action": "BUY/HOLD/SELL",
    "analyzedAt": "<current ISO timestamp>"
  },
  "globalSettings": { "discountRate": 10.0, "timeHorizon": 5 }
}
```

**IMPORTANT - Model Name Format:**
Use human-readable model names in `aiThesis.model` for clear identification in the UI:
- ✅ `"Claude Sonnet 4.5"` (not `"claude-sonnet-4.5"`)
- ✅ `"Gemini 3 Flash Preview"` (not `"gemini-3-flash-preview"`)
- ✅ `"Gemini 2.0 Flash"` (not `"gemini-2.0-flash-exp"`)
- ✅ `"GPT-4.5 Turbo"` (not `"gpt-4.5-turbo"`)

This ensures the My Projections modal displays: "AI Analysis (Claude Sonnet 4.5)" instead of "AI Analysis (claude-sonnet-4.5)".

## Step 6: Persist Findings

Choose one of the following methods to save your projection.

### Option A: CLI (Fast Path) — Recommended
Directly writes to the backend data store. Does not require the API server to be running.

```bash
# Write payload to temp file first
cat > /tmp/{TICKER}_projection.json << 'EOF'
<JSON_PAYLOAD>
EOF

# Pipe to persistence script
# Use --replace to overwrite existing entry for this model
cat /tmp/{TICKER}_projection.json | python3 tools/investment-screener/backend/py_services/persist_projection.py
```

### Option B: Web API (Slow Path)
Requires the backend server to be running on localhost:3000.

```bash
curl -X POST http://localhost:3000/api/projections \
  -H "Content-Type: application/json" \
  -d @/tmp/{TICKER}_projection.json
```

**Handling Responses**:
*   **Success**: Script/API returns success message or 200 OK.
*   **Error**: Script/API logs validation errors. Fix payload and retry.

## Step 7: Report Findings
Summarize your analysis to the user:
*   Fair Value vs Current Price.
*   The "Action" (Buy/Sell/Hold).
*   Key driver of your thesis.
