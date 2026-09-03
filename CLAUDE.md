# CLAUDE.md — InvestmentToolkit


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

## Day-1 Agent Bootstrap Protocol (Fresh Clone Quickstart)
When dropping into a fresh repository clone, execute this sequence to reach 100% operational parity:
1. **Initialize Data Files**: Copy missing private templates (`cash_flows.json.example` → `cash_flows.json`, `portfolio-config.json.example` → `portfolio-config.json`).
2. **Compile Deps & Deploy Plugins**: Run `python3 .agents/skills/plugin-syncer/scripts/sync_with_inventory.py` to symlink all 20 plugins into `.agents/`.
3. **If using Claude Code**: Also run `/plugin marketplace add richfrem/InvestmentToolkit`, then `/plugin install <name>@investment-toolkit-plugins` for each of `tradingview`, `portfolio-advisor`, `stock-valuation`, `toolkit-manager`, `etf-analysis` — this is required for `/tv-*` and other plugin skills to appear; Step 2 alone does not register them with Claude Code.
4. **Execute Master Coordinator**: Trigger `/toolkit-onboarding` to configure accounts, seed strategy pillars, ingest broker holdings via TV CDP, and build DCF baselines.
5. **Launch Suite**: Run `python3 run_investment_toolkit.py` (React :5173, Express :3001, TV CDP :9222).

## Core Agent Commands
| Command | Purpose |
|---------|---------|
| `/toolkit-onboarding` | Master Portfolio Bootstrap Wizard: pre-flight check → plugin install → account/pillar setup → broker sync → DCF baseline |
| `/daily` | Full daily loop: sync → brief → triage → execute → log |
| `/weekly-review` | Weekend drift + Grok sweep |
| `/run-advisor` | Post-catalyst: review → calibrate → rebalance |
| `/tv-portfolio-sync` | Sync portfolio.json from TradingView CDP |

## Non-Negotiable Rules

1. **TDW (TDD & TDO)**: NO CODE DEVELOPMENT OR ORCHESTRATION EXECUTION WITHOUT A FAILING TEST OR SUCCESS CONTRACT FIRST. Mocking strictly prohibited on critical runtime paths. See [`.agent/rules/test-driven-development.md`](file:///.agent/rules/test-driven-development.md) before any work begins.
2. **No Inline Python**: Never compute financial/analytical calculations inline. Always extract to versioned scripts in `investment_screener/backend/py_services/`.
3. **Coding Conventions**: Follow [`.agent/rules/coding-conventions.md`](file:///.agent/rules/coding-conventions.md). Standard file headers (Purpose, Layer, Usage, Key Functions, Key Input Dependencies), Google-style docstrings, type hints, `snake_case`/`camelCase`, refactor at 50+ lines or 3+ nesting levels.
4. **Dependency Management**: No manual `pip install`. Edit `requirements.in` → `pip-compile requirements.in -o requirements.txt`. See [`.agent/rules/dependency-management.md`](file:///.agent/rules/dependency-management.md).
5. **Plugin Architecture**: Symlinks ONLY via `symlink_manager.py`. Never raw `ln -s`. No cross-plugin script execution. See [`.agent/rules/plugin-architecture-policy.md`](file:///.agent/rules/plugin-architecture-policy.md) and [`.agent/rules/symlink-cross-platform.md`](file:///.agent/rules/symlink-cross-platform.md).
6. **Self-Evolution & Map Debt**: Classify failures/friction (Tiers 0/1/2/3), max 3 attempts. Active map debt audit must pass in `run_tests.py`. Always execute the `PRE-COMPLETION GATE` check block and log map debt before ending the session. See [`.agent/rules/self-evolution-policy.md`](file:///.agent/rules/self-evolution-policy.md).
7. **Destructive & Skill Deletion Guards**: Deletions are strictly forbidden without approval. See [`.agent/rules/destructive-action-guard.md`](file:///.agent/rules/destructive-action-guard.md) and [`.agent/rules/skill-deletion-guard.md`](file:///.agent/rules/skill-deletion-guard.md).
8. **Self-Healing**: Fix broken Bash/python3 snippets inline, re-run silently. Never advance with broken output visible.
9. **Standing Decision is anchor**: Read `investment.standing_decision_type`/`standing_decision_reason` (domain_model.sqlite) before any recommendation. DCF never silently overrides — only material delta (>15% FV change) or new information justifies revisiting. Never flip BUY→SELL on <15% variance.
10. **Post-trade update mandatory**: After ANY trade: sells → `lifecycle_status: "exit"`, `target_weight: 0`; buys → update `agent_rationale` (shares come from the broker sync into `account_investment`, never set manually). Dashboard reads `domain_model.sqlite` — stale entries = data integrity failure.
11. **`ticker` key, not `symbol`**: All investment lookups use the `symbol` column (Python/SQL) or `ticker` key (API JSON responses) — never conflate the two across the Python/TS boundary.
12. **Sync sweep templates**: When target weights/pillars/sub-strategies change, update "Core Portfolio Thesis Background" in both `daily_sweep.md.template` and `weekly_sweep.md.template`.
13. **Refine templates on Grok ingest**: After each Grok response, improve prompt templates to guard against observed gaps (grouped tickers, lazy placeholders, TA errors).
14. **Initialize missing private data**: If any local gitignored data files (e.g., `portfolio.json`, `cash_flows.json`) are missing from `investment_screener/backend/data/`, initialize them by copying their corresponding `.example` files.
15. **Worktree-first is mandatory, not a judgment call**: Before any code/script/multi-file change, create a git worktree first — never decide unilaterally that a task is "small enough" to skip it and work directly on the main checkout. Only a single trivial doc-typo fix is exempt. See [`.agent/rules/git-operations.md`](file:///.agent/rules/git-operations.md) and [`.agent/rules/worktree-subagent-isolation.md`](file:///.agent/rules/worktree-subagent-isolation.md).
16. **Worktree lifecycle does not end at "PR created"**: full routine is (1) create worktree/feature branch → (2) implement, commit, push → (3) open PR, **do not merge it yourself unless explicitly told to** → (4) user reviews and merges the PR on GitHub → (5) **you then close the loop**: `git fetch origin`; sync local `main` to `origin/main` (merge or fast-forward — check for other in-progress work first, never force); verify the merged commit is actually an ancestor of `main` (`git merge-base --is-ancestor <branch-tip> main`); once confirmed, remove the now-merged worktree (`ExitWorktree action: "remove"`); delete the local **and remote** feature branch; confirm a clean `git worktree list`/`git branch --list`. **A user telling you "I merged the PR" is the trigger for step 5, not the end of the task** — treat post-merge repository hygiene as a mandatory completion step, not optional cleanup, and do not start next-phase work until it's done.
17. **No Autonomous Trade Execution (TradingView ToS Compliance)**: In compliance with TradingView's Terms of Use prohibiting non-display automated trading and third-party execution APIs, AI agents are strictly forbidden from placing, modifying, or cancelling live broker orders autonomously. All agent outputs are advisory only; trade execution must remain 100% human-in-the-loop (HITL) executed manually by the user directly in the official broker / TradingView UI. See [`.agent/rules/trade-execution-policy.md`](file:///.agent/rules/trade-execution-policy.md).
18. **Mandatory Cash Invariant for Portfolio Totals**: Every portfolio total calculation (in TypeScript API routes, Python services, and SQLite repositories) MUST strictly compute: `Total USD = sum(Held Equities Market Value) + sum(Account Cash USD)`. Never compute total portfolio value from stock market value alone without uninvested cash. Omitting cash causes severe valuation drift, percentage distortion, and false discrepancies against broker reports. Verify with `verify_portfolio_total.py`.
19. **Adversarial Reasoning & News Confluence**: Challenge thesis assumptions before agreement; correlate news catalysts with price action. See [`.agent/rules/adversarial-reasoning-before-agreement-rule.md`](file:///.agent/rules/adversarial-reasoning-before-agreement-rule.md) and [`.agent/rules/news-technical-confluence.md`](file:///.agent/rules/news-technical-confluence.md).
20. **TradingView Baseline & Broker MCP Independence**: TradingView CDP is the universal baseline for live pricing, TA sweeps, and visual analysis. Broker-specific MCP plugins (e.g. `plugins/questrade`) are strictly optional user-level augments for chat queries and HITL order drafting; core toolkit services, DB schemas, and dashboard routes must never depend on them. See [`.agent/rules/broker-augment-policy.md`](file:///.agent/rules/broker-augment-policy.md).
21. **Domain Database Location & Sync Ingestion**: The sole source of truth for portfolio holdings, accounts, cash balances, target weights, and thesis data is `investment_screener/backend/data/domain_model.sqlite`. When updating portfolio state from broker feeds (TradingView or Questrade MCP), always execute the canonical sync scripts (`fetch_broker_data.py --snapshot` or `questrade_sync.py --payload`) rather than executing ad-hoc raw SQL statements.

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

**4. (Retired)**: The legacy broker seed endpoint this pitfall described was removed when the standalone legacy broker REST integration was archived (2026-07-16). Number kept unused, not reassigned — other docs reference pitfalls by number (e.g. #7, #27).

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

<!-- plugin: agent-agentic-os / adversarial-reasoning-before-agreement-rule -->
---
description: >
  Prevent sycophantic, agreeable, or premature agent responses by requiring adversarial reasoning,
  assumption checks, counterarguments, and explicit approval gates before recommendations are accepted.
globs:
  - "*.md"
  - "docs/**/*.md"
  - "plugins/**/*.md"
  - "plugins/**/*.py"
  - "plugins/**/*.ts"
  - "plugins/**/*.tsx"
  - ".agents/**/*.md"
  - ".agent/rules/**/*.md"
---

# Rule: Adversarial Reasoning Before Agreement

## Why This Rule Exists

AI agents tend to be too agreeable. They often reward the user's framing, complete the requested task too quickly, and miss the harder obligation: finding flaws before implementation creates rework.

This rule forces agents to act as reviewers, architects, and auditors before acting as assistants.

The goal is not argument for its own sake.

The goal is to make agreement earned.

**A useful agent does not merely help execute a plan. A useful agent stress-tests the plan first.**

---

## The Iron Law

NO IMPORTANT RECOMMENDATION, APPROVAL, DESIGN CHANGE, MIGRATION PLAN, OR IMPLEMENTATION PLAN MAY BE ACCEPTED WITHOUT AN ADVERSARIAL PASS FIRST.

This applies to:

- Architecture decisions
- ADRs
- migration plans
- database/schema design
- data-layer refactors
- plugin and skill updates
- sub-agent instructions
- security, governance, and persistence changes
- production code implementation plans
- cleanup or deletion plans
- Git/worktree/merge/release plans

It does not apply to:

- simple factual lookup
- trivial spelling or formatting changes
- isolated mechanical edits with no design implication
- user explicitly asking only for wording polish

If the work can create data loss, hidden coupling, broken workflows, or misleading agent behaviour, this rule applies.

---

## Mandatory Response Pattern

Before agreeing, approving, or implementing, produce this structure:

```text
Assumptions That Matter:
1.
2.
3.

Strongest Objections:
1.
2.
3.

Failure Modes:
1.
2.
3.

What Is Missing:
1.
2.
3.

Recommendation:
Proceed / Proceed with changes / Do not proceed
```

Do not omit the adversarial sections because the proposal appears reasonable.

Do not start with praise.

Start with the risk surface.

---

## Prompt Pattern 1: Interrogate the Assumptions First

### Required behaviour

Before answering, identify the assumptions that would materially change the answer if false.

### Required output

```text
Assumptions That Matter:
- Assumption 1
- Assumption 2
- Assumption 3
```

Only include assumptions that affect the recommendation.

Do not ask filler questions.

If the assumptions can be resolved from the repository, files, tests, or available context, inspect those sources instead of asking the user.

### Example

Bad:

```text
Sounds good. Let's use SQLite.
```

Good:

```text
Assumptions That Matter:
- This is local-first and not multi-user.
- SQLite is a derived read model, not the authoritative ledger.
- All writers can route through one shared data layer.

If any of these are false, the recommendation changes.
```

---

## Prompt Pattern 2: Steelman Against Agreement

### Required behaviour

Before agreeing with a conclusion, argue against it as strongly as possible using credible objections.

### Required output

```text
Strongest Objections:
1.
2.
3.
```

After that, decide whether the objections defeat the proposal or merely require mitigation.

### Example

Bad:

```text
This migration plan looks solid.
```

Good:

```text
Strongest Objections:
1. The plan may miss undocumented consumers of old JSON files.
2. The new SQLite layer could duplicate access logic unless repository boundaries are enforced.
3. Cleanup could delete files before replay equivalence is proven.

Recommendation: Proceed only after adding consumer inventory and cleanup gates.
```

---

## Prompt Pattern 3: Grade the Reasoning, Not the Answer

### Required behaviour

When reviewing a plan or draft, do not rewrite it first.

First evaluate the reasoning.

### Required output

```text
Strongest Reasoning:
Weakest Reasoning:
Unsupported Claim:
Highest-Risk Assumption:
Evidence Needed:
```

### Example

Bad:

```text
Here is a rewritten version.
```

Good:

```text
Strongest Reasoning:
The plan separates JSONL authority from SQLite projection.

Weakest Reasoning:
It assumes all legacy JSON consumers are known.

Unsupported Claim:
The plan says cleanup is safe, but no ownership map exists.

Highest-Risk Assumption:
No plugin or skill still reads the old JSON path.
```

---

## Prompt Pattern 4: Ask What Is Missing

### Required behaviour

Before concluding, identify blind spots.

### Required output

```text
What Is Missing:
- Missing dependency:
- Missing consumer:
- Missing test:
- Missing rollback path:
- Missing documentation:
```

At least one missing item must be considered for non-trivial architecture, data, or migration work.

### Example

```text
What Is Missing:
- No repo-wide scan for consumers of ta-sweep-results.json.
- No manifest proving migrated JSON events match source records.
- No rule preventing future direct SQLite access outside intelligence repositories.
```

---

## Prompt Pattern 5: Commit to a Position Before Assisting

### Required behaviour

The agent must state its actual recommendation before generating implementation details.

### Required output

```text
Recommendation:
- Proceed
- Proceed with changes
- Do not proceed

Reason:
```

The recommendation must follow from the adversarial pass.

Do not hide uncertainty behind vague wording.

### Example

```text
Recommendation: Proceed with changes.

Reason:
The architecture is sound, but the plan lacks a final GitHub push gate and legacy JSON ownership map. Add those before cleanup or merge completion.
```

---

## Anti-Sycophancy Rules

### 1. Agreement must be earned

Do not say:

```text
You're right.
Good idea.
Looks great.
This is solid.
```

unless the statement is followed by evidence and remaining risks.

Preferred:

```text
I agree with the direction because X, but the weak point is Y.
```

---

### 2. Never reward the framing without testing it

If the user proposes a solution, evaluate whether the problem framing is correct.

Required check:

```text
Is this solving the right problem?
```

---

### 3. Do not over-praise progress updates

When reviewing agent progress, avoid motivational filler.

Bad:

```text
Amazing progress. This looks fantastic.
```

Good:

```text
This is useful progress if the repository boundary holds. The next risk is whether consumers still bypass the new data layer.
```

---

### 4. Do not approve cleanup without proof

For deletion, archival, migration cleanup, or old-file removal, require evidence.

Required proof:

```text
- ownership map
- migration manifest
- source hash
- replay verification
- consumer inventory
- rollback path
```

No proof, no cleanup.

---

### 5. Separate confidence from certainty

Use clear confidence levels:

```text
High confidence:
Medium confidence:
Low confidence:
Unknown:
```

Do not present assumptions as facts.

---

## Required Falsification Pass

For architecture, migration, persistence, security, or workflow changes, include:

```text
How This Could Fail:
1.
2.
3.
```

At least one failure mode must involve hidden coupling or undocumented consumers.

At least one failure mode must involve rollback or recovery.

At least one failure mode must involve testing gaps.

---

## Required Alternative Pass

For significant recommendations, include at least one alternative.

Required format:

```text
Recommended Approach:

Alternative Considered:

Why Not:
```

Do not pretend the chosen path is the only path.

---

## Approval Gate

Approval must be explicit.

Use this format:

```text
Approval Status:
- Approved
- Conditionally approved
- Not approved

Conditions:
1.
2.
3.
```

Do not bury approval in narrative prose.

---

## Migration and Refactor Special Rules

For migrations and refactors, assume:

```text
Hidden consumers exist.
Old files are still read somewhere.
Tests miss at least one workflow.
Generated artifacts may be mistaken for authoritative data.
Cleanup will happen too early unless blocked.
```

Therefore require:

```text
- producer inventory
- consumer inventory
- ownership map
- rollback path
- generated artifact policy
- Git/worktree/push verification
```

---

## Agent Self-Check Before Final Response

Before finalizing a response, the agent must ask itself:

```text
1. Did I challenge the user's premise?
2. Did I identify assumptions that matter?
3. Did I provide the strongest objections?
4. Did I identify missing evidence?
5. Did I distinguish facts from recommendations?
6. Did I avoid empty praise?
7. Did I give a clear approval status when relevant?
```

If the answer to any of these is no, revise the response.

---

## Bad Responses

```text
Looks good. I would proceed.
```

```text
You're absolutely right. This is the correct architecture.
```

```text
The agent made great progress. I don't see any issues.
```

```text
Cleanup seems safe now.
```

These are invalid because they skip adversarial review.

---

## Good Responses

```text
Recommendation: Proceed with changes.

Assumptions That Matter:
- The SQLite database is derived and rebuildable.
- JSONL remains authoritative.
- All durable intelligence writes route through event_store.py.

Strongest Objections:
1. Old JSON files may still have undocumented consumers.
2. Skill.md files may still reference dated research Markdown.
3. Cleanup may run before replay equivalence is proven.

What Is Missing:
- Consumer inventory.
- Legacy path scan.
- GitHub origin push verification.

Approval Status: Conditionally approved.
```

---

## Final Principle

The agent's job is not to agree faster.

The agent's job is to make the user's reasoning harder to break.

---

## Relationship to Graph Planning's Phase 1 Fan-Out

This rule is the **single-agent, always-on** discipline: before *this* agent agrees with or
implements anything non-trivial, it self-applies adversarial reasoning. `graph-planning-superpowers-policy.md`
§2.2-2.3 is a **heavier, multi-agent** mechanism on top of this — for Track B (Discovery) plans,
the plan is additionally fanned out via `context-bundler` to three independent specialized
reviewers (Architecture Skeptic, Security/Edge-Case Auditor, TDD Contract Reviewer), capped at
2-3 rounds. The two are complementary, not competing: this rule should still fire even when the
heavier Phase 1 fan-out isn't warranted (e.g. Track A/Factory or Track C/Micro-Fix work).


<!-- plugin: agent-agentic-os / destructive-action-guard -->
---
name: destructive-action-guard
description: Pre-verification protocol required before any file deletion, bulk cleanup, or stand-in conversion. Prevents data loss from blind cleanup passes.
metadata:
  type: feedback
---

# Destructive Action Guard

Before deleting files, bulk-removing stand-ins, or resolving broken references, run the full verification protocol below. **No exceptions.**

## Scope

This rule applies to:
- Deleting files (any file, anywhere)
- Removing stand-in / text-file pointer files
- Bulk cleanup operations (`rm`, `git rm`, script-driven deletion)
- Converting stand-ins to symlinks (targets may have moved)
- "Dead reference" cleanup from consolidation or migration

## Protocol

### Step 1 — Extract the target from each file

For a single-line text stand-in at path `P` containing relative path `T`:
```bash
cat P  # confirm single line, relative path
```

### Step 2 — Repo-wide target search

```bash
git ls-files | grep -i "<filename>"
```

**Decision:**
- Target found in repo → classify as **MISLOCATED_REFERENCE** — do not delete; propose correct path
- Target not found → proceed to Step 3

### Step 3 — Git history check

```bash
git log --all --oneline --full-history -- "**/filename"
```

**Decision:**
- File existed and was recently deleted → classify as **POSSIBLE_ACCIDENTAL_DELETION** — add to Map Debt; do not delete
- File only appears in consolidation/migration commits with no subsequent history → likely safe, classify as **DEAD_CROSS_REPO_REFERENCE**

### Step 4 — SKILL_ALIAS check (commands/ and agents/)

If content matches `../skills/<name>/SKILL.md` pattern AND the target SKILL.md exists:
- Classify as **SKILL_ALIAS** → convert to symlink, do not delete

### Step 5 — Produce audit table before any change

Output this table and wait for implicit confirmation (no new instruction = proceed, conflict = stop):

| File | Target | Exists in Repo | Classification | Action |
|------|--------|----------------|----------------|--------|

### Step 6 — Kill switch

**Stop and output the audit table only (no changes)** if any of the following:
- 5+ files classified POSSIBLE_ACCIDENTAL_DELETION
- Any ambiguity in target resolution
- Content is multi-line (not a stand-in)
- Target path resolves outside the repo

## Classification → Action Map

| Classification | Action |
|----------------|--------|
| DEAD_CROSS_REPO_REFERENCE | Delete |
| MISLOCATED_REFERENCE | Propose corrected path; do not modify |
| POSSIBLE_ACCIDENTAL_DELETION | Escalate to Map Debt; do not modify |
| SKILL_ALIAS | Convert to symlink via `symlink_manager create` |

## Why

The consolidation from 26 → 11 plugins left pre-consolidation stand-ins with cross-repo paths
that never existed post-merge. Blind deletion passes treat MISLOCATED and DEAD references
identically — but only DEAD ones are safe to remove. The distinction requires a git search.

This incident was caught during the dev-utils Opus review (2026-06-28): 19 stand-ins identified,
repo search revealed MISLOCATED and SKILL_ALIAS cases that would have been incorrectly deleted.


<!-- plugin: agent-agentic-os / github-issue-logging-policy -->
---
trigger: always_on
description: Policy and decision matrix governing when and how agent friction events, map debt, and bugs are logged as GitHub issues.
globs: ["**/*"]
---

# GitHub Issue Logging Policy (`github-issue-logging-policy`)

## 1. Purpose & Integration with `self-evolution-policy.md`

This policy governs when and how friction events, execution workarounds, tool failures, and map debt identified during agent runs are logged into GitHub Issues.

It directly extends [`self-evolution-policy.md`](file:///Users/richardfremmerlid/Projects/agent-plugins-skills/plugins/agent-agentic-os/rules/self-evolution-policy.md) by defining the decision boundary between in-session fixes, local Map Debt entries (`map-debt.md`), and formal GitHub Issue creation.

---

## 2. Friction Tier Decision Alignment Matrix

Every friction event or failure detected during agent execution must be evaluated against the friction tiers defined in `self-evolution-policy.md`:

| Friction Tier | Condition | Primary Action | GitHub Issue Logging Action | Required Labels |
|---|---|---|---|---|
| **Tier 0 (Quickfix)** | Small friction, fixable inline within allowed edit boundaries in < 5 mins. | Patch inline, update rules/docs ("The Map"). | **Optional**. Log issue only if pattern recurs across sessions. | `type:friction`, `tier:0-quickfix`, `source:agent`, `risk:low` |
| **Tier 1 (Friction / Gap)** | Workaround used, capability missing or awkward, but non-blocking. | Patch inline OR record Map Debt in `map-debt.md`. | **Fix inline or log issue**. If deferred as Map Debt, log issue payload. | `type:friction`, `tier:1-friction`, `source:agent`, `risk:low` |
| **Tier 2 (Failure / Structural)** | Script/tool broken, execution error, or recurring friction. | Collect stack trace & empirical logs. Patch code or log debt. | **Mandatory Issue Logging** (or comment on existing root-cause issue). | `type:bug` or `type:friction`, `tier:2-structural`, `source:agent` |
| **Tier 3 (Regression / Architecture)** | External change, breaking API/selector change, core design flaw. | Collect full evidence bundle & present formal Escalation Template. Synthesized by `repository-improvement-agent`. | **Mandatory Issue Logging + Architecture Review**. | `type:architecture` or `type:bug`, `tier:3-architecture` |

---

## 2.1 Hotspot Synthesis Engine (`repository-improvement-agent`)

For Tier 3 architecture friction and recurring friction clusters identified by `friction_cluster_agent`:
- The **`repository-improvement-agent`** consumes cluster hotspot reports to auto-propose and synthesize systemic refactoring PRs.
- High-density hotspots are consolidated into architectural refactoring initiatives rather than fragmented single-line patches.

---

## 3. The Root-Cause Consolidation Principle

Before creating any new GitHub issue, the agent MUST perform root-cause consolidation:

> **Root-Cause Question:** *"Is this event itself the root issue, or is it merely one instance/symptom of a broader systemic issue?"*

### Operating Rules for Consolidation:
1. **Deduplication Search**: Run `search-related-issues` (via `gh_issue_search.py`) with title keywords and location labels (`area:*` or `plugin:*`).
2. **Existing Root Cause Found**: If an existing issue covers the root cause, do NOT create a new issue. Instead, use `comment-on-existing-issue` (`gh_issue_comment.py`) to append the new empirical evidence and log context to the open issue.
3. **Symptom vs. Cause**: Never open separate issues for "Script A failed line 10" and "Script B failed line 12" if both failed due to the same missing environment variable or missing helper parameter. Open one consolidated issue capturing the root cause.

---

## 4. Human Suppression Override

Humans retain full override control over automated issue logging.

If a prompt, system instruction, configuration, or issue logging context contains:
```yaml
issue_logging: suppressed
```
or if the user explicitly instructs "do not log issues" / "suppress issue creation":
- **Issue creation and commenting MUST be completely bypassed**.
- Friction events MUST still be recorded locally in `map-debt.md` or logged in the execution context, but no calls to `gh` issue creation scripts shall be executed.

---

## 5. Staged Rollout Stages

To ensure repository stability and prevent issue spam, automated issue logging follows a 4-phase rollout protocol:

- **Phase 1: Payload Generation (Current Default)**
  - All script runs operate in dry-run mode (`execute=False`).
  - Output is formatted as structured JSON payload containing issue title, body, taxonomy labels, and validation status.
  - No live network requests are made to GitHub.
- **Phase 2: Comment Operations**
  - Live commenting (`execute=True`) enabled for adding evidence to existing human-verified issues.
  - New issue creation remains dry-run.
- **Phase 3: Issue Creation**
  - Live issue creation (`execute=True`) enabled for Tier 2 and Tier 3 friction events passing all safety gates.
- **Phase 4: Label & Status Sync**
  - Full bidirectional sync of issue state, status labels, and resolution states.

---

## 6. Mandatory Body Evidence Requirements

Every issue body (whether generated as payload or submitted live) MUST strictly include all 5 markdown sections:

1. `## Summary`: Concise explanation of what failed or caused friction.
2. `## Observed Behavior`: Exact error output, stack trace snippet, or observed unexpected behavior.
3. `## Expected Behavior`: What should have happened according to specifications or rules.
4. `## Evidence`: Command executed, reproduction steps, log locations, or environment details.
5. `## Impact`: Impact on execution, developer flow, or system capabilities (e.g., blocked pipeline, workarounds required).

*Note: The `body_validator.py` script automatically verifies the presence of these 5 sections.*

---

## 7. Task Completion Reporting Rules

When completing a task where friction occurred:
- State whether issue logging was executed or produced dry-run payload.
- Include the issue number (if submitted live) or the dry-run payload summary (if in Phase 1).
- Emit the standard `PRE-COMPLETION GATE` block per `self-evolution-policy.md`.


<!-- plugin: agent-agentic-os / self-evolution-policy -->
---
trigger: always_on
description: Universal rules for agent self-healing, selector repair, and error recovery policies.
globs: ["**/*"]
---

## Self-Evolution & Self-Healing Policy

**Full context and execution protocol -> `<project_root>/.agent/skills/self-evolution/SKILL.md` (if available)**  
**Skill/directory deletion rules -> `<project_root>/.agent/rules/skill-deletion-guard.md` (if available)**

Governs responses when any tool call, subprocess, automation step, selector query, script, workflow, or sub-agent encounters failure or friction. Agents must treat failures as evolution events governed by graph state machines (via [`agent-orchestration:graph-execution`](../plugins/agent-orchestration/skills/graph-execution/SKILL.md) and [`agent-orchestration:select-loop-strategy`](../plugins/agent-orchestration/skills/select-loop-strategy/SKILL.md)) and 3-Layer Filesystem Memory.

---

### The 3 Filesystem Memory Layers

1. **Layer 1: Runtime Context (Lean Procedural Core)**
   - Lean `SKILL.md` files (target <= 100 lines). Loaded strictly on-demand.
   - Raw execution traces and multi-page dossiers are barred during active task execution.
2. **Layer 2: Compounding Wiki Layer (Permanent Knowledge)**
   - Permanent Markdown in `wiki/` and plugin `references/`: playbooks, edge cases, negative constraints, `map-debt.md`, and `evolution-log.md`.
   - **Taxonomy & Confidence Decay:** Entries tagged (`OBSERVED`, `HYPOTHESIS`, `CONFIRMED`, `REJECTED`, `OPEN`). Decays from `CONFIRMED` to `OBSERVED` if unverified for 30 days.
   - **Asymmetric Persistence Rule:** On failure, code mutations roll back, but wiki insights, edge-case findings, and failure logs are NEVER rolled back.
3. **Layer 3: Safe Audit Layer (Append-Only Manifests)**
   - Stored in `.agent/learning/traces/cycle_manifests.jsonl`.
   - Tracked audit log capturing event sequences, hashes, exit codes, and affected paths (no raw terminal text/credentials). Audited via `verify_evolution_receipt.py`.

---

### The 4-Box Automation Gate (Pre-Evolution Qualification)

Before triggering an autonomous self-evolution cycle, all 4 criteria must be satisfied:
1. *Recurring or structural failure?* (Ignore single transient flukes; repeatable errors/gaps qualify).
2. *Objective, programmatic verifier?* (Deterministic test/script returning shell exit code executed directly by controller — never self-reported).
3. *Iteration ceiling?* (Hard limit of max 3 attempts; controller strictly enforces rollback on 3rd failure).
4. *Immutable persistence sink?* (Layer 2 `wiki/` / `map-debt.md` and Layer 3 `cycle_manifests.jsonl` retain learnings regardless of code pass/fail).

---

### Proposal Mode & Verifier Sovereignty Invariants

- **Proposal Mode:** During Stage 1 (`PLAN`), workspace files and configs are strictly read-only. No repo files modified or branches/worktrees spawned until explicit human authorization (`evolution_state.py authorize`).
- **Verifier Sovereignty:** Mutation subject cannot modify the acceptance gate. Immutable base protection set (`evaluate.py`, `eval_runner.py`, tests, holdout sets, baselines, policies) and declared verifiers cannot be targeted for mutation. Pre-execution SHA256 hashes are locked; modifications abort cycle with exit code 2. Verifier command must run directly in isolated worktree.

---

### Hard Gates & Non-Negotiables (always active)

1. **Verify Edit Boundaries First**: Check permitted edit boundaries before making autonomous repairs. Escalate immediately if repairs require edits outside allowed boundaries.
2. **Three-Attempt Maximum**: Max 3 repair attempts. If the 3rd fails, hard stop and present Escalation Template with evidence bundle.
3. **Update The Map, Not Just the Diary**: Every fix must update domain playbooks, rules, or references. Log `Status: RESOLVED` in `map-debt.md` for every Tier 0-3 friction event even when patched immediately. Dual-log to `references/evolution-log.md` and `cycle_manifests.jsonl`.
4. **Autonomy & Permission Gates**:
   - **Auto-approved**: New functions/exports, fallback routines/selectors, appending diffs for modified functions.
   - **Confirmation Gated**: Renaming or moving files.
   - **Hard Gated (Requires explicit human permission)**: Deletions of any file, function, skill, rule, manifest, eval, or reference.
   - Composes with `graph-planning-superpowers-policy.md`'s Supreme Law Human Gate.
5. **The Absorption Fallacy - always wrong**: Never conclude an asset is "redundant", "consolidated", or "superseded" and delete it autonomously. Flag overlap; never delete.
6. **One Logical Fix at a Time**: Apply one clean fix per execution pass; never bundle independent repairs.
7. **Fix Forward, Never Skip**: Fix failures at source immediately and update rules/playbooks. Never skip, work around, or add blind retries.
8. **Synchronize Templates on Rule/Strategy Changes**: Update matching templates, generator configs, and prompts when core rules or strategies change.
9. **Refine Prompt Templates on Ingesting Outputs**: Evaluate external model outputs and update prompt templates to guard against observed gaps.
10. **Synchronize Manifests & Reinstall Cleanly on Deletion**: Remove deleted assets from `symlinks.json` and reinstall via `plugin_add.py <plugin-path> -y`.
11. **Pre-Deletion Git History Check**: Run `git log --follow -- <file>` before proposing any file deletion.
12. **Hub First, Spoke Second**: New skill assets must land in plugin root (`plugins/<plugin>/scripts/`, etc.) and symlink into skill folders via `symlink_manager.py` (ADR-002/003). Run `audit_plugin_structure.py`.
13. **Asymmetric Persistence via Worktree Transfer**: On 3rd attempt failure in isolated worktree, roll back code, but export Layer 2 insights, negative constraints, and debt records to main checkout before worktree teardown.
14. **Evolution Integrity Receipts**: Autonomous evolution commits require a programmatic pre-commit receipt (`EVO-INTEGRITY-<cycle_id>-<hash>`) binding staged tree, verifier exit code, and trace manifest.

---

### Friction-Driven Self-Evolution & Tiers

A self-evolution event is required when a script/eval/tool fails, an existing capability is bypassed/manually replaced, workarounds are used, or repeatable process issues arise. Task success does not waive this.

- **Tier 0 (Friction/Workaround)**: Bypassed capability or used workaround. Patch now + update map + log `Status: RESOLVED` in `map-debt.md` if small/safe; record `Status: OPEN` in `map-debt.md` if unsafe/deferred; escalate if repeated/blocking.
- **Tier 1 (Gap)**: Missing capability (build missing piece).
- **Tier 2 (Failure)**: Existing capability broken/errors (patch minimal code, save logs).
- **Tier 3 (Regression)**: External change broke working behavior (collect evidence, patch primary + fallback).

**No Silent Bypass Rule:** Agents must use intended capabilities. Workarounds are permitted only after recording the failure as a self-evolution event.

---

### Pre-Completion Self-Evolution Gate

Before claiming a task is complete, output this block verbatim:

```
PRE-COMPLETION GATE:
  Capability check: Did I verify whether an existing repo capability was intended for this task? [YES/NO]
  1. Did any existing capability fail, get bypassed, or get manually replaced?  [YES/NO - 1 line if YES]
  2. Did I guess, assume, or get corrected on a repeatable process?              [YES/NO - 1 line if YES]
  3. Did I notice something the next agent will hit again if not fixed?          [YES/NO - 1 line if YES]

If any YES: action taken -> FIX / MAP_DEBT / ESCALATE
```

The block must be emitted as literal text. The task is not complete until every YES has a declared action.

---

### Map Debt Management

If friction cannot be fixed immediately, record it as Map Debt in `<project_root>/references/map-debt.md` (mutable queue, separate from append-only evolution log).

Each entry must include: Logged date (`YYYY-MM-DD`), Cycle/Session ID, Artifact affected, Friction observed, Why not fixed now, Recommended fix, Evidence/repro, Severity (`S`/`M`/`L`), Repeat (`YES`/`NO`), Status (`OPEN`/`RESOLVED`/`ESCALATED`).

- **Aging rule:** If `OPEN` entry is older than 3 execution cycles or 14 days, auto-escalate before starting new work.
- **Repeat = YES:** Must escalate on next encounter — no further deferral permitted.


<!-- plugin: agent-agentic-os / test-driven-development -->
---
description: >
  Enforce Test-Driven Work (TDW) for all new code development (TDD) and orchestration flows (TDO).
  No implementation code is written or orchestration executed before a success contract or failing test exists.
globs:
  - "src/**/*"
  - "tests/**/*"
  - "plugins/**/*"
  - "backend/**/*"
  - "frontend/**/*"
---

# Rule: Test-Driven Work (TDW) — Tests & Contracts Before Execution

## Why This Rule Exists

A silent logic, path resolution, or orchestration contract bug is easily introduced during development or refactoring. Verification contracts written before execution force clarity of intent, define clear success boundaries, and catch bugs before any work is committed.

**Verification contracts written after the work only verify what you remember to check.  
Verification contracts written before the work verify what you actually require.**

---

## The Iron Law

```
NO CODE DEVELOPMENT OR ORCHESTRATION EXECUTION WITHOUT A FAILING TEST OR SUCCESS CONTRACT FIRST.
```

This applies to:
- **Code Development (TDD)**: New service modules, functions, API routes, automation scripts, and bug fixes to any of these.
- **Orchestration & Workflows (TDW/TDO)**: New prompt templates, agent tool execution paths, coordinator scripts, workflow engines, and task runners.

It does NOT apply to:
- Throwaway exploration or prototyping (which must be discarded before the actual implementation begins)
- Static, non-executable configuration files and JSON/YAML data files
- Automatically generated code (migration files, boilerplate, etc.)
- Declarative task checklists or static documents (unless executable)

---

## Mandatory Pre-Execution Step

**Before writing any implementation code or executing any new orchestration flow**, establish the verification contract:

1. **For Code**: Write a failing unit or integration test first.
2. **For Orchestration**: Write a mock evaluation scenario, an assertions list, or an expected output schema validator first.
3. **Skill Tooling**: If the workspace contains a custom test-driven development skill or test runner (such as `superpowers:test-driven-development`), invoke it:
   ```
   Skill: superpowers:test-driven-development (if available)
   ```

This enforces the Red-Green-Refactor cycle and blocks the rationalization patterns ("too simple to test", "I'll do it after") that lead to broken systems. If you start the work before writing the contract, it is invalid. Delete it and start over.

---

## Test Tier Locations

Place tests in the correct tier directory designated for the project. Always locate the project's existing test structure (e.g. `tests/`, `test/`, `spec/`) first and follow its naming patterns. Typical default locations:

| What you're building | Test location | Test file naming |
|---|---|---|
| Pure business logic / services | `/tests/unit/` or `/test/` | `test_<module_name>.py` / `<ModuleName>.spec.ts` |
| API routes / Controllers | `/tests/integration/` or `/tests/api/` | `test_<route_name>_routes.py` / `<RouteName>.spec.ts` |
| UI components | `/tests/ui/` or `/tests/frontend/` | `<ComponentName>.spec.ts` |
| Script automation / CLI tools | `/tests/cli/` or `/tests/` | `test_<script_name>.py` |

---

## What a Passing Test Looks Like

### 1. Pure Function (Deterministic Unit Test)
```python
# WRITE THIS FIRST — watch it fail
def test_calculate_total_with_override():
    result = calculate_total(base_amount=100.0, tax_rate=0.05, discount=10.0)
    assert result == 95.0  # discount applied before tax

# THEN write the implementation in calculations.py
```

### 2. CLI Argument Validation (Integration Test)
```python
# WRITE THIS FIRST
def test_tool_requires_target_argument():
    result = subprocess.run(
        ["python3", "cli_tool.py", "--action", "sync"],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "--target is required" in result.stderr
```

### 3. API Route Test (Backend Server)
```javascript
// WRITE THIS FIRST
describe('POST /api/payment/preflight', () => {
  it('should block transaction when balance is insufficient', async () => {
    const res = await request(app)
      .post('/api/payment/preflight')
      .send({ accountId: '123', amount: 1000.0 });
    expect(res.status).toBe(422);
    expect(res.body.state).toBe('INSUFFICIENT_FUNDS');
  });
});
```

---

## What Counts as a Valid Failing Test

A test only satisfies the TDD requirement if — **before** any implementation is written:
1. The test executes without syntax/runtime compilation errors.
2. The test **fails** for the expected reason (e.g., assertion error, missing function).
3. The failure **proves** the feature or bugfix does not yet exist.

**Invalid examples — these do NOT satisfy TDD:**
```python
assert True  # Trivial — proves nothing
```
```python
with pytest.raises(Exception): ...  # Too broad — does not verify the specific failure cause
```
```python
mock_fn.return_value = expected_value
assert mock_fn() == expected_value  # Tests the mock, not the actual code path
```
```python
@pytest.mark.skip  # Skipped test — does not prove a failure
pass
```

**For bug fixes:** The failing test must reproduce the original bug before the fix is applied. If the test passes before you change anything, it is not a valid TDD cycle.

---

## Critical Runtime Paths — No Mocking Allowed

Certain critical paths must be tested with **real subprocess execution, real file system resolution, and actual I/O** rather than synthetic mocks:

- Script execution wrappers and bridges (e.g., spawning helper scripts or subprocesses)
- File system path resolution logic and directory setup
- File readers and parsers handling external formats
- External API client boundaries

**Do NOT mock these in the primary integration test:**
```python
# FORBIDDEN for critical integration paths:
mock_subprocess_run.return_value = ...
mock_os_path_exists.return_value = True
mock_file_read.return_value = "fake file content"
```

**Reason:** Production bugs are frequently caused by runtime path resolution and formatting anomalies. Mocking these layers hides the bug entirely.

---

## Anti-Patterns — Stop and Start Over

| Pattern | What it produces |
|---|---|
| Writing the function first, then writing a test | Tests that only verify what you built, not what was required |
| Modifying paths or imports without verifying via an import test | Silent import and runtime load failures |
| Refactoring a bridge/helper without an end-to-end integration test | Invisible path or argument mismatch bugs |
| Testing only the happy path | Missed edge cases, poor error handling, and silent crashes |
| Testing via a heavy API when a unit test is more appropriate | Slow test suites that hide where the actual failure lies |
| Testing internal private methods instead of observable behavior | Brittle tests that break during refactoring without protecting against regression |

**Observable behavior is the contract.** Test exit codes, API response structures, JSON schemas, and state transitions—not internal flags, private variables, or cache internals.

---

## Mutation Safety Rule

Any change touching core business logic or security boundaries **must** include a regression test that reproduces the pre-change behavior AND an assertion for the new expected behavior. No existing critical-path test coverage may be reduced. If you refactor a test, the new version must cover at least the same cases.

---

## Prefer Replay Fixtures Over Synthetic Mocks

When capturing external behavior for tests, prefer **recorded real output** over fabricated mocks:
- Captured stdout/stderr logs from tools
- Raw API response payloads (saved as local JSON/YAML fixtures)
- Sample static files and databases

Real captures preserve formatting quirks, character encodings, and edge cases that synthetic mocks routinely miss.

---

## Red Flags — Stop Immediately

If you think any of the following, you are rationalizing. Stop and write the test first:
- *"This is just a quick script, tests would be overkill"*
- *"I'll add tests after I see if this approach works"*
- *"I manually ran it in my terminal and it worked"*
- *"It's just a path change, nothing could break"*
- *"The test is too hard to write before I know the interface"*

The last one especially: if you don't know the interface, write the test that describes **the interface you want**. That IS the design.

---

## Test-Driven Orchestration (TDO) & Prompt-Driven Work — Success Contracts First

For coordinator scripts, workflow engines, master orchestrators, agent prompts, and tool execution flows:
- **Define the Orchestration Contract First**: Before writing any coordination logic or sequencing scripts, write an integration test or schema assertion that verifies parameter propagation between sub-components, execution orders, and error bubbling.
- **Prompt & Output Schema Assertions**: When developing LLM prompts or templates, first define the exact output structure (e.g., JSON schema, markdown headings, or exact tone boundaries). Write validation checks (e.g., matching keys, non-empty outputs, schema compliance) before finalizing the prompt instruction.
- **Safety and Boundary Invariance**: Assert that critical safety boundaries (e.g., user confirmations, budget caps, authorization gates, and data privacy limits) cannot be bypassed by any code path, flag override, or exception handler in the orchestrator.
- **Runnable Integration Scenarios**: Every orchestrated workflow or skill must have a matching runnable evaluation scenario. Mock input fixtures must trigger the flow and verify that the output payload matches expectations in an offline or sandboxed environment.

---

## Related Rules and References

- `<project_root>/.agent/rules/no-inline-python.md` (or local script extraction policy) — extraction policy for scripts
- `<project_root>/.agent/rules/coding-conventions.md` (or local style guides) — coding conventions and documentation standards
- `<project_root>/docs/architecture/` (or project design docs) — system architecture details and design specifications
- `superpowers:test-driven-development` skill (if available) — invoke BEFORE writing any implementation
- `graph-planning-superpowers-policy.md` §3.2 (Phase 2: Strict Red-Green-Refactor Enforcement) — this Iron Law
  is the concrete implementation of that phase; the two are the same requirement, not competing rules

<!-- plugin: agent-agentic-os / worktree-lifecycle-management -->
---
description: Mandatory protocol for creating, reporting on, and closing out git worktrees -- prevents the "where is it" confusion loop caused by collapsing five distinct states into one vague "done".
globs: ["**/*"]
---

# Worktree Lifecycle Management

## The Problem This Rule Solves

**2026-08-18 incident:** a session created two worktrees to execute SharePoint plugin
work, and repeatedly reported progress as "done"/"merged"/"pushed" without distinguishing
which of five genuinely different states a change was actually in. This caused the user to
ask "where are the CRUD scripts" and "is the worktree gone" many times over, each time
receiving an answer that was locally true but did not match what the user could actually
see on their own disk. Concretely:

1. A subagent-driven-development round finished, the branch was pushed, and the session
   reported "final review complete" without stating that nothing was merged yet.
2. A second worktree's work (file moves + new scripts) sat fully uncommitted for many
   turns while the session narrated architecture debates instead of stating the plain
   fact: "nothing is saved anywhere except the worktree's working directory."
3. After the user merged a PR on GitHub, the session ran `git fetch origin main:main`
   (updating the **local branch ref**) and reported the plugin as present -- without
   checking that the user's actual working directory was checked out on a **different
   branch**, so the files were invisible on disk. The user had to ask "i don't see it are
   you sure?" before this was caught.
4. Within one of the worktrees, symlinks were created with raw `ln -s` and a hand-edited
   `symlinks.json` instead of this repo's mandated `.agents/skills/symlink-manager/
   scripts/symlink_manager.py` (per `.agent/rules/symlink-cross-platform.md`), discovered
   only when the user separately flagged it.

None of these were lies -- each statement was true in isolation. The failure was treating
"local worktree state", "committed", "pushed to origin", "merged on GitHub", "local branch
ref updated", and "checked out on disk" as one undifferentiated bucket called "done".

## The Law

> **A worktree-related change is not "done" until you state which of the six states below
> it is actually in, using the exact vocabulary below.** Never use the bare words "done",
> "merged", "pushed", or "saved" without one of these qualifiers attached. When the user
> asks "where is X" or "is it gone", answer with the state name and the exact path/branch,
> not a general reassurance.

## The Six States (use this exact vocabulary)

1. **Written in the worktree** -- exists only as an uncommitted file inside the worktree's
   working directory. Invisible to git log, invisible to any other checkout, lost if the
   worktree is deleted.
2. **Committed in the worktree** -- has a commit hash, but only reachable from the
   worktree's local branch. Invisible outside this machine.
3. **Pushed to origin** -- the branch exists on GitHub. A PR *can* be opened. **Not yet
   merged.** State the exact `git push` result and the PR URL, and say explicitly "not
   merged yet" in the same sentence.
4. **Merged into `origin/main`** -- verify this yourself via `git fetch origin main &&
   git log --oneline origin/main -3` and quote the actual merge commit hash back. Never
   infer this from "I pushed it" or from the user saying "ok" -- confirm the merge commit
   exists on `origin/main` before calling anything merged.
5. **Local branch ref updated** -- `git fetch origin main:main` (or equivalent) updates
   what your local `main` branch *points to*. **This does not change any file on disk if
   the current checkout has a different branch checked out.** Always state explicitly
   which branch is currently checked out (`git branch --show-current`) in the same breath
   as reporting this.
6. **Checked out on disk** -- the actual working directory files match the target branch.
   Verify with `ls`/`git status` on the real path, not by inference. Only at this state can
   you tell the user "you can see it now" -- and even then, name the exact path.

## Non-Negotiables

1. **State the state.** Every progress report on worktree-related work names which of the
   six states applies, e.g. "pushed to origin, PR link below, not yet merged" or "merged
   into origin/main (commit `988b77a`), but your checkout is still on
   `feature/x` -- run `git checkout main` to see it."
2. **Never say "merged" without verifying `origin/main` yourself.** A user saying "I
   merged" is a trigger to `git fetch` and quote the resulting commit hash, not license to
   parrot "merged" back without checking.
3. **Never claim a file is visible "now" without checking the actual checked-out branch.**
   Updating a local branch ref is not the same as changing the working directory. If the
   current checkout is on a different branch than the one just updated, say so before the
   user has to ask why they can't see anything.
4. **State exact absolute paths for every file/plugin/worktree you reference.** "It's in
   the new plugin" is not an answer; `C:\...\plugins\sharepoint-provisioning-execution\
   scripts\spo-update-list.ps1` is.
5. **Before deleting any worktree, verify state 4 (merged into origin/main) first**, via
   `git fetch` + `git log origin/main`, not by assuming a prior push means the PR was
   merged. Only after that verification, delete via the native worktree-removal tool (or
   `git worktree remove` + `git worktree prune` if the native tool reports no active
   session), and confirm via `git worktree list` that it's gone.
6. **All symlink creation/removal inside a worktree goes through
   `.agents/skills/symlink-manager/scripts/symlink_manager.py`**, per
   `.agent/rules/symlink-cross-platform.md` -- this applies inside worktrees exactly as
   much as the main checkout. If the tool isn't present in the worktree, restore it from
   the marketplace-cached copy or the sibling monorepo before touching any symlink, never
   fall back to raw `ln -s`.
7. **When multiple worktrees exist, or worktree work spans several turns, restate the
   current state of every open worktree at the start of any status report** -- don't make
   the user re-derive it from scattered messages.

## Where This Applies

- Every `superpowers:using-git-worktrees` / `EnterWorktree` session in this repo.
- Every report to the user about progress on worktree-based work, from creation through
  final deletion.
- Applies in addition to, not instead of,
  `.agent/rules/worktree-subagent-leak-detection.md` (renamed 2026-08-18, formerly
  `worktree-subagent-isolation.md`) — that file covers a narrower, different failure mode
  (a dispatched subagent's writes leaking into the wrong checkout); this file covers the
  full lifecycle around the worktree itself. Both apply simultaneously in any
  subagent-driven-development session run inside a worktree.


<!-- plugin: agent-agentic-os / worktree-subagent-leak-detection -->
---
description: A subagent's pwd/git-branch confirmation does not guarantee its Edit/Write calls stay inside the assigned worktree — a mandatory post-task check does. Companion to worktree-lifecycle-management.md, which covers the full worktree lifecycle (create/commit/push/merge/cleanup) this file does not.
globs: ["**/*"]
---

# Worktree/Subagent Isolation (Leak Detection)

**Scope note (renamed 2026-08-18):** this file covers exactly one failure mode — a
dispatched subagent writing outside its assigned worktree. For the broader lifecycle
(creating a worktree, reporting its state honestly, pushing, verifying an actual merge,
updating local `main`, and cleaning up afterward), see
`.agent/rules/worktree-lifecycle-management.md`, added the same day after a session
repeatedly conflated "pushed" with "merged" and "local branch ref updated" with "visible
on disk". Both rules apply simultaneously whenever a `subagent-driven-development` session
runs inside a worktree.

## The Problem This Rule Solves

Dispatching an implementer or fix subagent into a `superpowers:subagent-driven-development`
worktree, with an explicit instruction to `cd` into the worktree path and confirm via
`pwd` / `git branch --show-current` before making any change, is the project's standard
isolation pattern. It has still failed **twice**:

1. **Phase 2b, Task 3** — an implementer committed a change onto the user's active
   main-checkout branch instead of its assigned worktree (documented informally in
   `start_here.md` at the time; caught by independently verifying `git log`/`readlink`
   after the subagent's report, not by the subagent noticing its own mistake).
2. **Phase 3 C2, Task 7 fix rounds (2026-07-09)** — a fix subagent left a stray,
   uncommitted, *incomplete* copy of its changes in the main checkout's
   `plugins/portfolio-advisor/scripts/daily_brief.py`, despite reporting a passing
   `pwd`/`git branch --show-current` confirmation at task start. Not caught until the
   final pre-merge `git status` check on the main checkout — logged as
   `.agent/map-debt.md`'s "subagent-driven-development implementer wrote to main
   checkout instead of worktree (2nd occurrence)" entry.

Both times the subagent's own confirmation step passed. Both times a stray write still
landed in the main checkout anyway.

## The Law

> **A `cd`-and-confirm step at task start is not evidence that every subsequent
> Edit/Write call in that session targets the confirmed directory.** `cd` only changes
> the *Bash tool's* persisted shell state — the Edit/Write/Read tools resolve on the
> exact absolute path parameter they're given, independent of any prior `cd`. Treat the
> confirmation step as a cheap first-line check, not a guarantee, and verify the
> **controller's own main checkout** after every task, not just the worktree.

## Non-Negotiables

1. **Every subagent-driven-development dispatch still gets the standard confirmation
   step.** Instruct the subagent to `cd` into the exact worktree path as its first
   action and confirm via `pwd` and `git branch --show-current` before editing anything.
   This remains necessary — it just isn't sufficient on its own.

2. **After every implementer or fix subagent reports back, the controller runs
   `git status --short` in the main checkout (not the worktree) before generating the
   review package.** This is the mandatory second check. It catches a leak within one
   task cycle — while it's still uncommitted and trivially discardable — instead of
   only surfacing at final-merge time, when it's had 5+ more tasks to compound or get
   tangled into review history.

   ```bash
   # From the main repo root, not the worktree:
   git status --short
   ```

   Any unexpected `M` entry that wasn't present before the task's dispatch is a leak.
   Diff it before touching anything (`git diff <path>`) — don't assume.

3. **A leak found this way is virtually always safe to discard, but verify first.**
   The signature of this exact failure mode is: the main checkout's stray diff is an
   *incomplete* or *superseded* subset of work that's already properly committed in the
   worktree branch (e.g. missing a later fix-round commit's changes). If the diff
   content matches that pattern, discard it via `git checkout -- <path>` in the main
   checkout before merging. If the diff contains anything that doesn't look like a
   partial duplicate of the worktree's own committed work — stop and investigate before
   discarding; it may be unrelated, real, uncommitted user work that predates the
   session (check the pre-session `git status` baseline first).

4. **Log a repeat occurrence, don't just re-fix it silently.** Per
   `.agent/rules/self-evolution-policy.md`'s Map Debt register: a `Repeat: YES` entry
   requires action on next encounter, not further deferral. A third occurrence of this
   exact failure mode should prompt investigating the harness-level root cause directly
   (e.g. checking whether a specific tool or dispatch pattern is the common thread)
   rather than only reapplying this same procedural mitigation a third time.

## Where This Applies

- Any `superpowers:subagent-driven-development` or `superpowers:executing-plans`
  session that dispatches implementer/fix subagents into an isolated worktree.
- Applies to every task in a plan, not just the first or last — the leak in the C2
  incident happened during a mid-plan fix round (Task 7's second fix dispatch), not at
  the boundaries.


<!-- plugin: agent-scaffolders / plugin-architecture-policy -->
---
description: Universal rules for plugin file duplication, symlinks, cross-plugin resource bounds, Python script organization, and relative execution paths.
globs: ["plugins/**/SKILL.md", "plugins/**/scripts/**/*.py", "plugins/**/*.md"]
---

# Plugin Architecture & Coupling Policy

**Full ADR context → `ADRs/001_` through `007_`**

## 1. Hub-and-Spoke Resource Model & Installer Dereferencing

1. **Authoring Model vs. Runtime Model**:
   ```text
   one canonical editable source
   → managed file-level symlinks in skill source folders
   → plugin installer dereferences symlinks into hard copies
   → installed skills are fully self-contained
   ```
   Symlinks are used exclusively as a repository authoring and maintenance mechanism. The plugin installer dereferences all symlinks into physical hard copies during deployment into `.agents/`.

2. **Self-Contained Installed Skills**:
   An installed skill must be fully portable and independent. It must **NEVER** depend at runtime on:
   - The source repository or source symlink
   - The source plugin directory
   - The repository root or monorepo environment
   - Another installed plugin
   - A sibling Python distribution or external runtime package

3. **Canonical Ownership**:
   Every shared resource has exactly one editable canonical source owner in the repository. Consumers receive installer-materialized hard copies, which are deployed artifacts—not editable authorities. Do not create competing canonical source copies.

---

## 2. Separation of Concerns & Loose Coupling

1. **Pluggable Independence**: If a user installs a skill via `plugin_add.py` or `uvx`, that skill MUST function completely in isolation. It cannot crash or halt because another plugin is uninstalled or missing.
2. **Agent Delegation over Code Interfaces**: If a plugin requires coordination with another plugin, it must do so via Natural Language agent instructions (e.g., *"Please invoke the `<plugin>-agent` to..."*) rather than hardcoded Python imports, hidden filesystem state manipulations, or rigid cross-plugin bindings.
3. **Cross-Plugin Wire Contracts**: Sharing schemas, references, assets, or executable contract helpers through installer-materialized hard copies is permitted. Cross-plugin Python runtime imports or cross-plugin directory symlinks are strictly forbidden.

---

## 3. Plugin-Level Resource & Python Organization

1. **One Canonical Plugin-Level `scripts/` Directory**:
   Canonical Python code shared by skills belongs at the plugin root under `plugins/<plugin>/scripts/`.
2. **Logical Subfolders Approved**:
   Related Python scripts may be logically grouped into cohesive subfolders beneath `scripts/`.
   Approved examples:
   - `scripts/contracts/` (plugin-owned contracts and validation)
   - `scripts/pandoc_fixes/` (cohesive implementation modules)
   - `scripts/validation/` (input/output validation scripts)
   - `scripts/media/` (media conversion and handling)
3. **No Redundant Package-Name Directory**:
   Do **NOT** add a redundant package-name directory inside `scripts/` (e.g. `scripts/<plugin_name>/...`). The enclosing plugin directory already establishes the domain context.
4. **No Top-Level Sibling Runtime Packages**:
   Top-level external runtime packages (e.g. `contracts/python/` or `runtime/python/`) must not exist as required external dependencies. All shared code must belong to an owning plugin.

---

## 4. Resource Placement by Purpose

Resource placement is determined strictly by **purpose**, not file extension:

| Directory | Purpose |
|---|---|
| `references/` | Schemas, contracts, and documentation the agent reads |
| `scripts/` | Executable Python, validation, transformation, and helper scripts |
| `assets/` | Templates and static resources copied, embedded, transformed, or emitted |
| `tests/fixtures/` | Plugin test evidence and test fixtures |
| `evals/fixtures/` | Skill evaluation evidence and test cases |

---

## 5. Mandatory Symlink Workflow

1. **File-Level Symlinks ONLY**:
   All shared resources within or across plugins must use **file-level symlinks ONLY**. Directory-level symlinks are strictly forbidden because installation bridges drop them or fail on cross-platform checkouts.
2. **Zero Manual `ln -s`**:
   Never invoke `ln -s` directly. All symlink creation, updates, and maintenance must go through `symlink_manager.py` and be recorded in `symlinks.json`.
3. **Mandatory Symlink Validation Sequence**:
   After creating or editing any shared script or resource:
   ```bash
   # 1. Diagnose first
   python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose

   # 2. Restore all from manifest
   python3 .agents/skills/symlink-manager/scripts/symlink_manager.py restore

   # 3. Verify zero broken symlinks or real-file imposters
   python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose
   ```

---

## 6. Strict Relative Path Execution

1. **Relative to Skill Root**: Inside `SKILL.md` workflows, path references must always be **relative to the skill root** (e.g., `../scripts/script.py` or `python3 scripts/script.py`). **Never use absolute paths or paths relative to the repository root.**
2. **Self-Contained Content**: Every file a skill references must be present inside the skill's directory — either as a hard copy or a symlink.
3. **Execution Context**:
   Installed skills execute from dynamic target locations:
   - `.agents/skills/<skill-name>/` (canonical)
   - `.claude/skills/<skill-name>/`
   Relative paths inside commands resolve from the skill root at the installed location. Verify paths against the installed structure, not the source tree.


<!-- plugin: agent-scaffolders / pre-push-audit -->
---
description: Run compliance, coding conventions, and structural audits on all modified plugins and skills, and resolve errors before pushing to GitHub.
globs:
  - "plugins/**/*"
---

# Pre-Push Audit & Verification Rule

Before pushing any changes to GitHub or concluding updates to plugins or skills, you MUST run standard compliance, coding conventions, and structural audits on all affected plugins, and resolve any flagged errors or symlink issues.

## Verification Commands

Run the following checks from the repository root:

1. **Workspace Coding Conventions Audit**:
   Ensure all file headers, Purpose, Key Input Dependencies, and function docstrings match codebase policies:
   ```bash
   python3 plugins/dev-utils/scripts/workspace_conventions_auditor.py
   ```

2. **Compliance Audit**:
   ```bash
   python plugins/agent-scaffolders/scripts/audit.py --path plugins/<plugin-name>
   ```

3. **Structural Audit**:
   Verify symlink and resource compliance:
   ```bash
   python plugins/agent-scaffolders/scripts/audit_plugin_structure.py plugins/<plugin-name>
   ```

4. **Cross-Platform Symlink Check**:
   ```bash
   python .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose
   ```

## Resolution Action

If any errors, missing references, or duplicate files are reported:
- Resolve them immediately before proposing a commit or push.
- Move duplicates to the plugin root `references/` folder and symlink them back to the individual skills using `symlink_manager.py`.


<!-- plugin: agent-scaffolders / skill-deletion-guard -->
---
description: Hard gate preventing agents from deleting skill directories based on consolidation or absorption reasoning. Covers the specific failure mode where an agent incorrectly concludes a skill's function has been absorbed by another skill.
globs: ["plugins/**/skills/**", "plugins/**/SKILL.md"]
---

# Rule: Skill Deletion Guard — No Absorption Deletions

## The Failure Mode This Rule Prevents

An agent reviews two skills, concludes that skill A's "functionality is covered by" or "has been absorbed into" skill B, then **deletes skill A's directory**. This is always wrong without explicit user instruction.

This exact incident occurred in April 2026: `os-skill-improvement` was deleted because an agent concluded its methodology was "absorbed" by `os-improvement-loop`. It was not. Recovery required `git show` from history and manual restoration.

---

## Iron Law

**Never delete a skill directory, its SKILL.md, or its evals because you believe the skill is redundant, absorbed, consolidated, or superseded.**

This is a hard gate. No amount of reasoning makes autonomous deletion acceptable.

---

## Why "Absorption" Is Always a Rationalization

Even when two skills appear to overlap in body content, they are never interchangeable because each skill has three components that are always unique:

1. **Routing identity** — the `trigger:` field and `description:` in frontmatter. Two skills that do similar things still have different routing signatures. Deleting one breaks all prompts that relied on its specific triggers.

2. **Eval contract** — `evals/evals.json` contains should_trigger test cases specific to this skill's domain boundary. These cases define where the skill starts and its neighbors end. No other skill has the same eval contract.

3. **Methodology** — the skill body may encode a distinct protocol, phase sequence, or heuristic that the "absorbing" skill does not replicate verbatim, even if the overall goal is similar.

---

## What to Do Instead of Deleting

| Situation | Correct action |
|---|---|
| Skill seems redundant with another | Flag it to the user: "I noticed overlap between X and Y — do you want to consolidate?" |
| Skill directory exists but SKILL.md is missing | Report it as a zombie directory. Do NOT delete. Ask user. |
| Skill was renamed or moved | Update references. Do NOT delete the original until user confirms. |
| Consolidation task in progress | Move files, update symlinks. The delete step requires explicit user confirmation for each directory. |

---

## Permitted vs Prohibited

| Action | Permitted without user confirmation? |
|---|---|
| Adding content to a skill | Yes |
| Editing SKILL.md | Yes |
| Adding evals | Yes |
| Renaming a skill directory | No — requires explicit confirmation |
| Deleting a skill directory | **No — hard gate, always requires explicit user instruction naming the exact skill** |
| Deleting a skill because it "looks absorbed" | **Never — not even with user permission phrased as "clean up redundant skills"** |

The last row is intentional: "clean up redundant skills" is not explicit permission to delete. The user must name the specific skill: "delete `os-skill-improvement`."

A user request to "clean up", "deduplicate", "merge", "simplify", or "consolidate" skills is **not** deletion permission. These words describe intent, not authorization. Deletion permission must name the exact path or skill slug.

---

## Zombie Directory Protocol

A zombie is a skill directory that exists but has no `SKILL.md`. Zombies are created when:
- A consolidation move was interrupted
- A skill was accidentally deleted mid-migration
- A directory was created for a skill that was never completed

**Do not delete zombie directories.** Instead:
1. Check `git log -- plugins/<plugin>/skills/<name>/` to see the last known state
2. Report to user: "Found zombie directory at `<path>` — no SKILL.md. Last commit: `<sha>`. Restore or delete?"
3. Wait for explicit instruction

---

## For Audit Tools

When auditing a plugin, check for:

```bash
# Zombie skill directories (no SKILL.md)
for dir in plugins/<plugin>/skills/*/; do
    [ -f "${dir}SKILL.md" ] || echo "ZOMBIE: $dir"
done

# Skills listed in CLAUDE.md Plugin State but missing from plugins/
# (cross-reference CLAUDE.md skill lists against actual filesystem)
```

Report zombies as **Critical** findings — they indicate either data loss or an interrupted migration.

---

## Cleanup After Self-Evolution — Also Gated

Accidental deletion often happens during "cleanup after improvement" — an agent self-evolves a
skill, then tries to simplify or tidy surrounding artifacts. This is a common deletion vector.

Any "simplification", "tidying", "removal of overlap", or "cleanup" that occurs during or after
a self-evolution run is subject to the same hard gate as any other deletion. Self-evolution does
not grant additional deletion authority. The classification of a repair as Tier 0 (friction) does
not authorize removing the thing that caused friction.


<!-- plugin: dependency-management / dependency-management -->
---
description: Universal dependency management rules for Python and agent services.
globs: ["requirements*.txt", "requirements*.in", "Dockerfile", "pyproject.toml"]
---

## 🐍 Python Dependency Rules (Summary)

**Full workflow details → `.agents/skills/dependency-management/SKILL.md` (installed locally via `plugin_installer.py`)**

### Non-Negotiables
1. **No manual `pip install`** — all changes go through `.in` → `pip-compile` → `.txt`.
2. **Commit `.in` + `.txt` together** — the `.in` is intent, the `.txt` is the lockfile.
3. **Service sovereignty** — every agent service owns its own `requirements.txt`.
4. **Tiered hierarchy** — Core (`requirements-core.in`) → Service-specific → Dev-only.
5. **Declarative Dockerfiles** — only `COPY requirements.txt` + `RUN pip install -r`. No ad-hoc installs.
6. **Hub-and-Spoke DRY** (ADR-002) — canonical scripts at plugin root; file-level symlinks in `skills/` subfolders (no duplication in monorepo source).
7. **Symlink Resolution** (ADR-003) — installer resolves symlinks to physical copies in `.agents/`; installed skills must be fully self-contained.
8. **Agent Orchestration** (ADR-001) — cross-plugin coordination uses skill delegation via the prompt loop, not direct script execution.


<!-- plugin: dev-utils / coding-conventions -->
---
trigger: always_on
description: Universal coding conventions for Python, TypeScript, and C#.
globs: ["*.py", "*.ts", "*.js", "*.cs"]
---

## 🎯 PURPOSE: Enable Agents to Understand Code at a Glance

Every script must document **what it does, what it needs, and how to use it** in the first 20 lines.

**Why:** In fresh agent sessions, agents cannot afford to spend 5-10 minutes reading implementations or running exploratory commands. By reading a 20-line header, agents must be able to:
- Understand the script's purpose in 30 seconds
- Know what files/APIs/dependencies it requires
- See usage examples without trial-and-error
- Identify key functions without code diving

This transforms agent onboarding from minutes to seconds.

---

## 📝 Coding Conventions (Summary)

**Full standards → `.agents/skills/coding-conventions-agent/SKILL.md` (installed locally via `bridge_installer.py`)**

### Non-Negotiables
1. **Dual-layer docs** — external comment above + internal docstring inside every non-trivial function/class.
2. **File headers** — every source file starts with a purpose header (Python, TS/JS, C#).
   - **Crucial**: The header must explicitly list **Key Input Dependencies** (e.g. private JSON databases like `portfolio.json` or `cash_flows.json`).
   - **Index & Preservation Directive**: File headers must contain a complete index list of all functions, methods, and procedures present in the file. Never remove or reduce existing utility documentation (like usage examples, DOM structures, or technical flags lists) during updates—always preserve and enrich.
   - **Purpose**: This enables clean, token-efficient discovery in new agent sessions. Incoming agents can scan the top of a file to instantly map its capabilities and required state files without reading the full implementation.
3. **Type hints** — all Python function signatures use type annotations.
4. **Naming** — `snake_case` (Python), `camelCase` (JS/TS), `PascalCase` (C# public).
5. **Refactor threshold** — 50+ lines or 3+ nesting levels → extract helpers.
6. **Manifest schema** — use simple `{title, description, files}` format (ADR 097).

### 🔍 Automated Compliance Checks
To audit workspace source code compliance against these rules, run the developer conventions auditor script:
```bash
python3 .agents/skills/coding-conventions-agent/scripts/workspace_conventions_auditor.py
```
This utility outputs a detailed audit breakdown under `temp/workspace_conventions_report.md`.

<!-- plugin: dev-utils / git-operations -->
---
description: Rules for safe git operations — what requires explicit approval, what is forbidden, and how to handle push & lockfile conflicts.
globs: ["**/*"]
---

# Git Operations Policy

## Hard Rules (never violate)

### 1. No git stash without explicit instruction
Never run `git stash`, `git stash pop`, or `git stash apply` unless the user explicitly says to.
**Reason:** Stashing risks applying stale edits onto new branches and causing silent regressions.

### 2. Lockfile Conflict Protocol (`skills-lock.json`)
`skills-lock.json` contains machine-generated timestamps. When a branch or PR has conflicts in `skills-lock.json`:
- **NEVER** edit conflict markers by hand (`<<<<<<<`, `=======`, `>>>>>>>`).
- **NEVER** leave a PR in conflict state after pushing.
- **ALWAYS** resolve immediately via:
  ```bash
  git checkout --ours skills-lock.json
  python3 plugins/plugin-manager/scripts/plugin_add.py plugins/ -y
  git add skills-lock.json
  ```

### 3. Pre-Push Freshness Verification
Before pushing a feature branch for PR merge:
1. Verify the branch is up to date with `origin/main`:
   ```bash
   git fetch origin main
   git merge origin/main
   ```
2. If `skills-lock.json` conflicts, apply Rule 2 immediately before pushing.
3. Verify working directory is clean (`git status`) and push with `-u origin <branch>`.

### 4. When a push is rejected
If `git push` is rejected because the remote is ahead:
1. Run `git fetch origin` and `git merge origin/<branch>` or `git pull --rebase` (no stash).
2. If conflicts occur in `skills-lock.json`, resolve via Rule 2.
3. Push once clean. Never force-push around a rejected push.

### 5. No force push to main/master
Never `git push --force` to main or master under any circumstances.

### 6. No --no-verify
Never skip hooks with `--no-verify` unless the user explicitly requests it.

### 7. Commit only what is asked & required
- Commit only files within the task scope.
- Auto-modified files like `.DS_Store` or `uv.lock` should not be committed unless relevant.
- When `skills-lock.json` or `symlinks.json` changes as a direct result of adding/modifying skills or plugins, commit them together with the changes.

## Approval Required

- Any `git reset` (hard or soft)
- Any `git rebase -i`
- Any branch deletion (`git branch -d` / `-D`)
- Any `git push --force-with-lease` or force variant
- Any `git clean`

## Safe Without Asking

- `git status`, `git diff`, `git log` — read-only, always safe
- `git add <specific files>` + `git commit` when the user asked to commit
- `git push` (non-force) when the user asked to push
- Fetching and merging `origin/main` into the current working feature branch to keep PRs conflict-free
- `git checkout -b <branch>` when the user asks for a new branch



<!-- plugin: dev-utils / graph-planning-superpowers-policy -->
---
trigger: always_on
description: Graph Planning, Superpowers, and Execution Discipline Policy - native Plan Mode sandboxing, context-bundler adversarial convergence, worktree-isolated TDD, and multi-stage verification.
globs: ["**/*"]
---

# Graph Planning, Superpowers, and Execution Discipline Policy

> **THE SUPREME LAW: HUMAN GATE**
> You MUST NOT execute ANY state-changing operation (code writes, commits, external commands) without EXPLICIT user approval.
> "Sounds good" or "Looks right" is NOT approval.
> Only **"Proceed"**, **"Go"**, or **"Execute"** is approval.
> **VIOLATION = SYSTEM FAILURE**

---

## 1. Overview

All significant work MUST follow the three-phase lifecycle below. This replaces the linear
Specify/Plan/Tasks waterfall previously used here.
Before committing to an execution topology, consult [`agent-orchestration:select-loop-strategy`](../../agent-orchestration/skills/select-loop-strategy/SKILL.md)
to determine whether the task requires solo research, pair execution, an adversarial critique loop, or a deterministic state graph.

---

## 2. Phase 1: Native Plan Mode & Adversarial Review

### 2.1. Native Read-Only Plan Sandboxing
- Before generating code, you MUST enter host-native Plan Mode (Claude Code `/plan` / `Shift+Tab` or Copilot `@plan`).
- While in Plan Mode, filesystem mutations and write operations are **strictly prohibited**. Use only read-only search and AST analysis tools.
- The output must be written to an immutable spec/plan contract (e.g., `docs/plans/<feature-id>.md` or `~/.claude/plans/`).

### 2.2. Isolated Context Packaging via `context-bundler`
- Do NOT dump bloated whole-repo context or messy conversation history into reviewer prompts.
- Use `context-bundler` to package discrete codebase slices, interface contracts, and targeted role prompts for specialized adversarial reviewers.

### 2.3. Multi-Perspective Fan-Out & Convergence Cap
- Dispatch plan drafts to parallel reviewer personas coordinated via [`agent-orchestration:red-team-review`](../../agent-orchestration/skills/red-team-review/SKILL.md):
  - **Architecture Skeptic:** Interfaces, dependency cycles, missing contracts.
  - **Security / Edge-Case Auditor:** Injection, auth, failure paths, race conditions.
  - **TDD Contract Reviewer:** Deterministic test fixtures and assertion validity.
- **Convergence Rule:** Critique loops MUST cap at 2-3 rounds. If consensus is not reached, escalate the exact diff disagreement to the user for tie-breaking.

---

## 3. Phase 2: Worktree Isolation & Superpowers TDD

### 3.1. Worktree State Isolation & Graph Execution
- Execute implementation subagents strictly within dedicated `git worktree` branches (`../worktree-<feature-name>`).
- Subagents must not execute in shared or dirty working trees.
- High-assurance, multi-step tasks must execute as a deterministic Directed Acyclic Graph (DAG) state machine via [`agent-orchestration:graph-execution`](../../agent-orchestration/skills/graph-execution/SKILL.md), enforcing Proposal Mode, Verifier Sovereignty, and Asymmetric Persistence.
- Delegation between director and worker agents follows the [`agent-orchestration:dual-loop`](../../agent-orchestration/skills/dual-loop/SKILL.md) pattern (or [`agent-orchestration:co-pilot-loop`](../../agent-orchestration/skills/co-pilot-loop/SKILL.md) for fast-tier models).

### 3.2. Strict Red-Green-Refactor Enforcement
- Invoke `superpowers/test-driven-development` protocols:
  1. **Red:** Author concrete unit/integration test cases against the contract. Verify they FAIL.
  2. **Green:** Implement minimum functional code to make tests pass.
  3. **Refactor:** Clean up code while maintaining green test status.

---

## 4. Phase 3: Multi-Stage Verification

Verification is defense-in-depth and cannot rely solely on self-reported agent status:
1. **Deterministic Local Pass:** 100% green pass on test runners, static linters, and type checkers (`evaluate.py` / `npm test` / `cargo test`).
2. **Structural Workspace Verification:** Clean git worktree merge and branch teardown via host tools.
3. **Out-of-Band Context Alignment:** Use `context-bundler` to bundle modified files and git diffs for external alignment verification (e.g. Gemini UI inspection) prior to production deployment.
4. **Autonomous Receipt Emission:** The agent must proactively emit the verbatim `PRE-COMPLETION GATE` receipt and log resolved/open map debt to disk at the conclusion of every verification cycle without waiting for user prompts.

---

## 5. File & Character Standards
- **Paths:** Always provide unambiguous absolute or repo-relative paths (`specs/feature/plan.md`).
- **Encoding:** Strict UTF-8 only. No smart quotes (`"`, `'`), no em/en dashes (`—`, `–`), no non-ASCII glyphs. Use standard hyphens (`-`) and ASCII arrows (`->`).

---

## 6. Git & Agent Directory Discipline

- **NEVER** commit directly to `main`. **ALWAYS** use a feature branch.
- **NEVER** run `git push` without explicit, fresh approval.
- **NEVER** "auto-fix" via git operations.
- **HALT** immediately on any user "Stop/Wait" command.
- Write descriptive commit messages in the imperative mood.
- **NEVER** commit agent directories (`.agents/`, `.claude/`, `.gemini/`, `.codex/`) to version control. They contain session data and secrets.
- Any planning artifacts created inside an isolated git worktree will be deleted when the worktree is removed. Sync these to the main checkout directory before merging.

---

## 7. Context Management

- **Build context, then maintain it.** Do not redundantly re-read unchanged artifacts in a single session.
- **Never** use blind full-repo sweeps (`grep`, `find`, or `ls -R`); use targeted native `rg` / exact scoped file matches or structured directories. Zero background daemons required.

---
**Renamed**: 2026-08-27 (from `spec-driven-development-policy.md` — dropped "Spec-Kit" branding; this repo does not use the spec-kitty tool)
**Refactored**: 2026-08-27 — replaced with the three-phase Graph Planning, Superpowers, and Execution Discipline lifecycle (native Plan Mode sandboxing, context-bundler adversarial convergence capped at 2-3 rounds, worktree-isolated TDD, multi-stage verification)
**Ratified**: 2026-05-22 | **Replaces**: `constitution.md`, `AGENTS.md`, legacy `spec_driven_development_policy.md`


<!-- plugin: dev-utils / symlink-cross-platform -->
---
trigger: always_on
description: Enforce symlink_manager.py for all symlink creation, repair, and auditing.
globs: ["**/*"]
---

# Rule: Always Use symlink_manager.py for Symlink Operations

## Mandatory Protocol

**NEVER create symlinks with `ln -s` directly.**
**NEVER create real file copies where a symlink should exist.**

All symlink creation, repair, and auditing in this project MUST go through:

```
.agents/skills/symlink-manager/scripts/symlink_manager.py
```

---

## Required Workflow — Every Time You Touch Symlinks

### Step 1: Diagnose first
```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose
```
Read the output. Identify every `? regular file (not a link)` and `✗ broken symlink` before touching anything.

### Step 2: Remove real-file imposters
If a file that should be a symlink is a real file, delete it first:
```bash
rm -f path/to/real-file-that-should-be-symlink
```

### Step 3: Add new links to symlinks.json (the manifest)
```python
# Add entries via script, NOT by hand-editing symlinks.json:
# { "src": "canonical/source.py", "dst": "skill/scripts/source.py", "strategy": "symlink", "description": "..." }
```
The `src` must be the canonical master copy (in plugin root scripts/, references/, assets/).
The `dst` is the skill subfolder location.

### Step 4: Restore all from manifest
```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py restore
```

### Step 5: Verify
```bash
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose
```
Zero `? regular file` or `✗ broken symlink` entries must remain before committing.

---

## Canonical Source Locations (Ecosystem Standard)

| File | Canonical Master | All skills get a symlink |
|------|-----------------|--------------------------|
| `*.py` scripts | `plugins/<plugin-name>/scripts/` | → `skills/<skill>/scripts/` |
| references | `plugins/<plugin-name>/references/` | → `skills/<skill>/references/` |
| templates/assets | `plugins/<plugin-name>/assets/` | → `skills/<skill>/assets/` |

---

## ❌ Prohibited Actions

- ❌ `ln -s <src> <dst>` directly in shell (bypasses manifest, links won't be recreated on fresh checkout)
- ❌ Copying file contents into a skill subfolder instead of symlinking
- ❌ Editing symlinks.json by hand without running `restore` afterwards
- ❌ Committing without running `diagnose` to confirm zero broken/real-file issues

---

## Skill Reference

Read the full skill before any symlink work:
`.agents/skills/symlink-manager/SKILL.md`

