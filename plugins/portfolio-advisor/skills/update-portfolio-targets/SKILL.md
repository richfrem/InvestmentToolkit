---
name: update-portfolio-targets
plugin: portfolio-advisor
description: >
  Update target portfolio weights — by pillar (theme) and by holding (stock) —
  in the canonical thesis JSON file. Validates weights sum to 100% before writing.
  Bumps the thesis version and appends a changeLog entry. Aligns changes with the
  investment thesis document and strategic review proposals.
  Trigger phrases: "update target weights", "change target allocation",
  "apply formula changes", "update thesis targets", "adjust pillar weights",
  "set TICKER to X%", "rebalance the formula".
allowed-tools: Bash, Read, Write
---

# Update Portfolio Targets Skill

## Quick Reference
- **Trigger**: "update target weights", "apply formula changes from strategic review", `/update-portfolio-targets`
- **Thesis file**: `investment_screener/backend/data/theses/target_portfolio.json`  (id: `"target-portfolio"`)
- **Thesis doc**: `plugins/portfolio-advisor/references/investment_thesis.md`
- **Update script**: `investment_screener/backend/py_services/update_thesis.py`
- **ADR reference**: `docs/architecture/` — cross-plugin script conventions
- **Chains from**: `strategic-review` skill (after formula proposals are approved by user)
- **Chains into**: `rebalance-portfolio` skill (to execute trades aligned with new targets)

---

## Context: What This File Controls

`thesis.json` is the single source of truth for:
1. **Pillar (theme) target weights** — e.g. "AI Compute" = 43%, "Sovereign Finance" = 18%
2. **Individual holding target weights** — e.g. INTC = 8%, NVDA = 15%
3. **Holding metadata** — role (core/hedge/speculative/reserve), thesis-for-inclusion, thesis breakers
4. **Drift thresholds** — when to alert vs when to rebalance

All health checks (`/api/theses/target-portfolio/health`), drift monitoring, conviction audits, and
rebalance calculations read from this file. Changes here flow immediately into all downstream analysis.

---

## Step 0: Load Current State

```bash
# Print current thesis summary (pillars + holdings + weights)
python3 investment_screener/backend/py_services/update_thesis.py --list
```

Also read the investment thesis document for strategic context:
```bash
head -100 plugins/portfolio-advisor/references/investment_thesis.md
```

Note: The filename `investment_thesis.md` is the canonical thesis doc.
As the thesis evolves, its content is updated in place — the filename remains stable.

---

## Step 1: Establish the Proposed Changes

Changes may come from:
- A recent `strategic-review` session (formula proposals in the review markdown)
- Direct user instruction ("set INTC to 8%")
- Research findings that shift conviction on a position

Confirm with the user **before writing** if the source is a strategic review proposal:
```
📋 Proposed formula changes from {review date}:

Pillars:
  ai-compute:        {old}% → {new}%
  sovereign-finance: {old}% → {new}%
  ...

Holdings:
  INTC:  {old}% → {new}%  (reason: reduced DCF conviction, maintain for SA 13F thesis)
  AVGO:  {old}% → {new}%  (reason: increase to reflect networking moat)
  ...

Total pillar delta: {sum check}  →  target: 100%
Total holding delta: {sum check}  →  target: 100%

Shall I apply these changes?
```

**Always wait for user confirmation before Step 2 when running from a proposal.**
For direct "set X to Y%" instructions, proceed directly.

---

## Step 2: Validate Before Writing (Dry Run)

For single-field changes:
```bash
python3 investment_screener/backend/py_services/update_thesis.py \
  --holding INTC --target 8.0 \
  --note "Strategic review 2026-05-02: reduce INTC weight, DCF SELL but SA thesis intact" \
  --dry-run
```

For batch changes from a strategic review, write a patch file first:
```bash
cat > /tmp/formula_patch.json << 'EOF'
{
  "pillars": [
    {"id": "ai-compute", "targetWeight": 43.0},
    {"id": "sovereign-finance", "targetWeight": 18.0}
  ],
  "holdings": [
    {"ticker": "INTC",  "targetWeight": 8.0},
    {"ticker": "AVGO",  "targetWeight": 8.0},
    {"ticker": "ZS",    "targetWeight": 4.5},
    {"ticker": "CRWD",  "targetWeight": 0.5},
    {"ticker": "CRWV",  "targetWeight": 3.5}
  ]
}
EOF

python3 investment_screener/backend/py_services/update_thesis.py \
  --patch /tmp/formula_patch.json \
  --note "Strategic review 2026-05-02: formula v7.4 approved" \
  --dry-run
```

**Review the printed diff carefully.** Check:
- Pillar weights sum to 100%
- Holding weights sum to 100%
- No unintended changes

---

## Step 3: Apply the Changes

If dry run looks correct, remove `--dry-run`:
```bash
python3 investment_screener/backend/py_services/update_thesis.py \
  --patch /tmp/formula_patch.json \
  --note "Strategic review 2026-05-02: formula v7.4 approved"
```

The script will:
1. Validate weight sums (exits with error if invalid)
2. Increment `version` in the JSON
3. Append a `changeLog` entry with date and note
4. Atomically replace the file (write to `.tmp`, then `os.replace`)

---

## Step 4: Verify via API

```bash
# Confirm thesis loaded correctly
curl -s http://localhost:3001/api/theses/target-portfolio | python3 -c "
import json, sys
t = json.load(sys.stdin)
print(f'Name: {t[\"name\"]}  version: {t[\"version\"]}')
print(f'Pillars: {len(t[\"pillars\"])}  Holdings: {len(t[\"holdings\"])}')
for p in sorted(t['pillars'], key=lambda x: -x['targetWeight']):
    print(f'  {p[\"id\"]:<32} {p[\"targetWeight\"]:>6.2f}%')
"

# Run health check to verify drift is recalculated against new targets
curl -s http://localhost:3001/api/theses/target-portfolio/health | python3 -c "
import json, sys
h = json.load(sys.stdin)
print(f'Health check at: {h[\"analyzedAt\"]}')
alerts = h.get('alerts', [])
critical = [a for a in alerts if a['severity'] == 'CRITICAL']
warnings = [a for a in alerts if a['severity'] == 'WARNING']
print(f'Alerts: {len(critical)} CRITICAL, {len(warnings)} WARNING')
for a in critical[:5]:
    print(f'  ⛔ {a[\"message\"]}')
for a in warnings[:5]:
    print(f'  ⚠️  {a[\"message\"]}')
"
```

---

## Step 5: Update Thesis Document If Needed

If the formula change represents a meaningful strategic shift, update the thesis doc:

```bash
# The thesis doc is the human-readable narrative behind the numbers
# Edit the relevant section in:
#   plugins/portfolio-advisor/references/investment_thesis.md
#
# Typical updates:
# - Pillar weight rationale (why X% to AI Compute vs Y% to Sovereign Finance)
# - New/removed holdings and their thesis-for-inclusion
# - Revised thesis breakers for any holding
# - Version line at top: "Version: 7.4"
```

---

## Step 6: Chain to Rebalance (Optional)

If the user wants to execute trades to restore alignment with the new targets:
```
Formula updated to v{N}. Current portfolio has the following drift against new targets:
  {list of CRITICAL drift items from health check}

Would you like me to run /rebalance to generate the trade list?
```

Only chain to `/rebalance` if the user confirms.

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Pillar weights sum to X% (must be 100%)` | Partial update — other pillars need offsetting adjustment | Adjust compensating pillars to balance |
| `Holding weights sum to X%` | Same as above for holdings | Adjust other holdings |
| `pillar id 'X' not found` | Typo in pillar id | Run `--list` to see valid ids |
| `ticker 'X' not found` | Ticker not in thesis holdings | Add to holdings first (manual JSON edit) |

---

## Adding a New Holding

New holdings must be added manually to `thesis.json` until an `add-holding` subcommand is built.
When adding:
1. Choose the correct `pillarId` (run `--list` to see ids)
2. Set a realistic initial `targetWeight` (reduce another holding proportionally)
3. Add `thesisForInclusion` — why does this stock belong in the active investment thesis portfolio?
4. Optionally add 1-3 `thesisBreakers` — conditions that would force a full exit
5. Validate with `--dry-run` after editing the JSON directly
6. Run `/evaluate-stock {TICKER}` to generate the first AI valuation

---

## Sources Checked Declaration
```
## Sources Checked
- thesis.json current state: [✅ Loaded v{N} / ❌ File missing]
- Thesis doc context:        [✅ Reviewed / ⚠️ Skipped]
- Dry run validation:        [✅ Passed / ❌ Failed — weights don't sum to 100%]
- Applied changes:           [✅ Written v{N+1} / ❌ Skipped (dry run only)]
- API health check:          [✅ Verified / ⚠️ Backend not running]
- Thesis doc updated:        [✅ Yes / ⚠️ No strategic shift, doc unchanged]
```
