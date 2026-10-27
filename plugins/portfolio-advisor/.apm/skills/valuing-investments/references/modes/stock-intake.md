# Mode: stock-intake

Autonomous end-to-end stock intake wizard pulling live financials, technical levels, running scenario DCF models, and registering tickers into strategy pillars.

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](../ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- **Recommendation coherence**: Follow [Keeping recommendations coherent](../../../setting-portfolio-targets/references/recommendation-coherence.md) every session: refresh positions and executed trades first (TradingView by default), present `decision_check.effective` as the stance and reconcile any CONFLICT or OUTDATED standing decision with the owner through `set_standing_decision.py`, rank by today's priority with already-acted-on items last, and state every condition against current chart levels rather than as general guidance.
- Guide one conversational decision at a time using plain-English analogies for technical metrics.
- Respect existing standing decisions unless Fair Value delta exceeds 15%.
- Capital sourcing must compute advisory share counts funded by selling PSU-U.TO in the same account.
- Always require user confirmation before writing new tickers to SQLite or injecting chart overlays.

## Quick start
```bash
python3 investment_screener/backend/py_services/fetch_financials.py NVDA
```

## Workflow
1. **Intent & Checks**: Confirm ticker symbol, existing standing decisions, and target strategy pillar.
2. **News & Catalysts**: Ingest recent news and earnings context (optional Grok sweep).
3. **Technical Tiers**: Read TradingView CDP technical indicators (200 EMA, ADX, RSI) for entry and trim shelves.
4. **Valuation Modeling**: Execute 5-year scenario DCF model via `dcf_scenarios.py` to establish fair value.
5. **Capital Sourcing**: Calculate target weight, share tranche sizing, and account allocation (TFSA/RRSP).
6. **Persist & Overlay**: Present summary card, obtain approval, persist to database, and inject chart levels.
7. **Review Gate**: a newly added ticker starts as NEEDS_ANALYSIS and gets no call until its valuation is saved; then `python3 investment_screener/backend/py_services/review_gate.py mark --ticker {TICKER} --reason "Onboarded and valued today: ..."`.
8. **Closing Refresh**: Run `python3 investment_screener/backend/py_services/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
```bash
python3 investment_screener/backend/py_services/verify_screener_integrity.py
```

## References
- [Keeping Recommendations Coherent](../../../setting-portfolio-targets/references/recommendation-coherence.md) - Trade refresh, standing-decision reconciliation, daily priority order and chart-level conditions.
- [AI-sector Forward Valuation Evidence](../ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- Stock Analysis Surface Checklist (`docs/architecture/stock-analysis-surface-checklist.md`) - Canonical metric mappings, sources, and persistence verification rules.
