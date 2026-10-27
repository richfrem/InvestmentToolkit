# Wave 1 summary: questrade (9 skills -> 2 hubs)

Date: 2026-10-26. Mapping approved by the owner; checkpoint commit 50ca6fa3 precedes it.

| Check | Result |
|---|---|
| Ledger accounting (`rewrite_references.py verify --wave 1`) | 47 rows, 0 failures; 3 path-expression warnings (`parents[1]` inside the tests, relative to the skill folder, reviewed) |
| Knowledge parity (old SKILL.md lines vs new mode files) | 216 of 221 substantive lines verbatim after link/path normalisation; 5 are deliberate wording changes ("skill" -> "mode") |
| Evals | 26 of 26 carried over, tagged with `mode` |
| `validate_apm_package.py` (structure checks active: `packaging_mode: full`) | passed |
| `audit_skill.py --mode source` (authoring-skills version) | both hubs PASS, no warnings |
| Real `apm install` into a throwaway project (`agent-skills,claude`) | both hubs deployed, MCP server configured, 37 relative links in deployed copies all resolve |
| Regression suites vs baseline | backend Python 1771 = baseline; backend TypeScript 237/2 = baseline; stock-valuation 113, tradingview 126/4, toolkit-manager 74/2 = baseline; questrade 27 and etf-analysis 5 pass at their new paths |

Findings during the wave
- Pytest skips directories that start with a dot, so tests under `.apm/` are **not** found by `pytest plugins/<name>`; they must be passed as explicit paths (`run_wave_tests.sh` does this).
- `plugins/portfolio-advisor/scripts/test_portfolio_action.py` (a test sitting in `scripts/`) fails on the pre-migration commit as well; it was never collected by the baseline run. Added to the expected failures.
- The first inventory rebuild accidentally read the post-checkpoint `HEAD`; the baseline is now pinned in `baseline-commit.txt`.
