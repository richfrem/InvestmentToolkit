# ADR 006: Data Contracts Aligned with Questrade API Schemas

## Status
Accepted

## Context
To ensure consistency, reliability, and ease of integration, all internal data contracts for holdings, positions, and related entities will be aligned with the official Questrade API schemas. This applies to all backend and frontend TypeScript types, interfaces, and models.

## Decision
- All data contracts (TypeScript interfaces and Python TypedDicts/Models) will match the Questrade API response properties.
- Any changes to Questrade API schemas will be reflected in both backend layers (Node.js and Python).
- Documentation and code comments will reference the relevant Questrade API endpoints.
- This ADR must be updated if the alignment approach changes.

## Consequences
- Simplifies API integration and reduces mapping errors.
- Ensures future compatibility with Questrade updates.
- Developers must reference Questrade API docs when updating or adding new data contracts.

## Action Required
- Update all relevant TypeScript types/interfaces to match Questrade schemas.
- Add a note to `docs/DataContracts.md` referencing this ADR and the alignment requirement.
