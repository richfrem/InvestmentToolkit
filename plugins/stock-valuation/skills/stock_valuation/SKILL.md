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
- **Schema + Examples**: `references/examples/` ← Real validated projections (schemaVersion 1.2):
  - `example_GOOG_2026-05-02.json` — large-cap Internet/Platform, trending margins, multi-class shares
  - `example_NVDA_2026-05-02.json` — hypergrowth semiconductor, 73% near-term consensus, CAGR derivation
  - `example_PANW_2026-05-02.json` — SaaS/cybersecurity, volatile GAAP margins, one-time item handling, SELL result
  - `example_NVDA_placeholder.json` — **⚠️ DO NOT use as reference** (legacy placeholder, missing fields)
- **Benchmarks**: `references/valuation-benchmarks.md` ← Load for P/E + margin anchoring
- **Fallbacks**: `references/fallback-tree.md` ← Load on ANY step failure
- **API Docs**: `references/api_reference.md`

## ⚠️ Adversarial Objectivity Constraint
> **L4 Pattern**: Adversarial Objectivity Constraint — anti-sycophancy enforcement.

You are an **independent analyst**, not a stock promoter. Before generating scenarios:
- ❌ NEVER anchor fair value to current market price. Derive independently from fundamentals, then compare.
- ❌ NEVER set all three scenarios as minor variations of each other. Bear must reference a historical trough or named risk. Bull MUST name ≥1 specific catalyst.
- ❌ NEVER assign `qualityMultiplier > 1.1` without citing a specific structural moat from the company profile.
- ❌ NEVER inherit prior model's assumptions without independent re-derivation from fresh data. Prior analysis is **context only** — not a starting point to copy from.
- ❌ If the prior model was GPT-5 mini, Gemini, or any flagged non-Sonnet model, treat ALL its assumptions as unvalidated. Re-derive everything from scratch.
- ✅ If fair value < current price, output SELL or HOLD regardless of user sentiment about the stock.
- ✅ `exitPE` MUST be benchmarked against sector median from `references/valuation-benchmarks.md`.
- ✅ If prior thesis said BUY and price has since surged significantly, the new analysis MUST independently re-evaluate whether thesis still holds — do not carry forward the prior bullish stance.

## Dual-Mode Operation
See `CONNECTORS.md` for full degradation contract.

| Mode | Condition | Action |
|------|-----------|--------|
| **Full** | `~~financial-data-fetcher` + `~~projection-store` available | Full pipeline below |
| **Standalone** | Backend down or data unavailable | Announce degraded mode → request raw JSON paste → complete analysis → write to `/tmp/` → skip persistence |

If health check fails → immediately invoke **FB-02** from `references/fallback-tree.md`.

---

## Step 0: Freshness Check (Skip Analysis If Recent)
```bash
# Check for existing AI projection within the last 30 days
curl -s http://localhost:3001/api/projections/{TICKER} | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta
data = json.load(sys.stdin)
ai = [p for p in data if p.get('source') == 'AI_AGENT']
if not ai:
    print('NO_CACHE')
    sys.exit(0)
latest = max(ai, key=lambda p: p.get('savedAt',''))
age = datetime.now(timezone.utc) - datetime.fromisoformat(latest['savedAt'].replace('Z','+00:00'))
if age < timedelta(days=30):
    print(f'CACHED — analyzed {age.days}d ago — fair value \${latest[\"aiThesis\"][\"fairValue\"]}')
else:
    print(f'STALE — {age.days}d old — re-analyze')
"
```
- If output starts with `CACHED` → **STOP**. Report the cached fair value and action to the user. Offer to force-refresh if they explicitly ask.
- If `NO_CACHE` → skip Step 0.5, continue to Step 1.
- If `STALE` → continue to Step 0.5 (prior analysis review) before Step 1.

---

## Step 0.5: Prior Analysis Review (Build-On Mode)
> Only runs when a STALE prior projection exists. Purpose: extract the prior thesis for **context and fact-checking** — NOT to inherit its assumptions.

```bash
curl -s http://localhost:3001/api/projections/{TICKER} | python3 -c "
import json, sys
data = json.load(sys.stdin)
ai = [p for p in data if p.get('source') == 'AI_AGENT']
if not ai: sys.exit(0)
p = max(ai, key=lambda x: x.get('savedAt',''))
snap = p.get('snapshot', {})
s = p.get('scenarios', {})
print(json.dumps({
  'id': p.get('id'),
  'version': p.get('version', 1),
  'model': p.get('aiThesis', {}).get('model'),
  'date': p.get('savedAt','')[:10],
  'prior_price': snap.get('price'),
  'prior_fv': p.get('aiThesis', {}).get('fairValue'),
  'prior_action': p.get('aiThesis', {}).get('action'),
  'bear': {k: s.get('bear',{}).get(k) for k in ['growthRate','netMargin','exitPE','qualityMultiplier','weight']},
  'base': {k: s.get('base',{}).get(k) for k in ['growthRate','netMargin','exitPE','qualityMultiplier','weight']},
  'bull': {k: s.get('bull',{}).get(k) for k in ['growthRate','netMargin','exitPE','qualityMultiplier','weight']},
  'prior_rationale': p.get('aiThesis', {}).get('rationale','')[:300]
}, indent=2))
"
```

After reading the output, **explicitly answer each of these questions in your reasoning** before touching any scenario parameters:

1. **Price delta**: Current price vs prior price — did the thesis play out, overshoot, or miss?
2. **Assumption audit**: Were prior `growthRate`, `netMargin`, `exitPE`, `qualityMultiplier` grounded, or were they inflated? Compare each against sector benchmarks now.
3. **Model quality flag**: If prior model was GPT-5 mini, Gemini, Antigravity, or "UNKNOWN" → mark all assumptions as **unvalidated**. Re-derive everything independently.
4. **Thesis outcome**: If prior said BUY and stock surged, the thesis may have been correct *then* but irrelevant *now* — evaluate current entry, not past entry.
5. **What changed fundamentally**: New revenue data, margin trend reversal, competitive shift, regulatory news.

Record findings in `analyticsLog.priorAnalysisReview`. Then fetch fresh data and build scenarios **entirely from the new data** — prior assumptions inform but never constrain.

**Version continuity**: Preserve the prior projection's `id`. Set `version` = prior `version` + 1.

---

## Step 1: Fetch Financial Data
```bash
# Health check first
curl -sf http://localhost:3001/health || echo "DEGRADED — invoke FB-02"

# Fetch data
python3 investment_screener/backend/py_services/fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json
```
**If fetch fails** → invoke **FB-01** from `references/fallback-tree.md`. Do NOT hallucinate data.

## Step 2: Build Snapshot Object + Seed analyticsLog
```bash
# Standardize metrics using the canonical calculation engine
cat /tmp/{TICKER}_raw.json | python3 plugins/stock-valuation/skills/stock_valuation/scripts/standardize_metrics.py > /tmp/{TICKER}_metrics.json
```
Read `/tmp/{TICKER}_metrics.json` and use the `snapshot` and `ratios` blocks. 

> ⚠️ **The Canonical Calculation Policy**: Never compute P/E, P/S, CAGR, or Share Count derivations inline. Use the outputs from `standardize_metrics.py` to ensure consistency with the web dashboard.

**Also, begin building `analyticsLog` now** — record these facts as you read them so nothing is lost:
- `shareCountMethod`: copy from `snapshot.share_source` in the metrics JSON.
- `analystInputs`: capture Y1/Y2 revenue estimates, Y1/Y2 growth %, blended consensus, target mean, analyst count from the raw JSON.
- `historicalRevenue` + `historicalNetMargins` + `historicalEPS`: copy raw arrays from `financials.*` for durable record.
- `dataQualityFlags`: begin flagging anomalies immediately (outlier years, declining EPS estimates, zero-gap years, etc.).

This is a **live working document** — add to it throughout Steps 2 and 3, not just at the end.

## Step 3: Cognitive Analysis — Define Scenarios, Then Run DCF Calculator

> ⚠️ **NEVER compute DCF math by hand or inline.** After deciding scenario parameters,
> write them to `/tmp/{TICKER}_scenarios.json` and run the canonical calculator.
> The script validates constraints, computes all intermediates, and outputs `presentValue`
> for each scenario. See `plugins/stock-valuation/references/ADR-dcf-calculator.md`.

Use `references/analysis_prompt.md` for full methodology. Key constraints for choosing parameters:

1. **Forward Run-Rate Anchoring**: For stocks with massive committed but unrealized growth (e.g. data center buildouts, contracted backlog), do NOT anchor `base.growthRate` to trailing revenue (TTM). Instead:
   - Identify the "Locked-In" project value (e.g. $1B GPU cluster deployment).
   - Use the `optionalityAdjustment` field in the scenario JSON to represent the terminal value of these projects.
   - Set growth rates based on the *execution of the backlog*, not historical performance.
2. **Weights**: `bear.weight + base.weight + bull.weight` MUST equal **1.0** (±0.01)
3. **Growth ordering**: `bear.growthRate < base.growthRate < bull.growthRate`
3. **Price ordering**: `bear.scenarioPrice < base.scenarioPrice < bull.scenarioPrice`
4. **Margins**: Realistic (-100% to 100%); see sector benchmarks in `references/valuation-benchmarks.md`
5. **Large caps** (>$50B revenue): growth >30% requires named catalyst citation
6. **`shareChange`**: -5.0 to +5.0; **Scores**: integers 0–5
7. **Base anchoring — standard**: `base.growthRate` must be within ±3pp of analyst consensus growth, with explicit justification for any deviation
8. **Base anchoring — hypergrowth exception** (analyst Y1 consensus >40%): Do NOT use Y1 consensus directly as the 5-year CAGR. Instead derive a realistic CAGR from the analyst trajectory:
   - Collect Y1 and Y2 analyst revenue estimates from the data
   - Project years 3-5 using natural deceleration (typically halving the growth rate increment each year)
   - Compute the 5-year CAGR from `(Y5_revenue / TTM_revenue)^(1/5) - 1`
   - State this derivation explicitly in the scenario `rationale`
   - See `references/examples/example_NVDA_2026-05-02.json` for a worked example (73% Y1 consensus → 27% 5-yr CAGR base)
9. **Margin anchoring — trending vs mean-reverting**: The `analysis_prompt.md` rule of ±5pp from 4-year average applies to **mean-reverting** margins. For companies with a consistent multi-year expansion trend (every year higher), use the TTM margin as the anchor instead, and justify any projected expansion or compression relative to TTM:
   - ✅ Mean-reverting: volatile margins with no clear trend → use 4-year average
   - ✅ Trending: margin improving every year for 3+ years → use TTM as anchor; deviations >5pp from TTM require justification
   - See `references/examples/example_GOOG_2026-05-02.json` (4yr avg 26.7% vs TTM 37.9% — TTM used as anchor)
10. **Sector classification**: Match the company's `profile.industry` to the nearest row in `references/valuation-benchmarks.md`. When `profile.sector` is ambiguous (e.g. "Communication Services" for Alphabet), use the industry string to resolve: `Internet Content & Information` → "Technology — Internet / Platforms" benchmark row.

**After deciding parameters, run the calculator:**
```bash
# Write scenario params to temp file
cat > /tmp/{TICKER}_scenarios.json << 'EOF'
{
  "bear": { "weight": 0.XX, "growthRate": X, "netMargin": X, "exitPE": X, "qualityMultiplier": X.XX, "shareChange": X.X },
  "base": { "weight": 0.XX, "growthRate": X, "netMargin": X, "exitPE": X, "qualityMultiplier": X.XX, "shareChange": X.X },
  "bull": { "weight": 0.XX, "growthRate": X, "netMargin": X, "exitPE": X, "qualityMultiplier": X.XX, "shareChange": X.X }
}
EOF

# Run canonical DCF calculator — validates + computes all intermediates
python3 investment_screener/backend/py_services/dcf_scenarios.py \
  --raw /tmp/{TICKER}_raw.json \
  --scenarios /tmp/{TICKER}_scenarios.json \
  --pretty | tee /tmp/{TICKER}_dcf_result.json
```
- If exit code 1 → fix the validation errors reported to stderr before proceeding
- Use `year5Revenue`, `year5NetIncome`, `year5EPS`, `presentValue` from output to populate the projection JSON in Step 5
- `weightedFairValue` and `action` from output are the canonical fair value and recommendation

**Populate `analyticsLog` while reasoning** — record your decisions as you make them:
- `marginAnchor`: state TTM or 4yr avg, which value, and the exact rule applied (trending/mean-reverting)
- `growthDerivation`: state blended analyst consensus and how you derived the base CAGR (especially for hypergrowth — show the deceleration path)
- `sectorBenchmarkRow`: name the exact benchmark row used and the P/E range it provides
- `confidenceBreakdown`: document each positive/negative factor and its score impact

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
  "schemaVersion": "1.2",
  "version": 1,
  "savedAt": "<ISO timestamp>",
  "updatedAt": "<ISO timestamp>",
  "name": "AI Deep Dive — {TICKER} — <date>",
  "rationale": "<3-5 sentence thesis>",
  "snapshot": { "...from Step 2..." },
  "dataPreferences": { "growthBasis": "next", "marginBasis": "ttm" },
  "scenarios": { "bear": {...}, "base": {...}, "bull": {...} },
  "analyticsLog": {
    "shareCountMethod": "<which field used: shares_outstanding vs shares_diluted (NI/EPS derived). Note any discrepancy >15% and resolution. E.g.: 'Used 811M (mktcap-implied); NI/EPS derived 663M flagged as period mismatch — chose mktcap value for consistency'>",
    "marginAnchor": "<TTM or 4yr avg — exact value chosen and rule applied. E.g.: 'TTM 12.3% used; 4yr avg 4.6% distorted by FY2024 deferred tax benefit outlier (32.1%) — excluded per mean-reverting Rule #9'>",
    "growthDerivation": "<blended consensus and CAGR path. E.g.: 'Y1 +22.5% / Y2 +20.0% blended 21.2%; base 19% (deceleration yrs 3-5); within ±3pp consensus ✓; no hypergrowth exception (Y1 <40%)'>",
    "sectorBenchmarkRow": "<exact row from valuation-benchmarks.md. E.g.: 'Technology — Software (SaaS): conservative P/E 20, median 30, growth 50+; net margin typical 15–25%, best-in-class 30%+'>",
    "dataQualityFlags": [
      "<anomaly 1 — e.g. 'FY2024 net margin 32.1% = one-time deferred tax benefit — excluded from margin anchor'>",
      "<anomaly 2 — e.g. 'Analyst EPS Y1 ($3.69) > Y2 ($2.30) — unusual declining trend; suspected fiscal year period misalignment in API'>"
    ],
    "analystInputs": {
      "y1RevEstimate": "<number in $ or null>",
      "y2RevEstimate": "<number in $ or null>",
      "y1GrowthPct": "<number>",
      "y2GrowthPct": "<number>",
      "blendedConsensusPct": "<number>",
      "analystTargetMean": "<number or null>",
      "analystCount": "<number or null>"
    },
    "historicalRevenue": ["<array of last 4-5 fiscal years in $M, oldest→newest>"],
    "historicalNetMargins": ["<array of last 4-5 fiscal years as % floats, oldest→newest>"],
    "historicalEPS": ["<array of last 4-5 fiscal years, oldest→newest; post-split equivalent>"],
    "priorAnalysisReview": {
      "priorModel": "<model name from prior projection, e.g. 'Gemini 3 Pro'>",
      "priorDate": "<YYYY-MM-DD>",
      "priorPrice": "<price when prior analysis was done>",
      "priorFairValue": "<prior weighted fair value>",
      "priorAction": "<BUY/HOLD/SELL>",
      "priceDelta": "<e.g. '+113% since prior analysis — prior BUY thesis played out'>",
      "assumptionAudit": "<e.g. 'Prior base netMargin 22% had no grounding — semiconductor median is 15-30% but INTC was -0.5% TTM at the time; inflated. Prior QM 1.15 on bull unjustified — Intel has no durable pricing power across cycles per benchmark rule.'>",
      "modelQualityFlag": "<VALIDATED if prior was Claude Sonnet 4.6, UNVALIDATED if GPT-5 mini/Gemini/Antigravity/other>",
      "thesisOutcome": "<e.g. 'Thesis was correct directionally (BUY at $46 → now $99) but current price has exceeded prior base case $64 — full re-evaluation required at new entry point'>",
      "fundamentalChanges": "<list key changes since prior analysis: new earnings data, competitive shifts, management changes, macro events>"
    },
    "confidenceBreakdown": "<score>/1.0 — Base: 1.0. [+ for moat/quality signals, - for data anomalies/uncertainty]. E.g.: '0.72 — -0.08 volatile GAAP margins, -0.05 share count ambiguity, -0.05 EPS anomaly, -0.10 unproven platformization strategy'"
  },
  "aiThesis": {
    "model": "<human-readable model name e.g. 'Claude Sonnet 4.6'>",
    "rationale": "<full markdown analysis>",
    "fairValue": "<weighted value>",
    "action": "BUY/HOLD/SELL",
    "analyzedAt": "<ISO timestamp>",
    "researchReport": "{TICKER}_{YYYY-MM-DD}.md"
  },
  "globalSettings": { "discountRate": 10.0, "timeHorizon": 5 }
}
```
> **Model name**: Use human-readable names (`"Claude Sonnet 4.6"` not `"claude-sonnet-4-6"`).
> **analyticsLog is mandatory** in schemaVersion 1.2+. Every field must be populated — no null strings. `dataQualityFlags` must be a non-empty array (at minimum note "No anomalies detected" if clean).

## Step 6: Persist Projection JSON
```bash
cat > /tmp/{TICKER}_projection.json << 'EOF'
<JSON_PAYLOAD>
EOF

# Persist via REST API (persist_projection.py does not exist — use the API)
curl -s -X POST http://localhost:3001/api/projections \
  -H 'Content-Type: application/json' \
  -d @/tmp/{TICKER}_projection.json
```
- Success response: `{"success":true,"message":"Projection saved successfully"}`
- If 409 conflict → increment `version` field and retry once
- **Version continuity for updates**: If a prior projection exists (Step 0.5), reuse its `id` and set `version` = prior `version` + 1. This keeps the full version history queryable in the backend.
- If any other failure → invoke **FB-03** from `references/fallback-tree.md`

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
- Scenario Analysis — for each scenario (Bear/Base/Bull): one narrative paragraph **plus** an assumption table in this exact format:

  | Assumption | Value | Rationale |
  |-----------|-------|-----------|
  | 5-yr Revenue CAGR | X% | ... |
  | Year 5 Revenue | $XB | ... |
  | Net Margin (Yr 5) | X% | ... |
  | Exit P/E | Xx | ... |
  | Quality Multiplier | X.XX | ... |
  | Share Change | X%/yr | ... |
  | **Year 5 EPS** | **$X.XX** | — |
  | **Year 5 Price** | **$XXX** | — |
  | **Present Value** | **$XXX** | — |

- Valuation Math section showing full arithmetic for all three scenarios and the weighted average
- Key Risks (numbered list, 3-5 items), What to Watch, Comparables table
- Data Quality & Confidence Score with explicit flags
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

> **Prior analysis** ({prior_model}, {prior_date}): {prior_action} at ${prior_price} → now ${current_price} ({delta}%). {One sentence: thesis outcome — played out / overshot / missed / N/A}

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

## Step 10: Target Portfolio and Thesis Sync Gate
After completing any valuation and saving the projection, run the automated synchronization verification suite to ensure that target-portfolio.json, the investment_thesis.md, and all active projections are in perfect alignment.
```bash
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```
If this check fails, resolve any missing ticker entries, mismatched weights, or missing projection JSON files before concluding the session.

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
- Thesis synchronization: [✅ verify_thesis_sync.py passed / ❌ Failed]

## Sources Unavailable
- [any that failed or were skipped and why]
```

