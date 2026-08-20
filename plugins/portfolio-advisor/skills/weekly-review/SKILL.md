---
name: weekly-review
plugin: portfolio-advisor
description: >
  Run range-based weekly review sweep, calculate week-over-week price moves across holdings,
  and generate the weekly research sweep prompt for Grok.
  Trigger on /weekly-review, "run weekly review", or "generate weekly grok prompt".
allowed-tools: Bash, Read, Write
---

# Weekly Review Skill

**Trigger:** `/weekly-review` or `run weekly review`

---

## Purpose
Runs a comprehensive weekend drift audit, analyzes week-over-week performance deltas, and prepares the custom weekly news prompt for Grok/X.com.

---

## Execution
Run the canonical weekly review script:
```bash
python3 plugins/portfolio-advisor/scripts/weekly_review.py --prompt-output temp/weekly_grok_prompt.md
```

---

## Next Steps
1. Inspect the generated Grok prompt in `temp/weekly_grok_prompt.md`.
2. Paste into Grok for catalytic event analysis.
3. Review any suggested target weight or pillar calibrations.
