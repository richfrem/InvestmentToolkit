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

## 🇨🇦 Account Selection Heuristics (TFSA vs RRSP)

When surfacing trade recommendations, include an account suggestion based on Canadian tax optimization rules:

| Holding Type | Preferred Account | Reason |
|-------------|-------------------|--------|
| **High-growth equities** (tech, AI, speculative) | **TFSA** | Tax-free compounding on capital gains |
| **USD dividend payers** (REITs, ETFs with US dividends) | **RRSP** | IRS/CRA treaty exempts RRSP from 15% US withholding tax |
| **Canadian dividend stocks** | TFSA or non-reg | Dividend tax credit applies outside RRSP; TFSA shelters growth |
| **Bond ETFs / income funds** | **RRSP** | Shields interest income (fully taxable) from annual tax |
| **Speculative / high-volatility** | **TFSA** | Losses in TFSA don't reduce contribution room (unlike RRSP) |

Format the suggestion as a one-line note per trade:
```
→ Suggested: TFSA (growth equity — tax-free compounding on gains)
```

If the current portfolio.json account data shows the holding is already in the "wrong" account, surface it as a soft advisory — never block the trade.

---

## ⚠️ No-Trade Conditions

Block rebalance recommendations (surface as `PAUSED` state) when:

- `DATA_STALE` — portfolio.json > 60 min old. State: *"Run `/tv-portfolio-sync` first — rebalance math needs live prices."*
- `TARGETS_INVALID` — targets don't sum to 100% ± 0.5%. State: *"Run `/calibrate-targets` first — targets sum to {X}%."*
- `MISSING_VALUATIONS` — more than 30% of thesis tickers have no DCF projection. State: *"Too many holdings unvalued — run `/evaluate-stock` for the missing ones before rebalancing."*
- `EARNINGS_SEASON` — 3+ holdings have earnings within 7 days. Surface a list; let user decide whether to proceed.
- `THESIS_OUT_OF_SYNC` — target-portfolio.json, investment_thesis.md, or active projections are not in synchronization. State: *"Run `verify_thesis_sync.py` to check for and fix synchronization errors before rebalancing."*

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

## Step 1: Load Current State
```bash
# Load thesis + health check
API_TOKEN=$(cat .runtime/api-token)
curl -s -H "Authorization: Bearer $API_TOKEN" http://localhost:3001/api/theses/{THESIS_ID}/health | python3 -m json.tool

# Load valuations for all holdings
python3 << 'EOF'
import subprocess, json

token = open('.runtime/api-token').read().strip()
thesis_tickers = []  # populate from health check output
valuations = {}
missing = []

for ticker in thesis_tickers:
    r = subprocess.run(['curl','-s','-H',f'Authorization: Bearer {token}',f'http://localhost:3001/api/projections/{ticker}'],
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
# Assess capital per account — sells and buys must be sequenced within each account
cash_holding = get_holding_by_pillar('cash')
capital_from_trims = sum(trim_trades_value)
available_capital = cash_holding.value + capital_from_trims

# Per-account breakdown (use portfolio.json account field if present)
# If account field is missing/unknown, default to TFSA for all tech/AI holdings
tfsa_cash  = cash_held_in_tfsa   # from portfolio.json USD_CASH + TFSA sell proceeds
rrsp_cash  = cash_held_in_rrsp   # from portfolio.json RRSP cash + RRSP sell proceeds
```

**Capital sequencing rule**: Sells in account X fund buys in account X.
- TFSA sells → available for TFSA buys
- RRSP sells → available for RRSP buys
- Do NOT assume proceeds from one account fund buys in another

If insufficient capital to restore all underweights → prioritize by:
1. BUY-rated + largest negative drift first (per account)
2. HOLD-rated second
3. Leave SELL-rated underweights as `skippedRestores`
4. If still over budget per account → defer lowest-upside buys and tell the user explicitly

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
- Thesis synchronization: [✅ verify_thesis_sync.py passed / ❌ Failed/Out of sync]

## Sources Unavailable
- [any failures or missing data]
```
