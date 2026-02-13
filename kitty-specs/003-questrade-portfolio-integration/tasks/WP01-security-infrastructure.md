---
work_package_id: "WP01"
title: "Security & Token Infrastructure"
lane: "for_review"
dependencies: []
subtasks: ["T001", "T002"]
agent: "Antigravity"
shell_pid: "69517"
---

# WP01: Security & Token Infrastructure

## Objective
Implement a secure, hardware-backed token management system for Questrade credentials, ensuring resilience through atomic updates.

## Context
Following **ADR 015** (Stateful Token Rotation) and **ADR 019** (Hardware-Backed Encryption), we must store the Questrade refresh token in a way that is secure from disk-level access and resilient to system crashes.

## Guidance

### T001: Implement QuestradeTokenManager.py with Encryption
- **Goal**: Create a Python utility that handles AES-256 encryption using the macOS Keychain.
- **Details**:
  - Use the `keyring` library to store/retrieve a master secret from the macOS Keychain.
  - Implement a `TokenManager` class that handles reading/writing the `.questrade_cache` file.
  - Ensure the JSON content of the cache is encrypted before writing to disk.
- **Files**: `tools/investment-screener/backend/src/utils/QuestradeTokenManager.py`

### T002: Implement Atomic Swap Rotation Logic
- **Goal**: Ensure that writing the new token to disk cannot result in a corrupted or lost token.
- **Details**:
  - Implement a write-to-temp-then-rename pattern using `os.replace()`.
  - Validate the new token structure BEFORE overwriting the primary cache file.
- **Verification**: Run a loop that interrupts the script during a write and verify the old token remains valid.

## Definition of Done
- [ ] `QuestradeTokenManager.py` successfully stores and retrieves encrypted tokens.
- [ ] No plaintext tokens are visible in the `.questrade_cache` file.
- [ ] Atomic swap logic prevents file corruption during rotation.
- [ ] Unit tests pass for encryption and file operations.

## Activity Log

- 2026-02-13T18:22:47Z – Antigravity – shell_pid=69517 – lane=doing – Started implementation via workflow command
- 2026-02-13T18:33:17Z – Antigravity – shell_pid=69517 – lane=for_review – Implemented secure QuestradeTokenManager with AES-GCM and macOS Keychain integration. Subtask T002 verified with atomic swap test.
