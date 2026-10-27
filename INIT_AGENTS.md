# Agent Onboarding & Environment Initialization Guide (`INIT_AGENTS.md`)

Welcome to **InvestmentToolkit**. This is the single setup guide for both human engineers and AI coding assistants (Claude Code, Gemini CLI, Cursor, Antigravity, Copilot, Codex) on a fresh clone. `AGENTS.md` holds the rules; this file holds the order of operations.

## Contents

- [Quickstart](#quickstart-one-prompt-bootstrap)
- [Prerequisites](#prerequisites)
- [Step 1: Configuration (`.env`)](#step-1-configuration-env)
- [Step 2: Plugins and Ecosystem](#step-2-plugins-and-ecosystem)
- [Step 3: Core Substrate Health Check](#step-3-core-substrate-health-check)
- [Step 4: Runtime, TradingView and Databases](#step-4-runtime-tradingview-and-databases)
- [Optional: Questrade](#optional-questrade-pluginsquestrade)
- [Step 5: Master Onboarding (`/toolkit-onboarding`)](#step-5-master-onboarding-toolkit-onboarding)
- [Step 6: Maintenance & Worktree Protocol](#step-6-maintenance--worktree-protocol)

---

## Quickstart: One Prompt Bootstrap

If working with an AI assistant in chat, paste this directive:

```text
Please read INIT_AGENTS.md and work through it in order: prerequisites, .env, APM plugin install (ask me which plugin contribution mode I prefer: fork-and-pr, local-patch-and-issue, or domain-override), the runtime and database setup in Step 4, then run /toolkit-onboarding.
```

### Core Agent Commands Reference

| Command | Purpose |
| :--- | :--- |
| `/toolkit-onboarding` | Master Portfolio Bootstrap Wizard: pre-flight check → plugin install → account/pillar setup → broker sync → DCF baseline |
| `/daily` | The single daily skill (`daily-loop`). Full loop: sync → brief → triage → action cards → evolution log → verified receipts |
| `/daily --scan` | Fast non-interactive morning brief ("daily scan", "what should I do today"). Reads `data/daily-briefs/YYYY-MM-DD.json` |
| `/weekly-review` | Weekend drift + Grok research sweep |
| Post-catalyst review | `/strategic-review` → `/calibrate-targets` → `/rebalance-portfolio` |
| `/tv-portfolio-sync` | Sync broker positions and executed trades from TradingView into `domain_model.sqlite` (`fetch_broker_data.py --snapshot`) |

---

## Prerequisites

| Need | Required for | Notes |
| :--- | :--- | :--- |
| Python 3 with `venv` | everything | The launcher creates `venv/` and installs `requirements.txt`. The test suites run on 3.13. |
| Node.js and npm | backend, frontend, `tradingview-cdp` | The launcher exits if Node is missing. |
| `sqlite3` command line (optional) | inspecting databases by hand | The Python scripts do not need it. |
| TradingView Desktop (macOS) | broker sync, live quotes, TA sweeps, alerts, Pine, order views | The launcher can start it with the debugging port. The Windows launch path in `tv_launch.py` is a placeholder, so on Windows start TradingView yourself with `--remote-debugging-port=9222`. A TradingView account is needed; Premium is recommended for real-time data. |
| A broker connected inside TradingView's broker panel | loading holdings, cash and executed trades | No separate API credentials. See [what works without TradingView](#what-works-without-tradingview). |
| Questrade account and its MCP server (optional) | an additional source for positions and trades | Not needed for anything else. See Step 4, step 6. |

---

## Step 1: Configuration (`.env`)

```bash
cp .env.example .env
```

The launcher only prints a note when `.env` is missing, so do this first. Defaults work. Settings that matter:

- `TV_CDP_PORT=9222`: the TradingView debugging port.
- `QUESTRADE_ENABLED=false`: leave `false` unless you use Questrade and have completed `/questrade-setup`. TradingView is always the default source (`py_services/broker_sources.py` reads this setting).
- `BACKEND_PORT`, `FRONTEND_PORT`: only if 3001 or 5173 are taken.

---

## Step 2: Plugins and Ecosystem

InvestmentToolkit relies on shared ecosystem skills and plugins (from `agent-plugins-skills`, installed globally with APM) alongside domain-specific investment tools.

### 1. Choose Your Plugin Maintenance & Contribution Mode

When an agent encounters a bug, deprecated selector, or friction in an upstream skill during daily operations, how should it handle changes?

| Mode | Identifier | When to Choose | Agent Workflow |
| :--- | :--- | :--- | :--- |
| **Fork & PR** *(Recommended)* | `fork-and-pr` | You want to contribute improvements back to the ecosystem or maintain an active fork. | Clones/links `agent-plugins-skills`. Edits are made in a worktree, validated with `pytest`, and pushed as a Pull Request upstream. |
| **Local Patch & Issue** | `local-patch-and-issue` | You want rapid local resolution without maintaining a full git clone of the plugin repo. | Patches installed files directly in `.agents/skills/`. Generates an issue reproduction report to submit to upstream maintainers. |
| **Domain Override** | `domain-override` | Strict production consumer. Upstream plugins remain 100% vanilla. | Never alters upstream skills. Overrides logic using `.agent/rules/local-*` or dedicated `plugins/` in this repository. |

### 2. Install with APM (project plugins and shared library)

Everything installs with [APM](https://github.com/microsoft/apm), pinned to `apm-cli==0.33.0` (`pip install apm-cli==0.33.0`, then `apm --version`). There is no `uvx` or `plugin_add.py` step. Install each plugin with one installer only; installing it twice gives duplicate skill names.

**a. This repository's four plugins** (`portfolio-advisor`, `tradingview`, `toolkit-manager`, `questrade`). The root `apm.yml` lists them, so from the repository root:

```bash
apm install --target agent-skills
```

This deploys the skill hubs into `.agents/skills/` and writes `apm.lock.yaml` (commit it with any change; use `apm install --frozen` to reproduce exactly). `.agents/` and `apm_modules/` are gitignored. Never edit the deployed copies; change the plugin source under `plugins/<plugin>/.apm/` and reinstall. APM prints that questrade's MCP server cannot be configured for the `agent-skills` target; the skills still install, and `/questrade-setup` connects the server.

**b. The shared library is a global prerequisite, not a dependency of this repo.** `agent-plugins-skills` is a separate APM package set (`agent-agentic-os`, `agent-memory`, `agent-orchestration`, `agent-extension-authoring`, `agent-exploration-cycle`, `dev-utils`), maintained in its own clone (`../agent-plugins-skills`) and installed **globally**, so it is not listed in this repo's `apm.yml`. It supplies the Agentic OS substrate and the authoring and packaging skills (`packaging-with-apm`, `authoring-skills` and the rest) that this guide and `AGENTS.md` refer to. Confirm it before continuing:

```bash
grep -c "agent-plugins-skills/plugins" ~/.apm/apm.yml            # expect 6
ls ~/.claude/skills/packaging-with-apm ~/.claude/skills/authoring-skills >/dev/null && echo "global skills present"
```

If it is missing, clone it next to this repository (`cd .. && git clone https://github.com/richfrem/agent-plugins-skills.git`) and install each plugin globally from the clone with its **absolute path** (APM 0.33.0 rejects relative paths for global installs), for example `apm install -g /absolute/path/to/agent-plugins-skills/plugins/agent-agentic-os`, or use `packaging-with-apm`'s `scripts/apm_consumer.py` for a pinned install with backup and rollback. Install only universal infrastructure globally; domain plugins stay project-local (step a). Maintainers edit the clone directly and reinstall.

> The files `plugin-sources.json` and `plugin-retention.json` belong to the legacy `plugin-syncer` and cover only library plugins still deployed that way. They go away once every library plugin is installed with APM.

### 3. Run Agentic OS Initialization & Retrofit

This uses the globally installed `setting-up-agentic-os` skill (`init` mode), which depends on `running-control-plane` being installed beside it (Step 2b). Ask your agent to "set up the Agentic OS in this repository (retrofit, contribution mode `<your choice>`)" so it follows the skill's `init` workflow, or run the scripts yourself from the repository root:

```bash
# 1. Read-only preflight: classifies the repository
python3 ~/.agents/skills/running-control-plane/scripts/control_plane/installation_probe.py --target .

# 2. Retrofit (add --dry-run first to preview)
python3 ~/.agents/skills/setting-up-agentic-os/scripts/init_agentic_os.py \
  --target . --retrofit --contribution-mode fork-and-pr
```
*(Replace `fork-and-pr` with `local-patch-and-issue` or `domain-override` based on your choice.)*

The approval signing key is created by **you** in your own terminal (the skill's `signing-setup` mode walks you through it); an agent never creates or enrolls keys.

### 4. Claude Code only: register the project plugins

Skip this if you do not use Claude Code. The APM install above deploys the skills into `.agents/`. Claude Code also needs the plugins registered before `/tv-*` and the other plugin commands appear:

```text
/plugin marketplace add richfrem/InvestmentToolkit
/plugin install tradingview@investment-toolkit-plugins
/plugin install portfolio-advisor@investment-toolkit-plugins
/plugin install toolkit-manager@investment-toolkit-plugins
```

Questrade users also install `questrade@investment-toolkit-plugins`; see [Optional: Questrade](#optional-questrade-pluginsquestrade).

> [!IMPORTANT]
> **Single Instruction File (`AGENTS.md`) & Handling `.bak` Files**:
> - All agent instructions, rules, and architecture are consolidated into **`AGENTS.md`** to minimize context bloat.
> - `init_agentic_os.py` creates `.bak` files when updating existing guidelines or hooks.
> - **Agents MUST NOT blindly delete `.bak` files.** First review the diffs (`git diff`), reconcile any custom domain rules, and only remove `.bak` files once domain integrity is verified.

---

## Step 3: Core Substrate Health Check

Confirm that the local agentic runtime substrate is operational. These commands use the globally installed `agent-plugins-skills` skills (Step 2b); the project's own `.agents/skills/` appears after Step 2a:

```bash
# 1. Installation probe verification
python3 ~/.agents/skills/running-control-plane/scripts/control_plane/installation_probe.py --target .

# 2. Control plane, hooks, and evolution CI gate
test -f context/control_plane.db && echo "✅ control_plane.db active" || echo "❌ Missing control_plane.db"
test -f .claude/hooks/hooks.json && echo "✅ Claude hooks active" || echo "❌ Missing hooks.json"
test -f .git/hooks/pre-commit-evolution-guard && echo "✅ Evolution guard active" || echo "❌ Missing evolution guard"
test -f .github/workflows/verify-evolution-integrity.yml && echo "✅ CI integrity gate active" || echo "❌ Missing CI gate"

# 3. Cryptographic signing identity readiness (read-only status check)
python3 ~/.agents/skills/setting-up-agentic-os/scripts/setup_ciba_identity.py --check

# 4. Is control-plane gating on?
python3 ~/.agents/skills/running-control-plane/scripts/control_plane_mode.py status

# 5. Core test suites
python3 run_tests.py --t0-only
python3 run_tests.py --unit
```

For the full liveness check (event bus, locks, memory, metrics), ask your agent to "run health check"; that is the `health` mode of `running-control-plane`.

---

## Step 4: Runtime, TradingView and Databases

Work from the repository root. Order matters.

### 1. Install the `tradingview-cdp` engine dependencies

The launcher installs Node packages for `investment_screener/` only. The CDP engine is separate, and every TradingView call fails with `Cannot find package 'chrome-remote-interface'` until this runs:

```bash
cd tradingview-cdp && npm ci && cd ..
```

### 2. Start the suite once (creates the environment and the databases)

```bash
python3 run_investment_toolkit.py
```

This creates `venv/`, installs Python and Node dependencies, tries to launch TradingView Desktop with the debugging port (skip with `--no-tv`), backs up any existing databases, applies pending schema migrations, then starts the backend (3001) and frontend (5173). Use `--skip-deps` on later runs.

On a fresh clone the migrator creates `investment_screener/backend/data/domain_model.sqlite` (portfolio data, 23 tables) with **no rows**: no accounts, no pillars, no holdings. `intelligence.sqlite` (research ledger) is created when first used. Both files are gitignored personal data.

### 3. Verify the database

```bash
python3 investment_screener/backend/py_services/domain_model/schema_migrator.py --status
python3 plugins/toolkit-manager/.apm/skills/managing-the-toolkit/scripts/sqlite_admin.py status --db domain_model
```

`status` lists every table with its row count and the schema `user_version`. Right after step 2 only `schema_migrations` has rows.

### 4. Back up and export

Do this before any bulk write (syncs, imports, migrations) and after onboarding:

```bash
python3 investment_screener/backend/py_services/domain_model/db_backup.py backup --db domain_model
python3 plugins/toolkit-manager/.apm/skills/managing-the-toolkit/scripts/sqlite_admin.py export --db domain_model --out temp/exports/domain_model-$(date +%F)
python3 plugins/toolkit-manager/.apm/skills/managing-the-toolkit/scripts/sqlite_admin.py verify-export temp/exports/domain_model-$(date +%F)
```

The `sqlite-admin` mode of the `managing-the-toolkit` skill documents restore and rebuild. Worktrees hold their own empty copies of the gitignored databases; real backups are taken from the main checkout.

### 5. TradingView, then load holdings

1. `/tv-setup` (or `python3 investment_screener/backend/py_services/tv_health_check.py`) confirms port 9222 and the CDP dependencies. `/tv-onboarding` is the longer walkthrough.
2. Log in to your broker in TradingView's broker panel.
3. `/tv-portfolio-sync`. The accounts (TFSA, RRSP, CASH) and positions are created by this first sync; there is no separate account seeding command. The skill shows a per-account diff and asks for your go-ahead before writing.
4. Strategy pillars and sub-strategies are **not seeded** by any step yet (known gap, `references/map-debt.md` DEBT-20260930-02). They are created as theses are written.

### 6. Optional: Questrade

Skip this unless you use Questrade. The full walkthrough is [Optional: Questrade](#optional-questrade-pluginsquestrade) below; nothing else in the toolkit depends on it.

### What works without TradingView

| Works | Needs TradingView (or Questrade for holdings) |
| :--- | :--- |
| Backend and dashboard on the data already in SQLite | Loading positions, cash and executed trades (`/tv-portfolio-sync`; Questrade is the alternative) |
| Prices through the yfinance fallback (the launcher says "yfinance fallback active") | Live quotes from the chart, TA sweeps, alerts, Pine injection, order and watchlist views |
| DCF valuations, research, backups and exports | Placing or reviewing orders (execution is always done by you in TradingView) |

With neither TradingView nor Questrade there is currently **no way to load holdings** into a fresh database. Treat that as a known gap.

---

## Optional: Questrade (`plugins/questrade`)

Questrade support is an optional add-on for people who have a Questrade account. The core toolkit never depends on it (`AGENTS.md` rule 20): TradingView stays the default source for positions and trades, and every other feature works without it. Questrade is a second way to load holdings, cash, executed trades and prices, plus human-approved order drafting.

### What you get

| Skill | Does | Writes to the database |
| :--- | :--- | :--- |
| `/questrade-setup` | Connects Questrade's official MCP server, walks the browser sign-in, verifies it, records your choice in `.env` | No |
| `/questrade-get-balances`, `/questrade-get-positions`, `/questrade-activities` | Read-only views of balances and CAD/USD cash, open positions, and the cash-flow ledger (dividends, interest, deposits, trades) | No |
| `/questrade-sync-portfolio` | Loads accounts (`TFSA`, `RRSP`, `CASH`), holdings, cash splits, exchange rates and the last 30 days of executed trades into `domain_model.sqlite` | Yes |
| `/questrade-refresh-prices` | Refreshes prices for holdings or the watchlist from Questrade quotes | Yes |
| `/questrade-order-draft` | Drafts an order and sends a push-approval request to your Questrade mobile app. Nothing executes unless you approve it there | No |

### Prerequisites

- A Questrade account and an AI client that supports MCP servers (Claude Code, Codex CLI, Cursor or VS Code Copilot).
- The Questrade mobile app on a trusted device, if you want to approve drafted orders.
- Steps 1–4 above are done, so `domain_model.sqlite` exists and has a backup.

### Setup

1. **Install the plugin.** Claude Code: `/plugin install questrade@investment-toolkit-plugins` (the marketplace was added in Step 2, step 4). Other clients: `apm install --target agent-skills` (Step 2a) deploys it with the others.
2. **Run `/questrade-setup`.** It adds the server (Claude Code: `claude mcp add questrade --url https://mcp.questrade.com/v1/brokerage/mcp`; Codex CLI: `codex mcp add questrade --url ...`; Cursor and VS Code: add a server entry with that URL).
3. **Sign in.** You must complete the browser sign-in yourself; an agent cannot. If the page afterwards shows a connection error, paste the full address-bar URL back to the agent. No token is stored in the repository.
4. **Verify.** The agent calls `List Accounts`; it should return your account IDs. The sign-in lasts one session, so every Questrade skill re-checks it and sends you back to `/questrade-setup` when it has expired.
5. **Record the choice.** With your agreement the agent sets `QUESTRADE_ENABLED=true` in `.env` (adds the line, changes nothing else). Check it:

   ```bash
   python3 investment_screener/backend/py_services/broker_sources.py --json
   ```

   It should list `questrade` as available with `tradingview` still the default. From now on a position or trade refresh asks which source to use.
6. **First load.** Back up the database (Step 4, step 4), then run `/questrade-sync-portfolio`. It stages `temp/questrade_sync_payload.json`, previews with `--dry-run`, and writes only after you approve. It imports executed trades in the same run (only executed trades; open, cancelled and rejected orders are skipped), then runs the invariant check.

### Rules to keep

- **Orders are always your decision.** Questrade skills draft; you approve on your phone. No agent places an order on its own (`AGENTS.md` rule 17).
- **One source of truth.** Questrade data goes into the same `domain_model.sqlite` tables through the sync scripts (`questrade_sync.py`, `questrade_trades_import.py`); never write holdings with ad-hoc SQL.
- **Questrade-only users** still need TradingView for charts, TA sweeps and alerts; see the table in Step 4.
- **Turning it off:** set `QUESTRADE_ENABLED=false`. Nothing else changes.

---

## Step 5: Master Onboarding (`/toolkit-onboarding`)

Once Steps 1–4 are done, trigger the portfolio-side coordinator:

```text
/toolkit-onboarding
```

It does not install anything itself. It checks the runtime, backs up the database before the first write, asks whether you use Questrade, delegates to `/tv-portfolio-sync` and `/stock-intake` for holdings, builds DCF baselines, takes a verified export, and launches the suite through the `run-app` mode of `managing-the-toolkit`.

---

## Step 6: Maintenance & Worktree Protocol

When editing code across repositories:
- **Strict Worktree Discipline**: Always work in a dedicated git worktree (`.agent/rules/local-worktree-and-dual-repo-edit-protocol.md`).
- **Pre-Completion Gate**: Before concluding any agent turn, run `python3 run_tests.py --t0-only` and inspect `.agent/rules/test-driven-development.md`.
