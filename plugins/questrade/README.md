# questrade

Questrade Brokerage integration for the Investment Toolkit, packaged as an APM-native package (`type: full`, primitives under `.apm/`).

## Skills

| Skill | Modes |
|---|---|
| `syncing-questrade-accounts` | `setup`, `balances`, `positions`, `activities`, `sync-portfolio`, `refresh-prices` |
| `trading-with-questrade` | `order-draft`, `deposit-funds`, `norberts-gambit` |

Slash commands are unchanged (`/questrade-setup`, `/questrade-get-balances`, `/questrade-get-positions`, `/questrade-activities`, `/questrade-sync-portfolio`, `/questrade-refresh-prices`, `/questrade-order-draft`, `/questrade-deposit-funds`).

## Layout

```
apm.yml                     manifest (includes: auto, MCP server declared under dependencies.mcp)
.apm/skills/<skill>/        SKILL.md (hub), references/modes/, references/, scripts/, tests/, evals/
docs/                       governance, attribution, lifecycle
```

## Install

From the repository root, `apm install ./plugins/questrade --target agent-skills,claude` deploys the skills to `.agents/skills/` and `.claude/skills/` (both are generated and gitignored; edit the sources under `.apm/`).

## Prerequisites

Questrade tools exist only after the owner signs in through a browser, and the sign-in does not carry over between sessions. Start with the `setup` mode.

## Tests

`python3 -m pytest plugins/questrade/.apm/skills/syncing-questrade-accounts/tests`
