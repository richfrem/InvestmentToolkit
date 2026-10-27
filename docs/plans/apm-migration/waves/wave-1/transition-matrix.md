# Wave 1 (questrade): transition matrix

Old skill names are retired; slash commands are unchanged. Skills are read from `plugins/questrade/.apm/skills/<hub>/references/modes/<mode>.md`.

| Legacy skill | Hub skill | Mode | Slash command | What changed |
|:---|:---|:---|:---|:---|
| `questrade-setup` | `syncing-questrade-accounts` | `setup` | `/questrade-setup` | Also notes that APM writes the MCP config when the package is installed. |
| `questrade-get-balances` | `syncing-questrade-accounts` | `balances` | `/questrade-get-balances` | Content unchanged; paths made relative to the hub. |
| `questrade-get-positions` | `syncing-questrade-accounts` | `positions` | `/questrade-get-positions` | Content unchanged; paths made relative to the hub. |
| `questrade-activities` | `syncing-questrade-accounts` | `activities` | `/questrade-activities` | Content unchanged; paths made relative to the hub. |
| `questrade-sync-portfolio` | `syncing-questrade-accounts` | `sync-portfolio` | `/questrade-sync-portfolio` | Script paths are now `scripts/...` inside the hub; cross-plugin scripts keep their repo paths until wave 4. |
| `questrade-refresh-prices` | `syncing-questrade-accounts` | `refresh-prices` | `/questrade-refresh-prices` | Script path is now `scripts/questrade_price_refresh.py` inside the hub. |
| `questrade-order-draft` | `trading-with-questrade` | `order-draft` | `/questrade-order-draft` | Human-approval gate unchanged; tool schemas now linked from `syncing-questrade-accounts`. |
| `questrade-deposit-funds` | `trading-with-questrade` | `deposit-funds` | `/questrade-deposit-funds` | References to other skills are now links to modes. Content unchanged. |
| `norberts-gambit` | `trading-with-questrade` | `norberts-gambit` | `/DLR` | Now a mode of `trading-with-questrade`; reference file moved with it. |

## Other changes
- `plugins/questrade/scripts/`, `references/`, `assets/`, `tests/` no longer exist; their files live inside the hubs (see `master_migration_inventory.csv`, wave 1).
- Deleted with your approval: `scaffold_skill.py`, `assets/templates/SKILL.md.template`. Retired manifests: `plugin.json`, `plugin.yaml`, `.claude-plugin/plugin.json`, `.mcp.json` (the MCP server is declared in `apm.yml`).
- Scripts and tests find the repo root by the `investment_screener/` marker instead of a fixed `parents[N]` depth.
- `.claude-plugin/marketplace.json`: the questrade entry was removed (it required the retired `plugin.json`).
- Updated references elsewhere: `daily-loop`, `weekly-review` (portfolio-advisor), `toolkit-onboarding` (toolkit-manager) now name the new mode; three eval files expect `syncing-questrade-accounts`.

## Not done in this wave (needs your decision)
- Deployed copies in `.agents/skills/` (the nine old questrade skills) are unchanged generated local state and are now stale. Switching them to the APM install (`apm install ./plugins/questrade --target agent-skills`, root `apm.yml` and `apm.lock.yaml`) also means removing `questrade` from the tracked `plugin-sources.json` so the legacy sync stops reinstalling it. Decision 5.
