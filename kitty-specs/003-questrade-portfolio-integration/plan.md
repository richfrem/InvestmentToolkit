# Implementation Plan: Questrade Portfolio Integration

**Branch**: `003-questrade-portfolio-integration` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)

## Summary

This feature adds dynamic Questrade portfolio retrieval to the `investment-screener`, following the **Multi-Language Bridge Pattern** ([ADR 017](../../adrs/017-multi-language-bridge-pattern.md)). It uses a Python-based utility to fetch holdings across TFSA, RRSP, and Margin accounts, performing **Portfolio Data Aggregation** ([ADR 018](../../adrs/018-local-json-data-persistence.md)). Security is maintained through **Stateful Token Rotation** ([ADR 015](../../adrs/015-stateful-token-rotation.md)) and **Hardware-Backed Encryption** ([ADR 019](../../adrs/019-local-token-encryption.md)).

## Technical Context

**Language/Version**: Python 3.x (Retrieval Engine), Node.js (Express) with TypeScript (Backend)  
**Primary Dependencies**: `requests`, `cryptography`, `keyring` (Python); `child_process` (Node.js)  
**Storage**: `tools/investment-screener/frontend/src/data/portfolio.json` (Public), `.questrade_cache` (Secure)  
**Testing**: `pytest` for the Python manager; `Jest/Supertest` for the API bridge  
**Target Platform**: macOS (primary), Linux/Windows support  
**Project Type**: Web Application (Monorepo - [ADR 016](../../adrs/016-investment-screener-architecture.md))  
**Performance Goals**: Sync completes in <10s for portfolios with <50 positions  
**Constraints**: Single-use tokens require **Atomic Swap** rotation; hardware-backed encryption via `keyring`.

## Constitution Check

*GATE: Passed. Complies with Section 2 (Languages) and Section 3 (Quality).*

- **Rule 2.1**: Using Python for financial data fetching via Node `child_process`. [PASS]
- **Rule 2.2**: Frontend uses Tailwind CSS for the luxury dark theme. [PASS]
- **Rule 3.1**: Conventional commits and self-review required. [PASS]

## Implementation Details (Deep Dive)

### 1. Stateful Token Rotation ([ADR 015](../../adrs/015-stateful-token-rotation.md))
Following the [Stateful Token Rotation Guide](../../docs/architecture/Questrade/stateful_token_rotation.md):
- **Hybrid Initialization**: Uses `QUESTRADE_REFRESH_TOKEN` (Env) for seeding and `.questrade_cache` for ongoing operations.
- **Atomic Swap Strategy**: New tokens are written to `.questrade_cache.tmp` before an `atomic rename` to prevent loss during crashes.
- **Graceful Fallback**: Automatically reverts to the Setup Modal if all cached and environment tokens fail.

### 2. Data Retrieval & Aggregation ([ADR 018](../../adrs/018-local-json-data-persistence.md))
Based on the [Questrade Architecture Report](../../docs/architecture/Questrade/architecture_report.md):
- **Account Discovery**: Calls `/v1/accounts` to find all sub-accounts.
- **Position Fetching**: Iterates through accounts to fetch positions (`/v1/accounts/{id}/positions`) and balances.
- **Authoritative Sync**: Questrade data overwrites manual entries in `portfolio.json` for shared symbols.

### 3. Security & Encryption ([ADR 019](../../adrs/019-local-token-encryption.md))
- **Key Management**: Uses the macOS Keychain via the Python `keyring` library to store the AES-256 master key.
- **Git Hygiene**: `.questrade_cache` is strictly excluded from version control via `.gitignore`.

## Project Structure

### Documentation (this feature)

```
kitty-specs/003-questrade-portfolio-integration/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Security & Token Recovery
├── data-model.md        # Phase 1: Aggregated Holdings Model
├── quickstart.md        # Phase 1: Setup & Initialization Guide
└── checklists/
    └── requirements.md  # Quality validation results
```

### Source Code (repository root)

```
tools/investment-screener/
├── backend/
│   ├── src/
│   │   ├── services/
│   │   │   └── QuestradeSyncService.ts  # Node.js Bridge (calls child_process)
│   │   └── utils/
│   │       └── QuestradeManager.py      # Python Engine (handles auth/sync)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── QuestradeSetupModal.tsx  # Setup UI
│   │   └── data/
│   │       └── portfolio.json           # Authoritative Holdings
└── tests/
    ├── questrade_manager_test.py
    └── questrade_sync_api.test.ts
```

**Structure Decision**: Option 2: Web application (Monorepo - ADR 016).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Multi-Language Bridge | Python is superior for financial APIs | Direct Node.js implementation lacks robust library support for Questrade |
| AES-256 Encryption | Security compliance (ADR 019) | Plaintext storage is a critical security risk |
| Atomic Disk Swap | Resilience (ADR 015) | Standard file overwrite is susceptible to corruption on crash |