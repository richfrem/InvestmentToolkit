---
name: rebalance_portfolio
plugin: thesis-balancer
description: >
  Generate valuation-adjusted trade recommendations to rebalance the portfolio
  toward thesis target weights. Unlike a pure drift-correction engine, this
  skill integrates AI fair-value signals to avoid adding capital to SELL-rated
  holdings and prioritize BUY-rated underweights. Trigger when the user asks
  to rebalance, get trade recommendations, reduce drift, or optimize holdings.
  Also trigger on /rebalance or /rebalance-portfolio.
allowed-tools: Bash, Read, Write
---

# Rebalance Portfolio Skill

## Quick Reference
- **Trigger**: `/rebalance` or `/rebalance-portfolio`
- **Persona**: Disciplined Trade Optimizer — minimizes drift while valuation-gating all BUY trades
- **Rebalance Prompt**: `references/rebalance_prompt.md` ← LLM prompt for trade output
- **Fallbacks**: `references/fallback-tree.md`

## ⚠️ Valuation Gate Constraint
> This skill NEVER proposes buying a SELL-rated holding to restore drift.

- ❌ NEVER propose BUY on a SELL-rated holding without explicit user override request
- ❌ NEVER label "restore Core weight" as the reason without checking valuation action first
- ✅ When a core holding is SELL-rated and drifted down → surface a `skippedRestore` with explanation
- ✅ When a SELL-rated holding has drifted UP → prioritize trimming it (drift + valuation aligned)
- ✅ When a BUY-rated holding is underweight → prioritize restoring it (drift + valuation aligned)
- ✅ If all holdings in a pillar are SELL-rated → hold cash within pillar, recommend thesis review first

---

## Step 1: Load Current State
```bash
# Load thesis + health check
curl -s http://localhost:3001/api/theses/{THESIS_ID}/health | python3 -m json.tool

# Load valuations for all holdings
python3 << 'EOF'
import subprocess, json

thesis_tickers = []  # populate from health check output
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
                'upside': upside
            }
        else:
            missing.append(ticker)
    except:
        missing.append(ticker)

print(json.dumps({'valuations': valuations, 'missing': missing}, indent=2))
EOF
```

---

## Step 2: Classify All Drifted Holdings
For each holding with `|driftPct| > 1%`, classify by combining drift direction with valuation action:

| Drift Direction | Valuation | Classification | Priority |
|-----------------|-----------|----------------|----------|
| Drifted UP      | SELL      | **Trim First** | 1 — both agree |
| Drifted DOWN    | BUY       | **Restore First** | 2 — both agree |
| Drifted UP      | BUY       | **Hold or Trim Late** | 3 — momentum, trim only >8% |
| Drifted DOWN    | SELL      | **Skip Restore** | Blocked — flag as skippedRestore |
| Drifted UP      | HOLD      | **Trim** | 4 |
| Drifted DOWN    | HOLD      | **Restore** | 5 |
| No Valuation    | N/A       | **Flag Missing** | Last |

---

## Step 3: Assess Available Capital
```python
# Estimate trade capacity
cash_holding = get_holding_by_pillar('cash')
capital_from_trims = sum(trim_trades_value)
available_capital = cash_holding.value + capital_from_trims
```

If insufficient capital to restore all underweights → prioritize by:
1. BUY-rated + largest negative drift first
2. HOLD-rated second
3. Leave SELL-rated underweights as `skippedRestores`

---

## Step 4: Build Trade Payload
```python
rebalance_payload = {
    "thesis": { "name": thesis_name, "pillars": pillars, "holdings": holdings_with_targets },
    "healthCheck": health_check_data,
    "marketData": {
        ticker: {
            "currentWeight": h.currentWeight,
            "targetWeight": h.targetWeight,
            "driftPct": h.driftPct,
            "currentValue": h.currentValue,
            "price": h.price
        }
        for h, ticker in holdings
    },
    "valuations": valuations,
    "availableCapital": available_capital,
    "driftClassifications": drift_classifications  # from Step 2
}
```
Submit payload using `references/rebalance_prompt.md` as the system prompt.

---

## Step 5: Present Trade Recommendations
```
**Rebalance Recommendation — {THESIS_NAME}**
*Current Drift Score: {X} → Projected: {Y}*

📊 Trade Plan ({N} trades):
| # | Ticker | Action | Shares | Drift Reason      | Valuation Reason        | Score   |
|---|--------|--------|--------|-------------------|-------------------------|---------|
| 1 | CRWD   | SELL   | 15     | +3.8% overweight  | SELL-rated (−66% FV gap)| −66%    |
| 2 | ZS     | BUY    | 8      | −2.1% underweight | BUY-rated (+67% upside) | +67%    |
| 3 | VST    | BUY    | 12     | −1.8% underweight | BUY-rated (+27% upside) | +27%    |

⛔ Skipped Restores (SELL-rated underweights — NOT buying):
| Ticker | Drift   | FV Gap | Reason                                          |
|--------|---------|--------|-------------------------------------------------|
| INTC   | −4.2%   | −77%   | SELL-rated — thesis review recommended instead  |
| AVGO   | −1.9%   | −32%   | SELL-rated — hold cash in pillar                |

⚠️ Missing Valuations (cannot classify):
{list of tickers with no AI projection — recommend /evaluate-stock for each}

💡 Valuation Alignment Score: {X}/10 trades improve both drift AND valuation alignment

**Net capital required**: ${X} (${Y} from trims + ${Z} cash)

Ready to execute? Confirm each trade before I generate order details.
```

> ⚠️ **Recap Before Execute**: Always confirm individual trades with the user before finalizing.
> Never output "execute all" language. Each trade confirmation is explicit.

---

## Step 6: Confirm + Log Each Trade
For each proposed trade:
1. Present: *"Trade {N}: {ACTION} {shares} shares of {TICKER} at ~${price} — {reason}. Confirm?"*
2. Wait for explicit confirmation per trade
3. After confirmation, format as actionable order note:
   ```
   ✅ CONFIRMED: {ACTION} {shares} {TICKER} @ market
   Note: {drift reason} + {valuation reason}
   Expected drift correction: {driftPct}%
   ```

---

## Sources Checked Declaration
```
## Sources Checked
- Health API: [✅ /api/theses/:id/health / ❌ Failed]
- Valuations: [✅ {N}/{M} holdings / ⚠️ Missing: {list}]
- Drift Classifications: [✅ Completed]
- Rebalance Prompt: [✅ references/rebalance_prompt.md]
- Capital Assessment: [✅ Available: ${X} / ⚠️ Estimated]

## Sources Unavailable
- [any failures or missing data]
```
