# InvestmentToolkit Memory

## CRITICAL RULES
- **NEVER overwrite, delete, or modify gitignored user data files** (portfolio.json, .env, credentials, etc.) without EXPLICIT user approval
- Treat gitignored data files as sacred personal data -- same as .env
- ALWAYS ask before running destructive commands (cp, rm, mv) on untracked files
- If a file is gitignored, it likely contains user-specific data that cannot be recovered from git

## Project Context
- Frontend: React 19 + Vite + Tailwind (port 5173)
- Backend: Express + TypeScript (port 3001)
- Python bridge: yfinance for financial data
- Vite proxy handles `/api` -> `localhost:3001`
- `portfolio.json` is at `investment_screener/backend/data/portfolio.json`
- Startup: `python3 run_investment_toolkit.py`
- Backend must be restarted to pick up code changes

## Investment Analysis
- [VIX Buy Zone Feature Request](project_vix_buy_zone_feature.md) — User wants a Correction Playbook screener tab; specific tickers flagged; cash reserve strategy documented
