# ADR 024 — Extract tradingview-cdp to Project Root as a Shared Runtime Dependency

**Date:** 2026-05-17
**Status:** Proposed
**Deciders:** richfrem
**Scope:** plugins/tradingview/, all TradingView skills, project-root infrastructure

---

## Context
The TradingView CDP automation layer requires a heavy, multi-file Node.js execution environment (`chrome-remote-interface` and other dependencies). Previously, this environment lived inside the `plugins/tradingview/node/` directory.

However, our plugin installation tools (`npx skills add` and `uvx plugin-add`) strictly enforce file-level symlinks and silently drop directory-level symlinks to maintain plugin portability and decoupling. As a result, when a TradingView skill (like `pine-inject` or `place-order`) was installed elsewhere, it lacked the massive `node/` directory required for execution, breaking its functionality. Manually creating file-level symlinks for every file in a `node_modules` structure is brittle, unmaintainable, and defeats the purpose of modular skills.

We needed a way for skills to depend on a multi-file Node execution environment without violating the symlink rules or forcing complex setups inside individual skills.

## Decision
We decided to adopt a **"Thin Skill + Thick Engine"** approach, conceptually similar to Model Context Protocol (MCP) servers:

1. **Extract to Root:** Move the entire `plugins/tradingview/node/` directory to the project root and rename it to `tradingview-cdp/`. This establishes it as a standalone, shared runtime dependency.
2. **Install Once:** The `tradingview-cdp` package is initialized once (`npm ci`) at the project root, rather than being distributed inside individual skills via symlinks.
3. **Robust Path Resolution:** Rewrite the Python wrappers (like `tv_client.py`) to act as the single source of truth for locating the engine. Rather than relying on fragile relative paths (`parents[3]`), the client will:
   - Check the `TV_CDP_DIR` environment variable.
   - Walk up the directory tree to find `tradingview-cdp/cli.js`.
   - Provide a clear, actionable error message if the engine is not found or not set up.
4. **Refactor Invocations:** Update all core TradingView Python scripts to use the centralized `tv_client.py` resolver instead of hardcoding Node paths. Update skill markdown files (e.g., `pine-inject/SKILL.md`) to call their respective Python wrappers for complex operations like order placement or pine script injection.
   - **Exception for Read-Only Chart Utilities:** Direct Node CLI calls (`node tradingview-cdp/cli.js`) remain explicitly permitted in skill files (e.g., `chart-snapshot` or `technical-analysis-expert`) when executing simple, read-only chart utilities (like taking a screenshot, changing timeframe, or reading indicator status). This avoids unnecessary Python wrapper boilerplate for commands that do not interact with the backend data layers.

## Consequences
- **Positive:**
    - Skills remain lightweight, portable, and compliant with file-level symlink rules.
    - Eliminates plugin installation failures related to the Node environment.
    - Centralized management of the Node runtime reduces duplication.
    - Robust path resolution handles various deployment and CI scenarios gracefully via environment variables.
- **Negative:**
    - Introduces an external runtime dependency (`tradingview-cdp`) that must be explicitly managed and installed at the project level, slightly increasing global setup overhead.

## Alternatives Considered
- **Git Submodules:** Complex for end users to manage during standard plugin installations.
- **Bundling (e.g., `esbuild`/`pkg`):** Compiling the Node environment into a single executable binary for each platform. Adds significant build complexity and maintenance burden compared to simply exposing the Node project.
- **Updating Plugin Installer:** Modifying the installer to allow directory symlinks. Rejected because it violates the foundational architectural constraints defined for strict plugin decoupling.