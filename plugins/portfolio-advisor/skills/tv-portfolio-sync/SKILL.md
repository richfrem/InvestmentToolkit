---
name: tv_portfolio_sync
plugin: portfolio-advisor
description: >
  Sync portfolio.json from TradingView's live broker panel (all accounts: TFSA,
  RRSP, Cash) via CDP. Scrapes positions and balances, shows a diff vs the
  current portfolio.json (new positions, closed positions, qty/price changes),
  and waits for explicit CONFIRM before writing. Works with any TradingView-
  connected broker — no Questrade API credentials required.
allowed-tools: Bash, Read, Write
---

# TV Portfolio Sync Skill

## Quick Reference
- **Trigger**: `/tv-portfolio-sync`, "sync portfolio from TradingView", "update portfolio from TV"
- **Execution**: `fetch_broker_data.py --snapshot` → all accounts → diff → HITL → merge
- **Output**: Updates `portfolio.json` (preserves thesis/pillar/price fields)
- **Requires**: TradingView Desktop running, broker panel connected

---

## Hard Rules

- **NEVER write to `portfolio.json` without explicit CONFIRM from the user**
- If TV returns 0 positions, stop and tell the user TradingView is not connected
- Show the full diff before asking for CONFIRM — never skip the review step
- `portfolio.json` is gitignored user data — treat it as sacred

---

## Step 1: Fetch TV Snapshot (All Accounts)

```bash
python3 investment_screener/backend/py_services/fetch_broker_data.py --snapshot
```

This reads ALL accounts (TFSA, RRSP, Cash) from TradingView's broker panel.
Output is written to `portfolio_tv.json` and also printed as JSON.

Check the output:
- `positions` array length > 0 — TV data is live
- `accounts` array — all 3 accounts should be present (CASH, TFSA, RRSP)
- If `positions` is empty → tell user TradingView is not connected with a broker

If TradingView is not connected, tell the user:
> "TradingView isn't showing any broker positions. Make sure TradingView Desktop is running and you're logged into your broker account in the Questrade panel. Then try again."

---

## Step 2: Load Existing Portfolio

```bash
cat investment_screener/backend/data/portfolio.json
```

Read the current portfolio.json to generate the diff.

---

## Step 3: Generate and Display Diff

Compare TV snapshot (aggregated by symbol across all accounts) against portfolio.json.

Aggregate TV positions by symbol first (same stock can appear in TFSA + RRSP):

```python
agg = {}
for pos in snapshot["positions"]:
    sym = pos["symbol"]
    agg[sym] = agg.get(sym, 0) + pos["quantity"]
```

Display the diff in this format:

```
╔══════════════════════════════════════════════════════╗
║       TradingView → portfolio.json Sync Preview      ║
╠══════════════════════════════════════════════════════╣
║  TV positions:        31 (across TFSA + RRSP + Cash) ║
║  Current portfolio:   32 symbols                     ║
║  ✓ Unchanged:         28                             ║
║  + New positions:     1                              ║
║  ✎ Qty/price changes: 2                              ║
║  − Removed positions: 1                              ║
╚══════════════════════════════════════════════════════╝

+ NEW POSITIONS (will be added):
  NEWCO    qty=5   avgFill=$123.45

✎ CHANGED (qty or avg fill price):
  AMD      qty: 2 → 3     avgFill: $210.00 → $220.35
  NVDA     book_price: $185.00 → $199.59

− REMOVED (in portfolio.json but not in TV — position closed):
  OLDCO    qty=10

✓ PRESERVED (no change needed):
  BTDR, CEG, COHR, COIN, CORZ, ...
```

Note: `USD_CASH` is always excluded from the TV diff (TV tracks cash as a balance field, not a position).

---

## Step 4: Ask for CONFIRM

After showing the diff:

> "This will update **portfolio.json** with the TradingView data shown above. Fields like `thesis`, `pillar`, `price`, and `sector` are preserved from the existing portfolio — only `shares` and `book_price` are updated from TV. Type **CONFIRM** to apply, or tell me what to change."

Wait for exact **CONFIRM** (case-insensitive). Do not proceed on "yes", "ok", "sure".

---

## Step 5: Merge and Write

Merge TV data into portfolio.json:
- For existing positions: update `shares` = TV quantity, `book_price` = TV avgFillPrice; preserve all other fields
- For new positions: add with TV data only (thesis/pillar/price will be populated on next valuation run)
- For removed positions: remove from portfolio.json (unless it's `USD_CASH`)

Use the `/api/portfolio/sync-tv` backend endpoint, or apply the merge inline:

```python
# Merge approach (inline):
merged = []
tv_map = {}  # symbol → {quantity, avgFillPrice}
for pos in snapshot["positions"]:
    sym = pos["symbol"]
    tv_map[sym] = tv_map.get(sym, {"quantity": 0, "avgFillPrice": pos["avgFillPrice"]})
    tv_map[sym]["quantity"] += pos["quantity"]

existing_map = {item["symbol"]: item for item in portfolio if item.get("symbol") != "USD_CASH"}
usd_cash = next((item for item in portfolio if item.get("symbol") == "USD_CASH"), None)

for sym, tv in tv_map.items():
    if sym in existing_map:
        item = dict(existing_map[sym])
        item["shares"] = tv["quantity"]
        item["book_price"] = tv["avgFillPrice"]
        merged.append(item)
    else:
        merged.append({"symbol": sym, "shares": tv["quantity"], "book_price": tv["avgFillPrice"]})

if usd_cash:
    merged.append(usd_cash)  # preserve cash balance entry

# Write
import json
with open("investment_screener/backend/data/portfolio.json", "w") as f:
    json.dump(merged, f, indent=2)
```

---

## Step 6: Confirm Success

After writing:

> "✓ portfolio.json updated — {N} positions from TradingView (TFSA + RRSP). {added} added, {removed} removed, {changed} changed. The `/api/portfolio` endpoint will serve this data on next request."

---

## Example Flow

```
User: /tv-portfolio-sync
Agent: Fetching TV snapshot across all accounts...
       [runs fetch_broker_data.py --snapshot]
       [shows diff — 31 TV positions, 1 changed, 0 added, 0 removed]

       This will update portfolio.json with TV data. Type CONFIRM to apply.

User: CONFIRM

Agent: ✓ portfolio.json updated — 31 positions. 0 added, 0 removed, 1 changed (AMD shares: 2 → 3).
```

---

## Error Handling

| Error | Action |
|-------|--------|
| 0 positions returned | TV not connected — tell user to open TradingView Desktop with broker |
| Node.js error (CDP timeout) | Check TradingView is on the broker panel view, retry |
| portfolio.json missing | Write new file from TV data (no existing data to merge) |
| Account switch timeout for CASH | Normal — Cash account has no equity positions; skip silently |
