# Governance: questrade

This package uses APM as its primary distribution layer.

## Packaging Mode
Mode: full (APM-native; `.apm/` is the canonical source tree, no duplicate root primitives)

## Governance Lane
Lane: team

## Review Requirements
- Peer review of changes to skills, scripts and evals.
- README and this document stay current.
- Order drafting and deposit guidance keep the human-approval gates; no mode may execute a trade or move money autonomously.

## Promotion Rule
Changes are reviewed before merge; the lockfile in the consuming project pins what is installed.
