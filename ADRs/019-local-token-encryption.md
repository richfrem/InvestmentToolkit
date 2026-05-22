# ADR 019: Local Token Encryption

## Status
Accepted

## Context
The application manages sensitive Questrade OAuth2 tokens. Storing these tokens in plaintext on disk, even if git-ignored, presents an unacceptable security risk for a financial tool. Security for the user's investment portfolio is a non-negotiable requirement.

## Decision
Encrypt the `.questrade_cache` file using OS-level key management:
1. **OS Keychain**: Use the macOS Keychain (via the Python `keyring` library) to store a unique encryption key for the application.
2. **Encryption Algorithm**: Use AES-256 (via `cryptography` library) to encrypt the token payload before writing to `.questrade_cache`.
3. **Memory Safety**: Tokens must be decrypted only when needed for an API call and never cached in plaintext variables outside the active redemption window.
4. **Git Safety**: The `.questrade_cache` file **MUST** be added to `.gitignore`.

## Consequences
- **Pros**:
    - Significantly higher security posture for sensitive financial credentials.
    - Leverages robust, hardware-backed security (where available via OS Keychain).
- **Cons**:
    - Adds dependencies on `keyring` and `cryptography` Python packages.
    - Requires OS-level permissions for Keychain access (one-time prompt for user).
- **Security Note**: This moves the security model from "Secret in Git-ignored File" to "Secret Encrypted by Hardware-Backed Key".
