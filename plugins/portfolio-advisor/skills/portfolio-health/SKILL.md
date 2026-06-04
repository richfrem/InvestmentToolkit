---
name: portfolio_health
description: "Quick portfolio health check: drift monitor, pillar conviction audit, and thesis formula score. For full adversarial thesis challenge with formula improvement proposals, use /strategic-review."
allowed-tools: Bash, Read, Write
---

# Thesis Balancer Skill

## Quick Reference
- **Trigger**: `/review-portfolio` — quick health check. For full adversarial review: `/strategic-review`
- **Persona**: Portfolio Health Monitor — objective, fast, surfaces drift and conviction signals without formula improvement
- **Thesis Doc**: `investment_screener/backend/data/theses/investment_thesis.md`
- **Fallbacks**: `references/fallback-tree.md` ← load on any API failure
- **Acceptance**: `references/acceptance-criteria.md`
- **Rebalance Prompt**: `references/rebalance_prompt.md`

## Dual-Mode Operation

| Mode | Condition | Action |
|------|-----------|--------|
| **Full** | Backend + projection data available | Full pipeline below |
| **Standalone** | Backend down | Announce → request JSON paste → compute drift manually |

If backend unavailable → immediately invoke **FB-01** from `references/fallback-tree.md`.

---

## Phase 1: Select & Load Thesis
```bash
curl -s http://localhost:3001/api/theses | python3 -m json.tool
```
- If `thesis_id` provided → use directly
- Otherwise → present numbered list and ask user to select
- If empty or API down → invoke **FB-02**

## Phase 2: Run Health Check + Load All Valuations
```bash
# Run drift health check
curl -s "http://localhost:3001/api/theses/{THESIS_ID}/health" | python3 -m json.tool

# Run automated synchronization verification
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```

**Also, immediately load AI valuations for all thesis holdings:**
```bash
python3 << 'EOF'
import subprocess, json

# Load all AI projections for thesis holdings
thesis_tickers = [h['ticker'] for h in thesis['holdings']]
valuations = {}
for ticker in thesis_tickers:
    r = subprocess.run(['curl','-s',f'http://localhost:3001/api/projections/{ticker}'], capture_output=True, text=True)
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
                'model': th.get('model'),
                'confidence': p.get('analyticsLog',{}).get('confidenceBreakdown',''),
                'analyzedAt': th.get('analyzedAt','')[:10]
            }
    except:
        pass
print(json.dumps(valuations, indent=2))
EOF
```
This valuation snapshot is the **primary input** for all Phase 3 analysis steps. Carry it forward through all phases.

If health check schema unexpected → invoke **FB-03**.

---

## Phase 3: Strategic Analysis

### 3A: Classify Every Drifted Holding
For each alert from the health check:
- **Passive drift**: Price movement changed weight without user action → Rebalance candidate
- **Active drift**: User bought/sold → Confirm intent before suggesting correction

> **Recap Before Execute**: For any holding with drift > 5%, PAUSE and ask:
> *"I see {TICKER} has drifted {X}% from its target. Is this a temporary dislocation you want to correct, or has your conviction changed?"*
> ❌ Do NOT output trade instructions before this confirmation.

### 3B: Detect Strategic Conflicts (Valuation-Enhanced)
Flag a **Strategic Conflict** when ALL of:
- `hasValuation: true` AND Tool A recommendation is SELL
- Thesis designates role as "core"
- Upside gap is > −15% (i.e., FV is more than 15% below current price)

For each conflict, surface:
```
⚠️ Strategic Conflict: {TICKER} ({pillar})
   Thesis says: {role} at {target_weight}% target
   Valuation says: SELL — FV ${fair_value} vs ${price} ({upside}% downside)
   Confidence: {confidence_score}
   Key driver: {one sentence from priorAnalysisReview.assumptionAudit}
   → Resolution required: Which view takes priority?
```

Do NOT auto-resolve. Present both sides before asking for user direction.

### 3C: Check Thesis Breakers
For each holding with defined `thesisBreakers`, cross-check against:
- Current price level
- Latest news context (if provided)
- Any valuation-flagged structural changes in `analyticsLog.fundamentalChanges`

If a breaker is triggered:
- Present the specific condition crossed
- Present the mechanical exit as the required action
- Offer override with explicit user confirmation

### 3D: Surface Missing Valuations
For any holding with `hasValuation: false`:
- List all such tickers explicitly with pillar and role
- Recommend: *"Run `/evaluate-stock {TICKER}` for AI analysis (role: {role}, pillar: {pillar})."*
- Prioritize missing valuations for **core** holdings first

### 3E: Pillar Conviction Audit *(New — grounds thesis assessment in fair value data)*
For each pillar, aggregate the valuation signals of its holdings:

```
Pillar: {PILLAR_NAME} (Target: {X}%)
  BUY  [{N} holdings]: {ticker_list with upside%}
  HOLD [{N} holdings]: {ticker_list}
  SELL [{N} holdings]: {ticker_list with downside%}
  NO DATA [{N} holdings]: {ticker_list}

Pillar Signal: ✅ ALIGNED | ⚠️ UNDER PRESSURE | 🔴 CRITICAL
  → ALIGNED: weighted BUY ≥ weighted SELL
  → UNDER PRESSURE: weighted SELL > weighted BUY, at least one BUY
  → CRITICAL: all valuated holdings SELL, no BUY signals
```

**Compute Thesis Formula Health Score (0–100):**
```python
score = 100
for pillar in pillars:
    holdings = get_pillar_holdings(pillar)
    sell_weight = sum(h.targetWeight for h in holdings if valuation[h.ticker].action == 'SELL')
    total_weight = sum(h.targetWeight for h in holdings if h.ticker in valuations)
    sell_ratio = sell_weight / total_weight if total_weight else 0
    score -= sell_ratio * pillar.targetWeight * 0.5   # penalty: sell ratio * pillar weight
```
> A score of 100 = all core holdings are BUY-rated.
> A score below 60 = thesis formula requires structural review.

### 3F: Valuation Gap Score *(New — finds where thesis most agrees/disagrees with market)*
For each holding, compute: `ValueGap = (fairValue - price) / price * targetWeight`

Rank by ValueGap descending:
- **Top 5 positive ValueGaps** = *Thesis-Confirmed Opportunities* (own more of these)
- **Top 5 negative ValueGaps** = *Thesis-Challenged Positions* (thesis vs. valuation misaligned)

Surface as:
```
🎯 Thesis-Confirmed (Valuation Agrees):
  1. {TICKER}: +{upside}% upside, {target_weight}% target → thesis conviction validated
  ...

⚡ Thesis-Challenged (Valuation Disagrees):
  1. {TICKER}: −{downside}% overvalued, {target_weight}% target → thesis vs. DCF conflict
  ...
```

---

## Phase 4: Report & Recommendations

Present full findings in this structure:

```
**Portfolio Health: {STATUS}** | Thesis Formula Score: {X}/100

📊 Summary:
- {N} holdings on target | {N} drifting | {N} critical
- {N} strategic conflicts requiring resolution
- {N} pillar conviction signals: {N} ALIGNED / {N} UNDER PRESSURE / {N} CRITICAL
- Missing valuations: {N} holdings (run /evaluate-stock for each)
- Thesis synchronization check: [✅ verify_thesis_sync.py passed / ❌ Out of sync (run verify_thesis_sync.py for details)]

🏛️ Pillar Conviction Audit:
| Pillar | Target% | Signal | BUY | HOLD | SELL | No Data |
|--------|---------|--------|-----|------|------|---------|
| ...    | ...     | ...    | ... | ...  | ...  | ...     |

⚠️ Strategic Conflicts ({N}):
| Ticker | Pillar | Role | FV | Price | Upside | Confidence |
|--------|--------|------|----|-------|--------|------------|
| ...    | ...    | ...  | $. | $.    | −X%    | 0.XX       |

🎯 Thesis-Confirmed Opportunities:
[Top 3 BUY-rated holdings with highest upside × target weight]

⚡ Thesis-Challenged Positions:
[Top 3 SELL-rated core holdings with largest downside]

📈 Drift Details:
| Holding | Target | Actual | Drift | Valuation | Action |
|---------|--------|--------|-------|-----------|--------|
| {TICKER}| {X}%   | {Y}%   |{+/-Z%}| BUY/SELL  | {action}|

🚨 Thesis Breakers Triggered: {list or "None"}
🔍 Missing Valuations: {list with pillar/role or "None"}
```

---

## Phase 5: Thesis Evolution
If user indicates conviction change:
1. Show current Pillar Conviction Audit summary
2. Propose specific updated target weights grounded in valuation evidence
3. Show impact on drift scores AND Thesis Formula Score **before** applying
4. **Auto-apply if targets are conviction-grounded** (no new positions, no BLOCKED items) — state the proposed changes and apply immediately. Only wait for explicit confirmation if adding a new position (Gate 2) or user has flagged uncertainty. Waiting for "yes" on every health review leaves the modal permanently in PROPOSED state.

---

## Phase 6: Formula Improvement
> For formula improvement proposals, run `/strategic-review` — it runs the full adversarial review with structured formula proposals. This skill intentionally does not duplicate that step.

---

## Error Handling
| Condition | Action |
|:---|:---|
| Backend API down | FB-01 (standalone mode) |
| No thesis found | FB-02 |
| Malformed health response | FB-03 |
| Strategic conflict unresolvable | FB-04 |

---

## Sources Checked Declaration
> **L4 Pattern**: Source Transparency Declaration. Every completed review MUST end with:

```
## Sources Checked
- Thesis API: [✅ /api/theses responded / ⚠️ Manual input / ❌ Unavailable]
- Health API: [✅ /api/theses/:id/health responded / ⚠️ Calculated manually / ❌ Failed]
- AI Valuations: [✅ Available for {N}/{M} holdings / ⚠️ Missing for: {list} / ❌ Failed]
- Pillar Conviction Audit: [✅ Completed / ⚠️ Partial ({N} missing) / ❌ Skipped]
- Thesis Formula Score: [✅ Computed: {X}/100 / ❌ Skipped]
- Thesis synchronization: [✅ verify_thesis_sync.py passed / ❌ Failed/Out of sync]
- Fallback tree: [✅ references/fallback-tree.md consulted / ❌ Not needed]

## Sources Unavailable
- [any APIs or data sources that failed, with reason]
```
