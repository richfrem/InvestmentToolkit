# GEMINI.md — InvestmentToolkit

## Overview
High-end investment analysis suite: React 19 dashboard (port 5173), Node.js/Express backend (port 3001), Python yfinance bridge, TradingView CDP automation.

**Startup**: `python3 run_investment_toolkit.py` — creates venv, installs deps, launches frontend + backend + TradingView Desktop (CDP port 9222).

## Architecture
```
InvestmentToolkit/
├── investment_screener/frontend/   ← React 19 + Vite + Tailwind CSS 4.0
├── investment_screener/backend/    ← Node.js Express (port 3001)
│   ├── src/services/              ← BrokerSyncService.ts
│   └── data/projections/          ← per-ticker DCF + thesis JSON
├── tradingview-cdp/               ← CDP engine (standalone, `npm ci` once)
├── plugins/                        ← AI agent plugins
└── .agents/                        ← Skills/agents for all AI tools
```

**npm commands** — always run from `investment_screener/` (workspace root). Never use `--prefix investment_screener` from within `investment_screener/` — doubles the path and fails.
`npm run dev -w backend | frontend`, `npm run build -w backend | frontend`, `npm run lint -w frontend`.

## Daily Commands
| Command | Purpose |
|---------|---------|
| `/daily` | Full daily loop: sync → brief → triage → execute → log |
| `/weekly-review` | Weekend drift + Grok sweep |
| `/run-advisor` | Post-catalyst: review → calibrate → rebalance |
| `/tv-portfolio-sync` | Sync portfolio.json from TradingView CDP |

## Non-Negotiable Rules

1. **TDW (TDD & TDO)**: NO CODE DEVELOPMENT OR ORCHESTRATION EXECUTION WITHOUT A FAILING TEST OR SUCCESS CONTRACT FIRST. Mocking strictly prohibited on critical runtime paths. Check `.agent/rules/test-driven-development.md` before any work begins.
2. **No Inline Python**: Never compute financial/analytical calculations inline. Always extract to versioned scripts in `investment_screener/backend/py_services/`.
3. **Coding Conventions**: Google-style docstrings, type hints, snake_case/camelCase, refactor at 50+ lines or 3+ nesting levels.
4. **Dependency Management**: No manual `pip install`. Edit `requirements.in` → `pip-compile requirements.in -o requirements.txt`.
5. **Plugin Architecture**: Symlinks ONLY via `symlink_manager.py`. Never raw `ln -s`. No cross-plugin script execution.
6. **Self-Evolution & Map Debt**: Classify failures/friction (Tiers 0/1/2/3), max 3 attempts. Active map debt audit must pass in `run_tests.py`. Always execute the `PRE-COMPLETION GATE` check block and log map debt before ending the session. Deletions are strictly forbidden.
7. **Self-Healing**: Fix broken Bash/python3 snippets inline, re-run silently. Never advance with broken output visible.
8. **Standing Decision is anchor**: Read `investment.standing_decision_type`/`standing_decision_reason` (domain_model.sqlite) before any recommendation. DCF never silently overrides — only material delta (>15% FV change) or new information justifies revisiting. Never flip BUY→SELL on <15% variance.
9. **Post-trade update mandatory**: After ANY trade: sells → `lifecycle_status: "exit"`, `target_weight: 0`; buys → update `agent_rationale` (shares come from the broker sync into `account_investment`, never set manually). Dashboard reads `domain_model.sqlite` — stale entries = data integrity failure.
10. **`ticker` key, not `symbol`**: All investment lookups use the `symbol` column (Python/SQL) or `ticker` key (API JSON responses) — never conflate the two across the Python/TS boundary.
11. **Sync sweep templates**: When target weights/pillars/sub-strategies change, update "Core Portfolio Thesis Background" in both `daily_sweep.md.template` and `weekly_sweep.md.template`.
12. **Refine templates on Grok ingest**: After each Grok response, improve prompt templates to guard against observed gaps (grouped tickers, lazy placeholders, TA errors).
13. **Initialize missing private data**: If any local gitignored data files (e.g., `portfolio.json`, `cash_flows.json`) are missing from `investment_screener/backend/data/`, initialize them by copying their corresponding `.example` files.
14. **Worktree-first is mandatory, not a judgment call**: Before any code/script/multi-file change, create a git worktree first — never decide unilaterally that a task is "small enough" to skip it and work directly on the main checkout. Only a single trivial doc-typo fix is exempt. See `.agent/rules/git-operations.md` and `.agent/rules/worktree-subagent-isolation.md` (Failure Mode 2) — an entire phase of work was done directly on `main` in violation of this before the rule existed in writing.
15. **Worktree lifecycle does not end at "PR created"**: full routine is (1) create worktree/feature branch → (2) implement, commit, push → (3) open PR, **do not merge it yourself unless explicitly told to** → (4) user reviews and merges the PR on GitHub → (5) **you then close the loop**: `git fetch origin`; sync local `main` to `origin/main` (merge or fast-forward — check for other in-progress work first, never force); verify the merged commit is actually an ancestor of `main` (`git merge-base --is-ancestor <branch-tip> main`); once confirmed, remove the now-merged worktree (`ExitWorktree action: "remove"`); delete the local **and remote** feature branch; confirm a clean `git worktree list`/`git branch --list`. **A user telling you "I merged the PR" is the trigger for step 5, not the end of the task** — treat post-merge repository hygiene as a mandatory completion step, not optional cleanup, and do not start next-phase work until it's done.
16. **No Autonomous Trade Execution (TradingView ToS Compliance)**: In compliance with TradingView's Terms of Use prohibiting non-display automated trading and third-party execution APIs, AI agents are strictly forbidden from placing, modifying, or cancelling live broker orders autonomously. All agent outputs are advisory only; trade execution must remain 100% human-in-the-loop (HITL) executed manually by the user directly in the official broker / TradingView UI. See `.agent/rules/trade-execution-policy.md`.

## Canonical Scripts
| Script | Purpose |
|--------|---------|
| `py_services/fetch_financials.py {TICKER}` | Raw yfinance data |
| `py_services/dcf_scenarios.py --raw FILE --scenarios FILE` | DCF scenario math |
| `plugins/stock-valuation/.../validate_projection.py` | Schema validation |

Create a new `py_services/` script + ADR in `docs/architecture/` whenever you'd compute the same formula twice.

## Test Locations
| Area | Path |
|------|------|
| Python py_services | `investment_screener/backend/tests/py_services/` |
| Express routes | `investment_screener/backend/tests/api/` |
| TV CDP | `plugins/tradingview/tests/tv_test_harness.py` |
| Plugin scripts | `plugins/<plugin>/tests/` |
| React | `investment_screener/frontend/tests/` |

## Capital Sourcing
All cash is in **PSU-U.TO** (~$100 USD/share, TSX). To fund any buy: sell PSU-U.TO in the **same account** first (never cross-account). Shares to sell ≈ `ceil(N × price / 100)`. TFSA is primary (larger); RRSP mirrors at ~1/3 share count — separate trade log entries per account for both buy and PSU sell. TSX observes Canadian holidays — PSU-U.TO can't trade those days; defer or check for leftover USD cash.

## Known Pitfalls

**1. `__dirname` in TS backend**: `dist/index.js` resolves to `backend/dist/`, not `backend/src/`. Use `path.resolve(__dirname, '../src/script.py')`.

**2. Venv gaps**: New Python imports must be in `requirements.in`. Required pkgs: `keyring cryptography yfinance pandas fastapi uvicorn pydantic rich typer python-dotenv`. After edit: `venv/bin/pip-compile requirements.in -o requirements.txt`.

**3. Backend restart required**: Production runs `node dist/index.js`. Changes → `npm run build -w backend` → restart. Frontend hot-reloads; backend does not.

**4. (Retired)**: The Questrade seed endpoint this pitfall described was removed when the standalone Questrade REST integration was archived (2026-07-16). Number kept unused, not reassigned — other docs reference pitfalls by number (e.g. #7, #27).

**5. `lastActualPS` nullable**: In `zod-schemas.ts` use `.nullable().transform(v => v ?? 0)`. Strict `z.number()` causes 400s for pre-revenue/mining stocks.

**6. Projection `action` enum**: `aiThesis.action` carries `INITIATE|ACCUMULATE|MAINTAIN|TRIM|EXIT|WATCHLIST`. DCF signal is in `analyticsLog.valuationAction`. Portfolio urgency in `analyticsLog.portfolioUrgency`. Not limited to BUY/HOLD/SELL.

**7. TV CDP single-ticker**: `tv_call("quote", sym)` reads the **active chart** regardless of `sym`. Never use for batch prices (use yfinance). "TV Live" badge = port 9222 reachable, not the price source.

**8. ETF dual-write**: `persist_etf_analysis.py` writes to `data/etf_analysis/` AND `data/projections/`. Both must exist for Dashboard + ETF view.

**9. TV CDP `process.exit()`**: All Node.js CDP snippets must end with `.then(() => process.exit(0)).catch(() => process.exit(1))`. Without it, Python `subprocess.run()` never returns.

**10. TV CDP Monaco**: Don't use CSS class selectors for Pine Editor/Monaco — TV class names change. Use `__reactFiber` key traversal to locate Monaco internals.

**11. TV CDP engine location**: At `tradingview-cdp/` root (ADR-024). Import via `tv_client.py`: `from tv_client import TV_CLI, tv_call, TV_NODE_DIR`. Never hardcode path.

**12. Pine inject — content not path**: `tv_pine_inject.py` passes `--content` to Node. Node's cwd is `tradingview-cdp/` — relative file paths from Node fail silently.

**13. "Update on chart" = "Add to chart"**: When Pine Editor has a prior script loaded, button shows "Update on chart". Selector must match both: `/(?:add|update).*(?:to|on).*chart/i` on `button.textContent + button.title`.

**14. Data Window tab**: Toggle `data-name="object_tree"`. Must switch to "Data window" tab (not "Object tree" default). Read via `[data-test-id-value-title]`. Commands: `chart openDataWindow`, `chart read`.

**15. TV CDP CLI reference**: All via `node tradingview-cdp/cli.js`: `chart symbol/timeframe/addIndicator/removeIndicator/openDataWindow/read/saveLayout`, `pine inject --file / save / read`.

**16. Temp files**: Use `InvestmentToolkit/temp/<artifact>`, not `/tmp/`. Create with `os.makedirs(TEMP_DIR, exist_ok=True)`.

**17. Account dropdown click**: Standard `.click()` fails on TV React dropdowns. Dispatch `mousedown + mouseup + click` to both the option span and its `parentElement`.

**18. PSU alias**: `PSU.U.TO` (broker format) = `PSU-U.TO` (canonical, hardcoded in `fetch_broker_data.py`). Never create two thesis entries.

**19. `targetEntryPrice`**: Optional float, stored as a `TARGET_ENTRY`-kind row in `domain_model.sqlite`'s `price_level_tier` table. Set via `update_targets.py --set-entry TICKER=PRICE --write`. Never buy above this price.

**20. Portfolio sync fallback**: (1) Express API POST sync-tv/apply → (2) `fetch_broker_data.py --snapshot` (CDP, works without backend). Run `--snapshot` directly when backend is down.

**21. Fractional shares**: `place_order.py --shares` accepts float (e.g. `0.5`).

**22. GTC orders**: CDP submits limit orders as **Day orders**. Change to "Good till cancelled" manually in TradingView after placing.

**23. Pine Editor blocks `addIndicator`**: Pine Editor dialog overlays screen, blocking Indicators search. Use "Update on chart" button directly (mouse events, not `.click()`). Check `.editorBaseLayoutContainer-dialog-z_CXxRZA` visibility, not `aria-pressed`.

**24. `addIndicator` (no Pine Editor)**: Uses `Input.dispatchMouseEvent` at Indicators button center (not `.click()` — opens timezone dropdown). Result rows: `div[class*="container-WeNdU0sq"]`; match: exact → first → contains.

**25. Source code viewing**: Legend More menu → `"Source code…"` (unicode `…`). Or Indicators dialog search → source icon (more reliable). PA Toolkit Lite [UAlgo] is open source (CC BY-NC-SA 4.0), saved at `plugins/tradingview/assets/pinescript-indicators/community-reference/`.

**26. Custom Pine library**: `plugins/tradingview/assets/pinescript-indicators/ai-ta-levels.pine` (Multi-EMA 21/50/200 + volume bias, saved in TV as "AI TA Levels"). Lint before inject: `python3 .../pine_linter.py <file.pine>`.

**27. Portfolio total validation & Exchange Rates**: Compute totals using the formula: `cash value all accounts + sum(portfolio holding price * shares)`. Never convert USD to CAD via external API calls; always infer the exchange rate directly from TradingView's native values (e.g. `totalEquityCADCombined / totalEquityUSDCombined`).
**28. Worktree/subagent isolation**: Full rule + mandatory post-task check → `.agent/rules/worktree-subagent-isolation.md`.
**29. Gitignored data files never sync via worktree**: `domain_model.sqlite`, `portfolio.json`, `cash_flows.json`, `trade-log.json`, etc. are gitignored — each worktree has its own separate on-disk copy that git never syncs back to the main checkout. Any "real data migration write" (or its row-count verification) run inside a worktree only touches that worktree's copy. Before treating a migration wave as complete, independently re-verify the real write landed in the **main checkout's** actual files/DB — do not trust a worktree-side verification alone.

**30. `target-portfolio.json` and `portfolio.json` are both retired (Wave 7/8)**: `domain_model.sqlite` is the sole source of truth for portfolio holdings, thesis targets, pillars, price levels, and standing decisions. Both files are archived under `ARCHIVE/investment_screener/backend/data/` (and `ARCHIVE/.../theses/`). Never reintroduce a direct read/write of either — use `portfolio_io.load_portfolio_state()`/`load_thesis_holdings()`/`load_target_weights()` (Python) or `InvestmentRepository`/`ThesisService`/`PriceLevelRepository` (TS).

## Key Files
| File | Purpose |
|------|---------|
| `architecture.md` | Full system architecture, data flows, ADRs, glossary |
| `run_investment_toolkit.py` | Unified startup |
| `investment_screener/backend/data/domain_model.sqlite` | Investment/pillar/price-level/projection/trade/portfolio-policy tables — sole source of truth for portfolio + thesis data (gitignored, self-creating) |
| `investment_screener/backend/data/intelligence.sqlite` | Research/TA-sweep/prediction event ledger, incl. former `ta-sweep-results.json` data (gitignored, self-creating) |
| `plugins/tradingview/scripts/ta_sweep_batch.py` | TA sweep orchestrator |
| `.agents/` | All skills/agents (Claude, Gemini, Copilot) |
| `docs/superpowers/status/wave6-program-closure-report.md` | Domain Data Model v3.2 migration program closure report (final state, KPI rollup, retained-JSON rationale) |
