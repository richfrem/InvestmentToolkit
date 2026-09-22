# Agent Onboarding & Environment Initialization Guide (`INIT_AGENTS.md`)

Welcome to **InvestmentToolkit**. This guide is designed for both human engineers and AI coding assistants (Claude Code, Gemini CLI, Cursor, Antigravity, Copilot, Codex) when dropping into a fresh repository clone.

Follow this sequential protocol to configure your **Agentic OS Substrate**, align your **Plugin Contribution Policy**, and execute the **Master Onboarding Coordinator**.

---

## ⚡ Quickstart: One Prompt Bootstrap

If working with an AI assistant in chat, paste this directive:

```text
Please read INIT_AGENTS.md, run the initial substrate setup, ask me which plugin contribution mode I prefer (fork-and-pr, local-patch-and-issue, or domain-override), and then execute /toolkit-onboarding.
```

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

> [!IMPORTANT]
> **Single Instruction File (`AGENTS.md`) & Handling `.bak` Files**:
> - All agent instructions, rules, and architecture are consolidated into **`AGENTS.md`** to minimize context bloat.
> - `init_agentic_os.py` creates `.bak` files when updating existing guidelines or hooks.
> - **Agents MUST NOT blindly delete `.bak` files.** First review the diffs (`git diff`), reconcile any custom domain rules, and only remove `.bak` files once domain integrity is verified.

---

## Phase 2: Core Substrate Health Check

Confirm that the local agentic runtime substrate is operational:

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

## Phase 3: Launch Master Toolkit Onboarding (`/toolkit-onboarding`)

Once the Agentic OS substrate is confirmed, trigger the master investment coordinator:

```text
/toolkit-onboarding
```

The master wizard interactively guides you through:
1. **Engine Compilation**: Node.js dependencies, Python virtualenv, and TradingView CDP engine (`tradingview-cdp/`).
2. **Private Data Initialization**: Automatically creates `cash_flows.json` and `portfolio-config.json` from `.example` templates.
3. **Strategy Pillars & Accounts**: Configures account architecture (e.g. TFSA Primary + RRSP Mirror) and allocates target weights (Power, Compute, Data Infra, Cash).
4. **Broker / TradingView Sync**: Connects to TradingView Desktop (CDP port 9222) to ingest real-time positions, shares, and cash balances into `domain_model.sqlite`.
5. **DCF Valuation Baselines**: Generates institutional 5-year multi-scenario DCF baselines across your holdings.
6. **Live Chart Sync & Dashboard Launch**: Injects dynamic Fair Value / Entry overlays onto TradingView charts and boots the React/Express suite on port 5173 / 3001.

---

## Phase 4: Routine Maintenance & Dual-Repo Protocol

When editing code across repositories:
- **Strict Worktree Discipline**: Always work in a dedicated git worktree (`.agent/rules/local-worktree-and-dual-repo-edit-protocol.md`).
- **Pre-Completion Gate**: Before concluding any agent turn, run `python3 run_tests.py --t0-only` and inspect `.agent/rules/test-driven-development.md`.
