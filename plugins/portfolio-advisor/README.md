# Portfolio Advisor

> Investment portfolio advisor suite: AI stock valuation, ETF and fund analysis, the daily and weekly review loops, news and 13F sweeps, target calibration and valuation-gated rebalancing, and the data audits that guard them. Detects drift, flags thesis breakers and keeps every call in the SQLite record.
>
> Packaged as an APM-native package (`apm.yml`, primitives under `.apm/`). This plugin absorbed the former `stock-valuation` and `etf-analysis` plugins; slash commands are unchanged.

## Skills

| Skill | Modes (slash commands) |
|---|---|
| `valuing-investments` | `update-analysis` (`/update-stock-analysis`), `research-sweep` (`/research-stock`), `forward-challenge` (`/forward-valuation-challenge`), `math-validation` (`/valuation-math-validation`), `fund-analysis` (`/analyze-etf`), `stock-intake` |
| `running-portfolio-reviews` | `daily-loop` (`/daily`), `weekly-review`, `news-sweep` (`/news-sweep`), `external-review` (`/adversarial-review`, `/external-review`) |
| `setting-portfolio-targets` | `update-targets`, `calibrate-targets` (`/calibrate-targets`), `rebalance` (`/rebalance`), `strategic-review` (`/strategic-review`), `portfolio-health` (`/review-portfolio`), `thesis-review`, `set-thesis-breakers`, `pre-trade-analysis`, `ytd-return` |
| `tracking-13f-filings` | `track` (`/13f-tracker`), `analyze` (`/13f-analyze`) |
| `auditing-portfolio-data` | `data-quality`, `coverage`, `screener-integrity` |

Agents (`.apm/agents/`): `portfolio-advisor-orchestrator`, `red-team-agent`, `risk-officer-agent`, `thesis-review-agent`.

## Layout

```
apm.yml                      manifest (includes: auto)
CONNECTORS.md                tool connector abstractions and degradation contract
.apm/skills/<skill>/         SKILL.md (hub), references/modes/, references/, scripts/, assets/, tests/, evals/
.apm/agents/                 the four agents and their evals
docs/                        governance, attribution, lifecycle
```

The shared portfolio and valuation engine (`recommendation.py`, `update_targets.py`, `refresh_all.py`, `dcf_scenarios.py`, `wacc.py`, `fetch_financials.py`, and the rest) lives in `investment_screener/backend/py_services/` because the backend imports it; skills call it by repository path. Each skill keeps only its own scripts, templates, references and tests.

## How the valuation pipeline works (`update-analysis`)

1. Fetch financials (`fetch_financials.py`, yfinance) and consensus metrics.
2. Build the scenario inputs; run the peer comparison (`comps_valuation.py`) and the market-implied growth check (`reverse_dcf.py`).
3. Construct Bear/Base/Bull scenarios with the rate basis chosen under the valuation protocol (`wacc.py`, `leverage.py`, `dcf_scenarios.py`).
4. Adversarial review, then validate (`validate_projection.py`) and persist (`persist_valuation.py`) to `domain_model.sqlite`.
5. Publish the research report to the ledger, refresh price levels, mark the name reviewed, and run the closing refresh.

**Standalone mode**: if the backend or the data fetcher is unavailable, the skills ask for the raw data as JSON and still complete the analysis; persistence is skipped with an explicit notice (see `CONNECTORS.md`).

## External dependencies (web app)

This plugin does **not** own these; they are served by the Investment Screener backend.

| Dependency | Purpose |
|:---|:---|
| `GET /api/theses`, `GET /api/theses/:id/health` | Thesis list and per-holding drift and health |
| `investment_screener/backend/data/domain_model.sqlite` | The single source of truth for holdings, targets, valuations and decisions |
| `investment_screener/backend/data/intelligence.sqlite` | Research ledger |
| `yfinance` (Python) | Financial data for valuations |

## Install and test

`apm install ./plugins/portfolio-advisor --target agent-skills` from the repository root deploys the skills to `.agents/skills/` (generated and gitignored; edit the sources under `.apm/`).

Tests live under each skill's `tests/` and, for engine modules, in `investment_screener/backend/tests/py_services/`. Pytest skips dot-directories, so pass the paths explicitly, for example `python3 -m pytest plugins/portfolio-advisor/.apm/skills/running-portfolio-reviews/tests`.

## Related plugins

- `tradingview`: broker, price and chart integration (the default broker source).
- `questrade`: optional second broker source.
- `toolkit-manager`: running, backing up and auditing the toolkit itself.
