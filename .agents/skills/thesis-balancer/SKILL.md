---
name: thesis_balancer
description: >
  Monitor portfolio health, calculate drift, and enforce thesis alignment.
  Trigger when user asks to review their portfolio, check thesis compliance,
  detect drift, or rebalance holdings. Also trigger on /review-portfolio.
  Integrates with stock-valuation plugin for strategic conflict detection.
allowed-tools: Bash, Read, Write
---

# Thesis Balancer Skill

## Quick Reference
- **Trigger**: `/review-portfolio [thesis_id]`
- **Persona**: Strategic Guardian — objective, disciplined, data-driven
- **Fallbacks**: `references/fallback-tree.md` ← load on any API failure
- **Acceptance**: `references/acceptance-criteria.md`

## Dual-Mode Operation
See `CONNECTORS.md` for full degradation contract.

| Mode | Condition | Action |
|------|-----------|--------|
| **Full** | `~~portfolio-api` + `~~thesis-store` available | Full pipeline below |
| **Standalone** | Backend down | Announce → request JSON paste → compute drift manually |

If backend unavailable → immediately invoke **FB-01** from `references/fallback-tree.md`.

---

## Phase 1: Select & Load Thesis
```bash
# List available theses
curl -s http://localhost:3001/api/theses | python3 -m json.tool
```
- If `thesis_id` was provided → use it directly
- Otherwise → present numbered list and ask user to select
- If empty or API down → invoke **FB-02** from `references/fallback-tree.md`

## Phase 2: Run Health Check
```bash
curl -s "http://localhost:3001/api/theses/{THESIS_ID}/health" | python3 -m json.tool
```
If response schema is unexpected → invoke **FB-03** from `references/fallback-tree.md`.

## Phase 3: Strategic Analysis

### 3A: Classify Every Drifted Holding
For each alert from the health check:
- **Passive drift**: Price movement changed weight without user action → Rebalance candidate
- **Active drift**: User bought/sold → Confirm intent before suggesting correction

> **Recap Before Execute**: For any holding with drift > 5%, PAUSE and ask:
> *"I see {TICKER} has drifted {X}% from its target. Is this a temporary dislocation you want to correct, or has your conviction changed?"*
> ❌ Do NOT output trade instructions before this confirmation.

### 3B: Detect Strategic Conflicts
If a holding satisfies ALL of:
- `hasValuation: true` AND Tool A recommendation is SELL or HOLD
- Thesis designates it as "Core"
- Status is ON_TARGET or DRIFTING

→ Flag as **Strategic Conflict**:
> *"⚠️ Strategic Conflict: `/evaluate-stock` recommends {ACTION} on {TICKER}, but your thesis designates it as Core. Which view takes priority?"*

Do NOT auto-resolve. Invoke **FB-04** from `references/fallback-tree.md` if user declines to resolve.

### 3C: Check Thesis Breakers
If a holding crosses a hard thesis rule (e.g. mandatory exit condition):
- Present the breaker condition explicitly with the threshold crossed
- Present full mechanical exit as the required action
- Offer user ability to override with explicit confirmation

### 3D: Surface Missing Valuations
For any holding with `hasValuation: false`:
- List all such tickers explicitly
- Recommend: *"Run `/evaluate-stock {TICKER}` for a full AI analysis."*

## Phase 4: Report & Recommendations
Present findings:
```
**Portfolio Health: {STATUS}** (Total Drift Score: {X})

📊 Summary:
- {N} holdings on target
- {N} holdings drifting (>{Y}%)
- {N} critical alerts
- {N} strategic conflicts requiring resolution

🚨 Critical Alerts:
- {TICKER}: {alert_message} → Recommended: {BUY/SELL/TRIM}

📈 Drift Details:
| Holding | Target | Actual | Drift | Type | Action |
|---------|--------|--------|-------|------|--------|
| {TICKER} | {X}% | {Y}% | {+/-Z}% | Passive/Active | {action} |

⚠️ Strategic Conflicts: {list or "None"}
🔍 Missing Valuations: {list or "None"}
```

## Phase 5: Thesis Evolution
If user indicates conviction change:
1. Propose specific updated target weights
2. Show impact on drift scores **before** applying
3. Ask: "Want me to update the thesis with these new targets?" — wait for explicit confirmation
4. Only update after "yes/proceed/go"

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
- AI Valuations: [✅ Available for {N}/{M} holdings / ⚠️ Missing for: {list}]
- Fallback tree: [✅ references/fallback-tree.md consulted / ❌ Not needed]

## Sources Unavailable
- [any APIs or data sources that failed, with reason]
```
