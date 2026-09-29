---
name: daily-loop
plugin: portfolio-advisor
description: >
  The single master daily command (absorbed the former daily-brief skill). --scan runs
  the fast non-interactive morning brief (macro regime, conviction-scored REDUCE /
  ACCUMULATE lists, binary events, score deltas); the default interactive loop guides:
  portfolio freshness -> brief -> triage -> action cards -> self-evolution, with
  deterministic receipt verification. Trigger on /daily, /daily --scan, 'start my day',
  'daily scan', 'morning scan', 'run daily brief', /daily-brief, or 'what should I do today'.
allowed-tools: Bash, Read, Write
---

# /daily - Daily Investment Loop

Paths below are relative to this skill's folder.

Switch to the `daily-loop-agent` persona (portfolio-advisor plugin agent) for the
interactive loop. Read `references/daily-brief-methodology.md` before presenting any
brief: it holds the macro gate, binary event protocol, routing table and execution
rules that the brief must follow.

### Execution Modes
- Fast non-interactive brief ("daily scan" / "morning scan"):
  `python3 scripts/run_daily.py --scan`
  The runner records receipts only. Present the brief from the day's saved JSON,
  `investment_screener/backend/data/daily-briefs/YYYY-MM-DD.json` (also stored as a
  `REVIEW_DAILY` ledger event), using the methodology reference.
- Full interactive institutional loop:
  `python3 scripts/run_daily.py`

A failed brief ends the run as FAILED (non-zero exit, FAILED terminal receipt); report the
error instead of presenting stale data.

### Deterministic Verification Mandate
At completion, verify the run against context/control_plane.db:
`python3 scripts/verify_daily_run.py --latest`

Then begin Step 0 (Readiness Check) immediately - no introduction needed.
