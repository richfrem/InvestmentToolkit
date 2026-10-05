# Current recommendation consumer audit

2026-10-04 — branch `feat/canonical-recommendation`, worktree `.worktrees/canonical-action`.
The earlier Python checkpoint is `9425f92d`; this follow-up completes the consumer alignment.

## Web surfaces and API producers

| Surface / producer | Current recommendation source |
| --- | --- |
| Portfolio Table / portfolio dashboard | Shared React recommendation snapshot |
| Screener Table / Advisor table | Same snapshot; browser allocation override removed |
| Stock Analysis header / trade-button emphasis | Same snapshot |
| AI thesis summary | Same snapshot; saved research rationale remains dated research |
| AI analysis modal | Same snapshot; DCF lens comes from the same record |
| Valuation modeler action badge | Same snapshot; edited/saved model assumptions remain research inputs |
| Technical Analysis Summary | Same snapshot; regime and level references are timing information |
| Latest Review modal | Same snapshot; target deltas remain allocation information |
| Daily Brief score table / action cards | Same snapshot; current brief API rebuilds canonical cards |
| Trade preparation provenance | Canonical valuation lens; manually chosen trade side is user input |
| Pine viewer generated action | Dashboard passes canonical action; no INITIATE fallback |
| GET /screener/recommendations | Python recommendation loader through the real bridge |
| GET /screener/all-holdings | Same canonical records, including action/reason/upside/current weight |
| GET /stock/:ticker/technical-analysis | Same loader; technical action classifier removed |
| GET /stock/:ticker (ETF path) | Same loader replaces saved ETF action |
| GET /projections and /projections/:ticker | Same current recommendation annotation; stored versions preserved |
| POST /analysis/valuation | Same current action; model opinion retained as researchAction |
| Thesis health drift alerts | UNDERWEIGHT/OVERWEIGHT information, no BUY/SELL recommendation |
| Thesis optimizer endpoint | Canonical recommendations with separate health/drift context |

## Scripts

| Consumer | Alignment |
| --- | --- |
| portfolio_action | Compatibility signature only; caller weights/upside cannot override DB data |
| generate_news_prompt, generate_review_json, generate_sub_strategy_blocks, verify_refresh | Delegate through compatibility shim |
| generate_portfolio_blueprint | Canonical action and valuation lens; duplicate assign_action removed |
| relabel_actions | Canonical records; target delta is display data only |
| compute_conviction_scores | Canonical action/lens; numeric scores cannot produce action bands |
| brief_recommendations / query_ledger_brief | Preserve action while gating trade readiness; current snapshot overlay |
| daily_brief / alert_manager | Canonical action vocabulary; historical event compatibility retained |
| generate_reports / consolidate_research | Canonical current action instead of role fallback or saved opinion |
| scan_opportunities | Category membership and displayed recommendation come from canonical records |
| apply_catalyst / dcf_scenarios | Shared valuation_signal classifier, no second threshold ladder |
| rebalancer | Canonical valuation gate and action-direction permission before proposing trades |
| ta_sweep_batch | Canonical action; RSI/volume flags cannot override it |
| tv_thesis_overlay | Canonical action/fair value and matching selected projection scenarios |

Trade-log sides, order-preparation controls, historical projection/revision actions,
external analyst consensus, and dated TA observations are not current toolkit
recommendations. They remain explicitly historical, external, or user-selected.

## Snapshot comparison

Read from a SQLite backup of main plus a copy of its evaluated breaker state.
Main portfolio data was not modified. Current-price and valuation inputs may change;
these are consistency results, not fresh trade advice.

| Ticker | Canonical action | Current holding % |
| --- | --- | ---: |
| BE | TRIM | 6.21 |
| MU | TRIM | 4.30 |
| IREN | TRIM | 3.28 |
| GEV | TRIM | 1.70 |
| SHAZ | ACCUMULATE | 1.75 |
| INTC | WATCHLIST | 0.00 |

All current web displays consume the provider's same map, rather than reclassifying
these rows. Automated caller contracts enumerate those surfaces. A real HTTP test
renders two consumers and verifies one fetch, simultaneous refresh, and unavailable
state on source failure. This audit does not claim a manual browser walkthrough.

## Verification and remaining release gates

- Python: 1,741 passed, 9 skipped, 2 expected failures in the broad suite; another
  14 localhost/IPC-sensitive tests passed separately outside the sandbox.
- Backend: 191 passed after fixing both pre-existing failures. The holding fixture
  now includes assetClass. Price-level validation preserves SQLite's nullable
  metadata, imported annotations, tier zero, and zero-price unavailable levels;
  a real SQLite regression test verifies this without inventing metadata.
  Private-data tests use TEST_DOMAIN_MODEL_DB to read a backup without replacing
  the worktree DB or connecting to main's live database.
- Backend build and frontend `tsc -b`: pass.
- New provider/hook and recommendation-presentation lint: pass.
- Pre-push structural and symlink audits: no errors. The repo-wide conventions
  audit and legacy plugin compliance audit fail on broad documentation/convention
  debt and missing acceptance-criteria files. The new loader complexity finding
  was resolved by separating valuation input loading; focused real SQLite/CLI
  regression tests pass. The user explicitly approved publishing with these
  broader findings documented as an exception to the repository pre-push policy.
- Frontend suite: 33 passed across 10 test files, including the real HTTP context test.
- The worktree dependency links predate this continuation and remain untracked;
  they are not code changes to include in a commit.
- No live backend restart, merge, trade, or broker sync was performed. The user
  authorized committing, pushing, and opening a PR for review.
- The separate BE research worktree and main's pre-existing git-rule edit were preserved.
