# ADR 003: Security and Secrets Management

## Status
Proposed

## Context
The application must ensure secure handling of sensitive data, including API tokens and user credentials, while minimizing exposure and risk.

## Decision
- No password storage in the app.
- All secrets (refresh tokens, API keys) are stored in a local `.env` file, never hardcoded.
- OAuth2 refresh token management is used for secure authentication, as documented in ADR 001.
- Husky pre-commit hooks scan for secrets before code is committed.

## Pros
- Minimizes risk of credential leaks.
- Follows best practices for secrets management.
- Automated token rotation via OAuth2 reduces manual intervention.

## Cons
- Requires discipline in managing `.env` files and secret rotation.

## Alternatives Considered
- Cloud-based secrets managers (not needed for V1).

## Consequences
- Secure, local-first secrets management for V1.
- Easy migration to more advanced solutions if needed in future versions.
