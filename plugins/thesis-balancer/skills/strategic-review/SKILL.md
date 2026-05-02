---
name: strategic_review
plugin: thesis-balancer
description: >
  Challenge and stress-test the investment thesis against current AI valuation
  evidence, pillar performance, and market reality. Produces a structured
  assessment of which pillars are working, which are failing, and specific
  formula improvement proposals. Trigger when the user wants to review thesis
  health, question pillar sizing, or challenge underperforming positions.
  Also trigger on /strategic-review or /challenge-thesis.
allowed-tools: Bash, Read, Write
---

# Strategic Review Skill

## Quick Reference
- **Trigger**: `/strategic-review` or `/challenge-thesis`
- **Persona**: Adversarial Thesis Challenger — objective, data-grounded, does not protect user bias
- **Strategic Prompt**: `references/strategic_review_prompt.md` ← LLM prompt for structured output
- **Thesis Doc**: `docs/InvestmentThesis/twin_revolution_ASI_and_Sovereign_finance.md`
- **Fallbacks**: `references/fallback-tree.md`

## ⚠️ Adversarial Review Constraint
> This skill is designed to **challenge** the thesis, not validate it.

- ❌ NEVER soften SELL findings because the user has conviction in a holding
- ❌ NEVER avoid naming a pillar as CRITICAL because it may be uncomfortable
- ❌ NEVER propose formula improvements that preserve current weights without evidence
- ✅ If valuation evidence contradicts thesis sizing, say so explicitly
- ✅ Distinguish between "thesis intact but entry was wrong" vs "thesis structurally broken"
- ✅ Surface performance failure (negative price return + SELL rating) as compound evidence

---

## Step 1: Load Thesis + All Valuations
```bash
# Load thesis
curl -s http://localhost:3001/api/theses | python3 -c "
import json, sys
theses = json.load(sys.stdin)
for i, t in enumerate(theses):
    print(f'{i+1}. {t[\"id\"]} — {t[\"name\"]} (v{t.get(\"version\",1)})')
"

# Load health check
curl -s "http://localhost:3001/api/theses/{THESIS_ID}/health" | python3 -m json.tool

# Load all AI projections for thesis holdings
python3 << 'EOF'
import subprocess, json

thesis_tickers = []  # populate from thesis holdings above
valuations = {}
missing = []

for ticker in thesis_tickers:
    r = subprocess.run(['curl','-s',f'http://localhost:3001/api/projections/{ticker}'],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        ai = [p for p in d if p.get('source')=='AI_AGENT']
        if ai:
            p = max(ai, key=lambda x: x.get('savedAt',''))
            th = p.get('aiThesis',{})
            sn = p.get('snapshot',{})
            fv = th.get('fairValue',0)
            price = sn.get('price',0)
            upside = round((fv - price)/price*100, 1) if price else None
            valuations[ticker] = {
                'action': th.get('action'),
                'fairValue': fv,
                'price': price,
                'upside': upside,
                'confidence': p.get('analyticsLog',{}).get('confidenceBreakdown',''),
                'model': th.get('model'),
                'analyzedAt': th.get('analyzedAt','')[:10]
            }
        else:
            missing.append(ticker)
    except:
        missing.append(ticker)

print("=== VALUATIONS ===")
print(json.dumps(valuations, indent=2))
print(f"\n=== MISSING ({len(missing)}) ===")
print(missing)
EOF
```

---

## Step 2: Build Pillar Conviction Audit
For each pillar in the thesis, aggregate valuation signals weighted by each holding's `targetWeight`:

```python
for each pillar:
    buy_weight = sum(h.targetWeight for h in pillar.holdings if valuations[h.ticker].action == 'BUY')
    sell_weight = sum(h.targetWeight for h in pillar.holdings if valuations[h.ticker].action == 'SELL')
    hold_weight = sum(h.targetWeight for h in pillar.holdings if valuations[h.ticker].action == 'HOLD')
    no_data_weight = sum(h.targetWeight for h in pillar.holdings if h.ticker not in valuations)
    total_valued = buy_weight + sell_weight + hold_weight

    if sell_weight / total_valued >= 0.5:
        signal = "CRITICAL"
    elif sell_weight > buy_weight:
        signal = "UNDER_PRESSURE"
    else:
        signal = "ALIGNED"
```

---

## Step 3: Compute Thesis Formula Health Score (0–100)
```python
score = 100
for pillar in pillars:
    holdings = get_pillar_holdings(pillar)
    sell_w = sum(h.targetWeight for h in holdings if valuations.get(h.ticker,{}).get('action')=='SELL')
    total_w = sum(h.targetWeight for h in holdings if h.ticker in valuations)
    if total_w > 0:
        sell_ratio = sell_w / total_w
        score -= sell_ratio * pillar.targetWeight * 0.5
```
> Score < 70 → thesis requires structural review. Surface this to the user prominently.

---

## Step 4: Build Valuation Gap Ranking
```python
gaps = []
for ticker, val in valuations.items():
    holding = get_holding(ticker)
    gap = (val['fairValue'] - val['price']) / val['price'] * holding['targetWeight']
    gaps.append({'ticker': ticker, 'gap': gap, 'upside': val['upside'], 'action': val['action']})

gaps.sort(key=lambda x: x['gap'], reverse=True)
thesis_confirmed = gaps[:5]   # most positive gap × weight
thesis_challenged = gaps[-5:] # most negative gap × weight
```

---

## Step 5: Identify Underperforming Pillar Patterns
For any pillar flagged UNDER PRESSURE or CRITICAL, investigate:

1. **Is the SELL pressure concentrated (1 large holding) or systemic (multiple holdings)?**
   - Concentrated → position sizing problem; the thesis idea may still be valid
   - Systemic → the pillar thesis itself may be wrong

2. **What is the actual price performance of pillar holdings since thesis inception?**
   - If multiple holdings are down significantly AND SELL-rated → compounding evidence: thesis is failing
   - If price down but fair value UP → dislocation opportunity (buy the dip case)
   - If price up but SELL-rated → entry was at wrong price, thesis overshot

3. **Specific pillar challenges to always surface:**
   - **Crypto / Bitcoin Mining** (IREN, CORZ, CIFR, CLSK, BITF, BTDR): Cyclical exposure to BTC price; thin margins at BTC trough; SELL ratings at current BTC cycle highs are a mean-reversion signal, not thesis failure
   - **Cybersecurity** (CRWD, PANW, ZS): Crowding risk; after CrowdStrike outage, execution record matters — CRWD SELL at −66% is structural, not cyclical
   - **Energy / Power** (VST, CEG, OKLO): Policy-dependent; OKLO pre-revenue, speculative — SELL at −93% reflects DCF reality on pre-revenue nuclear; CEG regulatory compression

---

## Step 6: Submit to Strategic Review LLM Prompt
Assemble the full payload and process through `references/strategic_review_prompt.md`:

```python
review_payload = {
    "thesis": { "name": thesis_name, "pillars": pillars_with_holdings, "version": version },
    "pillarConvictionAudit": pillar_audit,
    "valuationGapRanking": { "thesisConfirmed": thesis_confirmed, "thesisChallenged": thesis_challenged },
    "thesisFormulaScore": formula_score,
    "holdingValuations": valuations,
    "missingValuations": missing,
    "strategicConflicts": [h for h in valuations if valuations[h]['action']=='SELL' and is_core(h)]
}
```
Use `references/strategic_review_prompt.md` as the system prompt to produce structured JSON output.

---

## Step 7: Present Strategic Review Report
```
**Strategic Review — {THESIS_NAME}**
*Thesis Formula Score: {X}/100 — {HEALTHY / UNDER PRESSURE / REQUIRES RESTRUCTURE}*

🏛️ Pillar Conviction Audit:
| Pillar        | Target% | Signal           | BUY%  | HOLD% | SELL% | No Data |
|---------------|---------|------------------|-------|-------|-------|---------|
| AI Titans     | 12.40%  | ✅ ALIGNED        | 100%  | 0%    | 0%    | 0%      |
| Compute       | 27.65%  | 🔴 CRITICAL       | 18%   | 0%    | 52%   | 30%     |
| Power         | 9.97%   | ⚠️ UNDER PRESSURE | 27%   | 0%    | 43%   | 30%     |
| ...           | ...     | ...              | ...   | ...   | ...   | ...     |

⚡ Thesis-Challenged Positions (valuation vs thesis most misaligned):
1. {TICKER}: −{X}% FV gap, {target_weight}% target — {thesis_role}
   Thesis says: {rationale}. Valuation says: {verdict}. Tension: {one sentence}

🎯 Thesis-Confirmed Opportunities:
1. {TICKER}: +{X}% FV upside, {target_weight}% target — thesis conviction validated

📋 Formula Improvement Proposals:
{N} proposals from strategic review (see full JSON output)

⚠️ Thesis Breakers Triggered: {list or "None"}

Want me to apply any formula improvements to the thesis, or run a rebalance
recommendation using the updated weights?
```

---

## Sources Checked Declaration
```
## Sources Checked
- Thesis API: [✅ Loaded / ❌ Failed]
- All Valuations: [✅ {N}/{M} holdings / ⚠️ Missing: {list}]
- Pillar Conviction Audit: [✅ Completed / ⚠️ Partial]
- Thesis Formula Score: [✅ {X}/100]
- Strategic Review Prompt: [✅ references/strategic_review_prompt.md]
- Valuation Gap Ranking: [✅ Completed]

## Sources Unavailable
- [any failures]
```
