# Analysis Tools

This directory contains the core utilities for the Antigravity Command System.

> **Tool Inventory:** For a complete, auto-generated list of all 75+ scripts with their locations and descriptions, see **[`TOOL_INVENTORY.md`](TOOL_INVENTORY.md)**.

## Directory Structure

### `ai-resources/`
Centralized resources for AI/LLM assistance.
*   **`prompts/`**: System Prompts and Task Prompts.
*   **`checklists/`**: Context gathering validation lists.

### `codify/`
Tools for generating code, documentation, diagrams, and tracking progress.
*   **`documentation/`**: Overview generators (Forms, Reports, Libraries).
*   **`diagrams/`**: Dependency graph generation (Mermaid, Graphviz).
*   **`rlm/`**: Repository Ledger Model (Intelligence Engine).
*   **`vector/`**: Embedding generation for semantic search.

### `curate/`
Tools for cleaning, organizing, and auditing the repository.
*   **`inventories/`**: Script to generate JSON/CSV inventories of all system objects.
*   **`link-checker/`**: Utilities to find and fix broken documentation links.
*   **`hygiene/`**: Deduplication and cleanup scripts.

### `investigate/`
Tools for deep exploration of the legacy codebase.
*   **`miners/`**: Specialized parsers for XML, PL/SQL, PLL, and DB schemas.
    *   *Includes regex matchers for `OPEN_FORM`, `CALL_FORM`, etc.*
*   **`search/`**: Dependency analysis (`parent_caller_summary.py`), reachability, and logic density scoring.
*   **`menu/`**: Tools for visualizing and querying legacy menu structures (MenuConfig).

### `retrieve/`
Tools for gathering context for the LLM.
*   **`bundler/`**: Creates "Smart Bundles" (single markdown files) of relevant source code.
*   **`vector/`**: Interface for querying the ChromaDB vector store.
*   **`rlm/`**: Interface for querying the RLM high-level summaries.

### `standalone/`
*   **`xml-to-markdown/`**: Node.js utilities for converting raw Oracle Forms XML to human-readable Markdown.

---

## Key Workflows

### 1. Form Relationship Analysis
We use a multi-stage process to map dependencies between forms:

1.  **Code Scanning**: `tools/investigate/miners/search_for_open_form_references.py` scans XML for `OPEN_FORM`, `CALL_FORM`, etc.
    *   *Output:* `legacy-system/reference-data/collections/code-detected/form_relationships.csv`
2.  **Configuration Analysis**: We ingest MenuConfig Menu Rules and Role Reports.
    *   *Source:* `legacy-system/reference-data/collections/menuconfig/`
3.  **consolidation**: `tools/curate/inventories/CreateCombinedListOfRelationships.py` merges these sources into a single source of truth.
    *   *Final Output:* `legacy-system/reference-data/collections/combined-relationships/form_relationships.csv`

### 2. Dependency Visualization
Visual graphs are generated from the combined CSV:
*   **Single Form**: `python tools/codify/diagrams/GenerateFormDependencyGraph.py -form [ID]`
*   **Batch**: `python tools/codify/diagrams/BatchGenerateGraphs.py`

### 3. Documentation Generation
Documentation is managed via the Overview Manager:
*   **Run**: `python tools/codify/documentation/overview_manager.py --id [ID] --type form --create --sync`

