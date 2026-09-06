---
name: daily-loop
plugin: portfolio-advisor
description: >
  The single daily command. Interactively guides through the full day:
  portfolio freshness → morning brief → triage → action cards → self-evolution.
  Enforces deterministic execution verification with temp run artifacts.
  Triggered by /daily or "start my day".
allowed-tools: Bash, Read, Write
---

# /daily — Interactive Daily Investment Loop

Switch to the `daily-loop-agent` persona by reading:
`plugins/portfolio-advisor/agents/daily-loop-agent.md`

### Deterministic Verification Mandate
To prevent skipping steps, all checklist phases must write verification artifacts to a temporary directory:
`temp/daily_run_<TIMESTAMP>/`

At completion of the daily loop, execute the deterministic verifier:
```bash
python3 plugins/portfolio-advisor/scripts/verify_daily_run.py --dir temp/daily_run_<TIMESTAMP>/ --cleanup
```

Then begin Step 0 (Readiness Check) immediately — no introduction needed.
