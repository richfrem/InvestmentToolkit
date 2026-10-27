# Governance: tradingview

This package uses APM as its primary distribution layer.

## Packaging Mode
Mode: full (APM-native; `.apm/` is the canonical source tree, no duplicate root primitives)

## Governance Lane
Lane: team

## Review Requirements
- Peer review of changes to skills, scripts and evals.
- README and this document stay current.
- Order placement, modification and cancellation keep the human-approval gates (Rule #17); no mode may execute a trade autonomously.

## Promotion Rule
Changes are reviewed before merge; the lockfile in the consuming project pins what is installed.
