---
name: questrade-setup
plugin: questrade
description: Diagnose and guide setup of the Questrade Brokerage MCP connection across Claude Code, Cursor, VS Code Copilot, and Codex CLI. Trigger on /questrade-setup or "set up questrade mcp".
allowed-tools: Bash, Read, Write
---

# Questrade Setup

Setup and diagnostic wizard for the official Questrade Model Context Protocol (MCP) server.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **Endpoint invariant**: Official MCP endpoint is `https://mcp.questrade.com/v1/brokerage/mcp` using `http` transport.
- **Credential isolation**: Never request or persist raw Questrade API tokens directly in repository files; authentication uses Questrade's OAuth browser flow.
- **Tool boundary**: MCP provides broker querying and order staging; core analytics and database operations remain in `InvestmentToolkit`.

## Quick start

Add server to MCP configuration:

```bash
claude mcp add questrade --url https://mcp.questrade.com/v1/brokerage/mcp
```

Trigger browser login via `/mcp` or `codex mcp login questrade`.

## Workflow

1. **Configure Environment**:
   - Claude Code: `claude mcp add questrade --url https://mcp.questrade.com/v1/brokerage/mcp`
   - Codex CLI: `codex mcp add questrade --url https://mcp.questrade.com/v1/brokerage/mcp`
   - VS Code / Cursor: Add server entry with URL `https://mcp.questrade.com/v1/brokerage/mcp`
2. **Authenticate Session**:
   Initiate browser OAuth sign-in flow.
3. **Verify Connectivity**:
   Call MCP tool `List Accounts` to confirm live connection.

## Verification

- Confirm `List Accounts` returns active account IDs.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade MCP Integration](references/questrade-mcp-ai-integration.md): Multi-environment integration and transport architecture.
- [Questrade Tool Schemas](references/questrade-tool-schemas.md): Tool parameter shapes, return schemas, and error codes.
