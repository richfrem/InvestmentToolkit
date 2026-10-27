---
name: running-portfolio-reviews
plugin: portfolio-advisor
description: Runs the recurring portfolio review loops. Covers the daily investment loop (readiness, morning brief, news sweep, triage, action cards, thesis pages), the weekend weekly review, the multi-model news and catalyst sweep with fact-check gate and ledger recording, and the adversarial or external review bundle for outside models. Trigger on /daily, /news-sweep, /adversarial-review, /external-review, "run the daily loop", "morning brief", "check the charts, what should I buy", "weekly review", "weekend drift audit", "news sweep", "prepare an adversarial review" or "bundle the thesis for external review".
allowed-tools: Bash, Read, Write
---

# Running Portfolio Reviews

The daily, weekly and news cycles and the review bundles for outside models. All of them present calls from one source (`recommendation.py --all`) and save before they say.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

From the repository root (paths starting with `scripts/` or `assets/` are relative to this skill's folder):

```bash
python3 scripts/run_daily.py --scan
```

## Workflow

1. Match the request to a mode and read its mode file. On a new trading day run the daily loop's steps 0-3 before answering any buy, sell or chart question.
2. Refresh reality first: positions and trades, then prices, then the review cycle (`review_gate.py begin`).
3. Present only canonical stances; any plan you give (price, size, wait condition, target) is recorded first with the owner's agreement, or labelled "draft, not in the record".
4. Finish with the review gate (`review_gate.py verify` exits 0) and the closing refresh.

## Constraints

- **One source of calls**: stances come from `recommendation.py --all` (`decision_check.effective`); follow [Keeping recommendations coherent](../setting-portfolio-targets/references/recommendation-coherence.md).
- **Gates before any trade price**: the macro gate (RISK-OFF: no new buys; NEUTRAL: only ACCUMULATE scoring at least +4; degraded data counts as RISK-OFF) and the binary-event protocol from the [daily brief methodology](references/daily-brief-methodology.md).
- **AI forward-evidence gate** from the [valuation hub](../valuing-investments/references/ai-forward-valuation.md) before valuation or action proposals for AI-exposed names.
- **Fresh prices**: write prices only through the price scripts, never ad hoc SQL; say so on every card whose price is stale.
- **Never execute live trades in a review**; reviews are analytical, the owner places orders.
- **Fact-check gate** (10Y yield, VIX, quoted prices) before trusting any model's findings; a failing model is excluded from triangulation and you say which and why.
- **Record every sweep** in the ledger (`record_news_sweep.py`); files under `temp/` are working copies only.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [daily-loop](references/modes/daily-loop.md) | `/daily` | The one daily command: readiness, brief, news sweep, triage, action cards, thesis pages, review gate |
| [weekly-review](references/modes/weekly-review.md) | weekend review | Drift audit, week-over-week moves, multi-model research prompt, calibration, thesis pages |
| [news-sweep](references/modes/news-sweep.md) | `/news-sweep` | Generate the sweep prompt, run it across models, fact-check, triangulate, record |
| [external-review](references/modes/external-review.md) | `/adversarial-review`, `/external-review` | Build the review bundle (prompt, thesis, targets, projections) for an outside model |

## Scripts

- `scripts/`: `run_daily.py`, `verify_daily_run.py`, `daily_receipts.py`, `news_sweep.py`, `record_news_sweep.py`, `weekly_review.py`.
- Shared engine (`py_services/`): `daily_brief`, `generate_news_prompt`, `refresh_all`, `review_gate`, `update_price_levels`, `rebaseline_targets`, `thesis_currency`, `set_standing_decision`, `update_targets`, `verify_refresh`, `generate_reports`.
- `assets/templates/`: `daily_sweep`, `weekly_sweep`, `daily_report`, `weekly_report`, `thesis-challenge-prompt`. Tests: `tests/` (pass the path explicitly).

## Verification

- `python3 scripts/verify_daily_run.py --latest`, `verify_refresh.py` and `verify_portfolio_invariants.py` pass; after a price refresh `CASH_INVARIANT` reports no discrepancy.
- Every price, size or wait condition told to the owner appears in the record and in the app.
- Routing cases for every mode are in `evals/evals.json`.

## References

- [Daily brief methodology](references/daily-brief-methodology.md), [news sweep model assessment](references/news-sweep-model-assessment.md), [evolution log](references/evolution-log.md).
- [Thesis page currency](../setting-portfolio-targets/references/thesis-page-currency.md) protocol, used by every loop that refreshes thesis pages.
- Sibling skills: `setting-portfolio-targets` (targets, rebalance, strategic review) and `valuing-investments` (valuations).
