# Questrade Portfolio Integration: Architecture & Documentation

This directory contains the formal architecture, design decisions, and implementation plans for the Questrade Portfolio Integration.

## 🗺️ Roadmap & Planning
- **[Implementation Plan](implementation_plan_questrade_integration.md)**: Overall technical roadmap and feature breakdown.
- **[Architecture Report](architecture_report.md)**: High-level system overview and component relationships.

## 🔐 Security & Token Management (ADR 015 / 019)
The integration uses a secure, hardware-backed token rotation pattern to ensure credentials are never stored in plaintext.

### 1. Encryption (Storage)
- **[Encryption Process](token_encryption_process.md)**: Overview of the AES-256-GCM storage logic and macOS Keychain integration.
- **[Encryption Sequence](token_encryption_sequence.mmd)**: Sequence diagram showing the flow from Questrade Portal to secure local cache.

### 2. Usage (Retrieval)
- **[Usage Process](token_usage_process.md)**: Documentation on how the application loads and decrypts tokens for API calls.
- **[Usage Sequence](token_usage_sequence.mmd)**: Sequence diagram mapping the authenticated data fetch cycle.

### 3. State Management
- **[Stateful Token Rotation](stateful_token_rotation.md)**: Detailed pattern for managing single-use refresh tokens.
- **[Master Sequence](stateful_token_rotation_sequence.mmd)**: The complete lifecycle of a token session.

## 🚀 Getting Started
- **[Questrade Token Setup](questrade_token_setup.md)**: Step-by-step guide for users to generate their initial manual token.

---
*Follows [ADR 015] (Stateful Token Rotation) and [ADR 019] (Hardware-Backed Encryption).*
