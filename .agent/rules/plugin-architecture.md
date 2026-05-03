---
description: >
  Canonical rules for all plugin and skill work: file structure, symlinks, resource sharing,
  installer compatibility, loose coupling, and cross-plugin boundaries.
  Encodes ADR-001 through ADR-006. READ THIS before touching any file in plugins/ or symlinks.json.
globs:
  - "plugins/**/SKILL.md"
  - "plugins/**/scripts/*.py"
  - "plugins/**/references/**"
  - "plugins/**/assets/**"
  - "symlinks.json"
---

# Plugin & Skill Rules — Canonical Reference (ADR-001 – ADR-006)

> Full ADR text lives at: `.agents/skills/create-plugin/references/ADRs/`
> Violations break plugin installation, portability, or future-compatibility. All rules are mandatory.

---

## 1. One File, One Location — Zero Duplication (ADR-002, ADR-003)

Every script, reference doc, and asset template has **exactly one canonical copy**: the plugin root.
Skills access them via file-level symlinks. Never copy a file; never put a real file inside a skill subfolder.

```
plugins/<plugin-name>/
  scripts/            ← REAL files, canonical (never duplicated)
  assets/
    templates/        ← REAL files, canonical
  references/         ← REAL files, canonical
  skills/
    <skill-name>/
      SKILL.md        ← real file (skill-specific)
      scripts/        ← real directory; contains ONLY file-level symlinks → ../../../scripts/
      assets/
        templates/    ← real directory; contains ONLY file-level symlinks → ../../../../assets/templates/
      references/     ← real directory; contains ONLY file-level symlinks → ../../../references/
```

**❌ PROHIBITED:** A real `.py` file or `.md` file inside `skills/<skill>/scripts/`, `skills/<skill>/references/`, or `skills/<skill>/assets/`. It must be a symlink.

---

## 2. File-Level Symlinks Only — Never Directory-Level (ADR-003)

`npx skills add` and the `uvx` plugin installer silently **drop** directory-level symlinks. Only file-level symlinks survive installation.

```bash
# ✅ Correct — file-level symlinks
skills/<skill>/scripts/foo.py          → ../../../scripts/foo.py
skills/<skill>/references/bar.md       → ../../../references/bar.md
skills/<skill>/assets/templates/T.md   → ../../../../assets/templates/T.md

# ❌ Wrong — directory-level symlink (silently dropped by installer)
skills/<skill>/scripts                 → ../../../scripts
```

**Symlink depth from skill subfolder to plugin root:**
| Skill subfolder | Depth to plugin root |
|---|---|
| `skills/<skill>/scripts/` | `../../../` (3 up) |
| `skills/<skill>/references/` | `../../../` (3 up) |
| `skills/<skill>/assets/templates/` | `../../../../` (4 up) |

---

## 3. Symlinks Must Stay Inside the Plugin Tree (ADR-001, ADR-003)

Skill-level symlinks must point to the **plugin root** (`../../../references/`, `../../../scripts/`). They must **not** jump outside the plugin to live data files, `.agents/`, or sibling plugins.

```bash
# ✅ Correct — stays within plugin tree
# From: plugins/portfolio-advisor/skills/strategic-review/references/portfolio.json
ln -s ../../../references/portfolio.json portfolio.json
# (plugin root references/ may itself symlink to investment_screener/ — that's fine at root level)

# ❌ Wrong — jumps outside plugin to live data
ln -s ../../../../investment_screener/frontend/src/data/portfolio.json portfolio.json

# ❌ Wrong — jumps to .agents/ (different install tree)
ln -s ../../../../.agents/skills/.../portfolio.json portfolio.json
```

> **Why this breaks the installer:** When `_copy_resolving_pointers` copies a skill to `.agents/`, it resolves symlinks. If both the source symlink and the `.agents/` destination symlink resolve to the **same inode** (e.g. both point at `investment_screener/frontend/src/data/portfolio.json`), Python's `shutil.copy2` raises `SameFileError` and the plugin fails to install.

---

## 4. Always Use symlink_manager.py — Never Raw `ln -s` (ADR-003)

```bash
# Step 1: Diagnose current state
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose

# Step 2: Add entries to symlinks.json, then restore all
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py restore

# Step 3: Verify — must show zero "regular file (not a link)" or "broken symlink"
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose
```

**❌ NEVER** call `ln -s` directly — it bypasses the manifest and the link won't be recreated on fresh checkout or on other machines.

The symlinks.json manifest is the single source of truth for all symlinks in this repo.

---

## 5. Hub-and-Spoke: Script Placement Based on Usage Scope (ADR-002)

| Script used by | Where it lives |
|---|---|
| **One skill only** | `plugins/<plugin>/skills/<skill>/scripts/` as a **real file** |
| **Two or more skills** | `plugins/<plugin>/scripts/` as a **real file** + file-level symlink in each skill |

Never put a shared script inside a single skill's folder if two skills need it — factor it up to the plugin root.

---

## 6. No Cross-Plugin Script Execution (ADR-001, ADR-004)

Plugins must be **self-contained**. A skill may not execute scripts from a sibling plugin.

```bash
# ❌ Forbidden
python ../../other-plugin/scripts/foo.py
python ${PLUGIN_ROOT}/../other-plugin/scripts/validate.sh

# ✅ Correct — use Agent Skill Delegation instead
# In SKILL.md: "Please invoke the `other-plugin-skill` to perform X."
```

In the **source repo**: cross-plugin file-level symlinks are acceptable for DRY.
At **install time**: the installer resolves all symlinks to real physical copies — installed skills are always self-contained.

---

## 7. SKILL.md Paths Are Relative to Skill Root (ADR-003)

Per the open Agent Skills spec, file references in SKILL.md must be relative to the skill root — not absolute, not backwards traversals.

```markdown
# ✅ Correct — works after install anywhere
python scripts/scan_opportunities.py --format markdown

# ❌ Wrong — absolute path, breaks portability
python /Users/richard/.agents/skills/strategic-review/scripts/scan_opportunities.py

# ❌ Wrong — backwards traversal, breaks after install
python ../../scripts/scan_opportunities.py
```

---

## 8. Loose Coupling — Skills Are Apps, Frameworks Are OS (ADR-005)

- Skills must function **in complete isolation**. A skill must not crash because `agent-agentic-os`, `spec-kitty`, or any other orchestration framework is absent.
- Skills must **never hard-code dependencies** on transitional frameworks for their core execution.
- Cross-plugin coordination happens via **natural language Agent Delegation** only — never via hardcoded Python imports, hidden filesystem state, or shared memory structures.
- When native AI SDKs eventually absorb orchestration features, skills must survive the transition untouched.

---

## 9. Plugin Installer Compatibility (ADR-006)

The `uvx --from git+... plugin-add` installer:
- Resolves all **file-level symlinks** → real physical copies in `.agents/` (self-contained)
- **Silently drops** directory-level symlinks → installed skill gets empty directory (silent failure)
- Source tree = DRY with symlinks; Installed tree = fully self-contained real files

---

## Pre-Commit Checklist

```
[ ] All scripts/assets/references have ONE real file at plugin root — no duplicates
[ ] skills/<skill>/scripts/     contains ONLY file-level symlinks (no real .py files)
[ ] skills/<skill>/references/  contains ONLY file-level symlinks (no real .md files)
[ ] skills/<skill>/assets/      contains ONLY file-level symlinks
[ ] Symlinks stay within the plugin tree (../../../scripts/, ../../../references/)
[ ] symlinks.json is updated and `symlink_manager.py diagnose` shows zero issues
[ ] SKILL.md uses relative paths from skill root (python scripts/foo.py)
[ ] No cross-plugin script execution anywhere
[ ] Skills work in isolation — no hard framework dependencies
```
