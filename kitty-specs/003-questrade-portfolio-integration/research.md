# Research: Questrade Security & Token Recovery

## Decision: Atomic Token Rotation
Questrade uses **single-use refresh tokens**. When a refresh token is redeemed for a new access token, a *new* refresh token is also issued, and the old one is immediately invalidated.

### The "Critical Window" Risk
If the application crashes or loses power after the server invalidates the old token but *before* the new token is written to disk, the user is locked out.

### Rationale for Atomic Rotation
To minimize this risk, we implement an **Atomic Swap** pattern:
1. Fetch new token pair from Questrade.
2. Write new tokens to a temporary file (`.questrade_cache.tmp`).
3. Call `os.replace()` (atomic on most filesystems) to overwrite the actual `.questrade_cache`.
4. This ensures that even if the system crashes during step 1 or 2, the previous valid (but un-redeemed) token remains on disk.

## Decision: Hardware-Backed Encryption
Plaintext tokens on disk are a security violation (ADR 019).

### Alternatives Considered
- **Environment Variables**: Too volatile; doesn't survive reboots well.
- **Custom AES with Local Key**: Key management is still a problem (where do you hide the key?).

### Chosen Approach: OS Keychain (`keyring`)
We use the Python `keyring` library to store the AES-256 encryption key in the macOS Keychain. The `.questrade_cache` file itself is encrypted, but the "Master Key" is protected by the user's OS login.

## Recovery Strategy: Graceful Fallback
If the cache is corrupted or the token is expired:
1. Catch the `OAuthError`.
2. Delete the invalid `.questrade_cache`.
3. Notify the Node.js backend via exit code and stdout.
4. UI displays the "Setup Questrade" modal to the user for re-seeding.
