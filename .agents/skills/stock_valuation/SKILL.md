---
name: stock_valuation
description: >
  Perform autonomous stock valuation. Produces a Projection object saved to
  backend/data/projections/{TICKER}.json AND a deep-dive research report saved
  to backend/data/research/{TICKER}_{DATE}.md. Summarizes findings
  conversationally and supports interactive Q&A. Trigger when user asks to
  value, analyse, or price a stock, or uses /evaluate-stock or
  /perform-stock-valuation.
has_tools: true
allowed-tools: Bash, Read, Write
---

# Stock Valuation Skill

## Quick Reference
- **Trigger**: `/perform-stock-valuation {TICKER}` or `/evaluate-stock {TICKER}`
- **Output (JSON)**: `backend/data/projections/{TICKER}.json`
- **Output (Research)**: `backend/data/research/{TICKER}_{YYYY-MM-DD}.md`
- **Schema**: `references/example_NVDA.json`
- **Benchmarks**: `references/valuation-benchmarks.md` ← Load for P/E + margin anchoring
- **Fallbacks**: `references/fallback-tree.md` ← Load on ANY step failure
- **API Docs**: `references/api_reference.md`

## ⚠️ Adversarial Objectivity Constraint
> **L4 Pattern**: Adversarial Objectivity Constraint — anti-sycophancy enforcement.

You are an **independent analyst**, not a stock promoter. Before generating scenarios:
- ❌ NEVER anchor fair value to current market price. Derive independently from fundamentals, then compare.
- ❌ NEVER set all three scenarios as minor variations of each other. Bear must reference a historical trough or named risk. Bull MUST name ≥1 specific catalyst.
- ❌ NEVER assign `qualityMultiplier > 1.1` without citing a specific structural moat from the company profile.
- ✅ If fair value < current price, output SELL or HOLD regardless of user sentiment about the stock.
- ✅ `exitPE` MUST be benchmarked against sector median from `references/valuation-benchmarks.md`.

## Dual-Mode Operation
See `CONNECTORS.md` for full degradation contract.

| Mode | Condition | Action |
|------|-----------|--------|
| **Full** | `~~financial-data-fetcher` + `~~projection-store` available | Full pipeline below |
| **Standalone** | Backend down or data unavailable | Announce degraded mode → request raw JSON paste → complete analysis → write to `/tmp/` → skip persistence |

If health check fails → immediately invoke **FB-02** from `references/fallback-tree.md`.

---

## Step 1: Fetch Financial Data
```bash
# Health check first
curl -sf http://localhost:3001/health || echo "DEGRADED — invoke FB-02"

# Fetch data
python3 investment_screener/backend/py_services/fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json
```
**If fetch fails** → invoke **FB-01** from `references/fallback-tree.md`. Do NOT hallucinate data.

## Step 2: Build Snapshot Object
Read `/tmp/{TICKER}_raw.json` and extract:
```json
{
  "price": <metrics.price>,
  "currency": <metrics.currency>,
  "shares": <metrics.shares_outstanding>,
  "revenue": <metrics.revenue>,
  "lastActualPS": <price * shares / revenue>,
  "fiscalPeriod": "TTM",
  "analystGrowthEstimate": <estimates.revenue_growth or null>,
  "analystMarginEstimate": <estimates.profit_margin or null>
}
```

## Step 3: Cognitive Analysis — Generate Scenarios
Use `references/analysis_prompt.md` for full methodology. Key constraints:

1. **Weights**: `bear.weight + base.weight + bull.weight` MUST equal **1.0** (±0.01)
2. **Growth ordering**: `bear.growthRate < base.growthRate < bull.growthRate`
3. **Price ordering**: `bear.scenarioPrice < base.scenarioPrice < bull.scenarioPrice`
4. **Margins**: Realistic (-100% to 100%); see sector benchmarks in `references/valuation-benchmarks.md`
5. **Large caps** (>$50B revenue): growth >30% requires named catalyst citation
6. **`shareChange`**: -5.0 to +5.0; **Scores**: integers 0–5
7. **Base anchoring**: `base.growthRate` must be within ±3pp of analyst consensus growth

## Step 4: Validate & Repair
```bash
# Run pre-persistence validator
cat /tmp/{TICKER}_projection.json | python3 plugins/stock-valuation/skills/stock_valuation/scripts/validate_projection.py --verbose
# Exit 0 = valid | Exit 1 = errors to fix
```
Fix all reported errors before proceeding. If math inconsistency detected → invoke **FB-05** from `references/fallback-tree.md`.

Normalize weights if sum ≠ 1.0. Cast string numbers to actual numbers. Clamp out-of-range values.

## Step 5: Assemble Projection Object
```json
{
  "ticker": "{TICKER}",
  "id": "<UUID>",
  "source": "AI_AGENT",
  "schemaVersion": "1.1",
  "version": 1,
  "savedAt": "<ISO timestamp>",
  "updatedAt": "<ISO timestamp>",
  "name": "AI Deep Dive — {TICKER} — <date>",
  "rationale": "<3-5 sentence thesis>",
  "snapshot": { "...from Step 2..." },
  "dataPreferences": { "growthBasis": "next", "marginBasis": "ttm" },
  "scenarios": { "bear": {...}, "base": {...}, "bull": {...} },
  "aiThesis": {
    "model": "<human-readable model name e.g. 'Gemini 2.0 Flash'>",
    "rationale": "<full markdown analysis>",
    "fairValue": <weighted value>,
    "action": "BUY/HOLD/SELL",
    "analyzedAt": "<ISO timestamp>",
    "researchReport": "{TICKER}_{YYYY-MM-DD}.md"
  },
  "globalSettings": { "discountRate": 10.0, "timeHorizon": 5 }
}
```
> **Model name**: Use human-readable names (`"Gemini 2.0 Flash"` not `"gemini-2.0-flash-exp"`).

## Step 6: Persist Projection JSON
```bash
cat > /tmp/{TICKER}_projection.json << 'EOF'
<JSON_PAYLOAD>
EOF

cat /tmp/{TICKER}_projection.json | python3 investment_screener/backend/py_services/persist_projection.py
```
If persistence fails → invoke **FB-03** from `references/fallback-tree.md`.

## Step 7: Generate Deep-Dive Research Report
**Iteration Directory Isolation**: Write to dated path to prevent overwrites.
```bash
mkdir -p investment_screener/backend/data/research
cat > investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md << 'REPORT_EOF'
<MARKDOWN_CONTENT>
REPORT_EOF
```
If write fails → invoke **FB-04** from `references/fallback-tree.md`.

**Report must include** (template in full at `references/analysis_prompt.md`):
- TL;DR (2-3 sentences, verdict + why)
- Company Snapshot table
- Investment Thesis (3-5 paragraphs, data-grounded)
- Scenario Analysis (Bear / Base / Bull — narrative paragraphs + assumption tables)
- Valuation Math (show arithmetic transparently)
- Key Risks, What to Watch, Comparables
- Data Quality & Confidence Score
- Discussion Log (initially empty, appended during Q&A)

## Step 8: Conversational Summary in Chat
```
**{TICKER}: {ACTION} — Fair value ${fair_value} vs ${price} ({+/-X%})**

{2-3 sentences: plain-English thesis. No jargon.}

**Scenarios:**
🐻 Bear ({weight}%): ${price} — {one sentence why}
⚖️  Base ({weight}%): ${price} — {one sentence why}
🚀 Bull ({weight}%): ${price} — {one sentence, name the catalyst}

**Biggest risk**: {Single most important risk.}
**Confidence**: {X}/1.0

I've saved the projection and a full deep-dive research report.
Want me to stress-test an assumption, adjust the model, or dig deeper?
```
> ⚠️ Be conversational. Do NOT just output a table.

## Step 9: Interactive Q&A Loop
Remain in analyst mode. Handle:
- **Assumption Challenges**: Recalculate, show fair value delta, offer to save revised version
- **Sensitivity Probes**: Recalculate all scenario PVs at new rate
- **Deep Dives**: Discuss qualitatively, connect back to model parameters
- **Cross-Stock Comparisons**: Load both projections from `data/projections/`
- **Scenario What-Ifs**: Model with adjusted parameters, show impact on weighted fair value

**Persisting Q&A Changes**: If material changes → bump `version` + `updatedAt` → re-persist → append to Discussion Log section of research report.

---

## Error Handling
| Condition | Action |
|:---|:---|
| Data Fetch Fail | **STOP** → FB-01 |
| Backend Down | Standalone mode → FB-02 |
| Validation (400) | Fix payload → retry once → FB-03 |
| Conflict (409) | Increment `version` → retry once |
| Research dir missing | `mkdir -p` → retry → FB-04 |
| Math inconsistency | Recompute from scratch → FB-05 |

---

## Sources Checked Declaration
> **L4 Pattern**: Source Transparency Declaration. Every completed run MUST end with:

```
## Sources Checked
- Financial data: [✅ fetch_financials.py / ⚠️ Manual input / ❌ Unavailable]
- Projection persistence: [✅ Saved / ⚠️ Skipped (standalone) / ❌ Failed]
- Research report: [✅ Saved to {path} / ❌ Failed]
- Valuation benchmarks: [✅ references/valuation-benchmarks.md]
- Analysis prompt: [✅ references/analysis_prompt.md]

## Sources Unavailable
- [any that failed or were skipped and why]
```
