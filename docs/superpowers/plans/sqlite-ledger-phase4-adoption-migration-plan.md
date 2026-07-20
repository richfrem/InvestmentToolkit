# SQLite Intelligence Ledger Migration — Phase 4 Implementation and Adoption Plan

## Executive Summary

The project is no longer blocked by architecture creation.

Verified status:

- SQLite infrastructure exists.
- Repository layer exists.
- Replay layer exists.
- Audit tooling exists.
- Consumer inventory exists.
- JSON inventory exists.
- Real migration has NOT occurred.
- Consumer adoption has NOT occurred.
- Cleanup has NOT occurred.

The next phase is not architecture work.

The next phase is adoption, validation, migration, cutover, and retirement.

---

## Guiding Principle

Original objective:

1. Build the new bridge.
2. Build the onramps and offramps.
3. Move traffic to the new bridge.
4. Verify traffic is using the new bridge.
5. Retire the old bridge.

The project is currently between steps 2 and 3.

---

# Phase 4A — Complete Architecture Adoption Audit

## Goal

Determine exactly which workloads use the new architecture and which still depend on legacy persistence.

## Deliverable A1

Create:

`docs/superpowers/status/architecture-adoption-matrix.md`

Required columns:

| Consumer | Type | Current Source | Target Source | Status | Migration Required | Test Coverage | Risk |
|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|

Consumer types:

- SKILL.md
- Sub-agent
- Plugin script
- Backend route
- Frontend component/page
- CLI utility
- Scheduled workflow
- Report generator

Statuses:

- USES_LEDGER_REPOSITORY
- USES_GENERATED_VIEW
- REMAINS_JSON_BY_DESIGN
- MIGRATION_REQUIRED
- OUT_OF_SCOPE
- UNKNOWN_REQUIRES_REVIEW

## Acceptance Criteria

- No known consumer left unclassified.
- Every consumer assigned owner and status.
- Consumer counts summarized by category.

---

# Phase 4B — Complete Consumer Audit

## Goal

Resolve all remaining UNKNOWN_REQUIRES_REVIEW and MIGRATION_REQUIRED consumers.

## Areas Required

Audit:

- plugins/**
- SKILL.md files
- sub-agents
- backend routes
- frontend pages/components
- report generators
- automation workflows

## Deliverable B1

Create:

`docs/superpowers/status/legacy-dependency-report.md`

Required sections:

### JSON Dependencies

| Consumer | JSON Path | Purpose | Migration Candidate |

### JSONL Dependencies

| Consumer | JSONL Path | Purpose | Migration Candidate |

### Markdown Dependencies

| Consumer | Path | Purpose | Migration Candidate |

## Acceptance Criteria

- Every dependency mapped.
- No unresolved migration candidates.
- No unknown ownership.

---

# Phase 4C — Real Migration Dry Run

## Goal

Determine exactly what would happen before touching production-like data.

## Deliverable C1

Create:

`docs/superpowers/status/migration-dry-run-report.md`

Must include:

### Research Migration

- files affected
- event count estimate
- failures
- skips

### Projection Migration

- files affected
- pointer updates
- rollback strategy

### Ledger Impact

- estimated observations.jsonl size
- estimated intelligence_event row count

### Database Impact

- estimated SQLite size
- estimated FTS row count

### Rollback Plan

- files restored
- commands
- validation steps

## Acceptance Criteria

- Dry run executed.
- No real data modified.
- User review completed.

---

# Phase 4D — Execute Real Migration (Only After Approval)

## Preconditions

All must be true:

- Adoption matrix complete.
- Consumer audit complete.
- Dry-run report complete.
- Backup plan complete.
- Rollback plan complete.
- User approval granted.

## Deliverable D1

Create:

`docs/superpowers/status/real-migration-report.md`

Record:

- commands executed
- timestamps
- files migrated
- event counts
- failures
- rollback results if used

## Acceptance Criteria

Verified evidence for:

- observations.jsonl exists
- intelligence.sqlite exists
- replay successful
- event counts match manifest

---

# Phase 4E — Consumer Rewiring (Task 18)

## Goal

Move consumers from legacy storage to repositories/views.

## Priority Order

### Wave 1

- daily_brief.py
- ta_sweep_batch.py
- compute_conviction_scores.py

### Wave 2

- remaining plugin scripts
- report generators

### Wave 3

- backend routes

### Wave 4

- frontend consumers

### Wave 5

- remaining skills and sub-agents

## Rule

No consumer is marked migrated until:

- tests updated
- functionality verified
- dependency inventory updated

---

# Phase 4F — Validation and Cutover

## Goal

Prove the ecosystem actually uses the new architecture.

## Deliverable F1

Create:

`docs/superpowers/status/cutover-validation-report.md`

Show:

- consumers migrated
- consumers remaining
- ledger usage
- repository usage
- generated view usage
- remaining legacy access

## Required Question

Answer:

"If legacy JSON disappeared tomorrow, what breaks?"

List each consumer explicitly.

---

# Phase 4G — Cleanup Readiness Review

## Goal

Determine whether cleanup is safe.

## Deliverable G1

Create:

`docs/superpowers/status/cleanup-readiness-review.md`

### Required Checklist

- ownership map complete
- allowed-json register complete
- migration completed
- consumers migrated
- rollback verified
- docs updated
- user approval received

## Rule

No cleanup during this phase.

This phase only determines readiness.

---

# Phase 4H — Legacy Retirement

## Goal

Retire obsolete storage after validation.

## Allowed Actions

- archive
- retire
- remove deprecated references

## Forbidden

Deleting anything before readiness review approval.

---

# Success Definition

The migration is complete only when all are true:

- Real data migrated.
- observations.jsonl populated.
- intelligence.sqlite populated.
- Adoption matrix complete.
- Consumer audit complete.
- Legacy dependency report complete.
- Consumers rewired.
- Validation complete.
- Cleanup readiness complete.
- Legacy paths retired or explicitly retained.

## Final Principle

Building SQLite structures was necessary.

The migration is not complete until the application, skills, agents, backend, frontend, reports, and automation workflows actually use them.
