# Backend Test Structure

This folder contains all automated tests for backend routes and service functions.

## Structure

- `routes/` — Integration tests for Express routes (API endpoints)
- `services/` — Unit tests for backend service functions (Questrade API, data stores, etc.)
- `utils/` — Utility/helper function tests (if needed)

## How to Run

- Use Jest for all tests: `npx jest`
- Route tests use supertest to make HTTP requests to the running server.
- Service tests use direct function calls and mocks.

## Example Test Files

- `routes/questradeRoutes.test.ts` — Tests for `/questrade` API endpoints
- `services/questradeService.test.ts` — Tests for Questrade service functions

## Setup

- Ensure the backend server is running for route tests.
- Use `.env.test` for test credentials if needed.
- Add/extend test files as new features/routes are added.

---
