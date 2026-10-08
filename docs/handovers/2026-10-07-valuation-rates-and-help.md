# Handoff: valuation rates, shared methodology, app help and APLD report

## Copy/paste prompt for the next agent

Continue the InvestmentToolkit valuation consistency work. First read this entire handoff and the repository AGENTS.md and git rules. Repository: `/Users/richardfremmerlid/Projects/InvestmentToolkit`. Worktree: `.worktrees/apld-earnings-review`. Branch: `docs/apld-earnings-review`. Find its PR with `gh pr view docs/apld-earnings-review`; do not assume it has merged. The user will merge the PR. Finish the post-merge lifecycle, synchronize the installed plugin skills, rebuild/restart the app and verify the saved-rate card, shared financial help, saved report consistency and APLD Deep Dive in the actual browser. Preserve unrelated main-checkout edits. Do not silently change APLD's valuation method or replace its inherited rate with an invented explanation. Use the documented skills and canonical scripts for financial calculations and database access, never ad hoc SQL. Report precisely what is complete and what remains uncertain.

## User intent and authorization

The user wants one source of truth for recommendations and valuation assumptions across every app page. The immediate work is:

1. Ask Astra to review valuation method and discount-rate selection.
2. Document that process once under `plugins/stock-valuation/references`, with managed reference symlinks in `update-stock-analysis` and `stock-research`.
3. Calculate rates in Python and persist rates, inputs and rationale with valuation versions in SQLite; views read saved results.
4. Explain DCF, WACC, cost of equity and discount rate through consistent help popups, including inside existing modals and reports.
5. Show the saved discount rate as a prominent Stock Analysis metric card.
6. Fix APLD's empty Deep Dive and prevent future un-ingested reports.
7. Commit this related work, push the feature branch and create a PR for the user to merge. This is explicitly authorized. Do not merge the PR yourself.

The user has almost exhausted their credits and asked for a detailed handoff before further work. Avoid unnecessary new investigations or broad refactors.

## Repository/worktree state

- Feature branch began at `c7d901dc53afb5bdb8fe7246a8865bd4a8e61b7c` (PR #247 merge). A fresh `git fetch origin main` confirmed the same origin/main before committing.
- The handoff was written before the final commit/push/PR. Query git and GitHub for the eventual commit and PR rather than treating that starting SHA as the feature tip.
- All code/skill changes are in `.worktrees/apld-earnings-review`; `.worktrees/zs-analysis-refresh` also exists and is unrelated.
- Main has pre-existing edits to `.agent/rules/git-operations.md`, generated `investment_screener/backend/data/theses/investment_thesis.md`, and untracked APLD/ZS research Markdown files. Do not stash, discard or commit these indiscriminately.
- The APLD report is included in this feature worktree. Once merged, reconcile the identical main-side untracked report safely before pulling if Git reports a collision. Verify equality first; preserve any newer content.
- The opt-in control plane is disabled: `.agents/skills/work-intake/SKILL.md` is absent. Do not initialize control-plane state or impose its stage gates.

## Financial context: do not misrepresent APLD

An earlier agent replaced the existing discounted terminal EPS/P/E model with an inadequately supported FCFF model, driving fair value to $6.53. The user rejected the unexplained model change. That result was withdrawn. A limited share-count remeasurement retained the prior terminal-equity assumptions and produced $27.67. It is explicitly marked **NEEDS_REVALUATION**, not a fully validated new forward cash-flow forecast.

The inherited rate is **12.77%**. We could not recover historical inputs that reproduce that exact number. Other historical artifacts showed different WACC figures; do not fabricate a precise CAPM/WACC rationale. Terminal common EPS×P/E should be discounted at cost of equity, while business FCFF uses WACC. A correction requires reviewed inputs and an explained comparison; do not silently migrate methods.

Retained remeasurement inputs: FY2026 revenue $611,311,000; filed common shares 302,387,140; five-year horizon. Bear/base/bull probabilities 20%/52%/28%; growth 24%/35%/45%; margins 8%/18%/25%; exit P/E 15/28/35; annual dilution 5%/3.5%/2.5%; quality multipliers 0.9/1/1.05. Canonical calculated scenario prices were $2.75/$21.09/$57.70. Older browser re-derivation using different shares produced slightly different targets; the popup now displays saved targets directly.

The main database was previously republished as APLD v12 through the supported authenticated API to repair display metadata. This implementation did not change the live valuation rate, fair value, holdings, standing decisions or targets. Quote snapshots can differ from today's market quote; inspect timestamps rather than treating changing upside as a rate change. The user-facing canonical action must come from the recommendation service, not a new page-level rule.

## Implemented changes

### Shared methodology and scripts

- `plugins/stock-valuation/references/valuation-method-and-discount-rate.md`: Astra-reviewed procedure covering prior-model reproduction, claim/rate matching, dated risk-free/ERP/beta/debt evidence, usable tax shields, project ownership and financing claims, dilution, sensitivities, migration acceptance, readiness and publication/readback.
- Managed symlinks into both requested skill references; `symlinks.json` updated. Both skills route to the procedure before valuation decisions.
- `wacc.py --inputs FILE --pretty`: explicit, reproducible, uncapped rate calculation with no live fetch or silent defaults. `annual_fcff` selects WACC; `terminal_earnings` selects cost of equity. Retains original inputs/sources, raw components and `REVIEW_REQUIRED`. Rates are decimals. The existing live diagnostic path retains its legacy defaults and 7–14% clamp; it is not a validated estimate.
- `persist_valuation.py --file PAYLOAD --rate-audit AUDIT --db MAIN_DB`: verifies audited rate arithmetic and known duplicated method/rate metadata before opening the DB. Stores the audit at `analyticsLog.valuationModel.discountRateAudit`, selected rate in the snapshot and calculated scenarios in their existing table. Preserves existing model metadata and the research report pointer. Domain persistence was split into small helpers to meet the modified-file complexity/length requirements; transaction behavior is covered by real CLI/SQLite tests.
- Python callers can use `attach_discount_rate_audit(payload, audit)` and then `persist_valuation(payload, db_path=...)`. Metadata checks do not prove scenarios were recalculated or sources authenticated. Review/recalculate before publication.
- `persist_research.py`: new canonical publisher using existing `intelligence.event_store.append_or_supersede_event` and `replay_events_to_db`. Reads dated Markdown, publishes an idempotent research event and replays the ledger into SQLite. Same-day corrected content supersedes the prior event. Invalid dates/empty content are rejected. No manual SQL, no report deletion. Managed py_services symlink added.
- Skills now require ledger publication of reports and explicit `projection.researchReport` metadata. Shared acceptance criteria added through managed links to satisfy the plugin auditor. Evolution log and realistic skill eval cases updated.

### Backend/app

- `ProjectionRepository.ts`: reconstructs Python snapshots into the API contract, returns the full stored rate audit, retains scenario prices/research pointer and converts known Python decimal rates to API percentage units without guessing from magnitude. Missing rates remain absent rather than fabricated 10%.
- `AIAnalysisModal`: displays persisted scenario prices, distinguishes missing targets from real zero, uses the shared saved-rate presentation and help trigger. It reads canonical recommendations.
- `SavedValuationRateCard`: first metrics row, with saved rate/fair value, audited WACC or cost-of-equity label when present, and evidence status. An unaudited legacy rate is labeled “Rate basis unverified”; an arithmetic audit still says evidence review is required.
- `valuationPresentation.ts`: one saved-rate presentation function for overview and thesis. It reads API percentage values; it does not estimate rates in the browser.
- `ValuationModeler`: retains the loaded saved projection separately from editable what-if state. Full Report opens the saved projection rather than inventing a temporary report with slider inputs. Uses saved snapshot revenue/shares when a projection is loaded. Changed editor rate is explicitly labeled a what-if assumption.
- `HelpContent` contains one shared DCF/WACC/cost-of-equity/discount-rate explanation. Removed the old claim that 10% is a universal baseline. Help dialogs have accessible names and remain above existing popups.
- `SmartText` links terms with word boundaries. `withFinancialHelp` preserves formatted Markdown/source links while adding term help; excludes links/buttons/code from nested triggers.
- Help wired into Daily Brief headers/rationales, trade-prep provenance, thesis narratives, tier explanations, analysis/modeler labels, research prompt card and Pine overlay UI. Generated Pine code is unchanged.
- Deep Dive shows actual API error details and supports help links in report paragraphs/lists/tables.

## Live Deep Dive repair already completed

Root cause: `/api/research/TICKER_DATE.md` intentionally reads **intelligence.sqlite**, with no filesystem fallback for dated reports. The APLD Markdown report existed, but no matching research event had been ingested.

Ran the reviewed feature publisher **from the main checkout**, with explicit main paths:

```bash
python3 .worktrees/apld-earnings-review/plugins/stock-valuation/scripts/persist_research.py \
  --file investment_screener/backend/data/research/APLD_2026-10-07.md \
  --db investment_screener/backend/data/intelligence.sqlite \
  --jsonl investment_screener/backend/data/observations.jsonl
```

Receipt: `evt_bbcba48f75b5`, one processed event, no skipped events. Canonical `query_ledger_research.py --get APLD_2026-10-07.md` returns the full report. Authenticated read of the **running main backend** at `http://127.0.0.1:3001/api/research/APLD_2026-10-07.md` returned **HTTP 200**; readback artifact `temp/APLD_research_api.json`. Refresh/reopen Deep Dive; no backend restart is required for this data repair.

Do not re-ingest repeatedly as a workaround or add a stale-file fallback to the route. Use the canonical publisher if the reviewed report changes.

## Verification completed

- **102 Python tests passed:** `python3 -m pytest plugins/stock-valuation/tests investment_screener/backend/tests/py_services/test_wacc.py -q`.
- **30 backend tests passed:** ProjectionRepository plus docs research route/query tests, including real Python CLI -> SQLite -> TypeScript readback.
- **16 frontend tests passed:** saved rates, missing rates, help dialogs, acronym boundaries, Daily Brief filters, formatted report source links, and changing editor rate to 15% while Full Report remains at saved 12.77% with saved scenario target $21.09.
- Frontend and backend production builds passed from `investment_screener/` workspace root.
- `git diff --check` passed. Managed symlink diagnosis passed. Structural plugin audit had zero errors, one existing external-doc-link warning.
- Plugin compliance auditor passed after acceptance criteria links were placed under skill `references/`. Existing reference-navigation warnings remain.
- Workspace conventions audit was run on main and feature. Main already had hundreds of legacy violations. Modified/new canonical files have no newly introduced hard errors; the long modified persistence function was split. Soft complexity/length warnings remain. Do not turn this handoff into a repository-wide cleanup.
- Installed audit-plugin executable initially failed because its installed package lacks `references/skill-authoring-contract.json`; used the canonical source auditor from sibling `agent-plugins-skills` instead. Generic Codex skill validator also rejects the repository's pre-existing `plugin` frontmatter; repository skill/structure audits are the appropriate compatibility checks.
- Skill behavioral model evals were added but not executed; Astra performed a static methodology/code review. Do not claim full agent behavioral evaluation.

Node details: default Node 20 works with native better-sqlite3. Backend Mocha uses `NODE_OPTIONS=--experimental-require-module ../node_modules/.bin/mocha -r ts-node/register tests/ProjectionRepository.spec.ts tests/api/docs.research.spec.ts`. Frontend Vitest/jsdom requires `/opt/homebrew/opt/node@26/bin/node ../node_modules/vitest/vitest.mjs run tests`. Local HTTP fixture tests need permission to bind localhost in the sandbox. The modeler test uses a real JSDOM Storage instance to avoid Node 26's unavailable native localStorage. Worktree dependencies were installed with `npm ci --offline --no-audit --no-fund`; no raw directory symlinks.

## Remaining work / post-merge checklist

1. Ensure commit, origin feature push and PR exist. If the prior agent completed these after writing the handoff, read them; do not duplicate the PR.
2. When the user says merged, verify the PR state/merge result. Fetch origin, safely fast-forward local main after inspecting its dirty state, and verify the merged work. Squash merges may require inspecting the actual PR merge SHA rather than assuming the original branch tip becomes an ancestor.
3. Read `plugin-syncer/SKILL.md` and run the canonical sync script from main after merge. Installed `.agents/skills` copies are still based on main before the feature merge; do not assume worktree skill edits updated installed skills.
4. Build backend from `investment_screener/` and restart the running main backend using the startup skill/script. Frontend source hot-reloads after main updates, but confirm the browser is on the intended server. Do not point production at the worktree's isolated databases.
5. Browser check: APLD overview rate card shows saved 12.77% with an unverified-basis label; its popup explains the method. Thesis popup shows the same saved rate and stored scenario prices. Modeler loading the same saved projection uses that rate; changing it is marked what-if, and Full Report still opens saved results. DCF/WACC links open above the active modal. Deep Dive renders APLD's report.
6. Verify labels and behavior for at least one audited FCFF and one audited terminal-equity **test fixture**. Do not change a live stock merely to demonstrate a card.
7. Remove the merged feature worktree and local/remote branch only after safe merge verification and preserving all in-progress files. Never force-reset, stash without authorization, or delete the unrelated ZS worktree on assumption.

## Explicit limitations / possible future work

- This work does not establish a newly researched APLD discount rate or complete its forward capex/financing/common-equity-waterfall valuation. The original research flag remains. A further APLD revaluation must use the named skills, dated earnings/transcript evidence and the new process with supported inputs.
- Explicit rate calculation supports a simple common equity/debt structure and nonnegative inputs. Preferred capital, changing NOL shields/leverage, APV/project waterfalls, negative-beta/rate cases and native FCFE are not implemented.
- Legacy live WACC still has fallbacks, a clamp and beta/data-quality limitations; the explicit input path avoids silently relying on them. Improving the live estimator is separate work.
- `recalculate_forward_valuation.py` forces annual FCFF and is not a method-neutral replacement tool. Its reverse earnings lens is not automatically independent cash-flow corroboration.
- General schema validation and direct API saves do not enforce the entire research protocol; Python audited persistence checks arithmetic/metadata, while source quality and migration acceptance remain agent review requirements.
- The interactive browser modeler remains an EPS/P/E what-if tool. It is not a full annual FCFF forecast editor. Do not present browser-generated earnings simulations as reproductions of an annual cash-flow model.
- No live trades were executed. No automatic backend restart or plugin sync was performed before the feature merge.
