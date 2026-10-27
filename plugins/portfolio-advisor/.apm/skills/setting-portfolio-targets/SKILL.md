---
name: setting-portfolio-targets
plugin: portfolio-advisor
description: Sets and defends portfolio targets. Covers writing and calibrating target weights, valuation-gated rebalancing, the strategic review and opportunity scan, the portfolio health check, thesis pitching and review, thesis breakers, pre-trade analysis and YTD return. Trigger on /strategic-review, /review-portfolio, /rebalance, /calibrate-targets, "update the targets", "calibrate targets", "rebalance the portfolio", "strategic review", "portfolio health", "review this thesis", "set thesis breakers", "pre-trade analysis" or "what is my YTD return".
allowed-tools: Bash, Read, Write
---

# Setting Portfolio Targets

The decision layer: target weights, thesis structure and the checks around a trade. A target change is a stance change, so it is made only from analysis saved this cycle or an explicit owner decision.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

From the repository root (paths starting with `scripts/` or `assets/` are relative to this skill's folder):

```bash
python3 investment_screener/backend/py_services/update_targets.py --show
python3 scripts/scan_opportunities.py --format summary
```

## Workflow

1. Match the request to a mode and read its mode file.
2. Begin with the review gate (`review_gate.py verify` must exit 0) so every change rests on analysis saved this cycle (procedure: [Keeping recommendations coherent](references/recommendation-coherence.md) section 0).
3. Make changes only with the owner's answer, one decision at a time, and state the weight a trade produces and the target that fits it.
4. Persist with `update_targets.py --write`, then run the review gate and the closing refresh.

## Constraints

- **Targets sum to 100.00% (tolerance 0.05%)**; no holding above 15% and no pillar above 40% post-trade; minimum trade $200, at least 2% uninvested cash, single-session buys capped at $15,000.
- **Never propose buying a SELL-rated holding to correct drift** without an explicit human override.
- **Capital sourcing**: every buy names the PSU-U.TO shares sold in the same account first (Rule 17); orders are placed only by the owner.
- **SQLite authoritative**: holdings and targets come from `domain_model.sqlite`, never from a file.
- **Standing decisions** stand unless the fair-value delta is over 15% or a confirmed catalyst occurred.
- **Human authority**: the owner has the final say; record explicit overrides and proceed. Present holdings one at a time; never batch-skip.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [update-targets](references/modes/update-targets.md) | "update the targets" | Mechanical write of agreed weights with `update_targets.py` |
| [calibrate-targets](references/modes/calibrate-targets.md) | `/calibrate-targets` | Interactive per-holding calibration to a 100% sum |
| [rebalance](references/modes/rebalance.md) | `/rebalance` | Valuation-gated trade plan with the risk-officer gate and PSU-U.TO funding |
| [strategic-review](references/modes/strategic-review.md) | `/strategic-review` | Opportunity scan, critical assessment, Socratic menu, dossier |
| [portfolio-health](references/modes/portfolio-health.md) | `/review-portfolio` | Drift, pillar conviction and thesis formula score |
| [thesis-review](references/modes/thesis-review.md) | "review this thesis" | Pitch or challenge a thesis through the `thesis-review-agent` |
| [set-thesis-breakers](references/modes/set-thesis-breakers.md) | "set thesis breakers" | Define 2-3 measurable invalidation conditions per holding |
| [pre-trade-analysis](references/modes/pre-trade-analysis.md) | "pre-trade analysis" | The mandatory 5-point pre-trade briefing |
| [ytd-return](references/modes/ytd-return.md) | "YTD return" | Simple and time-weighted return adjusted for cash flows |

## Scripts

- `scripts/`: `generate_review.py` (strategic-review dossier), `scan_opportunities.py` (ranked opportunity scan).
- Shared engine (`py_services/`): `update_targets`, `validate_weights`, `portfolio_action`, `relabel_actions`, `recommendation`, `review_gate`, `set_standing_decision`, `update_thesis`, `generate_review_json`, `generate_portfolio_blueprint`, `apply_catalyst`, `verify_refresh`, `ytd_return`.
- `assets/templates/`: `PortfolioAnalysisRecommendations.md`, `portfolio_analysis_recommendations_template.json`, `target_portfolio_template.json`, `thesis_proposal_template.md`, `ytd_performance_report_template.json`. Tests: `tests/` (pass the path explicitly).

## Verification

- `validate_weights.py --mode target`, `verify_refresh.py` and `verify_screener_integrity.py` pass; `review_gate.py verify` exits 0.
- The new stance appears in `recommendation.py --all` and in the app.
- Routing cases for every mode are in `evals/evals.json`.

## References

- [Keeping recommendations coherent](references/recommendation-coherence.md) (owner of this document), [thesis page currency](references/thesis-page-currency.md), [fallback tree](references/fallback-tree.md).
- [Strategic review prompt](references/strategic_review_prompt.md), [rebalance prompt](references/rebalance_prompt.md), [professional investment framework](references/definitive_professional_investment_framework.md).
- Sibling skills: `valuing-investments` (valuations and intake) and `running-portfolio-reviews` (daily and weekly loops).
