# Toolkit Manager Plugin

Orchestrator plugin for managing the Investment Screener suite.

## Commands

- `/start-screener`: Launch the Investment Screener suite (Frontend and Backend).

## Skills

### Run Screener
A utility skill that executes the unified `run_investment_toolkit.py` script to orchestrate the backend and frontend services.

## Data Architecture

All portfolio data (holdings, targets, thesis state, trades, cash, price levels, alerts, valuations,
thesis breakers) lives in `investment_screener/backend/data/domain_model.sqlite`; research and
analysis live in `intelligence.sqlite`. See ADR-038 (`docs/architecture/ADRs/038-sqlite-single-source-of-truth.md`)
and `INIT_AGENTS.md` for setup. The `sqlite-admin` skill backs up, exports, verifies and rebuilds
both databases. `references/data-architecture/domain-data-model.md` and `references/data-architecture/sql/`
document the model and its DDL.
