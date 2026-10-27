# Mode: weekly-review

Runs weekend drift audits, calculates week-over-week performance moves across holdings, and coordinates multi-agent research sweeps (Grok, Claude, ChatGPT, Gemini).

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](../../../valuing-investments/references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- **Recommendation coherence**: Follow [Keeping recommendations coherent](../../../setting-portfolio-targets/references/recommendation-coherence.md) every session: refresh positions and executed trades first (TradingView by default), present `decision_check.effective` as the stance and reconcile any CONFLICT or OUTDATED standing decision with the owner through `set_standing_decision.py`, rank by today's priority with already-acted-on items last, and state every condition against current chart levels rather than as general guidance.
- Weekend drift audit evaluates holdings against target weights and DCF signals in `domain_model.sqlite`.
- Multi-model prompt output file must be written to `temp/weekly_grok_prompt.md`.
- Never execute live trade orders during weekly reviews; review is strictly analytical.
- **One source of calls, saved before said**: present only stances from `recommendation.py --all`. Any plan you give (price, size, skip list, wait condition, target) is recorded first, with the owner's agreement, through `set_standing_decision.py` (price in the type) or `update_targets.py --set`; otherwise label it "draft, not in the record" (`.agent/rules/local-recommendation-coherence.md`).
- Enforce the 3-step fact check gate (10Y yield, VIX, real prices) before accepting any model's claims; a model that fails it is excluded from triangulation, and you say which and why.

## Quick start
```bash
python3 scripts/weekly_review.py --prompt-output temp/weekly_grok_prompt.md
```

## Workflow
1. **Refresh Reality**, in this order: positions and the week's trades with `/tv-portfolio-sync` (only if `python3 investment_screener/backend/py_services/broker_sources.py --json` lists `questrade`, ask whether to use TradingView (default) or Questrade); then prices with `python3 plugins/tradingview/.apm/skills/trading-via-tradingview/scripts/tv_price_refresh.py`, filling any `stale` symbols with the the `refresh-prices` mode of the `syncing-questrade-accounts` skill skill when Questrade is enabled, or reporting them.
2. **Start the Review Cycle**: `python3 investment_screener/backend/py_services/review_gate.py begin`, after step 1 so triage measures today's prices; the weekly review clears the whole queue (holdings and watchlist).
3. **Price Levels**: `python3 investment_screener/backend/py_services/update_price_levels.py --followed --source combined --write` so every holding and watchlist name has numbered buy/trim tiers from its latest valuation and this week's chart; the page and TradingView show the same tiers.
4. **Drift Audit**: Evaluate week-over-week price changes and allocation drift across all active holdings and watchlists.
5. **Compile Prompt**: Generate the model-agnostic research prompt with baseline anchors (prices, 1W moves, target weights, and each name's stance from `recommendation.py --all`).
6. **Multi-Model Dispatch**: The owner pastes the prompt into each model and pastes the responses back in chat; save each to `temp/news-sweep-responses/<model>/weekly-<mon><dd>-<yyyy>.md`.
7. **Fact-Check Gate**: Validate macro yield, VIX, and quoted prices against live market data before accepting findings.
8. **Calibrate & Apply**: Review triangulated findings. Catalyst adjustments (`apply_catalyst.py`) and target weights (`update_targets.py`) change only with the owner's answer, one decision at a time; a buy or trim proposal states the weight it produces and the target that fits it.
9. **Record Findings & Refresh Every Thesis Page**: Record the triangulated findings with `record_news_sweep.py --write`, then work through `thesis_currency.py stale --max-age-days 7`: rewrite each listed page's note from its `context` and `put` it, or `touch` it when nothing material changed (protocol: `plugins/portfolio-advisor/.apm/skills/setting-portfolio-targets/references/thesis-page-currency.md`).
10. **Review Gate**: `python3 investment_screener/backend/py_services/review_gate.py verify` must exit 0 before the review ends.
11. **Closing Refresh**: Run `python3 investment_screener/backend/py_services/refresh_all.py --publish`, then confirm the app shows the stances you presented.

## Multi-Agent Protocol
Leverage complementary agent capabilities across the weekly research sweep:
- **Grok**: Best for breaking catalysts, real-time X sentiment, and late-breaking datacenter/miner announcements.
- **ChatGPT**: Best for primary SEC filings, verified contract dollar amounts, and auditing prompt anchors.
- **Claude Opus**: Best for strategic red-teaming, macro regime analysis, and challenging valuation stretches.
- **Gemini**: Best for rapid full-breadth scanning across every holding and watchlist ticker and cross-checking candidate moves.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
```bash
test -s temp/weekly_grok_prompt.md && head -n 20 temp/weekly_grok_prompt.md
python3 investment_screener/backend/py_services/validate_weights.py --mode both
```

## References
- [Keeping Recommendations Coherent](../../../setting-portfolio-targets/references/recommendation-coherence.md) - Trade refresh, standing-decision reconciliation, daily priority order and chart-level conditions.
- [AI-sector Forward Valuation Evidence](../../../valuing-investments/references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- [News Sweep Model Assessment](../news-sweep-model-assessment.md) - Model scoring criteria, accuracy benchmarks, and historical performance evaluations.
