# Layer 2 Knowledge Base & Domain Playbooks

This directory stores confirmed architectural insights, domain heuristics, and failure analysis patterns that survive across sessions and agent cycles.

## Confirmed Playbooks
- [Stock Valuation Lifecycle & Five-Surface Alignment](playbook-stock-valuation-lifecycle.md) — `CONFIRMED (2026-08-31)`: Enforces Step 0.1 holdings anchor, 5-surface synchronization, and zero-inline-SQL invariant across stock analysis.
- [AI-Enhanced News Sweep & Prompt Generation](playbook-news-sweep-prompt-generation.md) — `CONFIRMED (2026-09-02)`: Enforces Phase 1.5 live context review, Markdown table cell sanitization, pipe delimiter integrity, and reader schema completeness.
- [Portfolio Invariants & Target Allocation Governance](playbook-portfolio-invariants-and-target-allocation.md) — `CONFIRMED (2026-09-02)`: Enforces Mandatory Cash Invariant (Rule #18), 100.0% Target Weight Invariant Gate, and Executive Action Prioritization Hierarchy.

## Rejected Patterns / Negative Constraints
- **Inline SQLite / Python Triage**: Bypassing canonical `portfolio_io.py` or running ad-hoc SQL updates during valuation is strictly rejected as a Tier 0 protocol violation.
- **Unsanitized Table Cell Delimiters**: Using pipe (`|`) join separators or unbounded risk strings inside Markdown table cells is strictly rejected.
- **Uncalibrated Target Additions**: Modifying target weights without maintaining the exact 100.0% sum invariant across active portfolio targets is strictly rejected.


