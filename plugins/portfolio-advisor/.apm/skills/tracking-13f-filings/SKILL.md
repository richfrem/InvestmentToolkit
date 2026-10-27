---
name: tracking-13f-filings
plugin: portfolio-advisor
description: Tracks institutional 13F filings and acts on them. Polls SEC EDGAR for new 13F-HR filings from target funds, parses holdings and computes quarter-over-quarter diffs, then cross-references the changes against the thesis holdings to produce gated INITIATE, ACCUMULATE, TRIM or EXIT recommendations. Trigger on /13f-tracker, /13f-analyze, "check for new 13F filings", "13F diff", "what did the fund buy" or "analyze the 13F".
allowed-tools: Bash, Read, Write
---

# Tracking 13F Filings

A data source plus the gate that decides whether it should change anything. Following a fund is never a reason by itself to change a target.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

From the repository root (paths starting with `scripts/` are relative to this skill's folder):

```bash
python3 scripts/fetch_13f.py --cik 0002045724 --poll
```

## Workflow

1. Match the request to a mode: `track` fetches and diffs, `analyze` turns the diff into gated recommendations.
2. Poll first; analyze only against the latest diff.
3. Apply the gates, present the table, and apply approved targets only with the owner's go-ahead.

## Constraints

- **EDGAR etiquette**: about 10 requests per second at most; back off when throttled.
- **Data location**: parsed holdings and diffs are stored in `investment_screener/backend/data/13f/`.
- **Never blindly follow a fund's moves**; thesis contradictions are flagged CONFLICT.
- **Gates for analysis**: A (a fund's call is not an equity signal), B (no INITIATE on a DCF SELL rating if the fund closed), C (a fund closing is not an immediate exit for a high-conviction holding), D (max 15% per position, 100% total).
- Lock actual broker weights during sector liquidations to avoid normalization drift; always update `agentRationale` for modified holdings.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [track](references/modes/track.md) | `/13f-tracker` | Poll EDGAR, download and parse new filings, diff against the prior quarter, export JSON |
| [analyze](references/modes/analyze.md) | `/13f-analyze` | Cross-reference the diff with thesis holdings, apply gates A-E, apply approved targets |

## Scripts

- `scripts/fetch_13f.py`: `--poll`, `--summary`, `--diff` for a CIK (Situational Awareness LP is `0002045724`).
- Shared engine (`py_services/`): `update_targets`, `refresh_all`, `verify_refresh`, `generate_review_json`.

## Verification

- `python3 scripts/fetch_13f.py --cik 0002045724 --summary` and `--diff` print the latest filing and changes.
- After applying targets: `python3 investment_screener/backend/py_services/verify_refresh.py` and `verify_thesis_sync.py` pass.
- Routing cases for both modes are in `evals/evals.json`.

## References

- The `setting-portfolio-targets` skill (targets and the recommendation-coherence rules) and `running-portfolio-reviews` (the closing refresh).
