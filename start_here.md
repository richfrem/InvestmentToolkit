# Session Start Briefing — InvestmentToolkit
_Last updated: 2026-06-04 | Thesis v9.4 | Portfolio ~$34,643 USD_

> **Read this first at the start of every new session.**
> Run `/tv-portfolio-sync` to refresh portfolio.json, then `/x-news-sweep` if it's a new trading day.

---

## 📊 Portfolio Snapshot

| | Value | % |
|--|-------|---|
| Total equity | ~$34,643 | 100% |
| USD Cash (raw) | $2,663 | 7.7% |
| PSU-U.TO (56sh) | $5,601 | 16.2% |
| **Cash + equiv** | **$8,264** | **23.9%** |

**Thesis:** Investment Thesis v9.4 · `investment_screener/backend/data/theses/target-portfolio.json`

---

## 🔴 Pending Decisions / Open Items

### 1. Dashboard: Show Entry Prices in Recommendations Table ← **PRIORITY TASK**
The modal currently shows `ACCUMULATE`, `INITIATE`, `TRIM` etc. but **not the target entry price**.
`targetEntryPrice` is now a first-class field in `target-portfolio.json` (added 2026-06-04).

**What needs building:**
- `generate_review_json.py` → include `targetEntryPrice` in the per-holding JSON output
- `InvestmentThesisModal.tsx` (or equivalent frontend component) → display "ACCUMULATE @ $X" instead of just "ACCUMULATE"
- The table column should show: `Action | Entry Price` — e.g. "ACCUMULATE @ $210" for NBIS
- If `targetEntryPrice` is null → show "—" or "at market"

**Only SNDK has a price set so far ($1,350).**
After the dashboard is wired up, run a pass to set entry prices for all ACCUMULATE positions.
Use formula as a starting point: `min(dcf_fair_value * 0.85, current_price * 0.85)` — then adjust per TA.

### 2. GTC Automation for Limit Orders ← **TV CDP BUG**
`/place-order` places limit orders as **Day** duration by default.
TradingView's "Extra Settings → Time in force" dropdown opens correctly via CDP but the
"Good till cancelled" option text isn't found (the dropdown uses fixed-position elements
that escape standard visibility checks).

**Where to fix:** `tradingview-cdp/core/trading.js` → `setGoodTillCancelled()`
The `clickDayAndSnapshot()` diagnostic shows the dropdown opens; the GTC option text
needs a position:fixed-aware selector or coordinate-based click.

**Workaround until fixed:** After placing a GTC limit, manually change duration in
TradingView broker panel → Orders tab.

### 3. Active GTC Limit Order
- **CBRS @ $185 TFSA** — lock-up dip target (Nov 2026). User manually set to GTC on 2026-06-01.
  Do not cancel unless user instructs.

### 4. PSU-U.TO Target Reconciliation
- **Actual: 16.2%** vs **Target: 11.9%** → TRIM signal of ~4.3pp
- User has NOT instructed a trim — PSU is their HISA/cash reserve, they're comfortable overweight
- Do not prompt to trim PSU unless user raises it

---

## 📈 Current Positions & Key Notes

| Ticker | Actual% | Target% | Action | Entry Price | Notes |
|--------|---------|---------|--------|-------------|-------|
| PSU-U.TO | 16.2% | 11.9% | HOLD | — | HISA cash equiv, ~$100/sh, monthly dividend |
| CORZ | 3.7% | 8.4% | ACCUMULATE | — | SA/DCF conflict, allowlisted |
| PANW | 4.0% | 5.9% | ACCUMULATE | — | Q3 FY2026 beat, AI cyber |
| CRWV | 3.7% | 5.5% | ACCUMULATE | — | Vera Rubin, $100B backlog |
| NBIS | 2.1% | 5.5% | ACCUMULATE | — | SA LP 5.6% stake, DCF BUY +100% |
| BE | 4.8% | 5.4% | MAINTAIN | — | $2.6B NBIS fuel cell deal |
| SNDK | 4.2% | 3.7% | MAINTAIN | **$1,350** | Do NOT add above $1,350. DCF FV $1,982, but was valued at $1,333 — real upside at current price only ~14%. 0.8 shares held. |
| CEG | 2.5% | 3.8% | HOLD | — | Underwater −27%, break-even ~$364. Hold, trim on strength only |
| OKLO | 1.9% | 2.8% | HOLD | — | Underwater −37%, break-even ~$101. Hold, trim on strength only |
| CBRS | 1.8% | 2.4% | ACCUMULATE | — | 3 shares held (1 RRSP + 2 TFSA @ $215). $185 GTC active |
| APLD | 2.5% | 1.9% | MAINTAIN | — | SA LP core holding, NOT exit |
| MSFT | 2.5% | 2.4% | MAINTAIN | — | Hold 2 shares, no add/trim |
| DXYZ | 0% | 0% | EXIT | — | Fully exited 2026-06-03, small loss |

---

## 🛠️ Recent System Changes (2026-06-01 to 2026-06-04)

### New Capabilities
- **`targetEntryPrice` field** — GTC limit price per holding in `target-portfolio.json`
  - Set via: `python3 plugins/portfolio-advisor/scripts/update_targets.py --set-entry TICKER=PRICE --write`
- **Fractional shares** — `place_order.py --shares 0.2` now works
- **Portfolio sync fallback** — after fills: Express API → direct CDP snapshot → Questrade REST
- **`fetch_broker_data.py --snapshot`** — now fetches balances BEFORE positions (avoids TV state corruption), writes live `cashUSD` + `totalUSD` to portfolio.json
- **Grok prompt v2** — conviction score (1–10) column, entry price column, "material only" framing, portfolio-level questions section (risks, mispriced, macro)
- **Auto-proceed in `/x-news-sweep`** — no longer waits for "apply" when all items APPROVED/WARN-allowlisted. Only gates on CONFIRM/BLOCKED.

### Bug Fixes
- **PSU.U.TO duplicate eliminated** — `fetch_broker_data.py` hardcodes alias `PSU.U.TO → PSU-U.TO`. Will never recreate the 0%-target EXIT entry again.
- **Limit order form fill** — `trading.js` now fills shares BEFORE limit price (prevents price field being overwritten with share count)
- **APLD/MSFT EXIT flags removed** — both are now MAINTAIN/core holdings
- **Modal auto-updates** — x-news-sweep, 13f-analyze, portfolio-health now auto-apply approved changes immediately

### Thesis Changes This Session
- CORZ: 7.8% → 8.4%
- PANW: 5.4% → 6.0%
- NBIS: 4.9% → 5.5%
- IREN: 1.6% → 2.4%
- SNDK: trimmed to 0.8 shares, target 3.7%, entry price $1,350
- DXYZ: exited (SpaceX IPO uncertainty)
- APLD: EXIT → MAINTAIN 2% (SA LP core holding)
- MSFT: EXIT → MAINTAIN 2.45%
- PSU.U.TO duplicate: removed
- CBRS: 1.0% → 2.5% target; 3 shares filled @ $215

---

## 🚀 Next Session Checklist

1. **Start of day**: `/tv-portfolio-sync` → `/x-news-sweep`
2. **Priority build**: Wire `targetEntryPrice` into review JSON + dashboard modal (see item #1 above)
3. **Set entry prices** for all ACCUMULATE positions once dashboard shows them
4. **GTC automation fix** in `trading.js` → `setGoodTillCancelled()` (see item #2 above)
5. **SNDK**: Do not add unless price drops to $1,350 or below
6. **CEG/OKLO**: Hold, only trim when back in profit ($364 / $101 respectively)

---

## 💡 Key Principles (user preferences)

- Recommendations must include **target entry price** — "ACCUMULATE" without a price is incomplete
- **Valuation always matters** — factor in current price vs DCF, not just directional signal
  (e.g. SNDK DCF says BUY +49% but that was calculated at $1,333; real upside at $1,741 is only 14%)
- **PSU-U.TO is HISA/cash equivalent** — not a trade, not a trim candidate unless user says so
- **CEG/OKLO**: only sell when green — both are underwater, hold discipline
- **Account structure**: TFSA is primary (larger), RRSP mirrors at ~1/3 share count
- **GTC limit orders**: after placing via CLI, manually change duration in TradingView broker panel
- **PSU cash source**: PSU-U.TO can be sold to fund new buys if cash is depleted
