# APM Installation & Harness Deployment Guide (`INSTALL.md`)

This guide covers installing and deploying the four local Investment Toolkit plugins (`plugins/portfolio-advisor`, `plugins/questrade`, `plugins/toolkit-manager`, `plugins/tradingview`) to all supported AI coding harnesses using **APM (Agent Package Manager)**.

---

## 1. Quick Install: All Supported Harnesses

Run this single command from the repository root to deploy skills, sub-agents, and MCP configurations across **Copilot**, **Agy (Antigravity)**, **Codex**, **Claude**, and the shared **Agent Skills** environment:

```bash
apm install --target agent-skills,copilot,agy,codex,claude
```

---

## 2. Common Scenarios

### Preview Changes (Dry Run)
Inspect what would be deployed or modified without writing files:
```bash
apm install --dry-run --target agent-skills,copilot,agy,codex,claude
```

### Reproduce Exact Versions (CI / Frozen Lockfile)
Install strictly from [`apm.lock.yaml`](apm.lock.yaml) without updating refs:
```bash
apm install --frozen --target agent-skills,copilot,agy,codex,claude
```

### Force Overwrite / Reinstall
If you modified files under `plugins/<plugin>/.apm/` or want a clean overwrite:
```bash
apm install --force --target agent-skills,copilot,agy,codex,claude
```

---

## 3. Harness Target Reference

You can target any subset of harnesses by comma-separating values passed to `--target` (or `-t`):

| Target Value | Harness / Tool | Deployed Locations & Behavior |
| :--- | :--- | :--- |
| `agent-skills` | Shared Standard | Deploys skills to `.agents/skills/`. Used as default in `apm.yml`. |
| `agy` *(or `antigravity`)* | Google Antigravity | Deploys skills and registers MCP servers for Antigravity CLI / IDE. |
| `claude` | Anthropic Claude Code | Adopts agents into `.claude/agents/`, skills into `.claude/skills/`, and MCP into `.claude/settings.json`. |
| `codex` | OpenAI Codex / CLI | Deploys skills and configuration into `.codex/`. |
| `copilot` | GitHub Copilot | Configures `.github/mcp.json` and Copilot instructions. |

### Example: Single Harness Deployments

```bash
# Claude only
apm install --target claude

# Copilot only
apm install --target copilot

# Antigravity (agy) only
apm install --target agy

# Codex only
apm install --target codex
```

---

## 4. MCP Servers

The local `questrade` plugin defines an MCP server. When targeting runtimes that support MCP (`copilot`, `agy`, `codex`, `claude`), APM automatically reconciles and trusts the server configuration:
- **Copilot**: `.github/mcp.json`
- **Claude**: `.claude/settings.json` (or `.claude.json`)
- **Antigravity / Codex**: harness-specific profile config

*(Note: The `agent-skills` runtime does not manage MCP processes, so APM skips MCP configuration for that target).*

---

## 5. Maintenance Rules

1. **Never edit deployed files**: Files in `.agents/skills/`, `.claude/skills/`, `.claude/agents/`, or `.codex/` are generated. Always edit the source files under `plugins/<plugin>/.apm/skills/` or `plugins/<plugin>/.apm/agents/`.
2. **Re-install after source edits**: After modifying plugin sources, re-run `apm install --target agent-skills,copilot,agy,codex,claude` to deploy changes.
3. **Commit the lockfile**: Always commit updates to [`apm.lock.yaml`](apm.lock.yaml) whenever dependencies or deployed target sets are modified.
