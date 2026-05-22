# ADR 010: Backend Testing Approach

## Status
Superseded (Current backend uses Mocha/Chai as defined in `backend/package.json`)

## Context
To ensure reliability, maintainability, and correctness of the backend, a structured testing approach is required. The backend consists of Express API routes and modular service functions for Questrade integration and data export. Automated tests are needed for both integration (routes) and unit (services) levels.

## Decision
- **Test Structure:**
  - All backend tests are located in `backend/tests/`.
  - `routes/` contains integration tests for Express API endpoints using supertest.
  - `services/` contains unit tests for service functions using Jest.
- **Test Tools:**
  - Jest is used as the test runner for all tests.
  - Supertest is used for HTTP integration tests against the running Express server.
- **Test Coverage:**
  - All critical service functions and API routes must have automated tests.
  - Tests should cover success, error, and edge cases.
- **Test Data:**
  - Use `.env.test` for test credentials and configuration if needed.
  - Mock external dependencies (e.g., axios, fs) for unit tests.
- **Execution:**
  - All tests are run with `npx jest`.
  - Route tests require the backend server to be running.
- **Documentation:**
  - Test conventions and structure are documented in `backend/tests/README.md`.

## Consequences
- Improved reliability and maintainability of backend code.
- Fast feedback on code changes and refactoring.
- Clear separation between integration and unit tests.
- Easy onboarding for new contributors.

---
