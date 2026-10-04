---
name: toolkit-onboarding
plugin: toolkit-manager
description: Master onboarding coordinator and holistic portfolio bootstrap wizard for InvestmentToolkit. Guides new users through runtime checks, accounts & strategy pillar setup, broker ingestion, automated DCF baselines, and dashboard launch. Trigger on /toolkit-onboarding or "help me set up the toolkit".
allowed-tools: Bash, Read, Write
---

# Toolkit Onboarding

Master coordinator for fresh clones to achieve full operational parity across services, schemas, holdings, and valuations.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints

- **Single source of truth**: All portfolio holdings, cash balances, and target allocations must be stored in `domain_model.sqlite`; never write to retired JSON files.
- **Cash invariant**: Portfolio totals must strictly follow `Total USD = sum(Equities Market Value) + sum(Account Cash USD)`.
- **HITL verification**: Never apply broker position syncs or place orders without explicit user confirmation.
- **Migration authority**: All schema updates must execute through `schema_migrator.py`; never alter database tables directly with raw SQL.

## Quick start

Initiate the onboarding wizard from repository root:

```bash
python3 run_investment_toolkit.py
```

Pre-flight connectivity check for TradingView Desktop CDP:

```bash
python3 plugins/tradingview/scripts/tv_health_check.py
```

## Workflow

1. **Verify Runtimes & Dependencies**:
   - Ensure Python 3.11+ and Node.js 18+ are present.
   - Sync plugins: `python3 .agents/skills/plugin-syncer/scripts/sync_with_inventory.py`.
   - Copy private data templates (`cash_flows.json.example` → `cash_flows.json`, `portfolio-config.json.example` → `portfolio-config.json`).
   - Run database migrations: `python3 investment_screener/backend/py_services/domain_model/schema_migrator.py`.
2. **Configure Accounts & Pillars**:
   - Establish account architecture (TFSA primary + RRSP mirror).
   - Seed accounts into `domain_model.sqlite` via `seed_real_accounts.py`.
3. **Ingest Active Holdings & Cash**:
   - Sync broker positions via `/tv-portfolio-sync` (TradingView CDP) or onboard watchlist tickers via `/stock-intake`.
4. **Build DCF Baselines (Silent Batch Mode)**:
   - For all imported tickers, fetch financials, compute Rule of 40 and Piotroski F-Scores, and compile Bear/Base/Bull DCF scenarios.
5. **Launch Application Suite**:
   - Start full stack (`python3 run_investment_toolkit.py`): Frontend (5173), Backend API (3001), TV CDP (9222).

## Verification

- Confirm schema migration status:
  ```bash
  python3 investment_screener/backend/py_services/domain_model/schema_migrator.py --status
  ```
- Validate portfolio invariants:
  ```bash
  python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
  ```
- Verify health check on `http://localhost:3001/api/health`.
- Test routing cases against `evals/evals.json`.
