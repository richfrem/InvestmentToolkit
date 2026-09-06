---
name: daily-loop
plugin: portfolio-advisor
description: >
  The single master daily command. Supports --scan for fast morning brief,
  or default interactive loop guiding through: portfolio freshness -> brief ->
  triage -> action cards -> self-evolution. Enforces deterministic receipt verification.
  Triggered by /daily or 'start my day'.
allowed-tools: Bash, Read, Write
---

# /daily - Interactive Daily Investment Loop

Switch to the daily-loop-agent persona by reading:
plugins/portfolio-advisor/agents/daily-loop-agent.md

### Execution Modes
- Fast Non-Interactive Brief:
  python3 plugins/portfolio-advisor/scripts/run_daily.py --scan
- Full Interactive Institutional Loop:
  python3 plugins/portfolio-advisor/scripts/run_daily.py

### Deterministic Verification Mandate
At completion of the daily loop, execute the deterministic verifier against context/control_plane.db:
python3 plugins/portfolio-advisor/scripts/verify_daily_run.py --latest

Then begin Step 0 (Readiness Check) immediately - no introduction needed.
