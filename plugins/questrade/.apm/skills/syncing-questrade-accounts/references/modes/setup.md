# Mode: setup (`/questrade-setup`)

Setup and diagnostic wizard for the official Questrade Model Context Protocol (MCP) server. Trigger on `/questrade-setup` or "set up questrade mcp".
Allowed tools: Bash, Read, Write.

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

When this plugin is installed with APM, the server entry is declared in the package manifest (`dependencies.mcp`) and APM writes each harness's MCP configuration at install time; the manual commands below are for harnesses or sessions where that has not been done.

## Workflow

1. **Configure Environment**:
   - Claude Code: `claude mcp add questrade --url https://mcp.questrade.com/v1/brokerage/mcp`
   - Codex CLI: `codex mcp add questrade --url https://mcp.questrade.com/v1/brokerage/mcp`
   - VS Code / Cursor: Add server entry with URL `https://mcp.questrade.com/v1/brokerage/mcp`
2. **Authenticate Session**:
   Initiate browser OAuth sign-in flow. The owner must complete it; an agent cannot.
   - Claude Code: call the `questrade` server's `authenticate` tool (or have the owner run `/mcp` and choose questrade) and give the owner the returned link.
   - The owner signs in and approves access in the browser. If the page after approval shows a connection error, the owner pastes the full address-bar URL back and the agent passes it to `complete_authentication`.
   - Sign-in is per session and expires: every sync, activities or order skill must re-check with `List Accounts` and return here when it fails.
3. **Verify Connectivity**:
   Call MCP tool `List Accounts` to confirm live connection.
4. **Record the Choice**:
   With the owner's agreement, set `QUESTRADE_ENABLED=true` in the repository `.env` (add the line; never rewrite other lines). Refresh skills and the Trade Log page read it through `broker_sources.py`. Without it the toolkit uses TradingView only.

## Verification

- Confirm `List Accounts` returns active account IDs.
- Validate test cases against `evals/evals.json`.

## References

- [Questrade MCP Integration](../questrade-mcp-ai-integration.md): Multi-environment integration and transport architecture.
- [Questrade Tool Schemas](../questrade-tool-schemas.md): Tool parameter shapes, return schemas, and error codes.
