---
trigger: /review-portfolio
args:
  - name: thesis_id
    required: false
---

# Review Portfolio Alignment
This workflow helps you assess your portfolio's health and alignment with your strategic thesis.

## Prerequisites
- [ ] Backend running on `http://localhost:3001`.
- [ ] `portfolio.json` populated with holdings.
- [ ] `twin_revolutions.json` (or other thesis) loaded.

## 1. Select Thesis
We need to know which thesis to evaluate against.

```bash
# List available theses
curl -s http://localhost:3001/api/theses | jq '.[] | {id, name}'
```

Please copy the `id` of the thesis you want to check (e.g. `a1b2c3d4-e5f6-7890-abcd-ef1234567890` for "Twin Revolutions").

## 2. Run Health Check
Execute the health check analysis.

```bash
# Replace YOUR_THESIS_ID with the ID from step 1
THESIS_ID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"

curl -s "http://localhost:3001/api/theses/$THESIS_ID/health" | jq '.'
```

## 3. Strategic Check (Crucial)
**Before acting**, ask yourself:
> "Is this drift a failure of discipline, or a change in conviction?"

- **Scenario A**: "I still love INTC, but it dropped 20%." -> **Rebalance (Buy)**.
- **Scenario B**: "I lost faith in INTC." -> **Update Thesis (Sell/Remove)**.

## 4. Analyze Results
### Summary
- **Overall Status**: Look at `summary.overallStatus`.
- **Total Drift**: Check `summary.totalDriftScore`.

### Alerts
Review the `alerts` array for `CRITICAL` warnings. These require immediate attention.

### Holding Details
Inspect `holdingHealth` for individual drift percentages.

## 4. Next Steps
- If Status is `CRITICAL`: Run the optimization workflow (coming soon).
- If Valuation Missing: Run Tool A on the specific ticker using the "Stock Valuation" workflow.
