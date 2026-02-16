# Antigravity Workflow Inventory

> **Generated:** 2026-02-15 16:30
> **Total Workflows:** 72


## Track: Factory

| Command | Tier | Description | Called By |
| :--- | :--- | :--- | :--- |
| `/adr-manager_create` | - | Create a new Architecture Decision Record from template | - |
| `/adr-manager_list` | - | List, view, or search Architecture Decision Records | - |
| `/agent-orchestrator_delegate` | - | "Generate a strategy packet and hand off execution to the inner loop agent" | - |
| `/agent-orchestrator_plan` | - | "Start the outer loop: specify, plan, and generate tasks via spec-kitty" | - |
| `/agent-orchestrator_retro` | - | "Session retrospective: what worked, what failed, fix one thing now" | - |
| `/agent-orchestrator_review` | - | "Bundle project context into a single markdown for red-team or human review" | - |
| `/agent-orchestrator_verify` | - | "Inspect inner loop output against acceptance criteria. Pass or generate correction packet." | - |
| `/claude-cli_audit` | - | Run a multi-persona audit loop (Red Team → Architect → QA) | - |
| `/claude-cli_list-personas` | - | List all available sub-agent personas by category | - |
| `/claude-cli_run` | - | Run a Claude CLI sub-agent with a persona prompt against a file or bundle | - |
| `/code-snapshot_capture` | - | Capture a full or subfolder code snapshot into a token-counted markdown artifact | - |
| `/coding-conventions_apply` | - | Apply the coding conventions — review code or generate compliant headers | - |
| `/context-bundler_add` | - | Add a file to the current context bundle manifest | - |
| `/context-bundler_bundle` | - | Bundle files from a manifest into a single Markdown context package | - |
| `/context-bundler_init` | - | Initialize a new context bundle manifest from a base template | - |
| `/context-bundler_manage` | - | Full bundle management workflow — init, curate, validate, and compile | - |
| `/dependency-management_audit` | - | Audit the dependency tree for conflicts, stale pins, or security issues | - |
| `/dependency-management_manage` | - | Add, upgrade, or patch a Python dependency using pip-compile workflow | - |
| `/link-checker_check` | - | Scan documentation for broken relative links and generate a report | - |
| `/link-checker_fix` | - | Auto-repair broken documentation links using fuzzy matching against the file inventory | - |
| `/link-checker_map` | - | Index all repository files to create the link resolution inventory | - |
| `/link-checker_post-move` | - | Run the full Map → Fix → Verify workflow after moving or renaming files | - |
| `/mermaid-export_check` | - | Check which .mmd diagrams have outdated or missing images | - |
| `/mermaid-export_render` | - | Render a single .mmd file or directory of diagrams to PNG/SVG | - |
| `/plugin-bridge_install` | - | "Install an Agent Plugin into the local environment(s)" | - |
| `/rlm-factory_audit` | - | Audit RLM cache coverage — compare ledger against filesystem (offline) | - |
| `/rlm-factory_cleanup` | - | Clean stale and orphan entries from the RLM cache (offline) | - |
| `/rlm-factory_distill` | - | Distill repository files into semantic summaries using Ollama (requires Ollama running) | - |
| `/rlm-factory_query` | - | Search the RLM cache for file summaries by keyword (offline — no Ollama needed) | - |
| `/spec-kitty.accept` | - | Validate feature readiness and guide final acceptance steps. | - |
| `/spec-kitty.analyze` | - | Perform a non-destructive cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md after task generation. | - |
| `/spec-kitty.checklist` | - | Generate a custom checklist for the current feature based on user requirements. | - |
| `/spec-kitty.clarify` | - | Identify underspecified areas in the current feature spec by asking up to 5 highly targeted clarification questions and encoding answers back into the spec. | - |
| `/spec-kitty.constitution` | - | Create or update the project constitution through interactive phase-based discovery. | - |
| `/spec-kitty.dashboard` | - | Open the Spec Kitty dashboard in your browser. | - |
| `/spec-kitty.implement` | - | Create an isolated workspace (worktree) for implementing a specific work package. | - |
| `/spec-kitty.merge` | - | Merge a completed feature into the main branch and clean up worktree | - |
| `/spec-kitty.plan` | - | Execute the implementation planning workflow using the plan template to generate design artifacts. | - |
| `/spec-kitty.research` | - | Run the Phase 0 research workflow to scaffold research artifacts before task planning. | - |
| `/spec-kitty.review` | - | Perform structured code review and kanban transitions for completed task prompt files | - |
| `/spec-kitty.specify` | - | Create or update the feature specification from a natural language feature description. | - |
| `/spec-kitty.status` | - | Display kanban board status showing work package progress across lanes (planned/doing/for_review/done). | - |
| `/spec-kitty.tasks` | - | Generate grouped work packages with actionable subtasks and matching prompt files for the feature in one pass. | - |
| `/spec-kitty_accept` | - | Validate feature readiness — all WPs must be done | - |
| `/spec-kitty_implement` | - | Create isolated worktree for a work package | - |
| `/spec-kitty_merge` | - | Automated batch merge of all WP worktrees into main | - |
| `/spec-kitty_plan` | - | Generate implementation plan from specification | - |
| `/spec-kitty_review` | - | Submit work package for review and move to for_review lane | - |
| `/spec-kitty_specify` | - | Create or update feature specification from natural language | - |
| `/spec-kitty_status` | - | Show kanban board — work package progress across lanes | - |
| `/spec-kitty_sync-rules` | - | Sync rules only — propagate .agent/rules to all agents | - |
| `/spec-kitty_sync-skills` | - | Sync skills only — distribute agent skills to all agents | - |
| `/spec-kitty_sync-workflows` | - | Sync workflows only — update workflow definitions for all agents | - |
| `/spec-kitty_sync` | - | Run Universal Bridge sync — propagate rules, workflows, and skills to all AI agents | - |
| `/spec-kitty_tasks` | - | Generate work packages (WPs) with subtasks and prompt files | - |
| `/spec-kitty_verify` | - | Verify bridge integrity — check that agent configs match Source of Truth | - |
| `/task-manager_board` | - | Show the kanban board overview | - |
| `/task-manager_create` | - | Create a new task on the kanban board | - |
| `/task-manager_list` | - | List tasks or filter by lane status | - |
| `/task-manager_move` | - | Move a task between kanban lanes | - |
| `/tool-inventory_add` | - | Register a new tool in the inventory (auto-extracts docstring, triggers ChromaDB upsert) | - |
| `/tool-inventory_audit` | - | Audit inventory — find missing files, untracked scripts, and ChromaDB coverage gaps | - |
| `/tool-inventory_discover` | - | Discover untracked scripts and auto-create stub entries | - |
| `/tool-inventory_generate` | - | Generate TOOL_INVENTORY.md documentation from the JSON registry | - |
| `/tool-inventory_list` | - | List all registered tools in the inventory | - |
| `/tool-inventory_manage` | - | Full tool update workflow — register, distill, generate docs, audit, verify | - |
| `/tool-inventory_remove` | - | Remove a tool from the inventory and ChromaDB | - |
| `/tool-inventory_search` | - | Search tools by keyword (JSON) or semantic query (ChromaDB vector search) | - |
| `/tool-inventory_sync` | - | Import tools from existing rlm_tool_cache.json into ChromaDB or sync inventory with cache | - |
| `/vector-db_cleanup` | - | "Remove stale chunks from deleted or renamed files in the vector database" | - |
| `/vector-db_ingest` | - | "Ingest repository files into the local ChromaDB vector store for semantic search" | - |
| `/vector-db_query` | - | "Search the vector database for semantically relevant code and documentation" | - |

## Quick Reference (All)

| Command | Track | Description |
| :--- | :--- | :--- |
| `/adr-manager_create` | Factory | Create a new Architecture Decision Record from template |
| `/adr-manager_list` | Factory | List, view, or search Architecture Decision Records |
| `/agent-orchestrator_delegate` | Factory | "Generate a strategy packet and hand off execution to the inner loop agent" |
| `/agent-orchestrator_plan` | Factory | "Start the outer loop: specify, plan, and generate tasks via spec-kitty" |
| `/agent-orchestrator_retro` | Factory | "Session retrospective: what worked, what failed, fix one thing now" |
| `/agent-orchestrator_review` | Factory | "Bundle project context into a single markdown for red-team or human review" |
| `/agent-orchestrator_verify` | Factory | "Inspect inner loop output against acceptance criteria. Pass or generate correction packet." |
| `/claude-cli_audit` | Factory | Run a multi-persona audit loop (Red Team → Architect → QA) |
| `/claude-cli_list-personas` | Factory | List all available sub-agent personas by category |
| `/claude-cli_run` | Factory | Run a Claude CLI sub-agent with a persona prompt against a file or bundle |
| `/code-snapshot_capture` | Factory | Capture a full or subfolder code snapshot into a token-counted markdown artifact |
| `/coding-conventions_apply` | Factory | Apply the coding conventions — review code or generate compliant headers |
| `/context-bundler_add` | Factory | Add a file to the current context bundle manifest |
| `/context-bundler_bundle` | Factory | Bundle files from a manifest into a single Markdown context package |
| `/context-bundler_init` | Factory | Initialize a new context bundle manifest from a base template |
| `/context-bundler_manage` | Factory | Full bundle management workflow — init, curate, validate, and compile |
| `/dependency-management_audit` | Factory | Audit the dependency tree for conflicts, stale pins, or security issues |
| `/dependency-management_manage` | Factory | Add, upgrade, or patch a Python dependency using pip-compile workflow |
| `/link-checker_check` | Factory | Scan documentation for broken relative links and generate a report |
| `/link-checker_fix` | Factory | Auto-repair broken documentation links using fuzzy matching against the file inventory |
| `/link-checker_map` | Factory | Index all repository files to create the link resolution inventory |
| `/link-checker_post-move` | Factory | Run the full Map → Fix → Verify workflow after moving or renaming files |
| `/mermaid-export_check` | Factory | Check which .mmd diagrams have outdated or missing images |
| `/mermaid-export_render` | Factory | Render a single .mmd file or directory of diagrams to PNG/SVG |
| `/plugin-bridge_install` | Factory | "Install an Agent Plugin into the local environment(s)" |
| `/rlm-factory_audit` | Factory | Audit RLM cache coverage — compare ledger against filesystem (offline) |
| `/rlm-factory_cleanup` | Factory | Clean stale and orphan entries from the RLM cache (offline) |
| `/rlm-factory_distill` | Factory | Distill repository files into semantic summaries using Ollama (requires Ollama running) |
| `/rlm-factory_query` | Factory | Search the RLM cache for file summaries by keyword (offline — no Ollama needed) |
| `/spec-kitty.accept` | Factory | Validate feature readiness and guide final acceptance steps. |
| `/spec-kitty.analyze` | Factory | Perform a non-destructive cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md after task generation. |
| `/spec-kitty.checklist` | Factory | Generate a custom checklist for the current feature based on user requirements. |
| `/spec-kitty.clarify` | Factory | Identify underspecified areas in the current feature spec by asking up to 5 highly targeted clarification questions and encoding answers back into the spec. |
| `/spec-kitty.constitution` | Factory | Create or update the project constitution through interactive phase-based discovery. |
| `/spec-kitty.dashboard` | Factory | Open the Spec Kitty dashboard in your browser. |
| `/spec-kitty.implement` | Factory | Create an isolated workspace (worktree) for implementing a specific work package. |
| `/spec-kitty.merge` | Factory | Merge a completed feature into the main branch and clean up worktree |
| `/spec-kitty.plan` | Factory | Execute the implementation planning workflow using the plan template to generate design artifacts. |
| `/spec-kitty.research` | Factory | Run the Phase 0 research workflow to scaffold research artifacts before task planning. |
| `/spec-kitty.review` | Factory | Perform structured code review and kanban transitions for completed task prompt files |
| `/spec-kitty.specify` | Factory | Create or update the feature specification from a natural language feature description. |
| `/spec-kitty.status` | Factory | Display kanban board status showing work package progress across lanes (planned/doing/for_review/done). |
| `/spec-kitty.tasks` | Factory | Generate grouped work packages with actionable subtasks and matching prompt files for the feature in one pass. |
| `/spec-kitty_accept` | Factory | Validate feature readiness — all WPs must be done |
| `/spec-kitty_implement` | Factory | Create isolated worktree for a work package |
| `/spec-kitty_merge` | Factory | Automated batch merge of all WP worktrees into main |
| `/spec-kitty_plan` | Factory | Generate implementation plan from specification |
| `/spec-kitty_review` | Factory | Submit work package for review and move to for_review lane |
| `/spec-kitty_specify` | Factory | Create or update feature specification from natural language |
| `/spec-kitty_status` | Factory | Show kanban board — work package progress across lanes |
| `/spec-kitty_sync` | Factory | Run Universal Bridge sync — propagate rules, workflows, and skills to all AI agents |
| `/spec-kitty_sync-rules` | Factory | Sync rules only — propagate .agent/rules to all agents |
| `/spec-kitty_sync-skills` | Factory | Sync skills only — distribute agent skills to all agents |
| `/spec-kitty_sync-workflows` | Factory | Sync workflows only — update workflow definitions for all agents |
| `/spec-kitty_tasks` | Factory | Generate work packages (WPs) with subtasks and prompt files |
| `/spec-kitty_verify` | Factory | Verify bridge integrity — check that agent configs match Source of Truth |
| `/task-manager_board` | Factory | Show the kanban board overview |
| `/task-manager_create` | Factory | Create a new task on the kanban board |
| `/task-manager_list` | Factory | List tasks or filter by lane status |
| `/task-manager_move` | Factory | Move a task between kanban lanes |
| `/tool-inventory_add` | Factory | Register a new tool in the inventory (auto-extracts docstring, triggers ChromaDB upsert) |
| `/tool-inventory_audit` | Factory | Audit inventory — find missing files, untracked scripts, and ChromaDB coverage gaps |
| `/tool-inventory_discover` | Factory | Discover untracked scripts and auto-create stub entries |
| `/tool-inventory_generate` | Factory | Generate TOOL_INVENTORY.md documentation from the JSON registry |
| `/tool-inventory_list` | Factory | List all registered tools in the inventory |
| `/tool-inventory_manage` | Factory | Full tool update workflow — register, distill, generate docs, audit, verify |
| `/tool-inventory_remove` | Factory | Remove a tool from the inventory and ChromaDB |
| `/tool-inventory_search` | Factory | Search tools by keyword (JSON) or semantic query (ChromaDB vector search) |
| `/tool-inventory_sync` | Factory | Import tools from existing rlm_tool_cache.json into ChromaDB or sync inventory with cache |
| `/vector-db_cleanup` | Factory | "Remove stale chunks from deleted or renamed files in the vector database" |
| `/vector-db_ingest` | Factory | "Ingest repository files into the local ChromaDB vector store for semantic search" |
| `/vector-db_query` | Factory | "Search the vector database for semantically relevant code and documentation" |