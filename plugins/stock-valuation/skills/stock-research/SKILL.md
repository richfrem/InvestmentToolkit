---
name: stock-research
plugin: stock-valuation
description: Perform a qualitative deep-dive research sweep on a stock covering earnings call highlights, competitive shifts, guidance updates, and analyst revisions. Produces a research report and structured decision on whether findings warrant a DCF re-valuation. Trigger on /research-stock or "research [TICKER]".
allowed-tools: Bash, Read, Write
---

# Stock Research

Qualitative deep-dive research sweep and re-valuation decision gate for existing equity stakes.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **No hallucinated events**: Never extrapolate unverified news or guidance; cite dates, official earnings releases, or SEC filings.
- **Decision gate requirement**: Never automatically re-run DCF valuation without presenting the structured re-valuation decision card to the user first.
- **Append timeline**: Research memos must be written directly to `investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md`.
- **Standing decision anchor**: Re-valuation recommendations require a material thesis catalyst or $>15\%$ fair value variance.

## Quick start

Execute a qualitative research sweep:

```bash
python3 plugins/stock-valuation/scripts/fetch_financials.py {TICKER}
```

Trigger with `/research-stock {TICKER}` or natural language when material events occur.

## Workflow

1. **Load Prior Context**:
   Query `domain_model.sqlite` for existing valuation date, model assumptions, and standing decision rationale.
2. **Execute Research Sweep**:
   - Collect recent quarterly earnings transcripts, SEC 10-Q/8-K filings, and guidance revisions.
   - Screen competitor dynamics, capacity additions, and regulatory changes.
3. **Classify Catalysts**:
   - `Class A (Structural)`: Guidance revision $>10\%$, contract win $>20\%$ backlog, or thesis breaker trip $\rightarrow$ Recommend re-valuation.
   - `Class B (Material)`: Margins $\pm 200$ bps, management change $\rightarrow$ Flag for user review.
   - `Class C (Informational)`: Price volatility without fundamental shift $\rightarrow$ Maintain thesis.
4. **Draft Research Report**:
   Append findings to `investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md`.
5. **Re-Valuation Decision Gate**:
   Present summary card with recommendation (`RE_EVALUATE`, `MAINTAIN_CURRENT`, or `WATCHLIST_ALERT`) and await user confirmation before chaining into `/update-stock-analysis`.

## Verification

- Confirm research file created at `investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md`.
- Test routing cases against `evals/evals.json`.

## References

- [Fallback Tree](references/fallback-tree.md): Operational degradation procedures when data feeds or APIs are unreachable.
