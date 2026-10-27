# Wave 3 summary: tradingview (27 skills -> 3 hubs, 1 agent)

| Check | Result |
|---|---|
| Ledger accounting (`verify --wave 3`) | 151 rows, 0 failures, 0 directory-level warnings; 16 path-expression warnings reviewed |
| Knowledge parity | 317 of 323 substantive lines verbatim; 6 deliberate (3 references to scripts that never existed corrected, 3 skill-name mentions turned into mode links) |
| Evals | 151 of 151 carried over (83 / 41 / 27 per hub), tagged with `mode` |
| `validate_apm_package.py` / `audit_skill.py` (3 hubs) | passed / PASS |
| Import smoke test of all 25 moved scripts in fresh interpreters | all import |
| Regression vs baseline | backend Python 1796 (= 1771 + 25 engine tests moved in), TypeScript 237/2, tradingview 101 passed + the same 4 expected failures (126 - 25 moved), all other suites identical |

Findings
- The exact-path rewrite is not enough for Python: `sys.path` inserts of a plugin's `scripts` folder, segment-built paths and dotted-module imports need their own handling. Added `dirfix` to the tool, a directory-level warning to `verify`, and a test for both.
- The first regression run showed 9 backend tests failing to import `pine_linter` / `tv_batch_quotes`; `fetch_portfolio_heatmap.py` (the module behind the web app's price Refresh) had the same problem and wraps its TradingView import in `except Exception: pass`, so it would have failed silently. Fixed before commit.
