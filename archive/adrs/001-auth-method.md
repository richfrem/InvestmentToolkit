# ADR 001: Authentication Method for Questrade API

## Status
Accepted

## Context
The application needs to securely access Questrade API to fetch portfolio holdings. Security is paramount: no storage of passwords, minimal exposure of sensitive data.

## Decision
Use Questrade's Manual Authorization Flow with OAuth2 refresh token management:
- User generates a single-use refresh token in the API Centre.
- App redeems the refresh token for an access (bearer) token and a new refresh token via API call.
- After each successful token exchange, the app automatically updates the .env file with the new refresh token.
- The bearer token is used for authorized API calls.

- **Pros:**
  - No password storage in the app.
  - Tokens managed securely in .env and updated automatically.
  - Refresh token used to get access tokens and is rotated after each use.

- **Cons:**
  - Manual setup required for initial token.
  - User must update .env if token is revoked or reset.

## Alternatives Considered
- OAuth browser flow: More complex for V1.

## Consequences
- /api/auth/start provides instructions.
- Tokens in .env: only REFRESH_TOKEN is required; ACCESS_TOKEN and API_SERVER are fetched dynamically.
- Automated refresh token management reduces manual intervention and improves security.