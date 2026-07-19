# Implementation Plan - Questrade Portfolio Integration

This plan outlines the steps to add dynamic Questrade portfolio retrieval to the `investment-screener` tool, leveraging patterns from the older toolkit version.

## Goal
Automatically update `investment_screener/backend/data/portfolio.json` with current holdings from Questrade using a Python-based backend service.

## User Review Required

> [!IMPORTANT]
> **Authentication**: This implementation relies on a Questrade Refresh Token. The user generates a **7-day application token** to seed the first **single-use refresh token**.
> **Dynamic Rotation**: The app rotates refresh tokens on every use, storing them in a local `.questrade_cache` to ensure the flow is seamless after the initial seed.

## Proposed Changes

### `tools/investment-screener`

#### [NEW] [QuestradeTokenManager.py](tools/investment-screener/backend/py_services/utils/QuestradeTokenManager.py)
A specialized utility class (used by other services) that:
1. **Implements ADR 015 & 019**: Handles stateful token rotation with atomic writes and **AES-256 encryption** via macOS Keychain keys.
2. **Hybrid Discovery**: Checks encrypted `.questrade_cache` first, then `os.environ`.
3. **Session Management**: Provides high-level methods for `get_access_token()` and `rotate_refresh_token()`.

#### [NEW] [fetch_questrade_portfolio.py](tools/investment-screener/backend/py_services/fetch_questrade_portfolio.py)
A backend service that uses the `QuestradeTokenManager` to:
1. **Fetch Data**: 
   - Call `/v1/accounts` to get all account IDs.
   - Call `/v1/accounts/{id}/positions` for each account.
3. **Aggregate & Map**:
   - Sum quantities for the same symbol across multiple accounts.
   - Map to the schema: `{ symbol, shares, sector, industry, price, last_updated }`.
4. **Enrich Metadata**: For symbols missing sector/industry (newly discovered), use `yfinance` to find them.
5. **Update JSON**: Read `portfolio.json`, merge current Questrade data (updating shares and prices), and write back the updated array.

### `tools/investment-screener/frontend`

#### [NEW] [QuestradeSetupModal.tsx](tools/investment-screener/frontend/src/components/QuestradeSetupModal.tsx)
A new UI component that:
1. **Guides the User**: Displays the refined 7-step process:
   - Login -> App Hub -> Create Personal App.
   - Generate "one-week" token.
   - Use the redemption URL to get the long-lived `refresh_token`.
2. **Input Field**: Provides a secure text area for the user to paste the resulting JSON or the specific `refresh_token`.
3. **Save Action**: Sends the token to a new backend endpoint (`/api/questrade/setup`) which saves it to the local cache/environment.

#### [SECURE] Token Storage Logic
1. **Primary**: Environment variable `QUESTRADE_REFRESH_TOKEN` (provided by the user via UI or shell).
2. **Active**: Local file `.questrade_cache` (JSON, git-ignored).
3. **Process**:
   - App reads `.questrade_cache` if it exists.
   - If not, it reads `os.environ`.
   - After a successful refresh call, the *new* token is written to `.questrade_cache`.
   - *This ensures the user only ever has to enter a token once.*

---

## Verification Plan

### Automated Tests
- **Python Unit Tests**: Create a mock script `test_questrade_mapping.py` to verify:
  - Token rotation logic (mocking Questrade Auth API).
  - Data aggregation (mocking Questrade Positions API).
  - Merging logic with existing `portfolio.json`.

### Manual Verification
1. **Initial Token**: User ensures `QUESTRADE_REFRESH_TOKEN` is exported in their shell.
2. **Execution**: Run the script manually:
   ```bash
   python3 tools/investment-screener/backend/py_services/fetch_questrade_portfolio.py
   ```
3. **Audit**: 
   - Verify the script correctly picks up the environment variable.
   - Check if `investment_screener/backend/data/portfolio.json` has updated `shares` and `price` values.
   - Verify timestamp `last_updated` is current.
