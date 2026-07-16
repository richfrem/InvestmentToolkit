# AGENTS.md — InvestmentToolkit Agentic Entry Point

Welcome, Agent. You are operating within the **InvestmentToolkit**, a professional-grade "Agentic OS" workstation for sophisticated retail investors. This document serves as your operational manual and routing guide.

## 🎯 Setup Entry Points (Start Here)

Two dedicated onboarding agents handle setup. Always route new users here first.

### Master Coordinator
**Trigger**: `"Help me set up the toolkit"`  
**Agent**: `toolkit-onboarding-guide` (`plugins/toolkit-manager`) — orients new users, checks Node.js/Python dependencies, runs the startup script, then routes to the right specialist below.

### TradingView Setup (Primary — all users)
**Trigger**: `"Set up TradingView for me"` or `"Help me connect TradingView"`  
**Agent**: `tradingview-onboarding` (`plugins/toolkit-manager`) — dedicated 8-phase guide covering:
1. TradingView Desktop install check
2. Subscription tier verification (Premium recommended)
3. Broker panel connection inside TradingView
4. CDP health check and broker data verification
5. First `/tv-portfolio-sync`

**Programmatic Check**: Run `/setup-tradingview` to trigger the `tv_setup` skill, which programmatically checks port `9222` health and `tradingview-cdp` node module dependencies.

### Questrade API (Optional — fallback only)
**Trigger**: `/setup-questrade`
**Skill**: `questrade-token-setup` — interactive wizard for AES-256-GCM encrypted token setup. Use only if TradingView is unavailable.

## 🛠️ Available Agent Capabilities

This workstation is built on a modular plugin architecture. You have access to the following specialized skills, organized by plugin:

### 1. Portfolio Advisor (`plugins/portfolio-advisor`)
*Adversarial thesis challenger and portfolio manager.*
- **`/daily`**: **The one daily command.** Interactive loop agent — portfolio freshness check → morning brief (macro regime, TA sweep, conviction scores, earnings) → ranked triage cards (one per holding, in urgency order) → trade execution → evolution log. Replaces the manual 10-step checklist. Agent: `plugins/portfolio-advisor/agents/daily-loop-agent.md`.
- `/review-portfolio`: Audit drift, pillar conviction, and thesis health.
- `/strategic-review`: Adversarial challenge of investment pillars. Proposes weight changes based on real-time drift.
- `/rebalance`: Valuation-gated trade recommendations (never buys SELL-rated holdings).
- `/calibrate-targets`: Interactive target-weight calibration session.
- `/update-portfolio-targets`: Apply formula/weight changes.
- `/update-price-levels {TICKER}`: Derive and write structured buy/sell tiers from DCF projections. Auto-runs after `/evaluate-stock`. Script: `plugins/portfolio-advisor/scripts/update_price_levels.py`. ADR: `docs/architecture/ADR-price-levels-schema.md`.
- `/x-news-sweep`: Daily news processing via Grok/X.com. Called by `/daily` agent on news days.
- `/bundle-thesis-review`: Package thesis/DCF for external LLMs.
- `/13f-tracker` & `/13f-analyze`: Poll and analyze SEC 13F EDGAR filings.
- `/run-advisor`: Full 5-phase orchestrator (Ingest → Calibrate → Review → Rebalance → Execution) — use post-catalyst (after 13F or news sweep), not daily. Agent: `plugins/portfolio-advisor/agents/portfolio-advisor-orchestrator.md`.
- `/weekly-review`: Weekend review cycle — range-based drift audit, weekly Grok sweep prompt generation, and TradingView technical checks. Agent: `plugins/portfolio-advisor/agents/weekly-review-agent.md`.
- `/set-thesis-breakers`: Interactive session defining 2-3 structured, measurable thesis-breaker conditions per holding (auto-checked metrics like RSI/DCF gap/trend state, or manual with a review-cadence staleness flag). A `TRIGGERED` breaker surfaces at the top of `/daily`'s triage.
- `/adversarial-review`: Package a projection or rebalance plan into an external-LLM adversarial-review prompt bundle.
- `/pitch-thesis`: Propose a new investment thesis or challenge an existing one. Triggers the Investment Committee agent to intake and validate it. Agent: `plugins/portfolio-advisor/agents/thesis-review-agent.md`.
- `/norberts-gambit`: Guide for converting cash between CAD and USD via the DLR.TO/DLR.U ETF pair.
- `/ytd-return`: Calculate Simple and Time-Weighted YTD returns, adjusted for cash flows.

**Specialist sub-agents** (not directly triggered by command — dispatched by the skills above):
- **`risk-officer-agent`**: Enforces the rebalancer's risk-gate and thesis-breaker warnings as real vetoes (25% MRC / 60% cluster-variance caps, `TRIGGERED` thesis breakers), one order at a time, with override logging. Dispatched by `/rebalance` (real enforcement) and `/daily` (read-only banner). `plugins/portfolio-advisor/agents/risk-officer-agent.md`.
- **`red-team-agent`**: Adversarial reviewer producing ≥3 falsifiable objections to a completed valuation or rebalance plan, plus a "what would change my mind" list. Never proposes trades; output is conversational only. Dispatched mandatorily by `/evaluate-stock` and `/rebalance`. `plugins/portfolio-advisor/agents/red-team-agent.md`.
- **`data-quality-agent`**: Decides degrade-gracefully vs. halt when a valuation-committee script (WACC, comps, peer bench, technicals) flags staleness or a cross-source data conflict. Read-only; dispatched by `/evaluate-stock` only when a flag fires. `plugins/portfolio-advisor/agents/data-quality-agent.md`.
- `/single-stock-advisor {TICKER}`: Interactive sub-agent guiding a full single-equity workflow — thesis writing/challenge, valuation math verification, technical entry charting, target sizing, order drafting. Agent: `plugins/portfolio-advisor/agents/single-stock-advisor.md`.

### 2. Stock Valuation Analyst (`plugins/stock-valuation`)
*Autonomous buy-side analyst.*
- `/evaluate-stock {TICKER}`: Deep-dive Bear/Base/Bull DCF modeling and research report generation.
- `/research-stock {TICKER}`: Qualitative catalyst and risk sweep.
- **`forward-valuation-challenge`** (auto-activating, no direct trigger): Challenges valuations overly anchored on historical financials for AI infrastructure / data center names, forcing forward-looking demand signals and secular growth drivers into bear/base/bull scenario construction. Activates automatically whenever the analyzed company falls in that sector.
- **`valuation-math-validation`** (auto-activating, no direct trigger): Deterministic math validation gate that MUST run on every valuation, catching unit mismatches, percent/decimal errors, double-discounting, and share-count explosions before results are displayed or saved.

### 3. ETF Analysis (`plugins/etf-analysis`)
*Thematic, closed-end, and cash fund analyst.*
- `/analyze-etf {TICKER}`: Holdings alignment against investment thesis, expense ratio review, BUY/HOLD/AVOID action. Co-writes to `data/projections/`.

### 4. TradingView Integration (`plugins/tradingview`)
*Execution, live pricing, chart control, and Pine Script layer via CDP.*
- `/setup-tradingview`: Programmatic diagnostics check for `tradingview-cdp` installation and Port 9222 health.
- `/tv-portfolio-sync`: Syncs all accounts (TFSA + RRSP + Cash) from TV broker panel via CDP.
- `/tv-watchlist-sync`: Syncs and aligns TradingView watchlists (`TA-Full Watchlist`, `TA-Current Holdings`, `TA-BOATS-Watchlist`) with `watchlist.json` / projections and `portfolio.json`. Invokes the `tv_manage_watchlists` skill. Direct script: `plugins/tradingview/scripts/watchlist_manager.py`.
- `/place-order`: Live order execution via CDP DOM automation. 3-step HITL confirmation.
- `/modify-order` & `/cancel-order`: Order management via CDP.
- `/get-orders`: Fetch current working/inactive orders.
- `/tv-alert-sync`: Sync DCF targets to TradingView price alerts.
- `/tv-alert-list`: List/fetch currently active TradingView price alerts.
- `/tv-price-refresh`: Pulls real-time prices.
- `/tv-snapshot` & `/tv-ta`: Capture technical charts and perform basic technical analysis.
- `ta-red-team` (internal, no direct trigger): Adversarial red-team pass on a completed TA thesis — challenges price levels against cited evidence. Dispatched internally by `technical-analysis-expert`, never invoked directly by the user.
- `/pine-inject {description}`: Generate a custom Pine Script v6 indicator from a description and inject it via CDP. Preflight validates version/indicator declarations.
- `/author-pine-script {description}`: **Full Pine Script v6 authoring workflow.** Phase 0 source research (reads community indicator source via `pine_source_reader.py` directly from TV Indicators dialog), Phase 2.5 lint gate (`pine_linter.py`), inject, and save to TV library. Studies top-10 indicators before writing.
- `/tv-ta-deep {TICKER} [TIMEFRAME]`: **Deep TA with custom view construction.** Builds the optimal indicator set for the analysis (adds built-ins, injects custom bundle, or authors Pine Script), multi-timeframe macro context check, synthesizes entry/accumulate/trim/exit levels, adversarial red-team review. Use `ta-guide` agent for an interactive guided session.
- **`ta-guide` agent**: Interactive, conversational TA tutor — walks through reading live chart indicators step by step in plain language, then dispatches the full `/tv-ta-deep` pipeline and explains the red-team verdict. `plugins/tradingview/agents/ta-guide.md`.
- `/ta-daily-sweep`: **Batch TA scan of all portfolio holdings in one CDP session** via `ta_sweep_batch.py`. Reads Data Window (RSI, Vol Bias %, ADX, Squeeze) per ticker. Flags momentum extremes, distribution signals, squeeze setups, DCF proximity. Outputs ranked REDUCE / MONITOR / ACCUMULATE / HOLD report. Auto-saves to `investment_screener/backend/data/ta-sweep-results.json`. Complements `/x-news-sweep`. Note: ADX values outside 0–100 are auto-nulled (`validate_adx()` inside `enrich_results()` — the nulled copy is what gets persisted); volume ratios use K/M-scaled parsing to prevent false VOLUME_SPIKE flags; `pctToFV` is price-denominated (`(FV − price) / price`) — values below −100% indicate the old FV-denominated bug.

**Dedicated skills wrapping the raw CDP commands below** (each also invokable via its own slash command, not just the low-level CLI):
- `/add-indicator {NAME}` — `tv-add-indicator` skill
- `/change-symbol {TICKER}` — `tv-change-symbol` skill
- `/change-chart-type {TYPE}` — `tv-change-type` skill
- `/tv-chart-setup {SYMBOL} {TIMEFRAME}` — `tv-chart-setup` skill
- `/save-indicator {NAME}` — `tv-save-indicator` skill

**CDP chart control (low-level, used by skills):**
```bash
node tradingview-cdp/cli.js chart addIndicator "Name"   # add built-in or personal library script
node tradingview-cdp/cli.js chart removeIndicator "Name"
node tradingview-cdp/cli.js chart timeframe 1D | W | 240
node tradingview-cdp/cli.js chart symbol NVDA
node tradingview-cdp/cli.js chart openDataWindow
node tradingview-cdp/cli.js chart read                  # returns JSON of all indicator values
node tradingview-cdp/cli.js pine inject --file <path>   # inject Pine Script from file
node tradingview-cdp/cli.js pine save "Name"            # save to TV personal library
```

**Custom indicator library**: `plugins/tradingview/assets/pinescript-indicators/`
- `ai-ta-levels.pine` — Multi-EMA (21/50/200) + volume bias %, saved in TV library as "AI TA Levels"
- `community-reference/pa-toolkit-lite-ualgo.pine` — PA Toolkit source (CC BY-NC-SA 4.0), reference for order blocks + liquidity sweep patterns

**Critical CDP rules:**
- Close Pine Editor before calling `addIndicator` — Pine Editor panel blocks the Indicators dialog search input
- `addIndicator` uses `Input.dispatchMouseEvent` at `getBoundingClientRect()` center (not `.click()`, which opens timezone dropdown). Result selector: `div[class*="container-WeNdU0sq"]`
- Source code accessible from Indicators dialog full list for any open-source script. PA Toolkit IS open source (CC BY-NC-SA 4.0) — source in community-reference folder

### 5. Toolkit Manager (`plugins/toolkit-manager`)
*Orchestrator.*
- `/start-screener`: Launch full suite (frontend + backend) via `run_investment_toolkit.py`. Also triggered by natural language ("run the screener", "start the app").
- `/setup-questrade`: Handle OAuth2 exchange for backup API sync. Also triggered by natural language ("set up questrade", "re-seed token").

## 📜 Agent Operating Guidelines

As an AI agent operating in this repository, you **MUST** adhere to the following directives from `.agent/rules/`:

### 1. Mandatory Rules & Conventions
- **TDD (`test-driven-development.md`)**: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST. Mocking is strictly prohibited on critical runtime paths.
- **No Inline Python (`no-inline-python.md`)**: Never perform financial/analytical calculations inline. Always use or create versioned `.py` scripts.
- **Coding Conventions (`coding-conventions.md`)**: Dual-layer docs, type hints, proper casing, and strict refactoring thresholds.
- **Dependency Management (`dependency-management.md`)**: No manual `pip install`. Edit `.in` files and use `pip-compile`.
- **Plugin Architecture (`plugin-architecture.md` & `symlink-cross-platform.md`)**: File-level symlinks ONLY via `symlink_manager.py`. No cross-plugin script execution.
- **Self-Evolution (`self-evolution-policy.md`)**: Classify failures, max 3 repair attempts, update playbooks. Deletions are strictly forbidden.

### 2. Agent Calculation Policy
- Always use or create versioned `.py` scripts in `investment_screener/backend/py_services/`.
- Fix bugs once in the script; every future run benefits automatically.

### 3. Exploration Workflow
- When building new features, prototyping, or exploring broad capabilities, use the **Exploration Workflow**.
- 4-phase loop: Discovery Planning → Visual Blueprinting → Prototyping → Handoff & Specs.
- Managed by the `exploration-workflow` skill and `exploration/exploration-dashboard.md` state file.

### 4. State Awareness & The Bridge Pattern
- Live brokerage state is maintained in `backend/data/*.ts` singletons.
- Portfolio syncing uses a source waterfall: TradingView CDP → Questrade API Fallback → Cached data.
- All Python-based analytical logic MUST be invoked via the `bridge.ts` service.
- **Initialize missing private data**: If any local gitignored data files (e.g., `portfolio.json`, `cash_flows.json`) are missing from `investment_screener/backend/data/`, initialize them by copying their corresponding `.example` files.

### 5. Security & Objectivity
- **Security**: Never prompt users to paste raw Questrade tokens or API keys. Always use built-in wizards that handle secure encryption.
- **Objectivity**: When running valuations, adhere to the **Adversarial Objectivity Constraint** to prevent sycophancy. Challenge the user's assumptions and ensure reports remain fiercely objective.

### 6. TradingView CDP — Critical Node.js Rules
- **Shared runtime at `tradingview-cdp/`**: The Node.js CDP engine lives at `tradingview-cdp/` (repo root), NOT inside `plugins/`. Installed once via `cd tradingview-cdp && npm ci`. Always import via `from tv_client import tv_call` — never hardcode the path. ADR-024.
- **process.exit() required**: Every Node.js CDP snippet in `tradingview-cdp/` MUST end with `.then(() => process.exit(0)).catch(() => process.exit(1))`. Without it, the CDP WebSocket holds the event loop open and `subprocess.run()` from Python never returns.
- **React fiber traversal for Monaco**: Do not rely solely on CSS selectors for Pine Editor / Monaco. Scan DOM nodes for the `__reactFiber` key prefix and walk the fiber tree. Reference: [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp).
- **Pine inject uses `--content`, not `--file`**: `tv_pine_inject.py` reads the file in Python (correct cwd), then passes content via `--content` to Node. Node's cwd is `tradingview-cdp/` — passing a relative path would inject the path string as Pine Script.
- **Pine Editor must be closed before `addIndicator`**: When the Pine Editor panel is open, `chart addIndicator` fails — the Indicators dialog search input is not reachable. Close the Pine Editor first.
- **`addIndicator` uses mouse events, not `.click()`**: Must use `Input.dispatchMouseEvent` at the button's `getBoundingClientRect()` center. `.click()` opens the timezone dropdown instead. Result rows: `div[class*="container-WeNdU0sq"]`.
- **Source code from Indicators dialog**: Open the Indicators toolbar button → search → source icon on result row (open-source scripts only). Also via chart legend More → `"Source code…"` (unicode `…`). PA Toolkit IS open source (CC BY-NC-SA 4.0) — source at `plugins/tradingview/assets/pinescript-indicators/community-reference/`.
- **Temp files**: Use `InvestmentToolkit/temp/` subfolder (gitignored), not `/tmp/` root. Task #0003 tracks legacy migration.
- **PSU.U.TO = PSU-U.TO**: Same fund (Purpose US Cash Fund). Broker panel returns `PSU.U.TO` (dot); canonical thesis uses `PSU-U.TO` (hyphen). Alias hardcoded in `fetch_broker_data.py`. Never create a duplicate thesis entry for `PSU.U.TO`.
- **targetEntryPrice field**: `target-portfolio.json` holdings have an optional `targetEntryPrice` float — the GTC limit order price for accumulating. Set via `update_targets.py --set-entry TICKER=PRICE --write`. The Grok prompt surfaces existing entry prices and asks for suggestions on ACCUMULATE rows.
- **Limit orders are Day by default**: CDP order automation does not yet set GTC. After placing a long-dated limit via `/place-order`, manually change it to "Good till cancelled" in TradingView broker panel → Orders tab.
- **Portfolio sync fallback**: After fills, tries (1) Express API, (2) `fetch_broker_data.py --snapshot` (direct CDP — updates cash + holdings without the backend running), (3) Questrade REST.
- **Fractional shares**: `place_order.py --shares` accepts float (e.g. `0.2`). TradingView/Questrade supports fractional orders.

---

## 🙏 Acknowledgements & Prior Art

### TradingView CDP Community
- **[tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)** — Most complete open-source TradingView CDP library. React fiber traversal technique for Monaco editor. No live broker execution.
- **[atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)** — TradingView screener/scanner via REST API. No CDP, no live orders.

**Our differentiator:** InvestmentToolkit is a **live broker execution layer** — places, modifies, and cancels real orders through TradingView's Questrade broker panel via CDP, with HITL confirmation, safety gates, multi-account support, and portfolio sync.

### AI Agent Infrastructure
- **[orba/superpowers](https://github.com/orba/superpowers)** — TDD Iron Law, brainstorming, and sub-agent driven development skills used throughout this project.
- **[richfrem/agent-plugins-skills](https://github.com/richfrem/agent-plugins-skills)** — Exploration Workflow (4-phase) and all project-local AI agent plugins and skills.

---
*For human-readable documentation, please direct the user to [README.md](README.md).*
*For a comprehensive system map and diagrams, see the [Architecture Overview](docs/architecture/README.md).*
