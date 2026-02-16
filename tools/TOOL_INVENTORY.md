# Tool Inventory

> **Auto-generated:** 2026-02-15 18:30
> **Source:** [`tools/tool_inventory.json`](tools/tool_inventory.json)
> **Regenerate:** `python tools/curate/inventories/manage_tool_inventory.py generate --inventory tools/tool_inventory.json`

---

## 📁 Adr-Manager

| Script | Description |
| :--- | :--- |
| [`adr_manager.py`](plugins/adr-manager/scripts/adr_manager.py) | Create, list, search, and view Architecture Decision Records (ADRs) using a template and auto-incrementing IDs. |
| [`next_number.py`](plugins/adr-manager/scripts/next_number.py) | Sequential Identifier Generator that scans artifact directories (Specs, Tasks, ADRs) to find the next available ID, preventing collisions and allowing gap-filling. |

## 📁 Code-Snapshot

| Script | Description |
| :--- | :--- |
| [`capture_code_snapshot.py`](plugins/code-snapshot/scripts/capture_code_snapshot.py) | A high-fidelity snapshotting engine that captures the "Base Genome" or specific project subfolders into consolidated Markdown documents for LLM ingestion. It generates role-specific "Awakening Seeds" to inoculate agents with strategic context. |
| [`logging_utils.py`](plugins/code-snapshot/scripts/logging_utils.py) | Shared logging utility designed for MCP servers and plugin scripts. It configures dual-output logging (Console + File) with environment-controlled persistence and standardized formatting. |
| [`snapshot_utils.py`](plugins/code-snapshot/scripts/snapshot_utils.py) | Core utility suite for the snapshot engine. Implements consolidated exclusion logic, token counting via tiktoken, GFM header generation, and the doctrinal prompt foundry for Awakening Seeds. |

## 📁 Context-Bundler

| Script | Description |
| :--- | :--- |
| [`bundle.py`](plugins/context-bundler/scripts/bundle.py) | Bundles multiple source files into a single Markdown Context Bundle based on a JSON manifest, supporting directory expansion and file tagging. |
| [`manifest_manager.py`](plugins/context-bundler/scripts/manifest_manager.py) | Primary CLI for Context Bundler manifest management, handling initialization, adding/removing files, and invoking the bundling process. |
| [`path_resolver.py`](plugins/context-bundler/scripts/path_resolver.py) | Standardizes path resolution across platforms and provides access to the Master Object Collection for artifact mapping. |

## 📁 Investment-Screener

| Script | Description |
| :--- | :--- |
| [`fetch_financials.py`](tools/investment-screener/backend/py_services/fetch_financials.py) | fetch_financials.py |
| [`fetch_portfolio_heatmap.py`](tools/investment-screener/backend/py_services/fetch_portfolio_heatmap.py) | fetch_portfolio_heatmap.py |
| [`fetch_portfolio_snapshot.py`](tools/investment-screener/backend/py_services/fetch_portfolio_snapshot.py) | fetch_portfolio_snapshot.py |
| [`persist_projection.py`](tools/investment-screener/backend/py_services/persist_projection.py) | persist_projection.py |

## 📁 Json-Hygiene

| Script | Description |
| :--- | :--- |
| [`find_json_duplicates.py`](plugins/json-hygiene/scripts/find_json_duplicates.py) | JSON Hygiene utility that detects duplicate keys in dictionary/map structures using a regex-based heuristic. Identifies potential data overwrites that standard JSON parsers would silently resolve by the "last winner wins" rule. |

## 🔗 Link-Checker

| Script | Description |
| :--- | :--- |
| [`check_broken_paths.py`](plugins/link-checker/scripts/check_broken_paths.py) | Recursively scans documentation files for broken relative links, ensuring documentation integrity and cross-referencing accuracy. |
| [`map_repository_files.py`](plugins/link-checker/scripts/map_repository_files.py) | Mapper tool that indexes a directory structure to create a filename-to-path registry, enabling discovery and automated repair of relative documentation links. |
| [`smart_fix_links.py`](plugins/link-checker/scripts/smart_fix_links.py) | Link Repair tool that auto-corrects broken documentation links using fuzzy matching against a pre-generated file inventory. Handles ambiguous matches and markups missing references. |

## 📁 Mermaid-Export

| Script | Description |
| :--- | :--- |
| [`export_mmd_to_image.py`](plugins/mermaid-export/scripts/export_mmd_to_image.py) | A utility to render Mermaid (.mmd) diagrams into PNG or SVG images using mermaid-cli, supporting batch processing and timestamp-based obsolescence checks. |

## 📁 Plugin-Bridge

| Script | Description |
| :--- | :--- |
| [`bridge_installer.py`](plugins/plugin-bridge/scripts/bridge_installer.py) | Universal Plugin Installer that deploys Agent Plugins (.claude-plugin structure) into target environments. It handles content transformation for platform-specific syntax (Antigravity, GitHub Copilot, Gemini) and manages namespacing to prevent command collisions. |

## 📁 Rlm-Factory

| Script | Description |
| :--- | :--- |
| [`cleanup_cache.py`](plugins/rlm-factory/scripts/cleanup_cache.py) | RLM Cleanup utility to remove stale (missing files) and orphan (not in manifest) entries from the RLM ledger. |
| [`distiller.py`](plugins/rlm-factory/scripts/distiller.py) | RLM Orchestration Engine that recursively summarizes repository contents using the Ollama API. Supports manifest-driven targeted distillation, incremental updates based on modification time, and agent-driven Flash Distill via summary injection. |
| [`inventory.py`](plugins/rlm-factory/scripts/inventory.py) | RLM Audit utility that validates the coverage and consistency of the semantic ledger against the physical filesystem. Reports on missing files, stale cache entries, and overall coverage percentages. |
| [`query_cache.py`](plugins/rlm-factory/scripts/query_cache.py) | RLM Search Utility providing instant O(1) lookup of the semantic ledger. Enables keyword-based discovery across file paths, generated summaries, and content hashes for both project documentation and tool inventories. |
| [`rlm_config.py`](plugins/rlm-factory/scripts/rlm_config.py) | Centralized configuration and utility logic for the RLM Toolchain. Implements the Manifest Factory pattern to resolve manifests and caches based on Analysis Type (Project vs. Tool). |

## 🚀 Root

| Script | Description |
| :--- | :--- |
| [`cli.py`](tools/cli.py) | Unified Command Router for the InvestmentToolkit system. Acts as the project-level entry point, coordinating vector database operations, context bundling, RLM searching, and agent workflow orchestration by dispatching commands to specialized plugin-resident scripts. |
| [`manage_servers.py`](tools/manage_servers.py) | Infrastructure Management utility for the InvestmentToolkit development environment. Orchestrates the lifecycle of the Node.js backend and Vite frontend, manages process termination via port-affinity and ghost hunting, and provides CLI tools for Questrade token seeding and system status checks. |

## 📁 Task-Manager

| Script | Description |
| :--- | :--- |
| [`task_manager.py`](plugins/task-manager/scripts/task_manager.py) | Lightweight Kanban Task Manager that provides a JSON-backed board with lanes (backlog, todo, in-progress, done). It serves as a standalone, plugin-resident replacement for task tracking, featuring transition notes and rich metadata support. |

## 📁 Tool-Inventory

| Script | Description |
| :--- | :--- |
| [`cleanup_cache.py`](plugins/tool-inventory/scripts/cleanup_cache.py) | cleanup_cache.py (CLI) |
| [`distiller.py`](plugins/tool-inventory/scripts/distiller.py) | RLM Engine for recursive summarization of repository content using Ollama to build a semantic knowledge base. |
| [`inventory.py`](plugins/tool-inventory/scripts/inventory.py) | RLM Auditor that reports the synchronization coverage of the semantic tool ledger against the actual plugin scripts on disk. |
| [`manage_tool_inventory.py`](plugins/tool-inventory/scripts/manage_tool_inventory.py) | Comprehensive CLI manager for Tool Inventories. Orchestrates CRUD operations on tool_inventory.json, triggers RLM distillation for consistency, and generates markdown documentation. |
| [`query_cache.py`](plugins/tool-inventory/scripts/query_cache.py) | RLM Search utility providing instant semantic search of the ledger by matching terms against file paths, summaries, or content hashes. |
| [`rlm_config.py`](plugins/tool-inventory/scripts/rlm_config.py) | Centralized configuration and utility logic for the RLM Toolchain. Implement the 'Manifest Factory' pattern (ADR-0024) to dynamically resolve manifests and cache files based on the Analysis Type (Legacy vs Tool). This module is the Single Source of Truth for RLM logic. |
| [`tool_chroma.py`](plugins/tool-inventory/scripts/tool_chroma.py) | Embedded ChromaDB wrapper for the tool-inventory plugin, providing a dedicated vector store for semantic tool discovery. |

## 📁 Vector-Db

| Script | Description |
| :--- | :--- |
| [`cleanup.py`](plugins/vector-db/scripts/cleanup.py) | Vector Consistency tool that prunes stale chunks (missing files) and orphan chunks (excluded by manifest) from the ChromaDB collection. |
| [`ingest.py`](plugins/vector-db/scripts/ingest.py) | Vector Ingestion engine that chunks code and documentation files, calculates embeddings via HuggingFace models, and persists them into ChromaDB. Supports Super-RAG context injection by prepending RLM summaries to document chunks. |
| [`ingest_code_shim.py`](plugins/vector-db/scripts/ingest_code_shim.py) | Source Code Transformer that converts XML, SQL, JSON, Python, and JavaScript/TypeScript files into searchable Markdown. Specifically optimized for Oracle Forms XML and SQL definitions to enhance semantic search precision. |
| [`query.py`](plugins/vector-db/scripts/query.py) | Vector Retrieval CLI providing a semantic search interface for the repository collection. Supports similarity-based document search, database statistics, and structured JSON output. |

## 📁 Workflow-Inventory

| Script | Description |
| :--- | :--- |
| [`workflow_inventory_manager.py`](plugins/workflow-inventory/scripts/workflow_inventory_manager.py) | Inventory manager for agent workflows (.agent/workflows/*.md). Scans, parses frontmatter, and generates both a JSON registry and a human-readable WORKFLOW_INVENTORY.md. |
