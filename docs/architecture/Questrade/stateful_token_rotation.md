# Stateful Token Rotation Pattern (ADR 015)

This document describes the robust mechanism for managing single-use Questrade Refresh Tokens, ensuring continuity and security.

## 1. Problem Statement
Questrade refresh tokens are **single-use**. If the redemption process is interrupted or the new token is not saved, the application loses access and requires manual user intervention (re-seeding).

## 2. Solution: Stateful Rotation
We implement a multi-layered approach to ensure reliability and security.

### A. Hybrid Initialization
- **Environment Variable**: `QUESTRADE_REFRESH_TOKEN` (provided in shell or via UI) acts as the "Seed".
- **Local Cache**: A git-ignored file `.questrade_cache` acts as the "Active" store for rotated tokens.

### B. Atomic Swap Strategy
To prevent "Lost Token" scenarios due to crashes during disk writes:
1. Fetch current token from Cache -> Fallback to Env.
2. Redeem token via Questrade API.
3. Receive JSON response with `NEW_REFRESH_TOKEN`.
4. **Write Temporary**: Write the new token to `.questrade_cache.tmp`.
5. **Atomic Rename**: Move `.questrade_cache.tmp` to `.questrade_cache`.

### C. Graceful Fallback & Recovery
- If `.questrade_cache` is valid, use it.
- If `.questrade_cache` fails (token expired/invalid), fall back to `QUESTRADE_REFRESH_TOKEN` (Env).
- If both fail, trigger the **Setup UI Modal** (following the [Token Setup Guide](questrade_token_setup.md)) for the user to provide a fresh one-week application token.

## 3. Security Requirements
- **Mandatory Encryption ([ADR 019](../../adrs/019-local-token-encryption.md))**: The `.questrade_cache` file **MUST** be encrypted using OS-level identifiers (macOS Keychain) via the `keyring` library. Plaintext storage is prohibited.
- **Git Safety**: `.questrade_cache` **MUST** be added to `.gitignore`.
- **Memory Safety**: Tokens are kept in memory only during the redemption window.
