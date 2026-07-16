# Phase 6 — Questrade Integration Archive — Design

_Date: 2026-07-16_

## Context

During Phase 6 brainstorming (skills/sub-agent architecture cleanup), the user revealed a decision
made outside this file's tracking: the toolkit has fully pivoted to TradingView CDP as its sole
broker/data integration. Questrade's standalone REST API integration (OAuth token exchange, direct
REST calls bypassing TradingView) is no longer used and should be removed from the active codebase.
`BrokerSyncService.ts` already shows evidence of a prior partial pivot — its Questrade fallback call
is already commented out ("Questrade fallback disabled per user request (pure TradingView mode)")
— but the surrounding integration code, skill, docs, and a frontend Settings modal were never
cleaned up.

This is explicitly **not** the same as the general "dead/superseded skill pruning" candidate
identified during initial Phase 6 scoping — it surfaced mid-session as a distinct, concrete
decision with its own full investigation, and is being treated as its own sub-project.

## Critical distinction driving scope

"Questrade" appears in two unrelated contexts across this repo:

1. **The deprecated standalone REST integration** — OAuth token exchange, `QuestradeDataEngine.py`,
   `QuestradeAPIClient.py`, `QuestradeTokenManager.py`, `QuestradeSyncService.ts`, the
   `questrade-token-setup` skill, `/setup-questrade`, `/sync-questrade`, `/api/questrade/seed`. This
   is what's being removed.
2. **The user's actual brokerage identity** — the real account TradingView CDP syncs from IS a
   Questrade account. Phrases like "Questrade panel visible in TradingView," "log in with your
   Questrade credentials," "Canadian equities on Questrade settle T+1," and the
   `norberts-gambit` skill's Questrade appendix all accurately describe the *current, live* broker
   via TradingView — not the deprecated integration. **These are left untouched.** Removing them
   would delete accurate information, not stale information.

Every file below was individually checked against this distinction before being placed in the
Archive or Edit list. A file mentioning "Questrade" is not automatically in scope.

## Approach

**Archive, don't delete.** Move Questrade-integration-specific files to `ARCHIVE/questrade/` at the
repo root (mirroring original relative paths), add `ARCHIVE/` to `.gitignore`, and `git rm --cached`
the original tracked paths. This means:
- The files remain immediately available locally (no `git checkout <sha> -- path` archaeology
  needed if ever revisited).
- They drop out of git tracking and out of the active plugin/routing surface (no `plugin.json`
  entry, no `SKILL.md` discovery, no doc mentions in the active docs).
- Git history still shows the removal commit, satisfying "we have code history in github if we ever
  need the questrade features back."

**Historical records are never touched.** ADRs (001, 003, 006, 010, 011, 012, 013, 015, 019, 023,
025), completed specs (`docs/superpowers/specs/done/*`), and archived tasks (`tasks/done/*`) stay
exactly as they are — they're immutable decision/implementation records. If a new ADR is ever
wanted to formally record this pivot, that's a separate, later decision, not part of this cleanup.

**Gitignored live data files are never touched.** `investment_screener/backend/data/{balances,
orders,currentHoldings,positions,accounts}.ts` and `theses/investment_thesis.md` likely contain
"questrade" only as a literal broker-name data value inside real synced portfolio state — per this
project's standing rule on gitignored user data files, these are not edited as part of a docs/code
cleanup pass.

## Scope

### A. Archive to `ARCHIVE/questrade/` (git rm --cached + physical move)

| Original path | Archive path |
|---|---|
| `investment_screener/backend/src/QuestradeDataEngine.py` | `ARCHIVE/questrade/backend/src/QuestradeDataEngine.py` |
| `investment_screener/backend/src/utils/QuestradeAPIClient.py` | `ARCHIVE/questrade/backend/src/utils/QuestradeAPIClient.py` |
| `investment_screener/backend/src/utils/QuestradeTokenManager.py` | `ARCHIVE/questrade/backend/src/utils/QuestradeTokenManager.py` |
| `investment_screener/backend/src/utils/PortfolioAggregator.py` (orphaned once DataEngine moves — its only caller) | `ARCHIVE/questrade/backend/src/utils/PortfolioAggregator.py` |
| `investment_screener/backend/src/services/QuestradeSyncService.ts` | `ARCHIVE/questrade/backend/src/services/QuestradeSyncService.ts` |
| `investment_screener/backend/tests/test_token_manager.py` | `ARCHIVE/questrade/backend/tests/test_token_manager.py` |
| `investment_screener/backend/tests/test_data_engine.py` | `ARCHIVE/questrade/backend/tests/test_data_engine.py` |
| `investment_screener/backend/tests/services/QuestradeSyncService.spec.ts` | `ARCHIVE/questrade/backend/tests/services/QuestradeSyncService.spec.ts` |
| `investment_screener/frontend/src/components/QuestradeSetupModal.tsx` | `ARCHIVE/questrade/frontend/src/components/QuestradeSetupModal.tsx` |
| `plugins/toolkit-manager/skills/questrade-token-setup/` (3 files) | `ARCHIVE/questrade/plugins/toolkit-manager/skills/questrade-token-setup/` |
| `plugins/toolkit-manager/references/Questrade/` (7 files) | `ARCHIVE/questrade/plugins/toolkit-manager/references/Questrade/` |

### B. Edit — remove the dead/removed-integration references only

- `investment_screener/backend/src/index.ts` — remove `/api/questrade/seed` route + its doc comment
- `investment_screener/backend/src/routes/portfolio.ts` — remove `/sync-questrade` route,
  `questradeSyncService` import, and the dead `() => questradeSyncService.runSync()` fallback arg
- `investment_screener/backend/src/services/BrokerSyncService.ts` — remove the already-dead
  commented-out fallback block, the unused `_questradeSyncFn` param, and `'questrade'` from the
  `dataSource` type union (now unreachable)
- `investment_screener/backend/src/README.md`, `architecture.md`, `docs/architecture/README.md` —
  update file-tree/diagram/table entries referencing the removed engine/service
- `plugins/tradingview/scripts/place_order.py` — remove the tier-3 legacy Questrade REST fallback
  in `sync_portfolio()` (currently subprocess-calls `QuestradeDataEngine.py` by path with no
  existence check — would hard-fail once archived); keep tiers 1 (Express API) and 2 (direct CDP
  snapshot) intact, with a clear failure message if tier 2 fails
- `plugins/tradingview/skills/place-order/SKILL.md`, `plugins/portfolio-advisor/skills/x-news-sweep/SKILL.md`
  — drop "Questrade API" from data-source template lists only (the rest of these files' Questrade
  mentions are live-broker-identity and stay untouched)
- `investment_screener/frontend/src/services/api.ts` — remove `syncQuestrade()` and
  `seedQuestradeToken()` functions
- `investment_screener/frontend/src/pages/Settings.tsx` — remove the `QuestradeSetupModal` import
  and its trigger/render
- `AGENTS.md`, `README.md` — remove the Questrade sections entirely (supersedes today's earlier
  "deprecated" labeling commit — full removal now, not just a label)
- `.claude/CLAUDE.md` (gitignored, local only), `GEMINI.md`, `.github/copilot-instructions.md` —
  remove Questrade Auth section and Overview mention (these three are near-duplicates of the same
  content)
- `.claude-plugin/marketplace.json` — remove Questrade mention from the toolkit-manager plugin
  description
- `ecosystem_yaml_summary.md`, `skills-lock.json` — remove the `questrade-token-setup` entries
  (check first whether either is auto-generated by an existing tool before hand-editing — if
  generated, prefer re-running that generator over hand-editing)
- `run_investment_toolkit.py`, `start_here.md`, `tradingview-cdp/README.md` — light-touch line
  removals (single mentions of the retired setup flow)
- `plugins/toolkit-manager/plugin.json`, `plugins/toolkit-manager/.claude-plugin/plugin.json` —
  remove the `questrade_token_setup` skill entry and `"questrade"` tag/keyword entirely (supersedes
  today's earlier "deprecated" labeling commit)

### C. Explicitly left untouched

- Historical ADRs, `docs/superpowers/specs/done/*`, `tasks/done/*`
- Gitignored live data files (`backend/data/*.ts`, `theses/investment_thesis.md`)
- Every file/line describing the live Questrade broker identity via TradingView (broker panel,
  credentials, settlement rules, `norberts-gambit`'s Questrade appendix, `fetch_broker_data.py`'s
  comparison-baseline labeling — none of these call the deprecated REST integration)

## Verification

This touches live route/service code with existing test coverage. Before considering this done:
1. Run the backend test suite (`npm test` in `investment_screener/backend`) — confirm no new
   failures beyond the pre-existing baseline (35 known-environmental failures per `start_here.md`).
2. Run a frontend typecheck/build (`npm run build -w frontend` or equivalent) — confirm removing
   `QuestradeSetupModal`'s import from `Settings.tsx` and the two `api.ts` functions doesn't leave
   dangling references anywhere else.
3. Confirm `ARCHIVE/` is genuinely gitignored and `git status` shows a clean set of deletions
   (archived files) and edits (modified files) with nothing left in a broken half-state.

## Out of Scope

- Rewriting or annotating historical ADRs/specs.
- Touching gitignored live portfolio data files.
- Editing any file where "Questrade" refers to the live broker identity rather than the retired
  REST integration.
- The other three Phase 6 sub-projects (eval coverage backfill, broader dead/superseded skill
  pruning beyond Questrade, reward-modeling groundwork) — separate specs.
