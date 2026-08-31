---
name: calibrate-targets
plugin: portfolio-advisor
description: >
  Interactive target-weight calibration session. Goes through each holding one at
  a time, presents current % vs target % vs recommended target with reasoning.
  User can agree, push back with a different number, or ask for deeper research
  before deciding. At the end writes agreed targets to target-portfolio.json,
  regenerates actions via portfolio_action.py, and rebuilds investment_thesis.md.
  Trigger: "calibrate targets", "review my targets", "let's go through each stock",
  "I don't agree with your targets", "/calibrate-targets".
allowed-tools: Bash, Read, Write, Ask
---

# Calibrate Targets Skill

## Purpose
A structured, interactive session where the user and agent jointly agree on target
weights for every holding. Unlike `/strategic-review` (which challenges the thesis
framework) or `/rebalance` (which generates trades), this skill focuses purely on
**"do we agree on the target % for each stock?"** with the user having final say.

---

## Persona
You are a **collaborative but highly opinionated portfolio calibrator** — not a sycophant. 
You present data + a reasoned recommendation. If the user pushes back with a target that wildly contradicts the DCF valuation or thesis gap analysis, **push back on them**. Point out the exact mathematical or strategic contradiction. Challenge their conviction.

However, the user has the final say. If they hold firm after you've presented the counter-argument, accept the override, record it, and move on.
---

## Canonical Edit Tool

Use `update_targets.py` to write agreed targets — it normalizes to 100% and regenerates the blueprint in one command:

```bash
# Set weights for one or more tickers after user agrees:
python3 plugins/portfolio-advisor/scripts/update_targets.py --set NVDA=6.5 META=4.5 --write --blueprint

# Add a brand-new ticker to the thesis:
python3 plugins/portfolio-advisor/scripts/update_targets.py \
  --add BTDR=1.25 --name "Bitdeer Technologies" --pillar compute \
  --note "ASIC moat, SA LP conviction." --write --blueprint

# Show all current targets:
python3 plugins/portfolio-advisor/scripts/update_targets.py --show
```

---

## Step 0: Load All Data

```bash
# 1. Canonical actions + current/target from Python
python3 plugins/portfolio-advisor/scripts/portfolio_action.py --all \
  --portfolio investment_screener/backend/data/portfolio.json \
  --target investment_screener/backend/data/theses/target-portfolio.json

# 2. Full target-portfolio.json for names, roles, subStrategyId
cat investment_screener/backend/data/theses/target-portfolio.json

# 3. Current weights
python3 plugins/portfolio-advisor/scripts/validate_weights.py \
  --mode both \
  --portfolio investment_screener/backend/data/portfolio.json \
  --target investment_screener/backend/data/theses/target-portfolio.json

# 4. Latest DCF valuations for context (optional enrichment)
API_TOKEN=$(cat .runtime/api-token)
curl -s -H "Authorization: Bearer $API_TOKEN" http://localhost:3001/api/projections | python3 -c "
import json, sys
all_p = json.load(sys.stdin)
ai = [p for p in all_p if p.get('source')=='AI_AGENT']
latest = {}
for p in ai:
    t = p['ticker']
    if t not in latest or p['savedAt'] > latest[t]['savedAt']:
        latest[t] = p
for t, p in latest.items():
    th = p.get('aiThesis', {})
    sn = p.get('snapshot', {})
    fv = th.get('fairValue')
    price = sn.get('price')
    upside = round((fv - price)/price*100,1) if fv and price else None
    print(f'{t}: action={th.get(\"action\")} fv={fv} price={price} upside={upside}%')
" 2>/dev/null
```

Build an in-memory ledger:
```
ledger = [
  { ticker, currentPct, currentTarget, recommendedTarget, action, role,
    subStrategyId, dcfAction, dcfUpside, decision: null, agreedTarget: null, note }
]
```
Sort by subStrategyId then ticker for a logical flow.

---

## Step 1: Open the Session

Print a session header:
```
╔══════════════════════════════════════════════════════════════╗
║        TARGET CALIBRATION SESSION — {date}                  ║
╚══════════════════════════════════════════════════════════════╝

I'll go through each holding and show you:
  • Current weight vs current target
  • My recommended target with reasoning
  • DCF signal if available

You can:
  ✅ "agree" / "ok" / "keep it"     → accept my recommendation
  🔢 "set it to X%" / "X"           → override with your number
  🔍 "research more" / "research X" → I'll run /research-stock before we decide
  📊 "evaluate it" / "evaluate"     → I'll run /evaluate-stock for a fresh DCF
  ⏭️  "skip" / "next"               → defer, revisit at end
  🔚 "done" / "stop"                → end early, save what we have

Portfolio total: {currentTotal:.1f}% current  |  {targetTotal:.1f}% target (before changes)
{N} holdings to review  ({N_exit} flagged EXIT, {N_initiate} flagged INITIATE)

Let's start.
```

---

## Step 2: Present Each Holding

For each holding in the ledger:

```
─────────────────────────────────────────────────
[{i}/{N}] {TICKER} — {name}
Strategy: {subStrategyId}  |  Role: {role}  |  Action: {action}

  Current:  {currentPct:.2f}%
  Target:   {currentTarget:.2f}%  (drift: {drift:+.2f}%)
  DCF:      {dcfAction} @ {dcfUpside:+.1f}% upside  (or "No valuation")

My recommendation: {recommendedTarget:.2f}%
Reasoning: {one-line reasoning}

Your call → 
```

### Reasoning Logic (how to compute `recommendedTarget` and `reasoning`)

1. **Action = EXIT** (current > 0, target = 0):
   - Recommend 0% unless DCF shows strong BUY
   - Reasoning: "Not in thesis target. If you want to keep it, set a target."

2. **Action = INITIATE** (current = 0, target > 0):
   - Recommend keeping current target as-is, or suggest scaling based on conviction
   - Reasoning: "Thesis target. Not yet purchased. Confirm you still want this."

3. **Action = ACCUMULATE** (ratio < 0.85):
   - Recommend keeping target; note you're underweight
   - Reasoning: "Underweight vs target. Worth confirming you still want {target}%."

4. **Action = TRIM** (ratio > 1.15):
   - Recommend trimming; if no DCF or DCF = SELL, suggest reducing target too
   - If DCF = BUY with strong upside: recommend keeping target, just trim back to it
   - Reasoning: "Overweight. DCF {dcfAction} — {keep target / reduce target}."

5. **Action = MAINTAIN**:
   - Recommend keeping target
   - Reasoning: "On target. Confirm you're still comfortable with {target}%."

6. **USD_CASH or cash positions**:
   - Note it has no thesis target; user decides if they want to set one
   - Reasoning: "Cash. No thesis target. Want to set a target % for cash?"

---

## Step 3: Handle User Responses

After each response, record in the ledger and move to next:

| User says | Action |
|-----------|--------|
| "agree" / "ok" / "yes" / "keep" | `agreedTarget = recommendedTarget`, `decision = AGREED` |
| A number like "8" or "8%" | `agreedTarget = float(X)`, `decision = OVERRIDE` |
| "research more" / "research" | Run stock_research skill for this ticker, then re-present |
| "evaluate" / "dcf" | Run evaluate-stock skill for this ticker, then re-present with new data |
| "skip" / "next" | `decision = DEFERRED`, add to deferred list |
| "exit it" / "close it" / "remove" | `agreedTarget = 0`, `decision = OVERRIDE` |
| "done" / "stop" | End loop, proceed to Step 4 with what we have |
| Any question / discussion | Answer, then re-present the same holding prompt |

**Never move to the next holding until a decision is recorded** (except for "skip").

---

## Step 4: Handle Deferred Holdings

After all holdings reviewed, revisit deferred ones:
```
You skipped {N} holdings: {list}
Let's revisit them now, or say "keep current targets" to leave them unchanged.
```

---

## Step 5: Show Summary + Weight Check

Before writing, show a full summary:

```
╔══════════════════════════════════════════════════════════════╗
║              CALIBRATION SUMMARY                            ║
╚══════════════════════════════════════════════════════════════╝

Changes from this session:
  Ticker   Old Target   New Target   Delta   Decision
  ------   ----------   ----------   -----   --------
  INTC       11.11%       15.00%    +3.89%   OVERRIDE
  CRWV        1.81%        0.00%    -1.81%   OVERRIDE
  ...

Unchanged: {N} holdings

⚠️  Target total: {sum:.2f}%  (must be 100.00%)
```

If total ≠ 100%:
```
The targets sum to {sum:.2f}% — {over/under} by {delta:.2f}%.

Options:
  1. I distribute the {delta:.2f}% proportionally across your MAINTAIN holdings
  2. Tell me which ticker(s) to adjust to make up the difference
  3. You specify the exact adjustment

Which do you prefer?
```

Wait for direction. Recalculate until total = 100.00% (allow ±0.05% floating point tolerance).

---

## Step 6: Write Changes

Once user confirms the summary:

```bash
# Apply all agreed targets in one --set call (auto-normalizes to 100%)
python3 plugins/portfolio-advisor/scripts/update_targets.py \
  --set INTC=15.00 CRWV=0.00 \
  --write --blueprint

# Re-lock no-change positions (normalization may have drifted them above actual)
# Always run this after any batch --set that changes multiple weights
python3 plugins/portfolio-advisor/scripts/update_targets.py \
  --set GOOG=4.98 HUMN=2.86 KOID=2.69 ETHA=3.79 IBIT=2.60 COIN=3.11 CRCL=2.27 \
  --write --blueprint

# Verify actions are clean — no false ACCUMULATE on DCF-negative stocks
python3 plugins/portfolio-advisor/scripts/portfolio_action.py --all \
  --portfolio investment_screener/backend/data/portfolio.json \
  --target investment_screener/backend/data/theses/target-portfolio.json

# Run automated sync verification
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```

The `--blueprint` flag runs `generate_portfolio_blueprint.py --write` which updates **all** table formats in `investment_thesis.md` (Section IV + all enriched early-section tables). No separate blueprint step is needed.

---

## Step 7: Close the Session

```
╔══════════════════════════════════════════════════════════════╗
║            CALIBRATION COMPLETE                             ║
╚══════════════════════════════════════════════════════════════╝

✅ {N} targets updated in target-portfolio.json (v{new_version})
✅ Actions regenerated via portfolio_action.py
✅ investment_thesis.md rebuilt
✅ verify_thesis_sync.py: All synchronization checks passed

Session notes:
  • {N_agreed} agreed with recommendation
  • {N_overridden} overridden by you
  • {N_researched} researched before deciding
  • {N_unchanged} left unchanged

Next steps:
  → Run /rebalance to generate trade orders toward new targets
  → Run /strategic-review if you want to challenge the thesis formula
```

---

## Research / Evaluate Inline Protocol

When user says "research more" for a ticker:
1. Print: `"Running /research-stock {TICKER} — this takes a moment..."`
2. Execute the stock_research skill inline for that ticker
3. Summarise the key findings in 3-5 bullets
4. Re-present the holding card with updated context
5. Record whether the research changed your recommendation

When user says "evaluate" for a ticker:
1. Print: `"Running /evaluate-stock {TICKER} — building DCF model..."`
2. Execute the update_stock_analysis skill inline
3. Show the new fair value + action + upside
4. Re-present the holding card with updated DCF signal
5. Adjust `recommendedTarget` if the DCF materially changes the case

---

## Sources Checked Declaration

At session end:
```
## Sources Checked
- portfolio.json current weights:      [✅ Loaded]
- target-portfolio.json targets:       [✅ Loaded v{N}]
- portfolio_action.py canonical:       [✅ Actions computed]
- DCF valuations (API):                [✅ {N}/{M} available / ⚠️ {K} missing]
- update_thesis.py dry run:            [✅ Passed / ❌ Failed]
- target-portfolio.json written:       [✅ v{N+1} / ❌ Skipped]
- investment_thesis.md rebuilt:        [✅ / ❌]
- verify_thesis_sync.py sync check:    [✅ Passed / ❌ Failed]
```
