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

Everything this skill runs itself is in its own `scripts/` folder; every other step is another skill, invoked by name. Run from this skill's folder:

```bash
python3 scripts/sqlite_admin.py status --db domain_model
```

On a fresh clone the database does not exist yet; the launcher (`run-screener`) creates it and applies pending migrations.

## Workflow

1. **Verify runtimes and dependencies:**
   - Ensure Python 3.11+ and Node.js 18+ are present.
   - Sync plugins with the `plugin-syncer` skill.
   - Copy `portfolio-config.json.example` to `portfolio-config.json` in the backend data folder if it is missing.
   - Invoke `run-screener` once so the virtual environment, dependencies and database migrations are in place, then stop it if the next steps need the ports free.
   - Invoke `tv-setup` to confirm TradingView Desktop's debugging port is reachable.
2. **Protect the database before the first write:** `python3 scripts/db_backup.py backup --db domain_model` (see `sqlite-admin` for restore and rebuild). Repeat before every later bulk write.
3. **Accounts and pillars:** establish the account structure (TFSA primary, RRSP mirror, CASH). There is no standalone seeding command; the account rows come from the portfolio migration and the broker sync, and pillar rows are created as theses are written.
4. **Ingest holdings and cash:**
   - Ask once: "Do you also use Questrade?" If no, leave `QUESTRADE_ENABLED=false` in `.env` (TradingView only, the default). If yes, invoke `questrade-setup`, which records `QUESTRADE_ENABLED=true`.
   - Invoke `tv-portfolio-sync` to sync broker positions and executed trades, or `stock-intake` to onboard watchlist tickers. Show the per-account diff and wait for the user's go-ahead before any sync is applied.
5. **Build DCF baselines (silent batch mode):** for all imported tickers, invoke the `stock-valuation` skills to fetch financials, compute Rule of 40 and Piotroski F-Scores, and compile Bear/Base/Bull DCF scenarios.
6. **Take a rebuild-from-anything export:** `python3 scripts/sqlite_admin.py export --db domain_model --out <empty folder>` then `python3 scripts/sqlite_admin.py verify-export <folder>`.
7. **Launch the suite:** invoke `run-screener` (Frontend 5173, Backend API 3001, TradingView CDP 9222).

## Verification

- `python3 scripts/sqlite_admin.py status --db domain_model` lists the tables with row counts and the schema `user_version`.
- `python3 scripts/sqlite_admin.py verify-export <folder>` prints `export ok` with matching counts.
- Invoke `portfolio-health` for the allocation and drift check; confirm `http://localhost:3001/api/health` once the suite is running.
- Test routing cases against `evals/evals.json`.
