# Playbook: AI-Enhanced News Sweep & Prompt Generation

`Status: CONFIRMED (2026-09-02)`

## Overview
Defines the architectural invariants for generating, reviewing, and sanitizing LLM/Grok prompts in `/x-news-sweep`. Prevents table corruption, dead-code branches, and unreviewed raw script outputs.

---

## Core Invariants

### Invariant A: Live Context Synthesis in Phase 1.5
- **Rule**: Raw outputs from `generate_grok_prompt.py` MUST NOT be dispatched to Grok without explicit model review and editing.
- **Requirement**: In Phase 1.5, the Agent must inspect `domain_model.sqlite`, recent daily briefs, binary earnings events (within 1–7 days), macro regime flags, and active standing decision anchors. The Agent then uses `replace_file_content` to synthesize specific, tailored inquiries (e.g. cluster delivery milestones, exact earnings dates, regulatory PPA terms) directly into the prompt file.

### Invariant B: Markdown Table Cell Sanitization & Delimiter Integrity
- **Rule**: Never use pipe (`|`) characters within markdown table cell text or as an inter-item join separator.
- **Requirement**:
  - Text fields from SQLite (`standing_decision_reason`, `agent_rationale`, `risks_json`) must be passed through `_clean_markdown_text()` to normalize whitespace, replace raw pipes (`|` -> `/`), and truncate to safe character limits (100–120 chars).
  - Multiple inquiries must be joined with semicolons (`; `), never pipes (` | `).
  - All prompt generation changes must verify that every data row contains the exact expected pipe count matching the table header.

### Invariant C: Reader Schema Completeness (`portfolio_io.py`)
- **Rule**: Domain data readers (`load_thesis_holdings()`) must expose all foundational anchor fields from the `investment` table (`standing_decision_type`, `standing_decision_reason`, `thesis_for_inclusion`, `agent_rationale`).
- **Requirement**: Never write fallback logic that assumes a schema field is present without verifying that the reader helper extracts and maps it.

---

## Negative Constraints / Anti-Patterns
- 🚫 **Unescaped Inquiries**: Never return `" | ".join(inquiries)` inside a table cell.
- 🚫 **Unbounded Risk Text**: Never inject raw 300+ character scenario risk strings without safe word-boundary truncation.
- 🚫 **Bypassing Phase 1.5**: Never output the prompt to the user or browser automation without performing and documenting the Phase 1.5 context synthesis.
