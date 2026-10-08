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
- **Method and rate contract**: Apply [Valuation method and discount-rate protocol](references/valuation-method-and-discount-rate.md) when assessing the existing valuation. Identify the cash-flow claim, matched rate and dated input evidence; an inherited unexplained rate is not reproducible. Research does not silently replace the valuation method.
- **AI forward-evidence gate**: Before valuation or action proposals for AI-exposed names, apply [AI-sector forward valuation evidence](references/ai-forward-valuation.md). Reconcile dated forward estimates, memory/storage or power demand, executable capacity and cash conversion; flag `NEEDS_REVALUATION` when material drivers are missing. This review flag does not replace the canonical action or standing decision.
- **Recommendation coherence**: Follow [Keeping recommendations coherent](references/recommendation-coherence.md) every session: refresh positions and executed trades first (TradingView by default), present `decision_check.effective` as the stance and reconcile any CONFLICT or OUTDATED standing decision with the owner through `set_standing_decision.py`, rank by today's priority with already-acted-on items last, and state every condition against current chart levels rather than as general guidance.

- **No hallucinated events**: Never extrapolate unverified news or guidance; cite dates, official earnings releases, or SEC filings.
- **Decision gate requirement**: Present the structured re-valuation decision card before chaining to valuation; wait for confirmation unless this session already explicitly authorizes the revaluation. A method migration requires a concrete comparison and acceptance within that authorization.
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
   Load existing valuation date, model assumptions, rate audit and standing decision through supported API/repository scripts. Identify missing evidence, method/rate mismatches and financing/ownership gaps using the shared protocol.
2. **Execute Research Sweep**:
   - Collect recent quarterly earnings transcripts, SEC 10-Q/8-K filings, and guidance revisions.
   - Screen competitor dynamics, capacity additions, and regulatory changes.
   - For AI-infrastructure names, complete the capacity-to-earnings build in the AI forward guide before any rate or re-valuation proposal.
3. **Classify Catalysts**:
   - `Class A (Structural)`: Guidance revision $>10\%$, contract win $>20\%$ backlog, or thesis breaker trip $\rightarrow$ Recommend re-valuation.
   - `Class B (Material)`: Margins $\pm 200$ bps, management change $\rightarrow$ Flag for user review.
   - `Class C (Informational)`: Price volatility without fundamental shift $\rightarrow$ Maintain thesis.
4. **Draft Research Report**:
   Write `investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md`, then publish with `persist_research.py --file REPORT.md --db /ABSOLUTE/MAIN_CHECKOUT/investment_screener/backend/data/intelligence.sqlite --jsonl /ABSOLUTE/MAIN_CHECKOUT/investment_screener/backend/data/observations.jsonl`. Verify `query_ledger_research.py --get {TICKER}_{YYYY-MM-DD}.md`; the app reads the ledger, not the draft file.
5. **Re-Valuation Decision Gate**:
   Present summary card with recommendation (`RE_EVALUATE`, `MAINTAIN_CURRENT`, or `WATCHLIST_ALERT`), existing/proposed method, rate basis and evidence dates, operating changes, sensitivity needs and unresolved gaps. Show old-method versus new-method comparisons for a proposed migration. Chain into `/update-stock-analysis` only within explicit session authorization; otherwise await confirmation.

## Verification

- Check the rate/method cases in `evals/evals.json`; evidence deficiencies do not justify inventing inputs or flipping the canonical recommendation. The valuation workflow saves rates and assumptions once to SQLite for all app views.
- For AI-exposed names, verify the forward-evidence cases in `evals/evals.json`; record source dates, modeled changes and unresolved gaps before relying on a valuation signal.

- Confirm research file created at `investment_screener/backend/data/research/{TICKER}_{YYYY-MM-DD}.md`.
- Test routing cases against `evals/evals.json`.

## References
- [Keeping Recommendations Coherent](references/recommendation-coherence.md) - Trade refresh, standing-decision reconciliation, daily priority order and chart-level conditions.
- [Valuation Method and Discount-Rate Protocol](references/valuation-method-and-discount-rate.md) - Shared research decision gate and reproducible valuation process.
- [AI-sector Forward Valuation Evidence](references/ai-forward-valuation.md) - Forward estimates, memory/storage and power drivers, cash-flow bridge, and recommendation readiness.

- [Fallback Tree](references/fallback-tree.md): Operational degradation procedures when data feeds or APIs are unreachable.
