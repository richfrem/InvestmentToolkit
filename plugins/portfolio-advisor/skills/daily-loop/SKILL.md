---
name: daily-loop
plugin: portfolio-advisor
description: The single master daily command. Provides fast non-interactive morning briefs or guides the interactive daily portfolio loop through freshness, brief, triage, and action cards. Also use it on a new trading day before answering any buy, sell, entry-price or chart question.
---

# Daily Investment Loop

## Contents
- [First action](#first-action)
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## First action
On a new trading day, run Steps 0–3 in order **before** answering any buy, sell, entry-price
or chart question (for example "check the charts, what should I buy"). Charts come after the
brief's macro gate and the news sweep, never instead of them. Run the loop before the market
opens when the owner is available then; prices and the plan must be ready before they act.

## Constraints
- **One source of calls**: present only stances from `recommendation.py --all` (`decision_check.effective`); follow [Keeping recommendations coherent](references/recommendation-coherence.md) and `.agent/rules/local-recommendation-coherence.md`.
- **Say it only after it is saved**: any plan you give the owner (buy price, size, skip list, wait condition) is recorded first: a standing decision with the price in its type (`set_standing_decision.py`), a target that fits the trade (`update_targets.py --set`), both only after the owner agrees. Chat-only advice is labelled "draft, not in the record".
- **Gates before any trade price**: the macro gate (RISK-OFF: no new buys; NEUTRAL: only ACCUMULATE scoring ≥ +4; degraded data counts as RISK-OFF) and the binary-event protocol (holdings within 14 days of earnings) from [Daily Brief Methodology](references/daily-brief-methodology.md) are applied and stated before any entry price.
- **AI forward-evidence gate**: before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md); flag `NEEDS_REVALUATION` when material drivers are missing. The flag does not replace the canonical action or standing decision.
- **Fresh prices**: the brief, weights and totals read `investment_price`. Write prices only through the price scripts, never ad-hoc SQL; if a refresh leaves symbols stale, say so on every affected card.
- **News sweep is part of every daily run**: invoke the `news-sweep` skill. Never skip it silently; if no model response is pasted yet, say so and continue.
- **Keep executing**: when a step fails, report it, mark affected cards stale and continue; stop only for a decision that is genuinely the owner's. One decision at a time.
- Check database freshness against `domain_model.sqlite` (never a file mtime). Fast scan (`--scan`) runs non-interactively; the full loop guides step-by-step triage.

## Quick start
```bash
python3 plugins/portfolio-advisor/scripts/run_daily.py --scan
```

## Workflow
0. **Readiness**, in this order:
   1. Positions and trades: `/tv-portfolio-sync`. Only if `python3 investment_screener/backend/py_services/broker_sources.py --json` lists `questrade`, ask whether to use TradingView (default) or Questrade.
   2. Prices: `python3 plugins/tradingview/scripts/tv_price_refresh.py` (also refreshes USD→CAD). On exit 1, fill the `stale` symbols with the `refresh-prices` mode of the `syncing-questrade-accounts` skill (`/questrade-refresh-prices`) when Questrade is enabled; otherwise report them.
   3. Review cycle: `python3 plugins/portfolio-advisor/scripts/review_gate.py begin`, then work the whole queue, holdings first: `/update-stock-analysis` for HARD triggers, `review_gate.py mark --ticker T --reason "..."` for age-only ones.
   4. Price levels for every holding and watchlist name, from the latest valuation and today's chart (one batch download): `python3 plugins/portfolio-advisor/scripts/update_price_levels.py --followed --source combined --write`. The Stock Analysis page and the TradingView chart both show these stored tiers.
   5. Targets superseded by trades: `python3 plugins/portfolio-advisor/scripts/rebaseline_targets.py`, then `--write`. A fill newer than a target resets it to the post-trade weight (0% when sold out); the cash target absorbs the difference. Report positions skipped for missing prices.
   6. Health: backend API, `domain_model.sqlite` sync timestamps, TradingView CDP (`node tradingview-cdp/cli.js status`).
1. **Morning Brief**: `python3 plugins/portfolio-advisor/scripts/daily_brief.py` (or read the JSON a `--scan` wrote). State the macro regime and the gate it implies, then binary events, before anything else.
2. **News Sweep**: generate the prompt (`generate_news_prompt.py --output temp/news-prompts/daily_news_prompt.md --clipboard`); the owner pastes it into the models and pastes the responses back in chat (save each to `temp/news-sweep-responses/<model>/daily-<mon><dd>-<yyyy>.md`). Follow the news-sweep workflow: fact-check gate, CONFLUENCE/PARTIAL/CONFLICT, record with `record_news_sweep.py`. Findings feed triage; they change no call on their own.
3. **Triage**: urgent holding alerts, thesis breaker breaches and price catalysts, one ticker at a time.
4. **Action Cards**: from today's weight (`weight.currentPct` → `weight.targetPct`, `deltaPp`). For a buy or trim card:
   - Quote entry and trim prices only from the stored tiers (`price_level_tier`: buy tiers, trims, stop, `TARGET_ENTRY`), refreshed in Step 0; redraw them for the ticker under discussion with `update_price_levels.py --ticker T --source combined --write --draw`. A chart read this session adds context (intraday, momentum) but never a second set of levels.
   - State the weight the trade produces. If it exceeds the target (a target reset to today's weight always does), ask for the new target and set it with `update_targets.py --set` before proposing the order. Never change a target without that answer.
   - Record the agreed entry or wait condition with `set_standing_decision.py` (price in the type), then re-read `recommendation.py --all` and present that stance.
   - For any of the five highest-priority cards marked `refreshFirst`, run `/update-stock-analysis TICKER` first and walk the owner through the result.
   - Size tranches and source capital (PSU-U.TO trims). Orders are placed only by the owner (push-to-approve).
5. **Evolution & Summary**: log operational friction in the evolution log, record execution receipts, show final status.
6. **Thesis Pages**: `python3 plugins/portfolio-advisor/scripts/thesis_currency.py stale`; for each page with new events, read `context`, write the current-developments note and `put` it (`plugins/portfolio-advisor/references/thesis-page-currency.md`).
7. **Review Gate**: `python3 plugins/portfolio-advisor/scripts/review_gate.py verify` must exit 0; the loop is not finished while any name is NEEDS_ANALYSIS.
8. **Closing Refresh**: `python3 plugins/portfolio-advisor/scripts/refresh_all.py --publish`, then confirm the app shows the stances you presented (`recommendation.py --all` against the app's `/api/screener/recommendations`).

## Verification

- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.
```bash
python3 plugins/portfolio-advisor/scripts/verify_daily_run.py --latest
python3 plugins/portfolio-advisor/scripts/verify_refresh.py
python3 investment_screener/backend/py_services/verify_portfolio_invariants.py
```
- After the price refresh, `CASH_INVARIANT` should report no discrepancy. A gap equal to the difference between TradingView's live total and the stored total means prices are still stale.
- Every price, size or wait condition you told the owner appears in the record (standing decision, target) and in the app.

## References
- [Keeping Recommendations Coherent](references/recommendation-coherence.md) - Trade refresh, standing-decision reconciliation, daily priority order and chart-level conditions.
- [Daily Brief Methodology](references/daily-brief-methodology.md) - Macro gate, binary-event protocol, conviction scoring and routing from the brief.
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.
- The `news-sweep` skill (invoke it; it is not bundled here) - Prompt generation, multi-model roles, fact-check gate, triangulation and ledger recording.
