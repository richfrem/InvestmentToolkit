---
name: 13f-analyze
plugin: portfolio-advisor
description: Surgical 13F analysis skill. Cross-references the latest SA LP 13F filing diff against target-portfolio.json to produce gated INITIATE/ACCUMULATE/TRIM/EXIT recommendations and updates targets.
---

# 13F Analysis

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)

## Constraints
- Apply Phase 3 gates before presenting recommendations (Gate A: SA calls != equity signal; Gate B: no INITIATE on DCF SELL-rated if SA closed; Gate C: SA close != immediate exit if high conviction; Gate D: max 15% position weight, 100% total sum).
- Never blindly follow fund moves; flag thesis contradictions as CONFLICT.
- Lock actual broker weights during sector liquidations to avoid normalization drift.
- Always update `agentRationale` for modified holdings.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/fetch_13f.py --cik 0002045724 --poll
```

## Workflow
1. **Poll & Load**: Check EDGAR for new filings via `fetch_13f.py --poll`. Load diff JSON and `investment_screener/backend/data/theses/target-portfolio.json`.
2. **Cross-Reference**: Match SA LP changes against portfolio targets, standing decisions, and DCF fair-value ratings.
3. **Gate Signals**: Evaluate gates A through E (INTC call options, weight ceilings, conviction exceptions).
4. **Present Gated Table**: Display approved, conflict, and blocked actions with rationale.
5. **Apply Targets**: Apply approved targets using `update_targets.py --set ... --write --blueprint` or `lock_and_normalize_targets.py`. Update metadata in `investment_thesis.md`.

## Verification
```bash
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
python3 investment_screener/backend/py_services/verify_thesis_sync.py
```
