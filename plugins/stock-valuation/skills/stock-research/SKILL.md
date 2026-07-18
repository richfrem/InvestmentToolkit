---
name: stock_research
plugin: stock-valuation
description: >
  Perform a qualitative deep-dive research sweep on a stock: recent news,
  earnings call highlights, competitive landscape shifts, macro/regulatory
  changes, management updates, and analyst sentiment. Updates the existing
  research report and priorAnalysisReview context. Ends with a structured
  judgment on whether findings warrant a full DCF re-valuation via
  /evaluate-stock. Trigger when something happened and the user wants to
  understand the impact before deciding whether to update the model.
  Also trigger on /research-stock.
allowed-tools: Bash, Read, Write
---

# Stock Research Skill

## Quick Reference
- **Trigger**: `/research-stock {TICKER}` or natural language: "research {TICKER}", "what's changed with {TICKER}"
- **Output (Research)**: Appends to `backend/data/research/{TICKER}_{YYYY-MM-DD}.md`
- **Output (Decision)**: Structured re-valuation recommendation — triggers `/evaluate-stock` if warranted
- **Chains into**: `stock_valuation` skill when re-valuation is confirmed
- **Fallbacks**: `references/fallback-tree.md`

## When to Use This Skill vs `/evaluate-stock`

| Situation | Use |
|-----------|-----|
| Something happened (earnings, news, product launch, competitor move) | `/research-stock` first |
| No prior valuation exists | `/evaluate-stock` directly |
| Prior valuation is stale (>30 days) and nothing specific happened | `/evaluate-stock` directly |
| You want to know *if* the model needs updating before re-running it | `/research-stock` |
| Explicit request for new DCF numbers | `/evaluate-stock` directly |

---

## Step 1: Load Prior Analysis Context
```bash
# Load the most recent AI projection
API_TOKEN=$(cat .runtime/api-token)
curl -s -H "Authorization: Bearer $API_TOKEN" http://localhost:3001/api/projections/{TICKER} | python3 -c "
import json, sys
from datetime import datetime, timezone
data = json.load(sys.stdin)
ai = [p for p in data if p.get('source') == 'AI_AGENT']
if not ai:
    print('NO_PRIOR — no existing AI analysis found')
    exit(0)
p = max(ai, key=lambda x: x.get('savedAt',''))
th = p.get('aiThesis', {})
sn = p.get('snapshot', {})
log = p.get('analyticsLog', {})
age = (datetime.now(timezone.utc) - datetime.fromisoformat(p['savedAt'].replace('Z','+00:00'))).days
print(json.dumps({
    'id': p.get('id'),
    'version': p.get('version', 1),
    'model': th.get('model'),
    'analyzedAt': th.get('analyzedAt','')[:10],
    'ageDays': age,
    'priceAtAnalysis': sn.get('price'),
    'fairValue': th.get('fairValue'),
    'action': th.get('action'),
    'rationale': th.get('rationale','')[:400],
    'priorFundamentalChanges': log.get('priorAnalysisReview', {}).get('fundamentalChanges',''),
    'dataQualityFlags': log.get('dataQualityFlags', []),
    'confidence': log.get('confidenceBreakdown','')
}, indent=2))
"
```

Establish baseline:
- What was the prior thesis and fair value?
- How old is it?
- What was the confidence level and any known data quality flags?
- What was the current price at analysis vs today?

---

## Step 2: Fetch Current Price + Basic Metrics
```bash
python3 investment_screener/backend/py_services/fetch_financials.py {TICKER} > /tmp/{TICKER}_raw.json

# Extract key snapshot for comparison
python3 -c "
import json
d = json.load(open('/tmp/{TICKER}_raw.json'))
m = d.get('metrics', {})
print(f'Current price:  \${m.get(\"price\")}')
print(f'Market cap:     \${m.get(\"market_cap_b\", 0):.1f}B')
print(f'TTM Revenue:    \${m.get(\"revenue\", 0)/1e9:.2f}B')
print(f'TTM Net Margin: {m.get(\"net_margin\", 0):.1f}%')
print(f'Forward PE:     {m.get(\"forward_pe\")}')
print(f'Analyst target: \${m.get(\"analyst_target_mean\")}')
"
```

Note the price delta since prior analysis: `(currentPrice - priorPrice) / priorPrice * 100`

---

## Step 3: Research Sweep — Qualitative Intelligence Gathering

Conduct a structured sweep across these domains. For each, note: **what changed**, **how material is it**, and **does it affect the DCF model inputs?**

### 3A: Recent Earnings & Guidance
- Revenue and EPS vs consensus (beat/miss/in-line)
- Management guidance for next quarter and full year
- Any revision to multi-year outlook
- Gross margin and operating leverage trend
- **Model impact**: Changes analyst revenue estimates → affects `growthRate` and `netMargin` inputs

### 3B: Competitive Landscape
- New entrants or product launches by competitors
- Market share data (wins/losses)
- Pricing pressure signals
- Partnership or ecosystem changes
- **Model impact**: Structural moat changes → affects `qualityMultiplier` and `exitPE`

### 3C: Macro & Regulatory
- Interest rate sensitivity (particularly for high-PE growth stocks)
- Regulatory rulings, antitrust actions, tariff exposure
- Government contracts (wins/losses for defense/energy/AI infra)
- Sector-wide policy changes
- **Model impact**: Discount rate assumptions; regulatory risk → may shift `bear` scenario weight

### 3D: Management & Capital Allocation
- CEO/CFO changes
- Share buybacks, dilution events (new equity raises, convertible notes)
- Acquisitions or divestitures
- Dividend changes
- **Model impact**: `shareChange` parameter; `qualityMultiplier` if governance improves/degrades

### 3E: Analyst Sentiment
- Target price revisions since last analysis
- Rating changes (upgrades/downgrades)
- Consensus shift in revenue/EPS estimates
- **Model impact**: New `analystGrowthEstimate` and `analystMarginEstimate` baseline

### 3F: Thesis-Specific Signals
Based on the prior thesis rationale, check the specific bets:
- If the thesis was a product cycle bet → is it playing out?
- If the thesis was a margin expansion bet → are margins actually expanding?
- If the thesis was a market share bet → is share growing?
- **Model impact**: Directly confirms or contradicts scenario assumptions

---

## Step 4: Assess Model Impact — Change Classification

For each finding from Step 3, classify:

| Change Class | Description | Model Impact | Re-Valuation Needed? |
|-------------|-------------|--------------|---------------------|
| **Class A** | Structural — changes long-term earnings power | `growthRate`, `netMargin`, `exitPE`, `qualityMultiplier` | ✅ Yes — full DCF update |
| **Class B** | Cyclical — temporary deviation from trend | Scenario weights only | Maybe — scenario reweight |
| **Class C** | Narrative — confirms or challenges thesis story | `rationale`, research report | No — report update only |
| **Class D** | Noise — irrelevant to 5-year model | None | No |

---

## Step 5: Re-Valuation Decision Gate

Compile the Class A and Class B findings. Make an explicit recommendation:

```
📊 Research Sweep Complete — {TICKER}

**Price delta since last analysis**: ${prior_price} → ${current_price} ({+/-X}%)
**Fair value at last analysis**: ${fair_value} ({action})
**Current analyst consensus target**: ${analyst_target}

**Key findings** ({N} total):
  Class A (structural changes requiring DCF update): {N}
    → {finding 1}
    → {finding 2}
  Class B (scenario weight changes only): {N}
    → {finding}
  Class C (narrative updates only): {N}
    → {finding}

**Re-Valuation Recommendation**:
  [✅ YES — Full DCF update recommended]
    Reason: {Class A findings materially change the model inputs}
    Changed inputs: {growthRate / netMargin / exitPE / qualityMultiplier}

  [⚠️ PARTIAL — Scenario reweight only]
    Reason: {Cyclical factors shift bear/base/bull weights but not 5-yr trajectory}

  [📝 NO — Research report update only]
    Reason: {No structural changes; findings are confirmatory or noise}

Shall I proceed with the recommended action?
```

**Wait for user confirmation before chaining into `/evaluate-stock`.**

---

## Step 6A: If Full Re-Valuation Confirmed
Pass research context forward as enriched input to the stock_valuation skill:

```bash
# Write research context for the valuation skill to consume
cat > /tmp/{TICKER}_research_context.json << 'EOF'
{
  "researchDate": "{YYYY-MM-DD}",
  "classAFindings": [
    {
      "domain": "Earnings",
      "finding": "Revenue beat by 12%; management raised FY guidance by 8%",
      "modelImpact": "base growthRate: +3pp; base netMargin: +1pp"
    }
  ],
  "classBFindings": [],
  "updatedAnalystEstimates": {
    "y1GrowthPct": 28.5,
    "y2GrowthPct": 22.0,
    "analystTargetMean": 245.00
  },
  "narrativeSummary": "2-3 sentence summary of what changed and what it means for the thesis"
}
EOF
```

Then invoke the stock_valuation skill:
> *"Based on the research findings, running a full DCF update for {TICKER}. The key input changes are: {list Class A impacts}. Prior model assumptions treated as UNVALIDATED per research findings."*

The stock_valuation skill will pick up the prior projection (Step 0.5) and incorporate the research context in `priorAnalysisReview.fundamentalChanges`.

---

## Step 6B: If Scenario Reweight Only
Update the existing projection's scenario weights and re-run DCF with same growth/margin/PE inputs but adjusted bear/base/bull weights:

```bash
# Load existing scenarios, adjust weights only, re-run DCF
python3 investment_screener/backend/py_services/dcf_scenarios.py \
  --raw /tmp/{TICKER}_raw.json \
  --scenarios /tmp/{TICKER}_reweighted_scenarios.json \
  --pretty
```

Persist as a new version with `version` = prior + 1. Note in `rationale`: *"Scenario weights updated based on {date} research sweep; growth/margin/PE inputs unchanged."*

---

## Step 6C: If Report Update Only
Append a "Research Update" event to the shared intelligence ledger and regenerate the
canonical views (never write dated markdown directly — per ADR-028's anti-duplication rule):

```bash
mkdir -p temp
cat > temp/research_body.md << 'EOF'

---

## Research Update — {YYYY-MM-DD}

**Summary**: {2-3 sentences on what was researched and key findings}

**Findings**:
- {Class C finding 1}
- {Class C finding 2}

**Model Impact**: None — findings are confirmatory. No DCF update required at this time.

**Next Review Trigger**: {specific condition that would warrant a full re-valuation}
EOF
cd investment_screener/backend/py_services
python3 -m intelligence.event_store \
  --event-type RESEARCH_IMPORT --ticker {TICKER} --effective-at "$(date +%F)" \
  --status ACTIVE --title "{TICKER} research update" --body-file temp/research_body.md
python3 -m intelligence.view_generator {TICKER}
```

---

## Sources Checked Declaration
```
## Sources Checked
- Prior projection API: [✅ Loaded v{N} from {date} / ❌ No prior analysis]
- Current financials: [✅ fetch_financials.py / ❌ Failed]
- Earnings data: [✅ Reviewed / ⚠️ Stale / ❌ Unavailable]
- Competitive landscape: [✅ Reviewed / ⚠️ Limited data]
- Analyst estimates: [✅ {N} analysts, target ${X} / ⚠️ No data]
- Re-valuation decision: [✅ Recommended {YES/PARTIAL/NO} / ⚠️ User declined]
- Research report: [✅ Updated {path} / ❌ Failed]

## Sources Unavailable
- [any failures or gaps]
```
