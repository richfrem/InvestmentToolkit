---
name: rebalance_portfolio
plugin: portfolio-advisor
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

## ⚠️ Position Sizing Sanity Checks

Apply before presenting any trade recommendation:

| Check | Rule | Action on Breach |
|-------|------|-----------------|
| Max single-position | No holding may exceed **15%** of portfolio after trade | Cap trade size; note in output |
| Max pillar concentration | No pillar may exceed **40%** after trade | Warn; suggest cross-pillar trim |
| Min liquidity | Don't recommend trades < $200 (transaction cost not worth it) | Merge with adjacent trade or skip |
| Cash floor | Maintain ≥ 2% portfolio in cash/USD after all buys | Reduce buy sizes proportionally |
| Single-session cap | Don't recommend more than **$15,000** total buys in one rebalance session | Split into two sessions; flag to user |

All math for P&L and position sizing must use the **exact values from the data files** — never round or estimate intermediate calculations. Derive size in shares as: `shares = floor(target_value_USD / current_price)`.

---

## ⚠️ Audit Log Awareness — Check Before Recommending

Before generating any trade recommendations, check today's order audit log to avoid double-recommending trades already placed this session:

```bash
API_TOKEN=$(cat .runtime/api-token)
curl -s -H "Authorization: Bearer $API_TOKEN" http://localhost:3001/api/trading/audit/today | python3 -m json.tool
```

For each ticker that already has a `ORDER_SUBMITTED` event today:
- Suppress the rebalance recommendation for that ticker
- Add a note: `"Order placed today — verify fill before adding more"`

If the audit endpoint is unreachable, proceed but prepend a warning:
> ⚠️ Could not check today's audit log — verify no duplicate orders before executing.

---

## 🇨🇦 Account Selection

Account routing (TFSA/RRSP/Cash preference rules, PSU-U.TO same-account funding rule) is now
computed by `rebalancer.py` from `investment_screener/backend/data/account_policy.json` — each
order in the plan already carries its `"account"` field. Edit `account_policy.json` directly
if the routing rules need to change; no skill-side heuristic table to keep in sync anymore.

---

## ⚠️ No-Trade Conditions

`rebalancer.py`'s `blockedReason` field covers `DATA_STALE`, `TARGETS_INVALID`, and
`MISSING_VALUATIONS` computationally — if `data/rebalance_plan.json`'s `blockedReason` is
non-null, state it verbatim and stop; no orders were generated.

Two conditions stay your judgment call, not a hard block — check before presenting the plan:
- `EARNINGS_SEASON` — 3+ holdings have earnings within 7 days. Surface a list; let the user
  decide whether to proceed.
- `THESIS_OUT_OF_SYNC` — run `verify_thesis_sync.py`; if it fails, tell the user to fix sync
  before rebalancing.

---

## Data Freshness Provenance

Every rebalance output must include a provenance line:

> "Data: portfolio.json at {timestamp} ({source}) · targets from target-portfolio.json v{version} · DCF projections: {N}/{M} holdings"

If source is `cache` (no recent sync): prepend ⚠️ and recommend sync before any trades.

---

## ⚠️ Verify Targets Before Rebalancing
Always confirm targets sum to 100% and reflect the latest agreed weights before generating trades.
If targets need adjustment, use `update_targets.py` first:
```bash
# Review current targets:
python3 plugins/portfolio-advisor/scripts/update_targets.py --show

# Adjust if needed (normalizes + regenerates blueprint automatically):
python3 plugins/portfolio-advisor/scripts/update_targets.py --set TICKER=X.X --write --blueprint

# Run automated sync verification:
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```

---

## Step 1: Run the Rebalancer Engine

```bash
python3 investment_screener/backend/py_services/rebalancer.py --pretty
```

This computes drift bands, candidate orders (with the EXIT/SELL-rated, targetEntryPrice, and
standingDecision hard-rule exclusions already applied), account routing (real per-account
data when available, heuristic TFSA/RRSP mirror otherwise), capital-gains estimates for any
Cash-account sells, risk-budget warnings against `risk_snapshot.json`, and thesis-breaker
warnings against `thesis_breaker_state.json` — then writes `data/rebalance_plan.json`.

If `blockedReason` is non-null, state it verbatim and stop (see No-Trade Conditions above).

Read `data/rebalance_plan.json` for the rest of this skill's steps — its `orders[]` array is
already sequenced sells-before-buys, per-account.

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

Under any order row with non-empty `riskGateWarnings` or `breakerWarnings`, render:
```
   ⚠️ {warning text}
```
one line per warning string, before moving to the next order row.

> ⚠️ **Recap Before Execute**: Always confirm individual trades with the user before finalizing.
> Never output "execute all" language. Each trade confirmation is explicit.

---

## Step 5b: Post Suggestions to Trade Log

After presenting the trade plan (Step 5), immediately post ALL proposed trades to the trade log as `suggested` entries. The endpoint accepts a batch — create **one entry per account per ticker**.

### ⚠️ Sequencing Rule — Sells Before Buys

**ALWAYS post sells before buys in the `suggestions` array.** The Trade Log displays entries in order, and the user executes them top-to-bottom. Buys that depend on sell proceeds will fail if submitted first.

**Per-account capital check (run before building the suggestions array):**

```python
# Compute available buying power per account separately
# Available = current cash in account + proceeds from all sells in that account

account_cash = {}  # populated from portfolio.json — USD_CASH split proportionally
                   # If account data unavailable, treat all cash as TFSA

for account in ['TFSA', 'RRSP']:
    cash = account_cash.get(account, 0)
    sell_proceeds = sum(s['shares'] * s['price'] for s in sells if s['account'] == account)
    total_available = cash + sell_proceeds
    buy_cost = sum(b['shares'] * b['price'] for b in buys if b['account'] == account)
    
    if buy_cost > total_available:
        # Flag which buys to defer — prioritize by DCF upside descending
        # Remove lowest-priority buys until buy_cost <= total_available
        # Mention deferred buys explicitly to user:
        print(f"⚠️ {account}: buys (${buy_cost:.0f}) exceed available capital (${total_available:.0f}). "
              f"Deferred: {[b['ticker'] for b in deferred]}")
```

**Settlement note**: Canadian equities on Questrade settle T+1. If you're selling today to fund a buy today, confirm the account has sufficient *settled* buying power before submitting the buy. If in doubt, submit the sell first and wait for settlement confirmation before submitting buys.

**Array ordering rule**: `suggestions` array must be ordered:
1. All SELL entries first (sorted by account: TFSA sells → RRSP sells)
2. All BUY entries second (sorted by DCF upside descending — highest-conviction buys first)

### Multi-Account Rules

**SELLS**: Check `portfolio.json` — if the ticker is held in multiple accounts (e.g., ZS in both TFSA and RRSP), create a separate entry for each account using that account's actual share count.

**BUYS**: Create two entries — one per account. The user mirrors buys across both accounts with proportional sizing:
- **TFSA** (main, larger account): full proposed share count
- **RRSP** (smaller account): approximately 1/3 the TFSA share count (round down, minimum 1)
- Use the TFSA/RRSP heuristic table to pick which account is "primary" for the asset type, but always create both entries.

Example — buying 6 shares of NVDA:
```json
{ "ticker": "NVDA", "action": "buy", "shares": 6, "account": "TFSA", ... },
{ "ticker": "NVDA", "action": "buy", "shares": 2, "account": "RRSP", ... }
```

### API Call

```bash
API_TOKEN=$(cat .runtime/api-token)
curl -s -X POST http://localhost:3001/api/trading/log/suggest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{
    "suggestions": [
      {
        "ticker": "CRWD",
        "action": "sell",
        "shares": 15,
        "price": 0,
        "account": "TFSA",
        "orderType": "market",
        "date": "'"$(date +%Y-%m-%d)"'",
        "notes": "Drift: +3.8% overweight · SELL-rated (−66% FV gap)",
        "source": "rebalance"
      },
      {
        "ticker": "NVDA",
        "action": "buy",
        "shares": 6,
        "price": 0,
        "account": "TFSA",
        "orderType": "market",
        "date": "'"$(date +%Y-%m-%d)"'",
        "notes": "Underweight +1.2% · BUY-rated (+82% upside)",
        "source": "rebalance"
      },
      {
        "ticker": "NVDA",
        "action": "buy",
        "shares": 2,
        "price": 0,
        "account": "RRSP",
        "orderType": "market",
        "date": "'"$(date +%Y-%m-%d)"'",
        "notes": "Underweight +1.2% · BUY-rated (+82% upside) — RRSP mirror (1/3)",
        "source": "rebalance"
      }
    ]
  }'
```

### Rules
- Post ALL proposed trades (only actionable buys/sells — not drift-skips)
- Set `price: 0` (fill price unknown at planning time); set `limitPrice` if suggesting a limit order
- Set `source: "rebalance"` always
- If the endpoint is unreachable (backend offline), proceed silently — do not block the recommendation

After posting, tell the user:
> "These trades have been added to your Trade Log (**Planned** tab) — {N} entries across {A} accounts. Open **Trade Log** in the sidebar to review and execute them one at a time."

---

## Step 6: Confirm + Log Each Trade
For each proposed trade:
1. Present: *"Trade {N}: {ACTION} {shares} shares of {TICKER} at ~${price} — {rationale}.
   {warning lines, if any}. Confirm?"*
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
- Thesis synchronization: [✅ verify_thesis_sync.py passed / ❌ Failed/Out of sync]

## Sources Unavailable
- [any failures or missing data]
```
