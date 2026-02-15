# Prompt: Red Team Review - Valuation Persistence

## Objective
Perform a comprehensive technical "Red Team" audit of the proposed **Valuation Persistence Architecture** for the Investment Toolkit.

## Role
You are a Lead Software Architect and Security Engineer specializing in financial applications and local-first data integrity.

## Context
The Investment Toolkit is a local-first application (React + Node + Python) currently migrating from ephemeral `LocalStorage` to a permanent backend JSON storage model. The "Valuation Modeler" handles high-stakes financial projections and AI-driven fair value targets.

## Review Scope
Analyze the bundled files (Design + Source Code) across the following vectors:

1.  **Persistence Integrity**:
    -   Does the JSON schema adequately handle the "Source of Truth" transition?
    -   Are there edge cases where `LocalStorage` and the backend file could desync (e.g., partial saves, network errors)?
    -   Is the "Data Snapshotting" sufficient to recreate a valuation in the future if the ticker profile (shares, currency) changes?

2.  **Financial Robustness**:
    -   Are the "Bear, Base, Bull" scenarios correctly isolated?
    -   Is the "Expected Target Price" calculation (probability-weighted) mathematically sound within the schema?
    -   Does the schema support multi-currency or share change effects accurately?

3.  **Security & Reliability**:
    -   Assess the risk of "JSON Injection" or backend data corruption.
    -   Is the migration strategy from LocalStorage safe? Can a user lose data during the transition?
    -   What happens if the `user_projections.json` becomes very large (e.g., hundreds of stocks, thousands of saves)?

4.  **Schema Versioning**:
    -   Is the `schemaVersion` approach robust enough for long-term backward compatibility?

## Output Requirements
Provide a critical report including:
- **Critical Vulnerabilities**: High-risk design flaws.
- **Data Integrity Warnings**: Potential desync or corruption points.
- **Architectural Recommendations**: Suggested improvements for "enterprise-grade" reliability.
- **Verification Tests**: Specific test cases to run during implementation.
