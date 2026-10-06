---
name: news-sweep
plugin: portfolio-advisor
description: Generates multi-agent news sweep prompts, gates cross-model findings (Grok, Claude, ChatGPT, Gemini) against DCF and technical levels, and applies approved target updates.
---

# Multi-Model News & Catalyst Sweep

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Multi-Model Roles](#multi-model-roles)
- [Verification](#verification)
- [References](#references)

## Constraints
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- Source portfolio and thesis data strictly from `domain_model.sqlite` (never legacy JSON files).
- Gate every recommendation against DCF fair values, live technicals, and the fact-check gate before applying.
- Label each ticker recommendation as CONFLUENCE, PARTIAL, or CONFLICT before presenting changes.
- Never apply target changes without updating `agentRationale` and catalyst fields via `apply_catalyst.py`.
- Complete full refresh chain after applying approved modifications.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/generate_news_prompt.py --output temp/news-prompts/daily_news_prompt.md --clipboard
```

## Workflow
1. **Generate Prompt**: Compile model-agnostic sweep prompt from `domain_model.sqlite` with live baseline anchors using `generate_news_prompt.py`.
2. **Multi-Model Sweep**: Run prompt across frontier models according to schedule (Grok daily default; escalate to ChatGPT/Claude on major moves or binary events).
3. **Fact-Check Gate**: Verify stated macro yields (10Y), VIX, and quoted prices against live market data before trusting findings.
4. **Triangulate & Present**: Cross-check findings across models, categorize as CONFLUENCE, PARTIAL, or CONFLICT, and flag required user confirmations.
5. **Apply & Refresh**: Update scenario weights with `apply_catalyst.py --write` or targets with `update_targets.py --write --blueprint`.
6. **Closing Refresh**: Run `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish` so the Portfolio Advisor and Daily Brief pages reflect this session.

## Multi-Model Roles
- **Grok**: Primary for breaking catalysts, real-time X news flow, and fast corporate partnership tracking.
- **ChatGPT**: Primary for auditing SEC filings, validating contract figures, and verifying prompt anchors.
- **Claude Opus**: Primary for strategic counter-theses, macro regime integration, and valuation stress-testing.
- **Gemini**: Primary for full-breadth context scanning and rapid cross-checking across large ticker batches.

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
```bash
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
```

## References
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- [News Sweep Model Assessment](references/news-sweep-model-assessment.md) - Model scoring criteria, accuracy benchmarks, and historical performance evaluations.
