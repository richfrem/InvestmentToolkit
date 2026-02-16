# ADR-021: Adopt Direct Plugin Execution Architecture

## Status
Proposed

## Context
Scripts were being mirrored from plugins/ to tools/ for legacy compatibility, creating redundancy and maintenance overhead. rlm_config.py now supports robust relative path resolution, and tool_inventory.json tracks canonical paths.

## Decision
Abolish tool mirroring. Execute directly from plugins/ by updating CLI routers and workflow references. Reduce tools/ to a project-specific proxy layer.

## Consequences
Eliminates redundancy, ensures single source of truth in plugins/, simplifies version control, but requires updating path references in workflows and CLI.

## Alternatives Considered
N/A
