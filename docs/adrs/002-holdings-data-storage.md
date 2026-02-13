# ADR 002: Holdings Data Storage Strategy

## Status
Superseded by [ADR 018: Local JSON Data Persistence](018-local-json-data-persistence.md)

## Context
The application needs to reliably preserve and access the user's current holdings data (stocks, ETFs, cash) for each account. The solution must be secure, local-first, and support incremental feature development.

## Decision
- **V1:** Store holdings data in a local TypeScript file (`backend/src/data/currentHoldings.ts`). This approach is simple, fast, and reliable for quick access and local development.
- **V2+:** Migrate holdings data to a local SQLite database for caching, persistence, and advanced queries. This enables more robust data management and future scalability.
- No external database will be used in V1 to maintain simplicity and security.

## Pros
- Fast, local access to holdings data.
- Easy to implement and maintain for initial versions.
- Supports incremental migration to SQLite for future enhancements.
- No external dependencies or cloud storage required.

## Cons
- TypeScript file storage is limited for advanced queries and large datasets.
- Migration to SQLite will require refactoring in future versions.

## Alternatives Considered
- JSON file storage: Simpler but less type-safe and harder to integrate with TypeScript codebase.
- External database (Postgres, MySQL): Adds complexity and security risks for V1.

## Consequences
- Holdings data is preserved locally and reliably in V1.
- Migration to SQLite in V2+ will enable caching, persistence, and more advanced features.
- No external DB or cloud storage is used, maintaining a secure, local-first approach.

---

This ADR should be updated as the data storage strategy evolves with future versions.
