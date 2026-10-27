# Mode: news-sweep

Generates multi-agent news sweep prompts, gates cross-model findings (Grok, Claude, ChatGPT, Gemini) against DCF and technical levels, and applies approved target updates.

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](../../../valuing-investments/references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- Source portfolio and thesis data strictly from `domain_model.sqlite` (never legacy JSON files).
- Gate every recommendation against DCF fair values, live technicals, and the fact-check gate before applying.
- Label each ticker recommendation as CONFLUENCE, PARTIAL, or CONFLICT before presenting changes.
- Never apply target changes without updating `agentRationale` and catalyst fields via `apply_catalyst.py`.
- Complete full refresh chain after applying approved modifications.
- Record every sweep's triangulated findings in the ledger (`record_news_sweep.py`); the prompt and response files under `temp/` are working copies only.

## Quick start
```bash
python3 investment_screener/backend/py_services/generate_news_prompt.py --output temp/news-prompts/daily_news_prompt.md --clipboard
```

## Workflow
1. **Generate Prompt**: Compile model-agnostic sweep prompt from `domain_model.sqlite` with live baseline anchors using `generate_news_prompt.py`.
2. **Multi-Model Sweep**: Run prompt across frontier models according to schedule (Grok daily default; escalate to ChatGPT/Claude on major moves or binary events). The owner pastes each response back in chat; save it verbatim (or as a faithful summary marked as such) to `temp/news-sweep-responses/<model>/daily-<mon><dd>-<yyyy>.md`, the placeholder the generator created.
3. **Fact-Check Gate**: Verify stated macro yields (10Y), VIX, and quoted prices against live market data before trusting findings. A model that fails the gate (a wrong 10Y, or claiming a held, quoted ticker does not trade) is excluded from triangulation; say which model and why.
4. **Triangulate & Present**: Cross-check findings across models, categorize as CONFLUENCE, PARTIAL, or CONFLICT, and flag required user confirmations.
5. **Apply & Refresh**: Update scenario weights with `apply_catalyst.py --write` or targets with `update_targets.py --write`.
6. **Record Findings & Refresh Thesis Pages**: Write the triangulated findings as `## TICKER` sections and record them with `record_news_sweep.py --source <model> --write` so they are kept in the ledger (a sweep that is not recorded is lost). For a multi-model sweep, record the triangulated sections once with a source naming the models used (for example `triangulated-claude-grok-chatgpt`). Findings never change a call by themselves; a change goes through a valuation, `set_standing_decision.py` or `update_targets.py` with owner approval. Then refresh the thesis pages whose stocks appear in them with `thesis_currency.py` (protocol: `plugins/portfolio-advisor/.apm/skills/setting-portfolio-targets/references/thesis-page-currency.md`).
7. **Improve the Prompt**: Collect each model's "Prompt improvements" list, merge duplicates, and show the owner the top 3 (suggestions two or more models made come first). Apply only approved ones, editing [the daily sweep template](../../assets/templates/daily_sweep.md.template), and log each applied change in `references/evolution-log.md`.
8. **Closing Refresh**: Run `python3 investment_screener/backend/py_services/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Multi-Model Roles
- **Grok**: Primary for breaking catalysts, real-time X news flow, and fast corporate partnership tracking.
- **ChatGPT**: Primary for auditing SEC filings, validating contract figures, and verifying prompt anchors.
- **Claude Opus**: Primary for strategic counter-theses, macro regime integration, and valuation stress-testing.
- **Gemini**: Primary for full-breadth context scanning and rapid cross-checking across large ticker batches.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
```bash
python3 investment_screener/backend/py_services/verify_refresh.py
```

## References
- [AI-sector Forward Valuation Evidence](../../../valuing-investments/references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- [News Sweep Model Assessment](../news-sweep-model-assessment.md) - Model scoring criteria, accuracy benchmarks, and historical performance evaluations.
