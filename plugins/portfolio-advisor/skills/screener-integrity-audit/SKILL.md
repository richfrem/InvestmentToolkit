---
name: screener-integrity-audit
plugin: portfolio-advisor
description: >
  Comprehensive audit and pre-flight validation skill for the Investment Screener,
  Portfolio Table, and Intelligence Feed dashboard. Verifies all 6 core portfolio
  and table invariants (100% target sum, logical actions, cash exclusion, taxonomy alignment,
  valuation freshness, and zero false signals) before and after changes.
  Trigger phrases: "/screener-audit", "audit screener integrity", "check table rules",
  "verify screener invariants", "validate portfolio dashboard".
allowed-tools: Bash, Read, Write
---

# Screener & Dashboard Integrity Audit Skill

## Quick Reference
- **Trigger Command**: `/screener-audit` or "audit screener integrity"
- **Purpose**: Prevent visual and logical inconsistencies across the Screener, Portfolio Analysis, and Advisor pages.
- **Canonical Gate Script**: `investment_screener/backend/py_services/verify_screener_integrity.py`
- **Taxonomy Script**: `investment_screener/backend/py_services/align_all_strategies.py`
- **Database**: `investment_screener/backend/data/domain_model.sqlite`

---

## 🛡️ The 6 Non-Negotiable Screener Invariants

Every agent modifying weights, tickers, valuations, or frontend tables MUST verify these 6 gates:

1. **Target Portfolio 100.0000% Sum**:
   * Total target percentage of all non-zero positions (holdings + pipeline + `CASH_USD`) must sum to **exactly 100.00%**.
   * Any change requires running `update_targets.py` which auto-normalizes.

2. **Holding State Action Invariant**:
   * **Unheld stocks (`shares == 0`)**: Can ONLY carry `INITIATE` (if target > 0 or valuation rating is BUY) or `WATCHLIST`. They can **NEVER** carry `TRIM`, `EXIT`, or `ACCUMULATE` (you cannot trim or accumulate what you do not own).
   * **Held stocks (`shares > 0`)**: If target is `0.00%`, action is strictly `EXIT`. If target > 0, action is derived dynamically from drift ratio (`ACCUMULATE`, `MAINTAIN`, or `TRIM`).

3. **Cash Invariant & Exclusion**:
   * Total portfolio value strictly equals `sum(Equities Market Value) + sum(Account Cash USD)`.
   * Cash assets (`CASH_USD`, `USD_CASH`, `PSU-U.TO`) are categorized under the `cash` pillar and excluded from `🚨 Needs Analysis` or actionable alerts.

4. **Taxonomy & Strategy Alignment**:
   * Every investment must belong to a registered pillar and sub-strategy matching its true operational business model.
   * Ex-crypto data center power operators (`RIOT`, `BTDR`, `CORZ`, `IREN`) belong in `datainfra` / `ai-infrastructure`.
   * Power grid / micro-nuclear (`BE`, `CEG`, `VST`, `OKLO`, `PSIX`) belong in `power` / `power-infrastructure`.

5. **Valuation Coverage & Zero Gaps**:
   * 100% of active target holdings must possess a verified DCF or ETF valuation model in SQLite.

6. **Frontend Table Preferences**:
   * Column defaults: `Strategy` (`subStrategyId`), `Action`, `Ticker`, `Current %`, `Target %`, `Fair Value`, `Price`, and `Upside` are visible by default.

---

## 📋 Execution Protocol

### Step 1: Run Full Integrity Audit Gate
```bash
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```
*If this fails with Exit 1, review the failing invariant and fix before proceeding.*

### Step 2: If Strategy/Pillar Mismatches Exist
```bash
python3 investment_screener/backend/py_services/align_all_strategies.py
```

### Step 3: Run Full Blueprint & Verification Chain
```bash
python3 plugins/portfolio-advisor/scripts/generate_portfolio_blueprint.py
python3 plugins/portfolio-advisor/scripts/generate_review_json.py
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
```

### Step 4: Verify Frontend Build
```bash
npm run build -w frontend
```
