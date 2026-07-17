# Design Spec: `co-pilot-loop` Skill Scaffolding

This design specification details the creation of the new `co-pilot-loop` skill under the `agent-loops` plugin.

---

## 1. Goal & Context
Our workspace plugins currently include orchestrators for Simple Learning, Red Team Review, and Swarms, but lack a first-class loop for **Cooperative Multi-Agent work** where the Primary Agent (Claude) supervises and QAs a secondary lightweight agent (Gemini 3.5 Flash) doing the core implementation work.

We will scaffold `plugins/agent-loops/skills/co-pilot-loop/` following the repository standards.

---

## 2. Directory Layout & Structure

We will create the following structure:
```
plugins/agent-loops/skills/co-pilot-loop/
  SKILL.md
  evals/
    evals.json
  references/
    acceptance-criteria.md
```

### Trigger Phrases
*   `/co-pilot-loop`
*   `delegate this task to gemini as qa`
*   `run cooperative dual agent loop`
*   `coordinate gemini sub-agent on this task`

---

## 3. Skill Design (`SKILL.md`)

The `SKILL.md` file will instruct the Outer Loop agent (Claude) on how to act as the Supervisor:
1.  **Interactive Setup**: Prompts for sub-agent runner parameters (`--model gemini-3.5-flash`).
2.  **Strategy Packet generation**: Emits the objective, scope, and target branch/worktree.
3.  **Supervisor Roles**:
    *   **Spec Review Gate**: Review Gemini's design spec. Reject vague stubs.
    *   **Plan Review Gate**: Review Gemini's task list.
    *   **QA & Verification**: Execute local tests. Reject with structured severity classification (Critical, Moderate, Minor).
4.  **Closure & Git Merge**: Merges the isolated worktree into main, updates summaries, and commits.

---

## 4. Verification Plan
*   Verify the skill triggers match local routing configurations.
*   Assert `evals.json` validates positive/negative scenarios under `should_trigger` schema.
