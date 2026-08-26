---
name: questrade-setup
description: "Diagnose and guide setup of the Questrade Brokerage MCP connection in Claude Code or other supported AI environments."
argument-hint: "[command]"
allowed-tools: Bash, Read, Write
---

# Questrade Multi-Agent Setup & Diagnostic Skill

## Purpose
Configures and verifies the official Questrade Model Context Protocol (MCP) server across supported AI environments (Antigravity / Gemini, Cursor, VS Code Copilot, Codex CLI, and Claude Code).

---

## 🛠️ Universal Setup Across Environments

### 1. Antigravity IDE (AGY) / Standard MCP Config
This repository provides a top-level `.mcp.json` and `plugins/questrade/.mcp.json`:
```json
{
  "mcpServers": {
    "questrade": {
      "url": "https://mcp.questrade.com/v1/brokerage/mcp",
      "transport": "http"
    }
  }
}
```
If your IDE supports MCP Server auto-discovery, it reads `.mcp.json` upon launch.

---

### 2. VS Code / GitHub Copilot Chat
1. Open Command Palette: `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows).
2. Type `MCP: Add Server`.
3. Select `HTTP`.
4. Enter URL: `https://mcp.questrade.com/v1/brokerage/mcp`.
5. Name: `questrade`.
6. Complete browser sign-in.

---

### 3. Cursor
1. `Settings` -> `Tools & Integrations` -> `MCP`.
2. Select `New MCP Server`.
3. Name: `questrade`, Type: `sse`/`http`, URL: `https://mcp.questrade.com/v1/brokerage/mcp`.
4. Save and toggle **On**.

---

### 4. Codex CLI
```bash
codex mcp add questrade --url https://mcp.questrade.com/v1/brokerage/mcp
codex mcp login questrade
```

---

### 5. Claude Code (CLI)

#### Step A: Register Marketplace & Install Plugin
In your Claude Code terminal, run:
```text
/plugin marketplace add richfrem/InvestmentToolkit
/plugin install questrade@investment-toolkit-plugins
```

#### Step B: Add MCP Server & Log In
```bash
claude mcp add --transport http questrade https://mcp.questrade.com/v1/brokerage/mcp
```
*In Claude Code: `/mcp` -> `questrade` -> `Log in` to complete the browser OAuth handshake.*

## 📱 Mandatory Prerequisite for Order Drafting: Mobile Push Approval
While account balances, positions, and market research are completely desktop-accessible, **order drafting (`Create Order Instruction`) strictly requires mobile Push-to-Approve**:
1. **Install App**: Install **QuestMobile** or **EdgeMobile** on your smartphone.
2. **Enroll Device**: Sign in on the app to register your phone as a trusted device under Security / Push Approvals.
3. **App State**: Ensure the mobile app is active/unlocked on your phone when requesting order drafts from your AI agent to receive the instant push approval prompt.
4. **Desktop Fallback**: If no mobile device is enrolled, orders will execute in **Preview mode only** (`Preview Order Instruction`), displaying margin and commission economics without sending to the broker.

---

## ⚠️ Claude Code Permission Guidelines
When configuring `.claude/settings.local.json` or granting tool permissions in Claude Code v2.1.246+:
- **Avoid Leading Wildcards**: Use trailing wildcards only (e.g. `"Bash(awk *)"` or `"Bash(npm run *)"`), never unescaped mid-command wildcards (e.g. avoid `"Bash(awk '/regex.*pattern/' file)"`).
- **Restart After Plugin Add**: After installing the plugin, restart Claude Code (`/exit` then `claude`) to load the newly registered `/questrade:*` slash commands.
