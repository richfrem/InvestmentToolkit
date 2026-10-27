# Wave 4 summary: portfolio-advisor (stock-valuation + etf-analysis + portfolio-advisor: 25 skills -> 5 hubs, 4 agents)

| Check | Result |
|---|---|
| Ledger accounting (`verify --wave 4`) | 349 rows, 0 failures after fixing one dangling link (a red-team review file that was never in the repository); 61 warnings reviewed (history files and docstrings) |
| Knowledge parity | 439 substantive lines checked; the one flagged line is the deliberate wording change in daily-loop (script path and skill name rewritten) |
| Evals | 193 carried over, tagged with `mode` |
| `validate_apm_package.py` | passed (after removing the leftover `agents/` folder) |
| `audit_skill.py` (5 hubs) | PASS or warnings only; remaining "missing link" errors are cross-hub links that `apm install` rewrites |
| Regression vs baseline | backend Python 2078 passed with the same expected failures; TypeScript 237 passing / 2 failing (same as baseline); every remaining failure is on the baseline list |

Findings
- Two contract tests encoded the old symlink model (`test_ai_forward_skill_contract`, `test_recommendation_coherence_contract`); both now check one real reference file and that mode-file links resolve.
- `test_persist_valuation`, `test_forward_recalculation` and `ProjectionRepository.spec.ts` pointed at the old `stock-valuation` scripts and fixtures; they now use the engine `wacc.py`, the engine fixtures and the hub's `persist_valuation.py`.
- Deleted: 18 ignored cache files (untracked, re-fetchable) under the old `stock-valuation/scripts/cache/`. Not recoverable, regenerated on demand.
- Left as is: `references/triage-history.json` (ignored runtime data), `external-review` mode still names a `bundle.py` that never existed in the repository (pre-existing).
- Marketplace entries removed; the catalog is now empty because the plugins install through APM.

## Web app Refresh bug (diagnosis)
- Not caused by the plugin move: `tv_batch_quotes` and the heatmap import resolve correctly after Waves 3 and 4.
- Cause found live on 2026-10-27: TradingView Desktop reported `document.hidden = true`; 24 of the 43 rows in "TV-Full Watchlist" stayed `data-status="pending"` with empty price cells, so only 19 had a price and the refresh wrote 19 and left 69 of 88 symbols stale. Held tickers APLD, CBRS, GOOG, MP, NBIS, RIOT, SPCX and STM are also not on that watchlist at all. KOID is still on it.
- Changes: the heatmap no longer swallows a failed TradingView overlay (logs to stderr) and the Refresh message now lists symbols that were not quoted. Scrolling the list and `Page.bringToFront` did not make pending rows resolve, so that attempt was reverted.
- Open: keep TradingView visible during Refresh, add the eight held tickers to the watchlist, remove KOID.
