---
description: Perform AI-driven stock valuation (Bear/Base/Bull) and persist the result as an AI_AGENT projection to the backend store. The executing agent is the analyst — it fetches data, performs cognitive analysis, and saves via the HTTP API.
trigger: /perform-stock-valuation
args:
  - name: ticker
    required: true
    description: Stock ticker symbol (e.g., NVDA, AAPL, MSFT, BRK-B, SHOP.TO)
  - name: model
    required: false
    default: self
    description: "self" = executing agent performs analysis. Alternatively specify a model name for API delegation.
---

# Perform Stock Valuation

## What This Produces
A complete `Projection` object with `source: "AI_AGENT"`, structurally identical to user saves from the web app. Saved to `backend/data/projections/{TICKER}.json` and visible in the Valuation Modeler's AI view.

## Prerequisites

Verify before executing — STOP and report if any check fails.

```bash
# Backend running
curl -sf http://localhost:3001/health || echo "FAIL: Start backend with: python3 tools/manage_servers.py"

# Python + yfinance
python3 -c "import yfinance; print('OK')" || echo "FAIL: pip install yfinance"

# Skill file exists
test -f .agent/skills/stock_valuation/SKILL.md || echo "FAIL: Skill file missing"
```

## Execution

When triggered with `/perform-stock-valuation {TICKER}`:

1. **Read Skill** — Load `.agent/skills/stock_valuation/SKILL.md` for the full schema, constraints table, and analysis prompt template.

2. **Fetch Data** — Execute the skill's Step 1 using the canonical backend script:
   ```bash
   python3 tools/investment-screener/backend/scripts/fetch_financials.py --ticker {TICKER}
   ```
   If this fails (invalid ticker, Yahoo down), STOP and report. Do not proceed with missing data.

3. **Build Snapshot** — Execute the skill's Step 2. Extract `price`, `currency`, `shares`, `revenue`, `fiscalPeriod`, and analyst estimates from the raw data into the snapshot object.

4. **Analyze** — Execute the skill's Step 3. YOU are the analyst. Using the raw financial data and the prompt template in `references/analysis_prompt.md` (or the inline framework in the skill), produce Bear/Base/Bull scenarios with specific justifications grounded in the data.

5. **Validate & Repair** — Execute the skill's Step 3b. Before assembling the final object, self-check:
   - Weights sum to 1.0 (rescale if not)
   - All values within Zod constraint bounds (clamp if not)
   - Bear ≤ Base ≤ Bull ordering on growth and PE
   - Rationales cite actual numbers from the financial data

6. **Assemble & Persist** — Execute the skill's Steps 4–5. Build the full `Projection` JSON per the skill's exact schema template, then POST to `http://localhost:3001/api/projections`.

7. **Verify & Report** — Execute the skill's Step 6. Confirm the projection appears in the API response, then report to the user:

   | | Bear | Base | Bull |
   |---|---|---|---|
   | **Weight** | {w} | {w} | {w} |
   | **Growth** | {g}% | {g}% | {g}% |
   | **Exit PE** | {pe}x | {pe}x | {pe}x |

   **Fair Value:** ${fv} ({upside/downside}% from ${current_price})
   **Action:** BUY / HOLD / SELL
   **Thesis:** {1–2 sentence summary}

## Error Handling

| Error | Action |
|-------|--------|
| Data fetch fails | STOP. Report error to user. Do not hallucinate data. |
| HTTP 400 (validation) | Read error message, fix payload per skill's constraints table, retry once. |
| HTTP 409 (conflict) | GET `/api/projections/{TICKER}`, find existing AI_AGENT entry, use its `version + 1`, retry. |
| HTTP 500 (server error) | Report to user. Suggest restarting backend. |
| Backend not running | Tell user: `python3 tools/manage_servers.py` |
| Weights don't sum to 1.0 | Proportionally rescale before POST. |

## Files

| | Path | Access |
|---|---|---|
| Skill definition | `.agent/skills/stock_valuation/SKILL.md` | Read |
| Analysis prompt | `.agent/skills/stock_valuation/references/analysis_prompt.md` | Read |
| Data fetch script | `tools/investment-screener/backend/scripts/fetch_financials.py` | Execute |
| Projection store | `backend/data/projections/{TICKER}.json` | Write (via HTTP API only) |
