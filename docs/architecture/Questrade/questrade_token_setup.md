# Questrade API Token Setup Guide

This guide covers the complete token lifecycle: from generating a one-week app token to seeding the encrypted local cache so the backend sync engine can run indefinitely without manual intervention.

---

## Token Lifecycle Overview

```
[Questrade Portal] → One-Week App Token
        ↓  (redeem once)
[Questrade OAuth2] → refresh_token (long-lived, single-use)
        ↓  (seed once)
[QuestradeDataEngine --seed] → .questrade_cache (AES-256-GCM encrypted)
        ↓  (every sync)
[Backend auto-rotates] → new refresh_token saved to .questrade_cache
```

After the initial seed, **you never need to touch `.zshrc` again**. The engine handles all token rotation internally. The `QUESTRADE_REFRESH_TOKEN` env var is only the emergency fallback when the cache is missing.

---

## 1. Generate a One-Week App Token (Portal)

1. Log in to your Questrade account.
2. Go to **Account Management** > **API Centre** (or visit [Questrade User Apps](https://apphub.questrade.com/UI/UserApps.aspx) directly).
3. Register a new application if you haven't already (personal apps require no `client_id`/`client_secret`).
4. Click **Generate Token** — this creates a **One-Week Application Token**.

> [!WARNING]
> This one-week token is only used **once** to bootstrap your local cache. It is NOT the long-lived `refresh_token`.

---

## 2. Redeem the One-Week Token for a Refresh Token

Run the following curl command from your terminal (must use `-d ''` to avoid HTTP 411):

```bash
ONE_WEEK_TOKEN="<paste your one-week token here>"

curl -s -X POST \
  "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=$ONE_WEEK_TOKEN" \
  -d '' \
  -H 'Content-Type: application/x-www-form-urlencoded'
```

**Successful response (HTTP 200):**
```json
{
  "access_token": "...",
  "api_server": "https://api01.iq.questrade.com/",
  "expires_in": 1800,
  "refresh_token": "Rqk-<your_long_lived_token>",
  "token_type": "Bearer"
}
```

Copy the **`refresh_token`** value — this is what you'll seed into the engine.

> [!WARNING]
> Each `refresh_token` is **single-use**. Redeeming it generates a new one. The engine handles rotation automatically after the initial seed.

---

## 3. Seed the Token into the Local Cache

Run this from the **repo root** (`/Users/<you>/Projects/InvestmentToolkit/`):

```bash
python3 investment_screener/backend/src/QuestradeDataEngine.py \
  --seed "<your_refresh_token>" \
  --cache-dir investment_screener/backend/
```

> [!IMPORTANT]
> The `--cache-dir investment_screener/backend/` flag is **required** when running from the repo root. The Node.js backend resolves its cache path to `investment_screener/backend/.questrade_cache` — the seed must write to the same location.

To verify the cache was written:
```bash
ls -la investment_screener/backend/.questrade_cache
```

---

## 4. Store as Fallback in ~/.zshrc (One-Time Setup)

The `QUESTRADE_REFRESH_TOKEN` env var acts as a **fallback seed** if the cache is ever deleted. Set it once and you won't need to change it frequently — the engine keeps the cache current.

```bash
# Add to ~/.zshrc
export QUESTRADE_REFRESH_TOKEN="Rqk-<your_refresh_token>"
```

Then reload:
```bash
source ~/.zshrc
```

> [!NOTE]
> You do **NOT** need to update `.zshrc` after each sync. The engine rotates and saves the latest token to `.questrade_cache` automatically. Only update `.zshrc` if you need to re-seed from scratch (e.g., after deleting the cache or on a new machine).

---

## 5. Verify via the Backend API

Once seeded, test the full stack:

```bash
# Backend must be running: npm run dev -w backend (from investment_screener/)
curl -s -X POST http://localhost:3001/api/portfolio/sync-questrade \
  -H 'Content-Type: application/json' -d '{}' | python3 -m json.tool
```

Expected response:
```json
{
  "success": true,
  "message": "Questrade portfolio sync completed successfully."
}
```

---

## 6. Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `HTTP 411 Length Required` | curl missing Content-Length | Add `-d ''` to your curl command |
| `HTTP 400 Bad Request` | Token already used or expired | Generate a new one-week token and re-seed |
| `Token rotation failed: 400` | Cache has stale/already-rotated token | Re-seed: `--seed "<new_token>" --cache-dir investment_screener/backend/` |
| `Expecting value: line 1 column 1` | Non-JSON response from Questrade | Token is invalid; check the token and try again |
| `Cache not found` | Cache written to wrong path | Ensure `--cache-dir investment_screener/backend/` is specified |

### When Do You Need to Re-Seed?

You only need to generate a new one-week token and re-seed in these scenarios:
1. **New machine / fresh clone** — no `.questrade_cache` exists
2. **Cache deleted** — `investment_screener/backend/.questrade_cache` removed
3. **Token expired without being redeemed** — typically if the app hasn't synced in a very long time
4. **Password change or Questrade security event** — all tokens are invalidated

In normal day-to-day use, the engine handles everything automatically.
