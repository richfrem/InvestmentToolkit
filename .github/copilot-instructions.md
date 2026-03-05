# Copilot Instructions
> Managed by Spec Kitty Bridge.

## Rule: constitution

---
trigger: always_on
---

# Project Sanctuary Constitution V3

> **THE SUPREME LAW: HUMAN GATE**
> You MUST NOT execute ANY state-changing operation without EXPLICIT user approval.
> "Sounds good" is NOT approval. Only "Proceed", "Go", "Execute" is approval.
> **VIOLATION = SYSTEM FAILURE**

## I. The Hybrid Workflow (Project Purpose)
All work MUST follow the **Universal Hybrid Workflow**.
**START HERE**: `python tools/cli.py workflow start` (or `/sanctuary-start`)

### Workflow Hierarchy
```
/sanctuary-start (UNIVERSAL)
├── Routes to: Learning Loop (cognitive sessions)
│   └── /sanctuary-learning-loop → Audit → Seal → Persist
├── Routes to: Custom Flow (new features)
│   └── /spec-kitty.implement → Manual Code
└── Both end with: /sanctuary-retrospective → /sanctuary-end
```

- **Track A (Factory)**: Deterministic tasks (Codify, Curate).
- **Track B (Discovery)**: Spec-Driven Development (Spec → Plan → Tasks).
- **Reference**: [ADR 035](../../ADRs/035_hybrid_spec_driven_development_workflow.md) | [Diagram](../../docs/diagrams/analysis/sdd-workflow-comparison/hybrid-spec-workflow.mmd)

## II. The Learning Loop (Cognitive Continuity)
For all cognitive sessions, you are bound by **Protocol 128**.
**INVOKE**: `/sanctuary-learning-loop` (called by `/sanctuary-start`)

- **Boot**: Read `cognitive_primer.md` + `learning_package_snapshot.md`
- **Close**: Audit → Seal → Persist (SAVE YOUR MEMORY)
- **Reference**: [ADR 071](../../ADRs/071_protocol_128_cognitive_continuity.md) | [Diagram](../../docs/architecture_diagrams/workflows/protocol_128_learning_loop.mmd)

### Identity Layers (Boot Files)
| Layer | File | Purpose |
|:------|:-----|:--------|
| **1. Contract** | [boot_contract.md](../learning/guardian_boot_contract.md) | Immutable constraints |
| **2. Primer** | [cognitive_primer.md](../learning/cognitive_primer.md) | Role Orientation |
| **3. Snapshot** | [snapshot.md](../learning/learning_package_snapshot.md) | Session Context |

## III. Zero Trust (Git & Execution)
- **NEVER** commit directly to `main`. **ALWAYS** use a feature branch.
- **NEVER** run `git push` without explicit, fresh approval.
- **NEVER** "auto-fix" via git.
- **HALT** on any user "Stop/Wait" command immediately.

### Defined: State-Changing Operation
Any operation that:
1. Writes to disk (except /tmp/)
2. Modifies version control (git add/commit/push)
3. Executes external commands with side effects
4. Modifies .agent/learning/* files
**REQUIRES EXPLICIT APPROVAL ("Proceed", "Go", "Execute").**

## IV. Tool Discovery & Usage
- **NEVER** use `grep` / `find` / `ls -R` for tool discovery.
- **fallback IS PROHIBITED**: If `query_cache.py` fails, you MUST STOP and ask user to refresh cache.
- **ALWAYS** use **Tool Discovery**: `python plugins/rlm-factory/scripts/query_cache.py`. It's your `.agent/skills/SKILL.md`
- **ALWAYS** use defined **Slash Commands** (`/workflow-*`, `/spec-kitty.ty.*`) over raw scripts.
- **ALWAYS** use underlying `.sh` scripts e.g. (`scripts/bash/sanctuary-start.sh`, `scripts/bash/sanctuary-learning-loop.sh`) and the `tools/cli.py` and `tools/orchestrator/workflow_manager.py`

## V. Governing Law (The Tiers)

### Tier 1: PROCESS (Deterministic)
| File | Purpose |
|:-----|:--------|
| [`workflow_enforcement_policy.md`](01_PROCESS/workflow_enforcement_policy.md) | **Slash Commands**: Command-Driven Improvement |
| [`tool_discovery_enforcement_policy.md`](01_PROCESS/tool_discovery_enforcement_policy.md) | **No Grep Policy**: Use `query_cache.py` |
| [`spec_driven_development_policy.md`](01_PROCESS/spec_driven_development_policy.md) | **Lifecycle**: Spec → Plan → Tasks |

### Tier 2: OPERATIONS (Policies)
| File | Purpose |
|:-----|:--------|
| [`git_workflow_policy.md`](02_OPERATIONS/git_workflow_policy.md) | Branch strategy, commit standards |

### Tier 3: TECHNICAL (Standards)
| File | Purpose |
|:-----|:--------|
| [`coding_conventions_policy.md`](03_TECHNICAL/coding_conventions_policy.md) | Code standards, documentation |
| [`dependency_management_policy.md`](03_TECHNICAL/dependency_management_policy.md) | pip-compile workflow |

## VI. Session Closure (Mandate)
- **ALWAYS** run the 9-Phase Loop before ending a session.
- **NEVER** abandon a session without sealing.
- **ALWAYS** run `/sanctuary-retrospective` then `/sanctuary-end`.
- **PERSIST** your learnings to the Soul (HuggingFace) and **INGEST** to Brain (RAG).

**Version**: 3.7 | **Ratified**: 2026-02-01

---


# Available Workflows
- /prompts/spec-kitty.accept.prompt.md
- /prompts/spec-kitty.analyze.prompt.md
- /prompts/spec-kitty.checklist.prompt.md
- /prompts/spec-kitty.clarify.prompt.md
- /prompts/spec-kitty.constitution.prompt.md
- /prompts/spec-kitty.dashboard.prompt.md
- /prompts/spec-kitty.implement.prompt.md
- /prompts/spec-kitty.merge.prompt.md
- /prompts/spec-kitty.plan.prompt.md
- /prompts/spec-kitty.research.prompt.md
- /prompts/spec-kitty.review.prompt.md
- /prompts/spec-kitty.specify.prompt.md
- /prompts/spec-kitty.status.prompt.md
- /prompts/spec-kitty.tasks.prompt.md


<!-- RULES_SYNC_START -->
# SHARED RULES FROM .agent/rules/


--- RULE: 01_PROCESS/spec_driven_development_policy.md ---

---
trigger: manual
---

# Spec-Driven Development (SDD) Policy

**Effective Date**: 2026-01-29
**Related Constitution Articles**: IV (Documentation First), V (Test-First), VI (Simplicity)

**Full workflow details → `.agent/skills/spec_kitty_workflow/SKILL.md`**

## Core Mandate
**All significant work** must follow the **Spec → Plan → Tasks** lifecycle.
Artifacts live in `specs/NNN/` using templates from `.agent/templates/workflow/`.

## The Three Tracks

| Track | Name | When | Workflow |
|-------|------|------|----------|
| **A** | Factory | Deterministic, repetitive ops (`/codify-*`, `/curate-*`) | Auto-generated Spec/Plan/Tasks → Execute |
| **B** | Discovery | Ambiguous, creative work | `/spec-kitty.specify` → Draft Spec → Approve → Plan → Execute |
| **C** | Micro-Tasks | Trivial atomic fixes (typos, restarts) | Direct execution or ticket in `tasks/`. **No architectural decisions.** |

## Required Artifacts (Tracks A & B)

| Artifact | Template | Purpose |
|----------|----------|---------|
| `spec.md` | `.agent/templates/workflow/spec-template.md` | The **What** and **Why** |
| `plan.md` | `.agent/templates/workflow/plan-template.md` | The **How** |
| `tasks.md` | `.agent/templates/workflow/tasks-template.md` | Execution checklist |

## Lifecycle Summary
1. **Specify** → `/spec-kitty.specify` (or auto-generate for Track A)
2. **Plan** → `/spec-kitty.plan`
3. **Tasks** → `/spec-kitty.tasks`
4. **Implement** → `/spec-kitty.implement` (creates isolated worktree)
5. **Review** → `/spec-kitty.review`
6. **Merge** → `/spec-kitty.merge`

## Reverse-Engineering (Migration Context)
When migrating or improving an existing component:
1. **Discovery**: Run investigation tools.
2. **Reverse-Spec**: Populate `spec.md` from investigation results.
3. **Plan**: Create `plan.md` for the migration.


--- RULE: 01_PROCESS/tool_discovery_enforcement_policy.md ---

---
trigger: always_on
---

# 🛡️ Tool Discovery & Use Policy (Summary)

**Full workflow → `.agent/skills/tool_discovery/SKILL.md`**

### Non-Negotiables
1. **No filesystem search for tools** — `grep`, `find`, `ls -R` are **forbidden** for tool discovery.
2. **Always use `query_cache.py`** — `python plugins/rlm-factory/scripts/query_cache.py --type tool "KEYWORD"`.
3. **Fallback prohibited** — if no results, run `python tools/codify/rlm/refresh_cache.py` and retry. Do **not** fall back to shell.
4. **Late-bind** — after finding a tool, read its header (`view_file` first 200 lines) before executing.
5. **Register new tools** — `python plugins/tool-inventory/scripts/manage_tool_inventory.py add --path "tools/..."`.
6. **Stop-and-Fix** — if a tool is imperfect, fix it. Do not bypass with raw shell commands.

--- RULE: 01_PROCESS/workflow_artifacts_integrity.md ---

---
trigger: always_on
---

# Workflow Artifacts Integrity Policy

**Effective Date**: 2026-02-12
**Related Constitution Articles**: I (Hybrid Workflow), III (Zero Trust)

## Core Mandate: Tool-Generated Truth
The Agent MUST NOT simulate work or manually create process artifacts that are controlled by CLI tools.
**If a command exists to generate a file, YOU MUST USE IT.**

### 1. Spec Kitty Lifecycle
The following files are **READ-ONLY** for manual editing by the Agent. They MUST be generated/updated via CLI:

| Artifact | Mandatory Command | Forbidden Action |
|:---|:---|:---|
| `spec.md` | `/spec-kitty.specify` | Manually writing a spec file |
| `plan.md` | `/spec-kitty.plan` | Manually scaffolding a plan |
| `tasks.md` | `/spec-kitty.tasks` | Manually typing a task list |
| `tasks/WP-*.md` | `/spec-kitty.tasks` | Manually creating prompt files |
| Task lane changes | `.kittify/scripts/tasks/tasks_cli.py update` | Manually editing frontmatter or `[x]` |

**Violation**: Creating these files via `write_to_file` is a critical process failure.

### 2. Proof-Before-Trust (Anti-Simulation)
The Agent MUST NOT mark a checklist item as complete (`[x]`) unless:
1. The specific tool command for that step has been **actually executed** (not described).
2. The tool output has been **pasted into the conversation** as proof.
3. The artifact exists on disk (verified via verification tool or file read).

**Simulation is Lying**: Marking a task `[x]` based on "intent", "mental model", or narrating "I would now run..." is prohibited. The ONLY acceptable proof is real command output.

**Known agent failure modes**:
- Writing "Seal complete" without running `/sanctuary-seal`
- Narrating "I would now run the verification" instead of running it
- Skipping closure phases (seal/persist/retrospective) to "save time"
- Marking kanban tasks as done without using the tasks CLI

### 3. Kanban Sovereignty
- **NEVER** manually edit WP frontmatter (lane, agent, shell_pid fields)
- **ALWAYS** use `.kittify/scripts/tasks/tasks_cli.py` for lane transitions
- **ALWAYS** run `/spec-kitty.status` after a lane change and paste the board as proof
- **NEVER** mark a WP as `done` without first running verification tools

### 4. Closure Is Mandatory
When a session ends, the agent MUST execute the full closure sequence:
```
/sanctuary-seal → /sanctuary-persist → /sanctuary-retrospective → /sanctuary-end
```
Each step requires pasted output as proof. Skipping any step is a protocol violation.

### 5. Git Sovereignty (Human Gate)
- **NEVER** set `SafeToAutoRun: true` for `git push`.
- **NEVER** push directly to `main` (Protected Branch).
- **ALWAYS** use a feature branch (`feat/...`, `fix/...`, `docs/...`).
- **ALWAYS** wait for explicit user approval for any push.

### 6. Worktree Hygiene
- **Never** manually create directories inside `.worktrees/`.
- **Always** use `spec-kitty implement` (or `run_workflow.py`) to manage worktrees.
- **Cleanup**: Delete worktrees only via `git worktree remove` or approved cleanup scripts.


--- RULE: 01_PROCESS/workflow_enforcement_policy.md ---

---
trigger: manual
---

# Workflow Enforcement Policy

**Tool discovery details → `.agent/skills/tool_discovery/SKILL.md`**
**Spec workflow details → `.agent/skills/spec_kitty_workflow/SKILL.md`**

## Core Principle
All agent interactions MUST be mediated by **Slash Commands** (`.agent/workflows/*.md`). No bypassing with raw shell.

## Architecture (ADR-036: Thick Python / Thin Shim)

| Layer | Location | Purpose |
|:------|:---------|:--------|
| **Slash Commands** | `.agent/workflows/*.md` | User-facing interface |
| **Thin Shims** | `scripts/bash/*.sh` | Dumb wrappers that `exec` Python |
| **CLI Router** | `tools/cli.py` | Dispatches to orchestrator/tools |
| **Orchestrator** | `tools/orchestrator/` | Logic, enforcement, Git checks |

## Command Domains
- 🗄️ **Retrieve** — Fetching data (RLM, RAG)
- 🔍 **Investigate** — Deep analysis, mining
- 📝 **Codify** — Documentation, ADRs, contracts
- 📚 **Curate** — Maintenance, inventory updates
- 🧪 **Sandbox** — Prototyping
- 🚀 **Discovery** — Spec-Driven Development (Track B)

## Registration (MANDATORY after creating/modifying workflows or tools)
```bash
python tools/curate/documentation/workflow_inventory_manager.py --scan
python plugins/tool-inventory/scripts/manage_tool_inventory.py add --path <path>
```

## Workflow File Standards
- **Location**: `.agent/workflows/[kebab-case-name].md`
- **Frontmatter**: `description`, `tier`, `track`
- **Shims**: No logic — only `exec` Python scripts


--- RULE: 02_OPERATIONS/git_workflow_policy.md ---

---
trigger: always_on
---

# Git Workflow Policy

### Non-Negotiables
1. **Never commit directly to `main`** — always use a feature branch.
2. **Never `git push` without explicit, fresh user approval** (Constitution: Human Gate).
3. **One feature branch at a time** — avoid concurrent branches.

### Branch Naming
- `feat/description` — New features
- `fix/description` — Bug fixes
- `docs/description` — Documentation updates
- `refactor/description` — Code refactoring
- `test/description` — Test additions/updates

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
`<type>: <description>` — types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Conflict Resolution
```bash
git fetch origin
git merge origin/main
# Resolve, test, then:
git add . && git commit -m "merge: resolve conflicts with main"
```

--- RULE: 03_TECHNICAL/coding_conventions_policy.md ---

---
trigger: manual
---

## 📝 Coding Conventions (Summary)

**Full standards → `plugins/coding-conventions/skills/conventions-agent/SKILL.md`**

### Non-Negotiables
1. **Dual-layer docs** — external comment above + internal docstring inside every non-trivial function/class.
2. **File headers** — every source file starts with a purpose header (Python, TS/JS, C#).
3. **Type hints** — all Python function signatures use type annotations.
4. **Naming** — `snake_case` (Python), `camelCase` (JS/TS), `PascalCase` (C# public).
5. **Refactor threshold** — 50+ lines or 3+ nesting levels → extract helpers.
6. **Tool registration** — all `tools/` scripts registered in `tool_inventory.json`.
7. **Manifest schema** — use simple `{title, description, files}` format (ADR 097).

--- RULE: 03_TECHNICAL/dependency_management_policy.md ---

---
trigger: manual
---

## 🐍 Python Dependency Rules (Summary)

**Full workflow details → `plugins/dependency-management/skills/dependency-agent/SKILL.md`**

### Non-Negotiables
1. **No manual `pip install`** — all changes go through `.in` → `pip-compile` → `.txt`.
2. **Commit `.in` + `.txt` together** — the `.in` is intent, the `.txt` is the lockfile.
3. **Service sovereignty** — every MCP service owns its own `requirements.txt`.
4. **Tiered hierarchy** — Core (`requirements-core.in`) → Service-specific → Dev-only.
5. **Declarative Dockerfiles** — only `COPY requirements.txt` + `RUN pip install -r`. No ad-hoc installs.

--- RULE: constitution.md ---

---
trigger: always_on
---

# Project Sanctuary Constitution V3

> **THE SUPREME LAW: HUMAN GATE**
> You MUST NOT execute ANY state-changing operation without EXPLICIT user approval.
> "Sounds good" is NOT approval. Only "Proceed", "Go", "Execute" is approval.
> **VIOLATION = SYSTEM FAILURE**

## I. The Hybrid Workflow (Project Purpose)
All work MUST follow the **Universal Hybrid Workflow**.
**START HERE**: `python tools/cli.py workflow start` (or `/sanctuary-start`)

### Workflow Hierarchy
```
/sanctuary-start (UNIVERSAL)
├── Routes to: Learning Loop (cognitive sessions)
│   └── /sanctuary-learning-loop → Audit → Seal → Persist
├── Routes to: Custom Flow (new features)
│   └── /spec-kitty.implement → Manual Code
└── Both end with: /sanctuary-retrospective → /sanctuary-end
```

- **Track A (Factory)**: Deterministic tasks (Codify, Curate).
- **Track B (Discovery)**: Spec-Driven Development (Spec → Plan → Tasks).
- **Reference**: [ADR 035](../../ADRs/035_hybrid_spec_driven_development_workflow.md) | [Diagram](../../docs/diagrams/analysis/sdd-workflow-comparison/hybrid-spec-workflow.mmd)

## II. The Learning Loop (Cognitive Continuity)
For all cognitive sessions, you are bound by **Protocol 128**.
**INVOKE**: `/sanctuary-learning-loop` (called by `/sanctuary-start`)

- **Boot**: Read `cognitive_primer.md` + `learning_package_snapshot.md`
- **Close**: Audit → Seal → Persist (SAVE YOUR MEMORY)
- **Reference**: [ADR 071](../../ADRs/071_protocol_128_cognitive_continuity.md) | [Diagram](../../docs/architecture_diagrams/workflows/protocol_128_learning_loop.mmd)

### Identity Layers (Boot Files)
| Layer | File | Purpose |
|:------|:-----|:--------|
| **1. Contract** | [boot_contract.md](../learning/guardian_boot_contract.md) | Immutable constraints |
| **2. Primer** | [cognitive_primer.md](../learning/cognitive_primer.md) | Role Orientation |
| **3. Snapshot** | [snapshot.md](../learning/learning_package_snapshot.md) | Session Context |

## III. Zero Trust (Git & Execution)
- **NEVER** commit directly to `main`. **ALWAYS** use a feature branch.
- **NEVER** run `git push` without explicit, fresh approval.
- **NEVER** "auto-fix" via git.
- **HALT** on any user "Stop/Wait" command immediately.

### Defined: State-Changing Operation
Any operation that:
1. Writes to disk (except /tmp/)
2. Modifies version control (git add/commit/push)
3. Executes external commands with side effects
4. Modifies .agent/learning/* files
**REQUIRES EXPLICIT APPROVAL ("Proceed", "Go", "Execute").**

## IV. Tool Discovery & Usage
- **NEVER** use `grep` / `find` / `ls -R` for tool discovery.
- **fallback IS PROHIBITED**: If `query_cache.py` fails, you MUST STOP and ask user to refresh cache.
- **ALWAYS** use **Tool Discovery**: `python plugins/rlm-factory/scripts/query_cache.py`. It's your `.agent/skills/SKILL.md`
- **ALWAYS** use defined **Slash Commands** (`/workflow-*`, `/spec-kitty.ty.*`) over raw scripts.
- **ALWAYS** use underlying `.sh` scripts e.g. (`scripts/bash/sanctuary-start.sh`, `scripts/bash/sanctuary-learning-loop.sh`) and the `tools/cli.py` and `tools/orchestrator/workflow_manager.py`

## V. Governing Law (The Tiers)

### Tier 1: PROCESS (Deterministic)
| File | Purpose |
|:-----|:--------|
| [`workflow_enforcement_policy.md`](01_PROCESS/workflow_enforcement_policy.md) | **Slash Commands**: Command-Driven Improvement |
| [`tool_discovery_enforcement_policy.md`](01_PROCESS/tool_discovery_enforcement_policy.md) | **No Grep Policy**: Use `query_cache.py` |
| [`spec_driven_development_policy.md`](01_PROCESS/spec_driven_development_policy.md) | **Lifecycle**: Spec → Plan → Tasks |

### Tier 2: OPERATIONS (Policies)
| File | Purpose |
|:-----|:--------|
| [`git_workflow_policy.md`](02_OPERATIONS/git_workflow_policy.md) | Branch strategy, commit standards |

### Tier 3: TECHNICAL (Standards)
| File | Purpose |
|:-----|:--------|
| [`coding_conventions_policy.md`](03_TECHNICAL/coding_conventions_policy.md) | Code standards, documentation |
| [`dependency_management_policy.md`](03_TECHNICAL/dependency_management_policy.md) | pip-compile workflow |

## VI. Session Closure (Mandate)
- **ALWAYS** run the 9-Phase Loop before ending a session.
- **NEVER** abandon a session without sealing.
- **ALWAYS** run `/sanctuary-retrospective` then `/sanctuary-end`.
- **PERSIST** your learnings to the Soul (HuggingFace) and **INGEST** to Brain (RAG).

**Version**: 3.7 | **Ratified**: 2026-02-01

--- RULE: standard-workflow-rules.md ---

# Git Worktree & Branch Lifecycle Protocol

> **Status:** MANDATORY
> **Enforcement:** Strict
> **Visual Guide:** [Standard Workflow Diagram](../docs/kittify/standard-spec-kitty-workflow.mmd)

## Context
This project utilizes a **Spec-Work-Package (WP)** workflow powered by `spec-kitty`. The "Standard Workflow" relies on **Worktree Isolation** and **Automated Batch Merging**.

## The Golden Rules

1.  **NEVER Merge Manually.** Spec-Kitty handles the merge.
2.  **NEVER Delete Worktrees Manually.** Spec-Kitty handles the cleanup.
    - **safe:** `git push origin WP-xx` (Backup feature branch)
    - **unsafe:** `git push origin main` (Never push directly to main)
3.  **NEVER Commit to Main directly.** Always working in a `.worktrees/WP-xx` folder.

## The Protocol

### Phase 1: The WP Execution Loop (Repeated)
For each Work Package (WP01, WP02...):

1.  **Initialize:**
    - Command: `spec-kitty implement WP-xx`
    - Action: `cd .worktrees/WP-xx`
    - **CRITICAL:** Do NOT proceed unless `pwd` confirms you are in the worktree.

2.  **Implement:**
    - Edit files **ONLY** inside the worktree.
    - Verify/Test inside the worktree.

3.  **Commit (Local Feature Branch):**
    - Command: `git add .`
    - Command: `git commit -m "feat(WP-xx): ..."`
    - **Note:** This commits to the LOCAL feature branch. Do **NOT** push to origin unless explicitly instructed for backup. Do **NOT** merge to main.

4.  **Submit for Review:**
    - Command: `spec-kitty agent tasks move-task WP-xx --to for_review`
    - Result: The CLI automatically updates `tasks.md` and the prompt file. You are done with this WP.

### Phase 2: Feature Completion (Once All WPs Done)
When **ALL** WPs in `tasks.md` are marked `[x]`:

1.  **Verify Readiness:**
    - Command: `spec-kitty accept`
    - Action: Run from **Main Repo Root**.

2.  **The Automated Merge:**
    - Command: `spec-kitty merge`
    - Context: **Main Repo Root**.
    - **System Action:** It automates the merge of ALL feature worktrees into `main` and cleans them up.
    - **Optional:** `spec-kitty merge --push` (if remote backup is required).

## Common Agent Failures (DO NOT DO THIS)
*   ❌ **Merging early:** Merging WP01 before WP02 is done. (Breaks the batch).
*   ❌ **Deleting worktrees:** Removing `.worktrees/WP01` manually. (Breaks `spec-kitty merge`).
*   ❌ **Drifting:** Editing files in `./` (Root) instead of `.worktrees/`. (Pollutes main).
*   ❌ **Relative Paths:** Agents using relative paths often get lost. **ALWAYS use Absolute Paths** for `view_file` and edits.

<!-- RULES_SYNC_END -->

<!-- BEGIN RULES FROM PLUGIN: coding-conventions -->
# SHARED RULES FROM coding-conventions


--- RULE: coding-conventions (coding-conventions) ---

---
description: Universal coding conventions for Python, TypeScript, and C#.
globs: ["*.py", "*.ts", "*.js", "*.cs"]
---

## 📝 Coding Conventions (Summary)

**Full standards → `plugins/coding-conventions/skills/conventions-agent/SKILL.md`**

### Non-Negotiables
1. **Dual-layer docs** — external comment above + internal docstring inside every non-trivial function/class.
2. **File headers** — every source file starts with a purpose header (Python, TS/JS, C#).
3. **Type hints** — all Python function signatures use type annotations.
4. **Naming** — `snake_case` (Python), `camelCase` (JS/TS), `PascalCase` (C# public).
5. **Refactor threshold** — 50+ lines or 3+ nesting levels → extract helpers.
6. **Tool registration** — all `plugins/` scripts registered in `plugins/tool_inventory.json`.
7. **Manifest schema** — use simple `{title, description, files}` format (ADR 097).

<!-- END RULES FROM PLUGIN: coding-conventions -->


<!-- BEGIN RULES FROM PLUGIN: dependency-management -->
# SHARED RULES FROM dependency-management


--- RULE: dependency-management (dependency-management) ---

---
description: Universal dependency management rules for Python and agent services.
globs: ["requirements*.txt", "requirements*.in", "Dockerfile", "pyproject.toml"]
---

## 🐍 Python Dependency Rules (Summary)

**Full workflow details → `plugins/dependency-management/skills/dependency-management/SKILL.md`**

### Non-Negotiables
1. **No manual `pip install`** — all changes go through `.in` → `pip-compile` → `.txt`.
2. **Commit `.in` + `.txt` together** — the `.in` is intent, the `.txt` is the lockfile.
3. **Service sovereignty** — every agent service owns its own `requirements.txt`.
4. **Tiered hierarchy** — Core (`requirements-core.in`) → Service-specific → Dev-only.
5. **Declarative Dockerfiles** — only `COPY requirements.txt` + `RUN pip install -r`. No ad-hoc installs.

<!-- END RULES FROM PLUGIN: dependency-management -->


<!-- BEGIN RULES FROM PLUGIN: spec-kitty -->
# SHARED RULES FROM spec-kitty
## Constitution (spec-kitty)

---
trigger: always_on
---

# Project Ecosystem Constitution V4

> **THE SUPREME LAW: HUMAN GATE**
> You MUST NOT execute ANY state-changing operation without EXPLICIT user approval.
> "Sounds good" is NOT approval. Only "Proceed", "Go", "Execute" is approval.
> **VIOLATION = SYSTEM FAILURE**

## I. The Spec-Driven Workflow (Project Purpose)
All significant work MUST follow the **Spec-Driven Development (SDD) lifecycle**.
Start with `/spec-kitty.specify` for new features.

### Workflow Hierarchy
```
/spec-kitty.specify   -> spec.md
/spec-kitty.plan      -> plan.md
/spec-kitty.tasks     -> tasks/ (work packages)
/spec-kitty.implement -> isolated worktree per WP
/spec-kitty.review    -> for_review -> done
/spec-kitty.accept    -> feature acceptance
/spec-kitty.merge     -> merge + cleanup
```

- **Track A (Factory)**: Deterministic tasks - auto-generated Spec/Plan/Tasks -> Execute.
- **Track B (Discovery)**: Ambiguous/creative work - full SDD lifecycle.
- **Track C (Micro-Task)**: Trivial fixes - direct execution, no spec needed.

## II. Zero Trust (Git & Execution)
- **NEVER** commit directly to `main`. **ALWAYS** use a feature branch.
- **NEVER** run `git push` without explicit, fresh approval.
- **NEVER** "auto-fix" via git.
- **HALT** on any user "Stop/Wait" command immediately.

### Defined: State-Changing Operation
Any operation that:
1. Writes to disk (except /tmp/)
2. Modifies version control (git add/commit/push)
3. Executes external commands with side effects
**REQUIRES EXPLICIT APPROVAL ("Proceed", "Go", "Execute").**

## III. Tool Discovery & Usage
- **NEVER** use `grep` / `find` / `ls -R` for tool discovery.
- **ALWAYS** use defined **Slash Commands** (`/spec-kitty.*`) over raw scripts.
- **ALWAYS** use `spec-kitty-cli` for SDD lifecycle operations.
- **ALWAYS** use the `task_manager.py` CLI for kanban lane transitions.

## IV. Governing Law (The Tiers)

### Tier 1: PROCESS (Deterministic)
| Policy | Purpose |
|:-------|:--------|
| `rules/spec_driven_development_policy.md` | **Lifecycle**: Spec -> Plan -> Tasks |
| `references/standard-workflow-rules.md` | **Worktree Protocol**: Branch & merge rules |

### Tier 2: TECHNICAL (Standards)
| Policy | Purpose |
|:-------|:--------|
| Coding conventions | Per language standards (snake_case, camelCase, PascalCase) |
| Dependency management | pip-compile locked-file workflow |

## V. Session Closure (Mandate)
- **ALWAYS** run `/spec-kitty.accept` then `/spec-kitty.merge` at feature completion.
- **NEVER** abandon a feature without acceptance + retrospective.
- **RLM sync**: Run distill after merge to update the semantic cache.

**Version**: 4.0 | **Ratified**: 2026-03-05

---



--- RULE: dependency-management (spec-kitty) ---

---
description: Universal dependency management rules for Python and agent services.
globs: ["requirements*.txt", "requirements*.in", "Dockerfile", "pyproject.toml"]
---

## 🐍 Python Dependency Rules (Summary)

**Full workflow details → `plugins/dependency-management/skills/dependency-management/SKILL.md`**

### Non-Negotiables
1. **No manual `pip install`** — all changes go through `.in` → `pip-compile` → `.txt`.
2. **Commit `.in` + `.txt` together** — the `.in` is intent, the `.txt` is the lockfile.
3. **Service sovereignty** — every agent service owns its own `requirements.txt`.
4. **Tiered hierarchy** — Core (`requirements-core.in`) → Service-specific → Dev-only.
5. **Declarative Dockerfiles** — only `COPY requirements.txt` + `RUN pip install -r`. No ad-hoc installs.


--- RULE: spec_driven_development_policy (spec-kitty) ---

---
trigger: manual
---

# Spec-Driven Development (SDD) Policy

**Effective Date**: 2026-01-29
**Related Constitution Articles**: IV (Documentation First), V (Test-First), VI (Simplicity)

**Full workflow details → `.agent/skills/spec_kitty_workflow/SKILL.md`**

## Core Mandate
**All significant work** must follow the **Spec → Plan → Tasks** lifecycle.
Artifacts live in `specs/NNN/` using templates from `.agent/templates/workflow/`.

## The Three Tracks

| Track | Name | When | Workflow |
|-------|------|------|----------|
| **A** | Factory | Deterministic, repetitive ops (`/codify-*`, `/curate-*`) | Auto-generated Spec/Plan/Tasks → Execute |
| **B** | Discovery | Ambiguous, creative work | `/spec-kitty.specify` → Draft Spec → Approve → Plan → Execute |
| **C** | Micro-Tasks | Trivial atomic fixes (typos, restarts) | Direct execution or ticket in `tasks/`. **No architectural decisions.** |

## Required Artifacts (Tracks A & B)

| Artifact | Template | Purpose |
|----------|----------|---------|
| `spec.md` | `.agent/templates/workflow/spec-template.md` | The **What** and **Why** |
| `plan.md` | `.agent/templates/workflow/plan-template.md` | The **How** |
| `tasks.md` | `.agent/templates/workflow/tasks-template.md` | Execution checklist |

## Lifecycle Summary (Pre-Execution Workflow Commitment)

Before starting work, display this visual map to commit to the state:
```text
┌────────────────────────────────────────────────────────┐
│               SPEC-KITTY LIFECYCLE MAP                 │
├────────────────────────────────────────────────────────┤
│ [ ] Phase 0: Plan (specify -> plan -> tasks)           │
│ [ ] Phase 1: Implement (implement WP -> code -> review)│
│ [ ] Phase 2: Close (accept -> retro -> merge -> sync)  │
└────────────────────────────────────────────────────────┘
```
1. **Specify** → `/spec-kitty.specify` (or auto-generate for Track A)
2. **Plan** → `/spec-kitty.plan`
3. **Tasks** → `/spec-kitty.tasks`
4. **Implement** → `/spec-kitty.implement` (creates isolated worktree)
5. **Review** → `/spec-kitty.review`
6. **Merge** → `/spec-kitty.merge`

## Reverse-Engineering (Migration Context)
When migrating or improving an existing component:
1. **Discovery**: Run investigation tools.
2. **Reverse-Spec**: Populate `spec.md` from investigation results.
3. **Plan**: Create `plan.md` for the migration.


--- RULE: coding-conventions (spec-kitty) ---

---
description: Universal coding conventions for Python, TypeScript, and C#.
globs: ["*.py", "*.ts", "*.js", "*.cs"]
---

## 📝 Coding Conventions (Summary)

**Full standards → `plugins/coding-conventions/skills/conventions-agent/SKILL.md`**

### Non-Negotiables
1. **Dual-layer docs** — external comment above + internal docstring inside every non-trivial function/class.
2. **File headers** — every source file starts with a purpose header (Python, TS/JS, C#).
3. **Type hints** — all Python function signatures use type annotations.
4. **Naming** — `snake_case` (Python), `camelCase` (JS/TS), `PascalCase` (C# public).
5. **Refactor threshold** — 50+ lines or 3+ nesting levels → extract helpers.
6. **Tool registration** — all `plugins/` scripts registered in `plugins/tool_inventory.json`.
7. **Manifest schema** — use simple `{title, description, files}` format (ADR 097).


--- RULE: AGENTS (spec-kitty) ---

# Agent Rules for Spec Kitty Projects

**⚠️ CRITICAL**: All AI agents working in this project must follow these rules.

These rules apply to **all commands** (specify, plan, research, tasks, implement, review, merge, etc.).

---

## 1. Path Reference Rule

**When you mention directories or files, provide either the absolute path or a path relative to the project root.**

✅ **CORRECT**:
- `kitty-specs/001-feature/tasks/WP01.md`
- `/Users/robert/Code/myproject/kitty-specs/001-feature/spec.md`
- `tasks/WP01.md` (relative to feature directory)

❌ **WRONG**:
- "the tasks folder" (which one? where?)
- "WP01.md" (in which lane? which feature?)
- "the spec" (which feature's spec?)

**Why**: Clarity and precision prevent errors. Never refer to a folder by name alone.

---

## 2. UTF-8 Encoding Rule

**When writing ANY markdown, JSON, YAML, CSV, or code files, use ONLY UTF-8 compatible characters.**

### What to Avoid (Will Break the Dashboard)

❌ **Windows-1252 smart quotes**: " " ' ' (from Word/Outlook/Office)
❌ **Em/en dashes and special punctuation**: — –
❌ **Copy-pasted arrows**: → (becomes illegal bytes)
❌ **Multiplication sign**: × (0xD7 in Windows-1252)
❌ **Plus-minus sign**: ± (0xB1 in Windows-1252)
❌ **Degree symbol**: ° (0xB0 in Windows-1252)
❌ **Copy/paste from Microsoft Office** without cleaning

**Real examples that crashed the dashboard:**
- "User's favorite feature" → "User's favorite feature" (smart quote)
- "Price: $100 ± $10" → "Price: $100 +/- $10"
- "Temperature: 72°F" → "Temperature: 72 degrees F"
- "3 × 4 matrix" → "3 x 4 matrix"

### What to Use Instead

✅ Standard ASCII quotes: `"`, `'`
✅ Hyphen-minus: `-` instead of en/em dash
✅ ASCII arrow: `->` instead of →
✅ Lowercase `x` for multiplication
✅ `+/-` for plus-minus
✅ ` degrees` for temperature
✅ Plain punctuation

### Safe Characters

✅ Emoji (proper UTF-8)  
✅ Accented characters typed directly: café, naïve, Zürich  
✅ Unicode math typed directly (√ ≈ ≠ ≤ ≥)  

### Copy/Paste Guidance

1. Paste into a plain-text buffer first (VS Code, TextEdit in plain mode)
2. Replace smart quotes and dashes
3. Verify no � replacement characters appear
4. Run `spec-kitty validate-encoding --feature <feature-id>` to check
5. Run `spec-kitty validate-encoding --feature <feature-id> --fix` to auto-repair

**Failure to follow this rule causes the dashboard to render blank pages.**

### Auto-Fix Available

If you accidentally introduce problematic characters:
```bash
# Check for encoding issues
spec-kitty validate-encoding --feature 001-my-feature

# Automatically fix all issues (creates .bak backups)
spec-kitty validate-encoding --feature 001-my-feature --fix

# Check all features at once
spec-kitty validate-encoding --all --fix
```

---

## 3. Context Management Rule

**Build the context you need, then maintain it intelligently.**

- Session start (0 tokens): You have zero context. Read plan.md, tasks.md, relevant artifacts.  
- Mid-session (you already read them): Use your judgment—don’t re-read everything unless necessary.  
- Never skip relevant information; do skip redundant re-reads to save tokens.  
- Rely on the steps in the command you are executing.

---

## 4. Work Quality Rule

**Produce secure, tested, documented work.**

- Follow the plan and constitution requirements.  
- Prefer existing patterns over invention.  
- Treat security warnings as fatal—fix or escalate.  
- Run all required tests before claiming work is complete.  
- Be transparent: state what you did, what you didn’t, and why.

---

## 5. Git Discipline Rule

**Keep commits clean and auditable.**

- Commit only meaningful units of work.
- Write descriptive commit messages (imperative mood).
- Do not rewrite history of shared branches.
- Keep feature branches up to date with main via merge or rebase as appropriate.
- Never commit secrets, tokens, or credentials.

---

## 6. Git Best Practices for Agent Directories

**NEVER commit agent directories to git.**

### Why Agent Directories Must Not Be Committed

Agent directories like `.claude/`, `.codex/`, `.gemini/` contain:
- Authentication tokens and API keys
- User-specific credentials (auth.json)
- Session data and conversation history
- Temporary files and caches

### What Should Be Committed

✅ **DO commit:**
- `.kittify/templates/` - Command templates (source)
- `.kittify/missions/` - Mission definitions
- `.kittify/memory/constitution.md` - Project constitution
- `.gitignore` - With all agent directories excluded

❌ **DO NOT commit:**
- `.claude/`, `.codex/`, `.gemini/`, etc. - Agent runtime directories
- `.kittify/templates/command-templates/` - These are templates, not final commands
- Any `auth.json`, `credentials.json`, or similar files

### Automatic Protection

Spec Kitty automatically:
1. Adds all agent directories to `.gitignore` during `spec-kitty init`
2. Installs pre-commit hook to block accidental commits
3. Creates `.claudeignore` to optimize AI scanning

### Manual Verification

```bash
# Verify .gitignore protection
cat .gitignore | grep -E '\.(claude|codex|gemini|cursor)/'

# Check for accidentally staged agent files
git status | grep -E '\.(claude|codex|gemini|cursor)/'

# If you find staged agent files, unstage them:
git reset HEAD .claude/
```

### Worktree Constitution Sharing

In worktrees, `.kittify/memory/` is a symlink to the main repo's memory,
ensuring all feature branches share the same constitution.

```bash
# In a worktree, this should show a symlink:
ls -la .kittify/memory
# lrwxr-xr-x ... .kittify/memory -> ../../../.kittify/memory
```

This is intentional and correct - it ensures a single source of truth for project principles.

---

### Quick Reference

- 📁 **Paths**: Always specify exact locations.  
- 🔤 **Encoding**: UTF-8 only. Run the validator when unsure.  
- 🧠 **Context**: Read what you need; don’t forget what you already learned.  
- ✅ **Quality**: Follow secure, tested, documented practices.  
- 📝 **Git**: Commit cleanly with clear messages.
<!-- END RULES FROM PLUGIN: spec-kitty -->
