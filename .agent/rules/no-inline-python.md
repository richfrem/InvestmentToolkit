---
description: >
  Never run ad-hoc inline Python snippets for logic that might be reused.
  Extract to a versioned .py script in the canonical location, add symlinks
  via symlink_manager.py, and reference from SKILL.md. This encodes the
  CLAUDE.md "Fix Once, Reuse Always" calculation policy.
globs:
  - "plugins/**/scripts/*.py"
  - "plugins/**/skills/**/SKILL.md"
---

# Rule: No Inline Python — Create Scripts Instead

## The Rule

**NEVER write multi-line Python logic directly in a Bash tool call** when that logic:
- Could be run more than once across sessions
- Computes financial data, derives actions, generates files, or validates state
- Relies on project-specific imports (validate_weights, portfolio_action, etc.)

Instead:
1. **Write a proper `.py` file** in `plugins/<plugin>/scripts/`
2. **Add it to `symlinks.json`** and run `symlink_manager.py restore`
3. **Reference it from SKILL.md** using relative path `python scripts/my_script.py`

---

## Canonical Script Locations

| What it does | Where it goes |
|---|---|
| Financial calculation, data derivation | `plugins/<plugin>/scripts/` |
| Used by only one skill | `plugins/<plugin>/skills/<skill>/scripts/` (real file) |
| Used by multiple skills | `plugins/<plugin>/scripts/` + symlinks via `symlinks.json` |
| Backend convenience alias | `investment_screener/backend/py_services/` (symlink) |

---

## When Inline Python IS Acceptable

- One-liners to inspect a value or print a quick check
- Ad-hoc debugging during a session (not a repeating pattern)
- Logic that will never run again and has no output worth keeping

The test: **"Would I want to run this again next session?"** If yes → write a script.

---

## Workflow for New Scripts

```bash
# 1. Write the canonical script
# plugins/<plugin>/scripts/my_script.py

# 2. Add symlinks for each skill that needs it
# In symlinks.json, add entries for skills/*/scripts/my_script.py

# 3. Restore and verify
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py restore
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose

# 4. Reference from SKILL.md using relative path
# python scripts/my_script.py --args
```

---

## Related Rules and References

- `.agent/rules/symlink-cross-platform.md` — symlink_manager.py protocol
- `.agent/rules/plugin-architecture.md` — canonical ADR-001 through ADR-006
- `CLAUDE.md` — "AI Agent Calculation Policy — Fix Once, Reuse Always"
