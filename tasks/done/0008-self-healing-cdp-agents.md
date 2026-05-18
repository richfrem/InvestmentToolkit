# 0008: Self-Healing & Evolving CDP Agents

**Status: COMPLETE** — 2026-05-18

## Objective
Implement a "self-healing" and "self-evolving" pattern for our `tradingview-cdp` and AI agent skills, inspired by the `browser-use/browser-harness` architecture. Claude should be empowered to dynamically detect execution issues, patch Python/Node helpers, and create or update `SKILL.md` playbooks based on empirical live-execution feedback.

## Context
Currently, our TradingView CDP integration and agent skills are mostly static. If TradingView changes its DOM or an edge case breaks a script, the agent fails and requires manual intervention to rewrite the skill or script. 

We want to adopt the paradigm from `browser-harness`:
1. **Self-Healing Helpers:** The agent should have the authority (and explicit instruction) to modify the `tradingview-cdp/` codebase or `py_services` wrappers if an action fails due to a stale selector or missing capability.
2. **"The Map, Not the Diary" (Domain Skills):** When the agent navigates a complex workflow or discovers a non-obvious solution (e.g., a specific timing wait, a weird TradingView UI quirk), it should explicitly generate or update a domain-specific skill playbook in the `.agents/skills/` directory. Next time, it reads this playbook first.
3. **Empirically Driven Improvement:** The agent should rely on actual execution (e.g., DOM snapshots, error logs, screenshots) to verify state, and save the exact mechanics that worked into its instructions.

## Deliverables Completed

### Generic Skill (agent-agentic-os v1.7.0)
- `agent-plugins-skills/plugins/agent-agentic-os/skills/self-evolution/SKILL.md`
  — 7-phase protocol: classify (Gap/Failure/Regression) → evidence → plan → execute
  with permission gates → verify (max 3 attempts) → update Map → log

### InvestmentToolkit Wiring
- `docs/superpowers/specs/2026-05-18-self-healing-cdp-design.md` — formal spec
- `plugins/tradingview/references/self-evolution-profile.md` — TV repo profile:
  allowed edit dirs, 10-entry error→tier classification table, playbook location
- `plugins/tradingview/references/evolution-log.md` — append-only fix record
- `plugins/tradingview/references/playbooks/README.md` — domain playbook index
- `plugins/tradingview/skills/author-pine-script/SKILL.md` Phase 3 — formal self-evolution reference replaces informal comment
- `plugins/tradingview/skills/technical-analysis-expert/SKILL.md` — Self-Evolution Protocol section
- `plugins/tradingview/agents/ta-guide.md` — Rule 7: self-heal CDP failures

## Relationship to Other Tasks
Builds on ADR-024 "Thin Skill + Thick Engine" by making the shared `tradingview-cdp/`
runtime adaptable and resilient without manual developer intervention.
