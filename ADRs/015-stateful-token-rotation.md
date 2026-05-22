# ADR 008: Stateful Token Rotation for Broker APIs

## Status
Proposed

## Context
Integration with broker APIs like Questrade often involves "single-use" refresh tokens that expire upon redemption. This creates a risk of losing access if the application or network fails during the rotation process. We need a robust, stateful mechanism to manage these tokens.

## Decision
Implement a **Stateful Token Rotation** pattern with the following components:
1. **Hybrid Initialization**: Pick up the initial refresh token from the environment (`QUESTRADE_REFRESH_TOKEN`).
2. **Local Cache**: Maintain a `.gitignored` local cache `.questrade_cache` to store the active, rotated refresh token.
3. **Atomic Writes**: Use a temporary file and atomic rename operation to ensure the new token is saved correctly before replacing the old one.
4. **Fallback Logic**: If the cache fails or is missing, try the environment variable. If both fail, trigger the **Setup UI Modal**.

## Detailed Design
Refer to the following architectural documents for implementation details:
- [Stateful Token Rotation Guide](../architecture/Questrade/stateful_token_rotation.md)
- [Sequence Diagram](../architecture/Questrade/stateful_token_rotation_sequence.mmd)

## Consequences
- **Pros**:
    - Reduces manual user intervention by automating rotation.
    - Prevents total loss of access due to partial write failures.
    - Improves security by keeping active tokens out of shared configuration files.
- **Cons**:
    - Adds minor complexity to the backend token manager.
    - Requires local disk write permissions.

## Alternatives Considered
- **Direct .env Modification**: Hard to manage programmatically and risky for data corruption.
- **External Secret Manager**: Too complex for a local-first desktop/tooling application in V1.
