# ADR 009: JavaScript/TypeScript Module Format Standardization

## Status
Superseded by monorepo structure in [ADR 016](016-investment-screener-architecture.md)

## Context
The InvestmentToolkit project contains scripts and modules written in both CommonJS and ES module formats. Inconsistent module usage can lead to runtime errors, tooling issues, and confusion for contributors. Modern Node.js and browser environments support ES modules natively, and TypeScript offers robust support for ES module syntax.

## Decision
- All new JavaScript/TypeScript code in this project will use **ES module syntax** (`import`/`export`).
- The TypeScript compiler will be configured with `"module": "ESNext"` (or `"ES2020"` if required for compatibility).
- The project `package.json` will include `"type": "module"` to ensure Node.js treats `.js` files as ES modules.
- Legacy code or third-party dependencies may use CommonJS (`require`, `module.exports`), but should be migrated to ES modules when practical.
- All contributors should use ES module syntax for new scripts, libraries, and refactors.

## Consequences
- Consistent module format across the codebase.
- Improved compatibility with modern tooling, LLMs, and deployment environments.
- Reduced risk of runtime errors due to module format mismatches.
- Easier onboarding for new contributors familiar with ES modules.

## Implementation Steps
1. Update all `tsconfig.json` files to use `"module": "ESNext"`.
2. Add `"type": "module"` to the root `package.json`.
3. Refactor scripts and modules to use `import`/`export` syntax.
4. Document this standard in onboarding and contribution guides.

---

**Author:** GitHub Copilot
**Date:** 2025-10-16
