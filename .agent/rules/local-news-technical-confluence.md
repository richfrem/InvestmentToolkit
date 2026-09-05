---
description: Mandatory confluence check between news sentiment (Grok/Gemini sweeps) and technical/DCF signals before any ACCUMULATE/EXIT/INITIATE/TRIM recommendation.
globs: ["plugins/portfolio-advisor/agents/*.md", "plugins/portfolio-advisor/skills/**/SKILL.md"]
---

# News × Technical Confluence Gate

## The Problem This Rule Solves

Agents were recommending EXIT/TRIM/ACCUMULATE/INITIATE purely from DCF + TA conviction
scores, without checking whether a recent news catalyst (earnings, contract, partnership)
had already moved the stock — or explained the technical signal. On 2026-07-01, BE scored
EXIT (-4: DCF SELL, RSI cooling, volume dry after a big day) from technicals alone. Both
Grok and Gemini news sweeps, run independently, surfaced a live catalyst (Brookfield fuel-cell
deal expanded 5x to $25B / Oracle 2.8GW deal) that both converted into "TRIM the rally, not
exit." That context did not reach the user until they asked for it directly.

## The Law

> **No ACCUMULATE / EXIT / INITIATE / TRIM recommendation is actionable until it has been
> checked against the most recent news sweep for that ticker.** Technicals and DCF describe
> price and valuation. News explains *why*. A recommendation with only one side is incomplete.

## Non-Negotiables

1. **Freshness check first.** Before finalizing any REDUCE/EXIT/ACCUMULATE/INITIATE/TRIM
   card, check `temp/news-sweep-responses/{grok,gemini}/` for a response dated within the
   last 7 days covering that ticker. If none exists, offer to generate one via `x-news-sweep`
   before presenting the recommendation as final — not only for ACCUMULATE candidates.

2. **Confluence label on every card.** Every action card must state the news stance
   (Grok/Gemini conviction + one-line reason) and a verdict:
   - `[CONFLUENCE]` — TA/DCF and available news sources agree on direction.
   - `[PARTIAL]` — TA/DCF and news partially agree, or only one source covered the ticker.
   - `[CONFLICT]` — TA/DCF direction and news direction disagree.

3. **Conflicts block confidence, not action.** A `[CONFLICT]` ticker must never be presented
   as a confident recommendation. State the conflict directly and require the same explicit
   user override bar as overriding a standing decision — do not silently pick a side.

4. **Exhaustion-pattern check.** When TA shows `RSI_COOLING` + `VOLUME_DRY` + `BIG_DAY`
   together, cross-reference news for the catalyst that caused the spike. If found, prefer
   TRIM (harvest the spike) over EXIT unless news also confirms the thesis itself is broken.

5. **No sweep = provisional, say so.** If no news sweep exists and one cannot be generated
   this session, label the recommendation `[TA/DCF-ONLY — NEWS UNCHECKED]` and treat it as
   provisional, not final.

## Where This Applies

- `daily-loop-agent.md` — Step 2/3 triage cards (all signal types, not just ACCUMULATE)
- `portfolio-advisor-orchestrator.md` — Phase 1 catalyst ingestion Q&A
- `thesis-review-agent.md` — new thesis intake and challenge validation
- `weekly-review-agent.md` — weekly drift + sweep recommendations
- `x-news-sweep` skill — the check, not just the offer, gates the agents above
