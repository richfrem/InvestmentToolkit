# GitHub Instructions (derived from GEMINI.md)

Purpose: concise onboarding to run and maintain the InvestmentToolkit backend and CI-safe handling of Questrade tokens.

1) Repo structure
- investment_screener/: frontend + backend workspaces
- backend/: Node.js API and py_services
- frontend/: Vite React app

2) Local development (recommended)
- From repo root (recommended):
  - Start backend: npm --prefix investment_screener run dev -w backend
  - Start frontend: npm --prefix investment_screener run dev -w frontend
- Or from inside investment_screener:
  - npm run dev -w backend
  - npm run dev -w frontend

3) Questrade token setup (do NOT commit secrets)
- Generate a one-week application token in Questrade Developer Portal.
- Redeem it for a long-lived refresh token (single-use) and seed locally.

Example redemption (from your shell):

```bash
# Ensure token is in $QUESTRADE_REFRESH_TOKEN or paste directly
curl -v -X POST "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=$QUESTRADE_REFRESH_TOKEN" -d '' -H 'Content-Type: application/x-www-form-urlencoded'
```

- If successful (HTTP 200), response JSON contains a new refresh_token. Seed it into the local engine:

```bash
cd investment_screener/backend
python3 QuestradeDataEngine.py --seed "<refresh_token>"
```

- The local engine encrypts the token and stores it in `.questrade_cache` (not committed). For CI or GitHub Actions, store tokens in repository Secrets and inject at runtime.

4) CI / GitHub Actions guidance
- Never store tokens in the repo. Use GitHub Secrets and supply as environment variables to jobs.
- Example: set QUESTRADE_REFRESH_TOKEN in Actions secrets and pass to steps that run sync.

5) Troubleshooting
- HTTP 411 on redemption: include `-d ''` so Content-Length is sent.
- HTTP 400 on redemption: token invalid/expired/used — generate a new one-week app token and redeem again.
- If sync fails with token rotation errors, re-seed a valid refresh_token and re-run the sync.

6) Useful commands
- Full managed start: python3 manage.py
- One-time seed: python3 investment_screener/backend/src/QuestradeDataEngine.py --seed "<refresh_token>"

Notes: This file was generated from GEMINI.md and the Questrade setup guide; do not commit tokens or .questrade_cache. Update GEMINI.md and docs/architecture/Questrade/questrade_token_setup.md if process changes.
