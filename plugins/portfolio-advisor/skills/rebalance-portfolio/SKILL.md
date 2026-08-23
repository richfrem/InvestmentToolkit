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
- **Engine**: `investment_screener/backend/py_services/rebalancer.py --pretty` ← computes `data/rebalance_plan.json`

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

All math for P&L and position sizing must use the **exact values from the data files** — never round or estimate intermediate calculations. Share counts are pre-computed by `rebalancer.py` (`orders[].shares`, drift-based sizing — not a flat `target_value_USD / current_price` formula); this table is a human-side sanity check to apply on top of the engine's output, not a formula to re-derive shares from scratch.

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
computed by `rebalancer.py` from the `portfolio_policy` table in `domain_model.sqlite` (Wave 5E —
formerly `investment_screener/backend/data/account_policy.json`, now archived) — each
order in the plan already carries its `"account"` field. Use
`python3 investment_screener/backend/py_services/update_portfolio_policy.py --set FIELD=VALUE --write`
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

## Step 1b: Risk Officer Review

Dispatch `risk-officer-agent` (Mode 1: real enforcement) via the Agent tool. It runs
`risk_officer.py --pretty` and returns vetoed vs approved orders.

- Any order in `vetoedOrders` is **removed** from the trade plan presented in Step 5 and
  instead rendered in a new "⛔ Vetoed by Risk Officer" section (same table style as the
  existing "Skipped Restores" section in Step 5), each row listing its `vetoReasons`.
- If the user chooses to override a veto, that override is handled entirely inside
  `risk-officer-agent`'s own conversation (one order at a time, logged via
  `risk_officer.py --log-override`) — once overridden, the order rejoins the set of orders
  this skill treats as approved for the rest of the flow (Step 5 table, Step 5b posting,
  Step 6 confirm+log).
- If `risk_officer.py` reports `"status": "no_plan"` or `"plan_blocked"`, or fails outright,
  degrade gracefully: show a one-line warning and proceed with the unreviewed plan — same
  degrade pattern E1/C2 already use in `daily_brief.py` when their own engines are
  unavailable.

---

## Step 1c: Red Team Review

Dispatch `red-team-agent` via the Agent tool, passing the post-veto-filtering order set (what
will actually be proposed in Step 5, after Step 1b's exclusions and any overrides). Print its
"Objections" and "What would change my mind" sections to the user, directly above Step 5's
trade table. This step is **mandatory, every `/rebalance` run** — never skipped, never made
conditional on plan size or user request.

---

## Step 5: Present Trade Recommendations
```
**Rebalance Recommendation — {THESIS_NAME}**
*{N} holdings out of band → {M} orders proposed*

📊 Trade Plan ({M} trades):
| # | Ticker | Action | Shares | Account | Rationale                                  |
|---|--------|--------|--------|---------|---------------------------------------------|
| 1 | CRWD   | SELL   | 15     | TFSA    | Out of band: +3.8pp vs 2.0pp band            |
| 2 | ZS     | BUY    | 8      | TFSA    | Out of band: −2.1pp vs 2.0pp band            |
| 3 | VST    | BUY    | 12     | RRSP    | Out of band: −1.8pp vs 2.0pp band            |

⛔ Skipped Restores (buy blocked by valuation gate, entry price, or standing decision — NOT buying):
| Ticker | Reason                                                                                          |
|--------|--------------------------------------------------------------------------------------------------|
| INTC   | SELL-rated — not restoring                                                                        |
| AVGO   | Standing decision (USER): Wait for FY26 guidance. Signal stands but no trade proposed without your direction. |

💡 {X}/{M} orders carry risk-gate or thesis-breaker warnings (`riskGateWarnings` / `breakerWarnings` non-empty)

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

**Per-account capital check**: Per-account capital sequencing — including same-account
PSU-U.TO funding sells when a buy's target account can't cover its cost — is already resolved
inside `rebalancer.py`'s `compute_account_routing()`. Every order in `orders[]` is already
capital-aware; when a buy needs more cash than its target account has, the engine inserts a
synthetic PSU-U.TO sell order (`rationale: "Same-account funding for {ticker} buy"`) directly
ahead of that buy in the same account. There is nothing to manually compute or sequence here.

Note: if even the PSU-U.TO funding sell can't fully cover a buy's cost, the engine does **not**
defer or drop the buy — it still emits the order as-is (unfunded shortfall included). Don't
invent a "defer lowest-priority buys by DCF upside" step; that logic doesn't exist in the engine.
If you see an order whose cost looks larger than the account's available cash even after any
PSU-U.TO funding sell in the plan, flag it to the user rather than silently dropping or
re-sequencing it yourself.

**Settlement note**: Canadian equities on Broker settle T+1. If you're selling today to fund a buy today, confirm the account has sufficient *settled* buying power before submitting the buy. If in doubt, submit the sell first and wait for settlement confirmation before submitting buys.

**Array ordering rule**: `suggestions` array must be ordered:
1. All SELL entries first
2. All BUY entries second

`orders[]` in `rebalance_plan.json` is already sequenced this way (sells before buys) by
`rebalancer.py` — post them in the order the engine produced, don't re-sort by upside or
conviction; the engine has no such field to sort by.

### Multi-Account Rules

**SELLS**: Check `portfolio.json` — if the ticker is held in multiple accounts (e.g., ZS in both TFSA and RRSP), create a separate entry for each account using that account's actual share count.

**BUYS**: `rebalancer.py` already resolves each buy to exactly ONE account (via
`portfolio_policy.account_preference_rules_json`, Wave 5E — formerly `account_policy.json`'s
`accountPreferenceRules`) and puts that single account directly on the
order. Post exactly one trade-log entry per buy order, using that order's own `account` field —
never fabricate a second mirrored entry in another account.

Example — buying 6 shares of NVDA (order's `account` field is `"TFSA"`):
```json
{ "ticker": "NVDA", "action": "buy", "shares": 6, "account": "TFSA", ... }
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
        "notes": "Out of band: +3.8pp vs 2.0pp band",
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
        "notes": "Out of band: -2.1pp vs 2.0pp band",
        "source": "rebalance"
      }
    ]
  }'
```

### Rules
- Post ALL proposed trades (only actionable buys/sells — not drift-skips)
- Set `notes` to the order's own `rationale` field from `rebalance_plan.json` — don't invent
  FV-gap percentages or upside figures that aren't part of `orders[]`'s real shape
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
   Note: {rationale}
   ```

---

## Sources Checked Declaration
```
## Sources Checked
- Rebalance Engine: [✅ rebalancer.py --pretty ran successfully / ❌ Failed — {error}]
- Blocked Reason: [✅ null — orders generated / ⛔ {blockedReason value} — no orders]
  (MISSING_VALUATIONS is one possible value here — it blocks the whole run, not a per-ticker list;
  there is no per-ticker "N/M holdings have valuations" field in `rebalance_plan.json`.)
- Thesis synchronization: [✅ verify_thesis_sync.py passed / ❌ Failed/Out of sync]

## Sources Unavailable
- [any failures or missing data]
```
