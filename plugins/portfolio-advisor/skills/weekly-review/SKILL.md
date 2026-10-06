---
name: weekly-review
plugin: portfolio-advisor
description: Runs weekend drift audits, calculates week-over-week performance moves across holdings, and coordinates multi-agent research sweeps (Grok, Claude, ChatGPT, Gemini).
---

# Weekly Review

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Multi-Agent Protocol](#multi-agent-protocol)
- [Verification](#verification)
- [References](#references)

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- Weekend drift audit evaluates holdings against target weights and DCF signals in `domain_model.sqlite`.
- Multi-model prompt output file must be written to `temp/weekly_grok_prompt.md`.
- Never execute live trade orders during weekly reviews; review is strictly analytical.
- Enforce the 3-step fact check gate (10Y yield, VIX, real prices) before accepting any model's claims.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/weekly_review.py --prompt-output temp/weekly_grok_prompt.md
```

## Workflow
1. **Drift Audit**: Evaluate week-over-week price changes and allocation drift across all active holdings and watchlists.
2. **Compile Prompt**: Generate model-agnostic research prompt containing baseline anchor data (prices, 1W moves, target weights).
3. **Multi-Model Dispatch**: Ingest responses from multiple frontier models leveraging their distinct strengths.
4. **Fact-Check Gate**: Validate macro yield, VIX, and quoted prices against live market data before accepting findings.
5. **Calibrate & Apply**: Review triangulated findings and apply catalyst adjustments via `apply_catalyst.py` or target weights via `update_targets.py`.
6. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Multi-Agent Protocol
Leverage complementary agent capabilities across the weekly research sweep:
- **Grok**: Best for breaking catalysts, real-time X sentiment, and late-breaking datacenter/miner announcements.
- **ChatGPT**: Best for primary SEC filings, verified contract dollar amounts, and auditing prompt anchors.
- **Claude Opus**: Best for strategic red-teaming, macro regime analysis, and challenging valuation stretches.
- **Gemini**: Best for rapid full-breadth scanning across all 95 tickers and cross-checking candidate moves.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
```bash
test -s temp/weekly_grok_prompt.md && head -n 20 temp/weekly_grok_prompt.md
python3 plugins/portfolio-advisor/scripts/validate_weights.py --mode both
```

## References
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- [News Sweep Model Assessment](references/news-sweep-model-assessment.md) - Model scoring criteria, accuracy benchmarks, and historical performance evaluations.
