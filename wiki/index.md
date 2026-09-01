# Layer 2 Knowledge Base & Domain Playbooks

This directory stores confirmed architectural insights, domain heuristics, and failure analysis patterns that survive across sessions and agent cycles.

## Confirmed Playbooks
- [Stock Valuation Lifecycle & Five-Surface Alignment](playbook-stock-valuation-lifecycle.md) — `CONFIRMED (2026-08-31)`: Enforces Step 0.1 holdings anchor, 5-surface synchronization, and zero-inline-SQL invariant across stock analysis.

## Rejected Patterns / Negative Constraints
- **Inline SQLite / Python Triage**: Bypassing canonical `portfolio_io.py` or running ad-hoc SQL updates during valuation is strictly rejected as a Tier 0 protocol violation.

