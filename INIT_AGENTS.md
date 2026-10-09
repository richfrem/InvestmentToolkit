# Agent Onboarding & Environment Initialization Guide (`INIT_AGENTS.md`)

Welcome to **InvestmentToolkit**. This is the single setup guide for both human engineers and AI coding assistants (Claude Code, Gemini CLI, Cursor, Antigravity, Copilot, Codex) on a fresh clone. `AGENTS.md` holds the rules; this file holds the order of operations.

## Contents

- [Quickstart](#quickstart-one-prompt-bootstrap)
- [Prerequisites](#prerequisites)
- [Phase 0: Configuration (`.env`)](#phase-0-configuration-env)
- [Phase 1: Agentic OS and plugins](#phase-1-interactive-agentic-os--dependency-alignment)
- [Phase 2: Substrate health check](#phase-2-core-substrate-health-check)
- [Phase 3: Runtime, TradingView and the databases](#phase-3-runtime-tradingview-and-the-databases)
- [Phase 4: `/toolkit-onboarding`](#phase-4-launch-master-toolkit-onboarding-toolkit-onboarding)
- [Phase 5: Routine maintenance](#phase-5-routine-maintenance--dual-repo-protocol)

---

## Quickstart: One Prompt Bootstrap

If working with an AI assistant in chat, paste this directive:

```text
Please read INIT_AGENTS.md and work through it in order: prerequisites, .env, plugin install (ask me which plugin contribution mode I prefer: fork-and-pr, local-patch-and-issue, or domain-override), the runtime and database setup in Phase 3, then run /toolkit-onboarding.
```

---

## Prerequisites

| Need | Required for | Notes |
| :--- | :--- | :--- |
| Python 3 with `venv` | everything | The launcher creates `venv/` and installs `requirements.txt`. The test suites run on 3.13. |
| Node.js and npm | backend, frontend, `tradingview-cdp` | The launcher exits if Node is missing. |
| `sqlite3` command line (optional) | inspecting databases by hand | The Python scripts do not need it. |
| TradingView Desktop (macOS) | broker sync, live quotes, TA sweeps, alerts, Pine, order views | The launcher can start it with the debugging port. The Windows launch path in `tv_launch.py` is a placeholder, so on Windows start TradingView yourself with `--remote-debugging-port=9222`. A TradingView account is needed; Premium is recommended for real-time data. |
| A broker connected inside TradingView's broker panel | loading holdings, cash and executed trades | No separate API credentials. See [what works without TradingView](#what-works-without-tradingview). |
| Questrade account and its MCP server (optional) | an additional source for positions and trades | Not needed for anything else. See Phase 3, step 6. |

---

## Phase 0: Configuration (`.env`)

```bash
cp .env.example .env
```

The launcher only prints a note when `.env` is missing, so do this first. Defaults work. Settings that matter:

- `TV_CDP_PORT=9222`: the TradingView debugging port.
- `QUESTRADE_ENABLED=false`: leave `false` unless you use Questrade and have completed `/questrade-setup`. TradingView is always the default source (`py_services/broker_sources.py` reads this setting).
- `BACKEND_PORT`, `FRONTEND_PORT`: only if 3001 or 5173 are taken.

---

## Phase 1: Interactive Agentic OS & Dependency Alignment

InvestmentToolkit relies on shared ecosystem skills and plugins (from `agent-plugins-skills`) alongside domain-specific investment tools.

### 1. Choose Your Plugin Maintenance & Contribution Mode

When an agent encounters a bug, deprecated selector, or friction in an upstream skill during daily operations, how should it handle changes?

| Mode | Identifier | When to Choose | Agent Workflow |
| :--- | :--- | :--- | :--- |
| **Fork & PR** *(Recommended)* | `fork-and-pr` | You want to contribute improvements back to the ecosystem or maintain an active fork. | Clones/links `agent-plugins-skills`. Edits are made in a worktree, validated with `pytest`, and pushed as a Pull Request upstream. |
| **Local Patch & Issue** | `local-patch-and-issue` | You want rapid local resolution without maintaining a full git clone of the plugin repo. | Patches installed files directly in `.agents/skills/`. Generates an issue reproduction report to submit to upstream maintainers. |
| **Domain Override** | `domain-override` | Strict production consumer. Upstream plugins remain 100% vanilla. | Never alters upstream skills. Overrides logic using `.agent/rules/local-*` or dedicated `plugins/` in this repository. |

### 2. Upstream Dependency Alignment (Local Checkout vs. Remote Clone)

- **For Maintainers / Authors (if `agent-plugins-skills` is already cloned locally)**:
  Use your existing local sibling checkout directly without cloning from GitHub:
  ```bash
  # Fast local install using adjacent checkout:
  python3 ../agent-plugins-skills/plugins/plugin-manager/scripts/plugin_add.py ../agent-plugins-skills/plugins/ --all -y
  ```
- **For External Users / Fresh Machines (remote GitHub clone)**:
  If opting for **`fork-and-pr`**, clone upstream adjacent to this repository:
  ```bash
  cd ..
  git clone https://github.com/richfrem/agent-plugins-skills.git
  cd agent-plugins-skills && python3 run_tests.py && cd ../InvestmentToolkit
  ```
  *(Or install universally via uvx: `uvx --from git+https://github.com/richfrem/agent-plugins-skills plugin-add richfrem/agent-plugins-skills`)*

### 3. Run Agentic OS Initialization & Retrofit

Run the installation probe preflight first, then initialize or retrofit targeting this workspace:

```bash
# 1. Check current substrate state (read-only diagnostic):
python3 ../agent-plugins-skills/plugins/agent-agentic-os/scripts/control_plane/installation_probe.py --target .

# 2. Run retrofit (if agent-plugins-skills is local):
python3 ../agent-plugins-skills/plugins/agent-agentic-os/scripts/init_agentic_os.py \
  --target . \
  --retrofit \
  --contribution-mode fork-and-pr

# 3. Ensure control plane schema migration is current:
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('../agent-plugins-skills/plugins/agent-agentic-os/scripts').resolve()))
from agent_control import ControlPlane
ControlPlane(db_path=Path('context/control_plane.db')).init_db()
"
```
*(Replace `fork-and-pr` with `local-patch-and-issue` or `domain-override` based on your choice).*

### 4. Claude Code only: register the project plugins

Skip this if you do not use Claude Code. The plugin sync above deploys skills into `.agents/`; Claude Code also needs the plugins registered before `/tv-*` and the other plugin commands appear:

```text
/plugin marketplace add richfrem/InvestmentToolkit
/plugin install tradingview@investment-toolkit-plugins
/plugin install portfolio-advisor@investment-toolkit-plugins
/plugin install stock-valuation@investment-toolkit-plugins
/plugin install toolkit-manager@investment-toolkit-plugins
/plugin install etf-analysis@investment-toolkit-plugins
```

> [!IMPORTANT]
> **Single Instruction File (`AGENTS.md`) & Handling `.bak` Files**:
> - All agent instructions, rules, and architecture are consolidated into **`AGENTS.md`** to minimize context bloat.
> - `init_agentic_os.py` creates `.bak` files when updating existing guidelines or hooks.
> - **Agents MUST NOT blindly delete `.bak` files.** First review the diffs (`git diff`), reconcile any custom domain rules, and only remove `.bak` files once domain integrity is verified.

---

## Phase 2: Core Substrate Health Check

Confirm that the local agentic runtime substrate is operational. These commands use tools installed by Phase 1, so run Phase 1 first (`.agents/` does not exist on a fresh clone):

```bash
# 1. Installation probe verification
python3 ../agent-plugins-skills/plugins/agent-agentic-os/scripts/control_plane/installation_probe.py --target .

# 2. Control plane, hooks, and evolution CI gate
test -f context/control_plane.db && echo "✅ control_plane.db active" || echo "❌ Missing control_plane.db"
test -f .claude/hooks/hooks.json && echo "✅ Claude hooks active" || echo "❌ Missing hooks.json"
test -f .git/hooks/pre-commit-evolution-guard && echo "✅ Evolution guard active" || echo "❌ Missing evolution guard"
test -f .github/workflows/verify-evolution-integrity.yml && echo "✅ CI integrity gate active" || echo "❌ Missing CI gate"

# 3. Cryptographic signing identity readiness (read-only)
python3 .agents/skills/os-health-check/scripts/setup_ciba_identity.py --check

# 4. Symlink integrity
python3 .agents/skills/symlink-manager/scripts/symlink_manager.py diagnose

# 5. Core test suites
python3 run_tests.py --t0-only
python3 run_tests.py --unit

# 6. Run full OS health check loop
python3 .agents/skills/os-health-check/scripts/kernel.py emit_event --agent os-health-check --type intent --action scan_metrics
```

---

## Phase 3: Runtime, TradingView and the databases

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
python3 plugins/toolkit-manager/scripts/sqlite_admin.py status --db domain_model
```

`status` lists every table with its row count and the schema `user_version`. Right after step 2 only `schema_migrations` has rows.

### 4. Back up and export

Do this before any bulk write (syncs, imports, migrations) and after onboarding:

```bash
python3 plugins/toolkit-manager/scripts/db_backup.py backup --db domain_model
python3 plugins/toolkit-manager/scripts/sqlite_admin.py export --db domain_model --out temp/exports/domain_model-$(date +%F)
python3 plugins/toolkit-manager/scripts/sqlite_admin.py verify-export temp/exports/domain_model-$(date +%F)
```

The `sqlite-admin` skill documents restore and rebuild. Worktrees hold their own empty copies of the gitignored databases; real backups are taken from the main checkout.

### 5. TradingView, then load holdings

1. `/tv-setup` (or `python3 plugins/tradingview/scripts/tv_health_check.py`) confirms port 9222 and the CDP dependencies. `/tv-onboarding` is the longer walkthrough.
2. Log in to your broker in TradingView's broker panel.
3. `/tv-portfolio-sync`. The accounts (TFSA, RRSP, CASH) and positions are created by this first sync; there is no separate account seeding command. The skill shows a per-account diff and asks for your go-ahead before writing.
4. Strategy pillars and sub-strategies are **not seeded** by any step yet (known gap, `references/map-debt.md` DEBT-20260930-02). They are created as theses are written.

### 6. Optional: Questrade

Skip this unless you use Questrade. Run `/questrade-setup` (it connects Questrade's MCP server through its browser sign-in; no token is stored in the repo). It sets `QUESTRADE_ENABLED=true` in `.env`; position and trade refreshes then ask which source to use, with TradingView still the default. Nothing else in the toolkit depends on it.

### What works without TradingView

| Works | Needs TradingView (or Questrade for holdings) |
| :--- | :--- |
| Backend and dashboard on the data already in SQLite | Loading positions, cash and executed trades (`/tv-portfolio-sync`; Questrade is the alternative) |
| Prices through the yfinance fallback (the launcher says "yfinance fallback active") | Live quotes from the chart, TA sweeps, alerts, Pine injection, order and watchlist views |
| DCF valuations, research, backups and exports | Placing or reviewing orders (execution is always done by you in TradingView) |

With neither TradingView nor Questrade there is currently **no way to load holdings** into a fresh database. Treat that as a known gap.

---

## Phase 4: Launch Master Toolkit Onboarding (`/toolkit-onboarding`)

Once Phases 0-3 are done, trigger the portfolio-side coordinator:

```text
/toolkit-onboarding
```

It does not install anything itself. It checks the runtime, backs up the database before the first write, asks whether you use Questrade, delegates to `/tv-portfolio-sync` and `/stock-intake` for holdings, builds DCF baselines, takes a verified export, and launches the suite through `run-screener`.

---

## Phase 5: Routine Maintenance & Dual-Repo Protocol

When editing code across repositories:
- **Strict Worktree Discipline**: Always work in a dedicated git worktree (`.agent/rules/local-worktree-and-dual-repo-edit-protocol.md`).
- **Pre-Completion Gate**: Before concluding any agent turn, run `python3 run_tests.py --t0-only` and inspect `.agent/rules/test-driven-development.md`.
