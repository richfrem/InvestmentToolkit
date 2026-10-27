---
name: valuing-investments
plugin: portfolio-advisor
description: Values stocks and funds and onboards new tickers. Covers the full autonomous valuation of a held or tracked stock (5-year Bear/Base/Bull scenarios persisted to SQLite, price levels, research report), qualitative research sweeps with a re-valuation decision gate, the forward-valuation challenge for AI-exposed names, deterministic math validation of DCF payloads, ETF and fund analysis (closed-end NAV premium, thematic ETF alignment, cash funds), and the stock-intake wizard. Trigger on /update-stock-analysis, /research-stock, /forward-valuation-challenge, /valuation-math-validation, /analyze-etf, "value [TICKER]", "research [TICKER]", "challenge [TICKER] forward valuation", "validate valuation math", "analyze [TICKER]" for a fund, "onboard [TICKER]" or "add [TICKER] to the portfolio".
allowed-tools: Bash, Read, Write
---

# Valuing Investments

Everything that produces or checks a valuation: single stocks, funds, and the intake of new names. Valuations are saved once to `domain_model.sqlite` and every screen reads them from there.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Scripts](#scripts) · [Verification](#verification) · [References](#references)

## Quick start

From the repository root (paths starting with `scripts/`, `assets/` or `references/` are relative to this skill's folder):

```bash
python3 investment_screener/backend/py_services/fetch_financials.py {TICKER} > temp/evaluations/{TICKER}_raw.json
```

## Workflow

1. Match the request to a mode and read its mode file.
2. Load prior context first: the existing valuation, method, rate audit and standing decision, so the new work is compared with what is saved.
3. Do the work the mode describes; every call you intend to make is saved before it is said (see the constraints).
4. Validate, persist, and finish with the closing refresh (`refresh_all.py --publish`) so the app shows what you presented.

## Constraints

- **Method and rate contract**: follow the [valuation method and discount-rate protocol](references/valuation-method-and-discount-rate.md): FCFF with WACC, common-equity earnings with cost of equity; keep dated inputs and the rate audit; never silently replace a model.
- **AI forward-evidence gate**: for AI-exposed names apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md); flag `NEEDS_REVALUATION` when material drivers are missing. The flag never replaces the canonical action or standing decision.
- **Recommendation coherence**: follow [Keeping recommendations coherent](../setting-portfolio-targets/references/recommendation-coherence.md) every session; present `decision_check.effective` as the stance.
- **Single source of truth**: valuations go through `scripts/persist_valuation.py` into `domain_model.sqlite`; never write retired JSON files or ad hoc SQL.
- **Adversarial objectivity**: never anchor fair value to the market price; Bear cites a structural risk, Bull names a catalyst, Base reflects normalized operating leverage; Bull must stay under 50x Bear except for pre-revenue biotech.
- **Standing decisions**: respect them unless the fair-value delta is over 15% or a material catalyst occurred.
- **Funds are not valued with a DCF.** State NAV premium or discount before any action on a closed-end fund.

## Modes

| Mode | Trigger | What it does |
|---|---|---|
| [update-analysis](references/modes/update-analysis.md) | `/update-stock-analysis` | Full valuation: financials, comps, reverse DCF, scenarios, red team, persist, report, price levels |
| [research-sweep](references/modes/research-sweep.md) | `/research-stock` | Qualitative sweep and the RE_EVALUATE / MAINTAIN / WATCHLIST decision card |
| [forward-challenge](references/modes/forward-challenge.md) | `/forward-valuation-challenge` | Stress-test a valuation against backlog, capex and delivery schedules |
| [math-validation](references/modes/math-validation.md) | `/valuation-math-validation` | Unit, monotonicity, spread and reconciliation checks on a scenario payload |
| [fund-analysis](references/modes/fund-analysis.md) | `/analyze-etf` | Closed-end, thematic and cash fund analysis, persisted to SQLite |
| [stock-intake](references/modes/stock-intake.md) | "onboard [TICKER]" | Wizard: financials, technical tiers, scenario DCF, pillar registration |

## Scripts

- `scripts/`: `validate_projection.py`, `persist_valuation.py`, `fetch_fund_data.py`, `validate_etf_analysis.py`, `persist_etf_analysis.py`, `list_strategy_pillars.py`. Maintenance helpers with tests: `rebase_equity_valuations.py` (re-base earnings-multiple valuations for debt), `consolidate_research.py`, `research_parity_report.py` (read-only report of research files not yet in the ledger).
- Shared engine (backend `py_services/`): `fetch_financials`, `dcf_scenarios`, `dcf_sensitivity`, `comps_valuation`, `reverse_dcf`, `wacc`, `leverage`, `price_changes`, `standardize_metrics`, `recalculate_forward_valuation`, `persist_research`.
- `assets/templates/`: `projection_template.json`, `etf_analysis_template.json`. Tests: `tests/` (pass the path explicitly).

## Verification

- `validate_projection.py` reports zero schema errors; the scenario spread is under 50x; probability weights sum to 1.00.
- The saved valuation, method, rate audit and canonical action read back through `portfolio_io.py --ticker {TICKER} --json` or the API.
- Routing cases for every mode are in `evals/evals.json`; the [acceptance criteria](references/acceptance-criteria.md) are testable pass/fail checks.

## References

- [Valuation method and discount-rate protocol](references/valuation-method-and-discount-rate.md), [AI-sector forward valuation evidence](references/ai-forward-valuation.md), [valuation benchmarks](references/valuation-benchmarks.md), [analysis prompt](references/analysis_prompt.md), [API reference](references/api_reference.md), [DCF calculator ADR](references/ADR-dcf-calculator.md), [fallback tree](references/fallback-tree.md), [valuation persistence](references/valuation-persistence.md).
- [Interaction flow](references/interaction_flow.md), [sequence diagram](references/stock_valuation_sequence.mmd), [index of these references](references/README.md), [evolution log](references/evolution-log.md), [ETF evolution log](references/evolution-log-etf-analysis.md).
- Dated forward-valuation reviews (BE, MU) are kept in `references/forward-valuation-reviews/`.
