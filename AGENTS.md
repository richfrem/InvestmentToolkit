# AGENTS.md

## Overview
High-end investment analysis suite built around **TradingView CDP automation** (port 9222) for live prices, chart telemetry, TA sweeps, and broker execution monitoring, backed by a React 19 dashboard (port 5173) and Node.js/Express backend (port 3001). Broker integration via Questrade MCP is an optional augment for Questrade account holders. yfinance serves strictly as a background fundamentals data bridge and offline fallback.

**Startup**: `python3 run_investment_toolkit.py` — creates venv, installs deps, launches frontend + backend + TradingView Desktop (CDP port 9222).

## Architecture
Complete repository structure, data flows, and subsystem architecture live in [`architecture.md`](architecture.md). ADRs and deep-dive specs live in [`docs/architecture/`](docs/architecture/).

**npm commands** — run from `investment_screener/` (workspace root): `npm run dev -w backend | frontend`, `npm run build -w backend | frontend`, `npm run lint -w frontend`. (Never use `--prefix investment_screener` from inside `investment_screener/`).

## On-Demand Skills (Enable / Disable)
Plugin skills, agents, rules and hooks are on demand. Look for them in `.agents/` first (`.agents/skills/<name>/SKILL.md`, `.agents/agents/`); read `SKILL.md` directly and don't copy assets into `.claude/`. Desired state lives in `.agents/ownership/<plugin>.json` (one JSON line per component with a `should_install` flag).

When the user asks to enable or disable a skill or plugin:
1. Read `.agents/ownership/<plugin>.json`, find the matching component(s); if several match or none, confirm first.
2. Set `should_install` to `true`/`false` for only those entries, keeping the one-line-per-component format.
3. Read `.agents/skills/plugin-syncer/SKILL.md` and run `python3 .agents/skills/plugin-syncer/scripts/sync_with_inventory.py` (`--dry-run` first for large changes). Never `plugin_add.py`: it resets every component to `true`.
4. Report what was enabled/disabled and what the sync changed.

Disabling removes files, so only the user's explicit request naming the skill or plugin authorizes it ("clean up skills" does not). Never toggle skills on your own initiative; suggest it and let the user decide.

## Task Planning & Discovery (Plan Mode)
For complex tasks, multi-file refactors, or feature requests:
- **Think Before Coding**: Run discovery in read-only Plan Mode first. Explicitly state assumptions, propose the minimal viable design, and list verification criteria.
- **Human Approval**: Obtain explicit user authorization before creating worktrees or modifying code.
- **Optional Control Plane**: If the optional `work-intake` skill is installed (`.agents/skills/work-intake/SKILL.md`), use `python3 scripts/agent_control.py init` to register structured tasks in `context/control_plane.db`. Otherwise, keep planning lean and direct.

## Behavioral Guidelines (Karpathy Principles)
These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
- Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- If you write 200 lines and it could be 50, rewrite it.

### 3. Surgical Changes
- Touch only what you must. Clean up only your own mess.
- Don't refactor things that aren't broken. Match existing style.
- When your changes create orphans, remove imports/variables/functions that your changes made unused.

### 4. Goal-Driven Execution
- Define success criteria. Loop until verified.
- For multi-step tasks, state a brief plan:
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]

---

## Day-1 Agent Bootstrap & Core Commands
The full, ordered setup and core command reference (`/toolkit-onboarding`, `/daily`, `/weekly-review`, `/strategic-review`, `/tv-portfolio-sync`) live in [`INIT_AGENTS.md`](INIT_AGENTS.md). Follow it in order on any fresh clone; this file (`AGENTS.md`) holds behavioral rules and invariants.

## TradingView Skills & CDP Engine
- **Use the skills for TradingView work.** The `tv-*` skills (`.agents/skills/tv-*/SKILL.md`, e.g. `tv-portfolio-sync`, `tv-place-order`, `tv-ta-daily-sweep`, `tv-pine-inject`, `tv-get-orders`, `tv-alert-sync`) hold the documented workflow, constraints and verification steps. Read the matching `SKILL.md` and follow it; don't improvise a script run from memory.
- **All TradingView access goes through the CDP engine in `tradingview-cdp/`** (`node tradingview-cdp/cli.js status|quote|chart|pine|alert|watchlist|sweep`, or `tv_client.py` from Python). Check connectivity first with `node tradingview-cdp/cli.js status`; port 9222 must be reachable.
- **Per-account broker reads**: `--positions` and `--accounts` reflect only the account currently selected in the broker panel. For all accounts, use `getPortfolio()` from `tradingview-cdp/core/broker_data.js` (via `tv_client.run_node_module`), which switches through each account and returns one snapshot per account. Compare against the stored per-account holdings (`account_investment` joined to `account`) before any commit. A `--positions` read that matches one account's share counts (about a third of the stored total for RRSP) is not a full sync.
- **Account switching**: `switchAccount` checks whether the dropdown is open before toggling it and retries on a miss (`switchWithRetry`). If a sync still reports "Account not found in dropdown", that account was not read and its stored rows are unchanged; re-run rather than asking the owner to click. The CASH account has no positions but holds real cash, so its balance must still be read; `--allow-partial` skips it and leaves the stored balance stale.
- **Commits need approval**: a `--snapshot` or trade import writes to `domain_model.sqlite`. Show the per-account diff and get the owner's go-ahead first.

## Non-Negotiable Rules
Detailed policy documents and invariants are governed in [`.agent/rules/`](file:///.agent/rules/). Key invariants:

1. **TDW (TDD & TDO)**: Strict test-first development. No runtime mocking on critical paths. See [`.agent/rules/test-driven-development.md`](file:///.agent/rules/test-driven-development.md).
2. **No Inline Python**: Never compute analytical or financial math inline. Always extract to versioned scripts in `investment_screener/backend/py_services/`.
3. **Coding Conventions**: Follow [`.agent/rules/coding-conventions.md`](file:///.agent/rules/coding-conventions.md) (standard headers, docstrings, type hints).
4. **Dependency Management**: No manual `pip install`; edit `requirements.in` → `pip-compile`. See [`.agent/rules/dependency-management.md`](file:///.agent/rules/dependency-management.md).
5. **Plugin Architecture**: Symlinks only via `symlink_manager.py`. No cross-plugin script execution. See [`.agent/rules/plugin-architecture-policy.md`](file:///.agent/rules/plugin-architecture-policy.md).
6. **Self-Evolution & Map Debt**: Active map debt audit must pass in `run_tests.py`. Always run the `PRE-COMPLETION GATE` and log map debt before turn end. See [`.agent/rules/self-evolution-policy.md`](file:///.agent/rules/self-evolution-policy.md).
7. **Destructive Action Guards**: Deletions strictly forbidden without approval. See [`.agent/rules/destructive-action-guard.md`](file:///.agent/rules/destructive-action-guard.md) and [`.agent/rules/skill-deletion-guard.md`](file:///.agent/rules/skill-deletion-guard.md).
8. **Self-Healing**: Fix broken scripts/snippets inline; re-run silently. Never leave broken command output visible.
9. **Standing Decision is Anchor**: Read `standing_decision_type` in SQLite before recommending action changes. Never flip BUY→SELL on <15% variance.
10. **Post-Trade Update Mandatory**: After ANY trade: sells → `lifecycle_status: "exit"`, `target_weight: 0`; buys → update `agent_rationale`. Never set shares manually.
11. **`ticker` Key, Not `symbol`**: Use `symbol` column for SQL/Python and `ticker` key for API JSON payloads — never conflate.
12. **Sync Sweep Templates**: Update "Core Portfolio Thesis Background" in daily/weekly sweep templates when target weights change.
13. **Refine Templates on Grok Ingest**: Guard prompt templates against observed gaps after each Grok response.
14. **Initialize Missing Config**: Copy `.env.example` to `.env` if missing; record YTD baseline with `set_cash_flow_baseline.py`. Never recreate legacy JSON files.
15. **Worktree-First Mandatory**: Create a dedicated git worktree before any multi-file change. See [`.agent/rules/git-operations.md`](file:///.agent/rules/git-operations.md), [`.agent/rules/local-git-operations-overrides.md`](file:///.agent/rules/local-git-operations-overrides.md), and [`.agent/rules/worktree-lifecycle-management.md`](file:///.agent/rules/worktree-lifecycle-management.md).
16. **Worktree Lifecycle Completion**: PR merge triggers cleanup: sync local main, verify ancestry, remove worktree, and delete local/remote branch.
17. **No Autonomous Trade Execution (HITL Only)**: TradingView ToS compliance. All orders are strictly advisory; trade execution is 100% human-in-the-loop. See [`.agent/rules/local-trade-execution-policy.md`](file:///.agent/rules/local-trade-execution-policy.md).
18. **Mandatory Cash Invariant for Portfolio Totals**: Total USD = `sum(Held Equities Market Value) + sum(Account Cash USD)`. Never omit uninvested cash.
19. **Adversarial Reasoning & News Confluence**: Challenge thesis assumptions and correlate news catalysts with price action. See [`.agent/rules/adversarial-reasoning-before-agreement-rule.md`](file:///.agent/rules/adversarial-reasoning-before-agreement-rule.md) and [`.agent/rules/local-news-technical-confluence.md`](file:///.agent/rules/local-news-technical-confluence.md).
20. **TradingView Baseline & Broker MCP Independence**: TradingView CDP is the universal baseline. Broker plugins (Questrade MCP) are optional user augments. See [`.agent/rules/local-broker-augment-policy.md`](file:///.agent/rules/local-broker-augment-policy.md).
21. **Domain Database Location & Sync Ingestion**: `investment_screener/backend/data/domain_model.sqlite` is the sole source of truth. Always use canonical sync scripts (`fetch_broker_data.py --snapshot` or `questrade_sync.py --payload`).
22. **One Implementation Per Concept**: Proper architecture over duplicate code. Consolidate formulas, calculations, and UI helpers into canonical shared modules.
23. **One Table System, One SQLite Row Source**: All ticker screens render through `PositionsTable` (`investment_screener/frontend/src/components/positions/`) fed by `/api/screener/all-holdings`. Never hand-write ticker tables or freeze static markdown tables.
24. **Thesis Pages Stay Current From SQLite Ledger**: Sweep findings record into `intelligence.sqlite`; thesis notes update in `thesis_document_currency`. Never write dated volatile prices into markdown.
25. **Installed Rules vs Local Rules**: Installed rules from `agent-plugins-skills` overwrite during sync; project-specific overrides must strictly live in [`.agent/rules/local-*.md`](file:///.agent/rules/). See [`.agent/rules/local-worktree-and-dual-repo-edit-protocol.md`](file:///.agent/rules/local-worktree-and-dual-repo-edit-protocol.md).

## Canonical Scripts
| Script | Purpose |
|--------|---------|
| `py_services/fetch_financials.py {TICKER}` | Raw yfinance data |
| `py_services/dcf_scenarios.py --raw FILE --scenarios FILE` | DCF scenario math |
| `plugins/stock-valuation/.../validate_projection.py` | Schema validation |
| `plugins/stock-valuation/scripts/price_changes.py` (`period_changes`) | The only 1D/1W/1M/3M/YTD/1Y/5Y % change calculation (heatmap, tables, Stock Analysis) |

Create a new canonical script + ADR in `docs/architecture/` whenever you'd compute the same formula twice (see rule 22).

## Test Locations
| Area | Path |
|------|------|
| Python py_services | `investment_screener/backend/tests/py_services/` |
| Express routes | `investment_screener/backend/tests/api/` |
| TV CDP | `plugins/tradingview/tests/tv_test_harness.py` |
| Plugin scripts | `plugins/<plugin>/tests/` |
| React | `investment_screener/frontend/tests/` |

**Frontend type check:** run `npx tsc -b` in `investment_screener/frontend` (what `npm run build` runs). `tsc -p .` checks nothing: the root `tsconfig.json` has `"files": []` and only references `tsconfig.app.json` / `tsconfig.node.json`. Under `verbatimModuleSyntax`, import types with `import type`.

## SUB-agent usage
Use the cheapest models possible where possible. If the job doesn't require spawning sub-agents don't do so.

## Capital Sourcing
All cash is in **PSU-U.TO** (~$100 USD/share, TSX). To fund any buy: sell PSU-U.TO in the **same account** first (never cross-account). Shares to sell ≈ `ceil(N × price / 100)`. TFSA is primary (larger); RRSP mirrors at ~1/3 share count — separate trade log entries per account for both buy and PSU sell. TSX observes Canadian holidays — PSU-U.TO can't trade those days; defer or check for leftover USD cash.

## Known Pitfalls
All 30 cataloged integration traps, TradingView CDP subtleties, and database edge cases are permanently documented in [`docs/architecture/known-pitfalls.md`](docs/architecture/known-pitfalls.md). Always consult this reference before writing TradingView automation scripts, SQLite queries, or price calculation logic.


