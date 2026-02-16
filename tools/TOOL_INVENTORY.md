# Tool Inventory

> **Auto-generated:** 2026-02-13 08:21
> **Source:** [`tools/tool_inventory.json`](tools/tool_inventory.json)
> **Regenerate:** `python plugins/tool-inventory/scripts/manage_tool_inventory.py generate --inventory tools/tool_inventory.json`

---

## 📁 Bridge

| Script | Description |
| :--- | :--- |
| [`speckit_system_bridge.py`](plugins/spec-kitty/scripts/speckit_system_bridge.py) | Bridges the Antigravity IDE configuration (.agent/) to the Gemini CLI (.gemini/). This script is the 'System Sync' mechanism that ensures the CLI always respects the project's Single Source of Truth. |
| [`sync_rules.py`](plugins/spec-kitty/scripts/sync_rules.py) | [DISTILLATION FAILED] |
| [`sync_skills.py`](plugins/spec-kitty/scripts/sync_skills.py) | [DISTILLATION FAILED] |
| [`sync_workflows.py`](plugins/spec-kitty/scripts/sync_workflows.py) | [DISTILLATION FAILED] |
| [`verify_bridge_integrity.py`](plugins/spec-kitty/scripts/verify_bridge_integrity.py) | Audits the 'Dual Tri Bridge' synchronization. Verifies that every artifact in .agent/ is correctly represented in: 1. .gemini/ (CLI) and 2. .github/ (Copilot). |

## 📁 Codify

| Script | Description |
| :--- | :--- |
| [`capture-code-snapshot.js`](tools/codify/utils/capture-code-snapshot.js) | Generates a single text file snapshot of code files for LLM context sharing. |
| [`debug_rlm.py`](tools/codify/rlm/debug_rlm.py) | Debug utility to inspect the RLMConfiguration state. Verifies path resolution, manifest loading, and environment variable overrides. Useful for troubleshooting cache path conflicts. |
| [`distiller.py`](plugins/rlm-factory/scripts/distiller.py) | Recursive summarization of repo content using Ollama. |
| [`export_mmd_to_image.py`](plugins/mermaid-export/scripts/export_mmd_to_image.py) | Renders all .mmd files in docs/architecture_diagrams/ to PNG images. Run this script whenever diagrams are updated to regenerate images. |
| [`generate_todo_list.py`](tools/codify/tracking/generate_todo_list.py) | Creates a prioritized TODO list of forms pending AI analysis. Bubbles up Critical and High priority items based on workflow usage. |
| [`ingest.py`](plugins/vector-db/scripts/ingest.py) | Vector Ingestion: Chunks code/docs and generates embeddings via ChromaDB. |
| [`ingest_code_shim.py`](plugins/vector-db/scripts/ingest_code_shim.py) | Shim for ingesting code files into Vector DB. |
| [`rlm_config.py`](plugins/tool-inventory/scripts/rlm_config.py) | Centralized configuration and utility logic for the RLM Toolchain. Implement the 'Manifest Factory' pattern to dynamically resolve manifests and cache files based on the Analysis Type (Legacy vs Tool). This module is the Single Source of Truth for RLM logic. |

## 📁 Curate

| Script | Description |
| :--- | :--- |
| [`check_broken_paths.py`](plugins/link-checker/scripts/check_broken_paths.py) | Inspector: Recursively scans documentation files for broken relative links. |
| [`cleanup.py`](plugins/vector-db/scripts/cleanup.py) | Vector Cleanup: Consistency check to remove stale chunks from DB. |
| [`cleanup_cache.py`](plugins/rlm-factory/scripts/cleanup_cache.py) | [DISTILLATION FAILED] |
| [`config_manager.py`](tools/curate/utils/config_manager.py) | Manages shared configuration settings |
| [`enrich_links_v2.py`](tools/curate/link-checker/enrich_links_v2.py) | [DISTILLATION FAILED] |
| [`find_json_duplicates.py`](tools/curate/hygiene/find_json_duplicates.py) | Finds duplicate entries across JSON inventory files. |
| [`find_source_links.py`](tools/curate/link-checker/find_source_links.py) | [DISTILLATION FAILED] |
| [`fix_analysis_links.py`](tools/curate/link-checker/fix_analysis_links.py) | Fixes legacy analysis path references. |
| [`fix_pdf_links.py`](tools/curate/link-checker/fix_pdf_links.py) | Scans markdown files and fixes broken PDF links by URL-encoding spaces. |
| [`manage_tool_inventory.py`](plugins/tool-inventory/scripts/manage_tool_inventory.py) | Comprehensive manager for Tool Inventories. Supports list, add, update, remove, search, audit, and generate operations. |
| [`map_repository_files.py`](plugins/link-checker/scripts/map_repository_files.py) | Mapper: Indexes the entire repository to create a file inventory for link fixing. |
| [`organize_screenshots.py`](tools/curate/utils/organize_screenshots.py) | [DISTILLATION FAILED] |
| [`smart_fix_links.py`](plugins/link-checker/scripts/smart_fix_links.py) | Fixer: Auto-corrects broken links using fuzzy matching against the file inventory. |
| [`standardize_manifests.py`](tools/curate/hygiene/standardize_manifests.py) | Ensures all base context-bundler manifests have a consistent structure by inserting the Context Bundler System Prompt as the first file entry. Iterates through base-*-file-manifest.json files and reorders entries as needed. |
| [`workflow_inventory_manager.py`](tools/curate/documentation/workflow_inventory_manager.py) | Manages the workflow inventory for agent workflows (.agent/workflows/*.md). Provides search, scan, add, and update capabilities. Outputs are docs/antigravity/workflow/workflow_inventory.json and docs/antigravity/workflow/WORKFLOW_INVENTORY.md. |

## 📁 Investigate

| Script | Description |
| :--- | :--- |
| [`next_number.py`](plugins/adr-manager/scripts/next_number.py) | Next Number Generator Returns the next available number for any artifact type with sequential IDs. |
| [`path_resolver.py`](plugins/context-bundler/scripts/path_resolver.py) | Standardizes cross-platform path resolution and provides access to the Master Object Collection. |
| [`rlmConfigResolver.js`](tools/investigate/utils/rlmConfigResolver.js) | [DISTILLATION FAILED] |
| [`test_infrastructure.py`](tools/investigate/utils/test_infrastructure.py) | Verifies the Hybrid Discovery Tooling (Method A/B/C) on sample artifacts. |

## 📁 Investment-Screener

| Script | Description |
| :--- | :--- |
| [`eslint.config.js`](tools/investment-screener/frontend/eslint.config.js) | [DISTILLATION FAILED] |
| [`fetch_financials.py`](tools/investment-screener/backend/py_services/fetch_financials.py) | [DISTILLATION FAILED] |
| [`fetch_portfolio_heatmap.py`](tools/investment-screener/backend/py_services/fetch_portfolio_heatmap.py) | [DISTILLATION FAILED] |
| [`postcss.config.js`](tools/investment-screener/frontend/postcss.config.js) | [DISTILLATION FAILED] |
| [`tailwind.config.js`](tools/investment-screener/frontend/tailwind.config.js) | [DISTILLATION FAILED] |

## 📁 Orchestrator

| Script | Description |
| :--- | :--- |
| [`proof_check.py`](tools/orchestrator/proof_check.py) | [DISTILLATION FAILED] |
| [`workflow_manager.py`](tools/orchestrator/workflow_manager.py) | Core logic for the 'Python Orchestrator' architecture (ADR-0030 v2/v3). Handles Git State checks, Context Alignment, Branch Creation & Naming, and Context Manifest Initialization. Acts as the single source of truth for 'Start Workflow' logic. |

## 📁 Retrieve

| Script | Description |
| :--- | :--- |
| [`bundle.py`](plugins/context-bundler/scripts/bundle.py) | Bundles multiple source files into a single Markdown 'Context Bundle' based on a JSON manifest. |
| [`fetch_tool_context.py`](tools/retrieve/rlm/fetch_tool_context.py) | [DISTILLATION FAILED] |
| [`inventory.py`](plugins/rlm-factory/scripts/inventory.py) | RLM Auditor: Reports coverage of the semantic ledger against the filesystem. Uses the Shared RLMConfig to dynamically switch between 'Legacy' (Documentation) and 'Tool' (CLI) audit modes. |
| [`manifest_manager.py`](plugins/context-bundler/scripts/manifest_manager.py) | Handles initialization and modification of the context-manager manifest. Acts as the primary CLI for the Context Bundler. |
| [`query.py`](plugins/vector-db/scripts/query.py) | Vector Search: Semantic search interface for the ChromaDB collection. |
| [`query_cache.py`](plugins/rlm-factory/scripts/query_cache.py) | RLM Search: Instant O(1) semantic search of the ledger. |

## 🚀 Root

| Script | Description |
| :--- | :--- |
| [`__init__.py`](tools/__init__.py) | TBD |
| [`cli.py`](tools/cli.py) | Main entry point for the Antigravity Command System. Provides unified access to all core operations including vector database management, context bundling, analysis, business rules, and workflow orchestration. |
| [`extract_portfolio_symbols.py`](tools/extract_portfolio_symbols.py) | [DISTILLATION FAILED] |
| [`manage_servers.py`](tools/manage_servers.py) | [DISTILLATION FAILED] |

## 🛠️ Utils

| Script | Description |
| :--- | :--- |
| [`__init__.py`](tools/utils/__init__.py) | TBD |
| [`path_resolver.py`](plugins/context-bundler/scripts/path_resolver.py) | [DISTILLATION FAILED] |
