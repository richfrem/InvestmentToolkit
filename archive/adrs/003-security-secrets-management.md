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

## AI keys policy (addition)

- API keys used by server-side AI integrations (for example, `OPENAI_API_KEY`) MUST be stored in environment variables or a secured secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) for non-local deployments.
- `.env` files are permitted for local development only and MUST be listed in `.gitignore`. Any committed secrets must trigger immediate key rotation.
- Client-side code must never expose secret keys. Only non-sensitive values (for example, model names) may be exposed to the client via `VITE_`-prefixed environment variables.
- Access to AI keys should follow the principle of least privilege and be limited to operators or service accounts that require them.
- Audit and rotation: keys should be rotated on a regular cadence (policy-defined), and usage audited for unexpected patterns.
- Logging: do NOT log raw API keys or full prompts/responses in plaintext. If request/response capture is required for debugging, store them in a protected trace store with strict access control and automatic expiration.
