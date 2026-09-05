---
description: Mandatory rule forbidding hardcoded absolute user/computer paths across all plugins, skills, scripts, rules, and documentation.
globs: ["**/*.md", "**/*.py", "**/*.js", "**/*.ts", "**/*.json", "**/*.pine"]
---

# No Hardcoded Absolute Machine Paths Rule

## 1. Non-Negotiable Invariant
Hardcoding absolute local user or machine filesystem paths (e.g. `~/...`, `C:\Users\...`, `/home/...`) is strictly prohibited in all:
- Plugins and Skills (`SKILL.md`, references, evals, scripts)
- Source code (TypeScript, Python, JavaScript, Shell scripts)
- Indicator definitions (Pine Script)
- Rules and documentation (`.agent/rules/`, `AGENTS.md`, `README.md`, `architecture.md`)
- Configuration and lock files (`marketplace.json`, `plugin.json`, `symlinks.json`)

---

## 2. Path Formatting Standards

### A. Inside Skills & Plugins
Always use **skill-root-relative** paths:
- **Correct**: `references/chart-types-reference.md` or `../scripts/helper.py` or `./scripts/task_manager.py`
- **Incorrect**: `/Users/.../plugins/tradingview/references/chart-types-reference.md`

### B. Inside Python & Node Scripts
Derive paths dynamically using standard library utilities:
- **Python**: `Path(__file__).resolve().parent` or `Path.cwd()` or `os.environ.get("WORKSPACE_ROOT")`
- **Node/TS**: `path.resolve(__dirname, '...')` or `process.cwd()`
- **Incorrect**: `const root = "/Users/..."`

### C. Markdown Links
Use repository-relative or skill-relative paths:
- **Correct**: `[Chart Types Reference](references/chart-types-reference.md)`
- **Incorrect**: `[Chart Types Reference](file://~/...)`

---

## 3. Pre-Commit / Audit Check
Before completing any task or pushing to source control, run an audit grep to guarantee zero occurrences:
```bash
git grep "/Users/" || true
```
Any matches must be immediately converted to relative or environment-derived paths.
