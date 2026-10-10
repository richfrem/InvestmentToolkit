---
name: strategic-review
plugin: portfolio-advisor
description: >-
  Master strategic portfolio review and coordinator. Ingests DCF valuations, technical sweeps,
  and live broker balances from SQLite to deliver an honest, adversarial assessment across EXIT,
  TRIM, ACCUMULATE, and INITIATE priorities. Interactively guides the user through strategic
  conflict resolutions (Options 1–5), target calibrations (/calibrate-targets), and rebalancing
  execution (/rebalance-portfolio). Trigger on /strategic-review, "review my portfolio", "overall
  analysis", "critical review", or "recommend top priorities to trim, exit, accumulate, initiate".
allowed-tools: Bash, Read, Write
---

# Strategic Review & Master Portfolio Coordinator

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow (Phases 1–4)](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- **Recommendation coherence**: Follow [Keeping recommendations coherent](references/recommendation-coherence.md) every session: refresh positions and executed trades first (TradingView by default), present `decision_check.effective` as the stance and reconcile any CONFLICT or OUTDATED standing decision with the owner through `set_standing_decision.py`, rank by today's priority with already-acted-on items last, and state every condition against current chart levels rather than as general guidance.
- **SQLite Authoritative**: Live holdings and target weights come strictly from `domain_model.sqlite`; technical telemetry from `intelligence.sqlite`. Never read holdings from a file.
- **Target Invariant**: Target weights must sum to 100.00% (±0.05%); normalize after any adjustment.
- **Position Sizing Caps**: No holding may exceed 15.00% and no strategy pillar may exceed 40.00% of total portfolio.
- **Standing Decision Anchor**: Require >15% Fair Value delta or confirmed fundamental catalysts to revisit standing decisions.
- **Capital Sourcing Invariant**: All buy proposals must identify `PSU-U.TO` shares to sell in the same account first (Rule 17).
- **Refresh Chain**: Write target changes with `update_targets.py --write`, then always finish with the Closing Refresh in Phase 4 (`refresh_all.py --publish`).

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/scan_opportunities.py --format summary
python3 plugins/portfolio-advisor/scripts/scan_opportunities.py
python3 plugins/portfolio-advisor/scripts/generate_review.py
```

## Workflow
### Phase 1: Multi-Source Opportunity Scan
Run `scan_opportunities.py` to ingest cross-asset evidence from SQLite and DCF models into ranked tables:
- **🚨 EXIT Queue**: Canonical EXIT signals, ranked by locked capital; show standing-decision conditions.
- **✂️ TRIM / 🔵 ACCUMULATE**: Canonical signals with drift and technical timing shown separately; targets do not derive the action.
- **🚀 INITIATE Opportunities**: Top unowned watchlist setups with margin of safety (upside $\times$ confidence).
- **⚔️ Strategic Conflicts**: Holdings where Thesis says "HOLD" but DCF says "SELL" (e.g. `MU`, `PANW`, `RIOT`).
- **⚠️ Evidence Gaps & Imminent Catalysts**: Missing material forward drivers, earnings within 14 days, or analyses >90 days old; recently saved models still need the evidence check.

### Phase 2: Executive Critical Assessment
Deliver a non-sugarcoated, honest critique:
- **Pillar Balance & Drift**: Which pillars drive returns vs under stress or over-concentrated.
- **Capital Trapped**: Capital idle in dead-weight EXIT positions or uninvested cash.
- **Key Vulnerabilities**: Strategic conflicts and thesis assumptions misaligned with market reality.

### Phase 3: Interactive Socratic Menu (Options 1–5)
Present a structured, interactive menu of prioritized next steps:
- **`[1] Harvest Capital & Trim`**: Review current canonical EXIT/TRIM signals and standing conditions after the evidence gate.
- **`[2] Resolve Strategic Conflicts`**: Step through conflicted holdings (MU, PANW, RIOT) to calibrate target weights.
- **`[3] Full Portfolio Rebalance`**: Launch the integrated rebalancer to generate exact BUY/TRIM orders and PSU-U.TO tickets.
- **`[4] Pillar Concentration Deep-Dive`**: Audit specific pillars to re-align sub-strategy allocations.
- **`[5] Refresh Valuations`**: Run `/update-stock-analysis` for material evidence gaps or stale assumptions before deciding.

### Phase 4: Downstream Calibration & Rebalancing Handoff
- **Target Calibration**: If adjusting weights, seamlessly transition into `/calibrate-targets` with 100% normalization.
- **Rebalancing Execution**: If generating orders, invoke `rebalancer.py --pretty` (`/rebalance-portfolio`), apply `risk_officer.py`, and draft account-level orders with PSU-U.TO funding.
- **Persist Dossier**: Scaffold `PortfolioAnalysis/strategic-reviews/YYYY-MM-DD-PortfolioAnalysisRecommendations.md` with `generate_review.py` and fill in every pending section, including the Priority Action List.
- **Refresh Thesis Pages**: Refresh every thesis page's current-developments note with `thesis_currency.py` (protocol: `plugins/portfolio-advisor/references/thesis-page-currency.md`). If the review changed a thesis's conviction, structure or sizing, also update that page's own prose so it agrees.
- **Closing Refresh**: Always finish with `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
```bash
python3 -m pytest plugins/portfolio-advisor/tests/test_scan_opportunities.py
python3 -m pytest plugins/portfolio-advisor/tests/test_generate_review.py
```

## References
- [Keeping Recommendations Coherent](references/recommendation-coherence.md) - Trade refresh, standing-decision reconciliation, daily priority order and chart-level conditions.
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- [Investment Thesis](references/investment_thesis.md) - Canonical portfolio thesis and sub-strategy definitions.
- [Strategic Review Prompt](references/strategic_review_prompt.md) - Qualitative criteria and JSON evaluation schema.
- [Fallback Tree](references/fallback-tree.md) - Operational fallback procedures for backend disruptions.
