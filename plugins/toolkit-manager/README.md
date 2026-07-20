# Toolkit Manager Plugin

Orchestrator plugin for managing the Investment Screener suite.

## Commands

- `/start-screener`: Launch the Investment Screener suite (Frontend and Backend).

## Skills

### Run Screener
A utility skill that executes the unified `run_investment_toolkit.py` script to orchestrate the backend and frontend services.

## Data Architecture

The toolkit's portfolio/target/watchlist/valuation data is currently JSON-file based. A
SQLite-backed domain data model (`account` / `investment` / `account_investment`, replacing
`portfolio.json` + `target-portfolio.json` + `watchlist.json`) is in active design — see
`references/data-architecture/domain-data-model.md` for the model and
`references/data-architecture/sql/` for the DDL. Not yet implemented; nothing in this plugin
currently depends on it.
