---
name: trading-with-questrade
plugin: questrade
description: Moves money and places orders through Questrade with the owner approving every step. Covers drafting equity or options orders with Human-in-the-Loop mobile approval, guiding Interac e-Transfer deposits into a TFSA, RRSP or Cash account and recording them as contributions, and converting CAD to USD with Norbert's gambit. Trigger on /questrade-order-draft, /questrade-deposit-funds, "draft an order in questrade", "add money to my TFSA", "deposit to questrade", "fund my account", "convert CAD to USD" or "Norbert's gambit".
allowed-tools: Bash, Read, Write
---

# Trading with Questrade

Money-movement and order skills. They are kept apart from the read-only account skills because each step here needs the owner's explicit approval.

## Contents

- [Quick start](#quick-start) · [Workflow](#workflow) · [Constraints](#constraints) · [Modes](#modes) · [Verification](#verification) · [References](#references)

## Quick start

Confirm a signed-in session with `List Accounts` (setup mode of the `syncing-questrade-accounts` skill if it fails), then pick the mode below and read its mode file.

## Workflow

1. Match the request to a mode and read its mode file.
2. Resolve the account by type (TFSA, RRSP, Cash); ask the owner when it is unclear.
3. Preview or explain before anything is dispatched, and wait for the owner's explicit confirmation in chat.
4. After the owner has acted, verify with `Get Balances` and record the result as the mode describes.

## Constraints

- **The owner moves the money and approves every order.** The agent never logs in, approves a transfer, handles bank credentials or executes a live trade autonomously (Rule #17).
- **Questrade tools need a signed-in session.** Before any call, run `List Accounts`; if it fails, stop and follow the setup mode of the `syncing-questrade-accounts` skill. Tool schemas are in its [Questrade Tool Schemas](../syncing-questrade-accounts/references/questrade-tool-schemas.md).
- **Never record account numbers or Interac reference numbers** in skills, notes, logs or chat summaries. Name the account by type (TFSA, RRSP, Cash).
- **Explicit consent before anything is dispatched.** Preview first, then confirm in chat, then dispatch.
- **Pick the currency route by when the money is needed**, not only by fee, and never run two conversion routes on the same money at once (see [deposit-funds](references/modes/deposit-funds.md) step 7).

## Modes

Read the mode file before acting.

| Mode | Trigger | What it does |
|---|---|---|
| [order-draft](references/modes/order-draft.md) | `/questrade-order-draft` | Preview an equity or options order, then dispatch it to the owner's phone for mobile push approval |
| [deposit-funds](references/modes/deposit-funds.md) | `/questrade-deposit-funds` | Guides an Interac e-Transfer deposit, checks it landed, records the contribution, chooses the CAD to USD route |
| [norberts-gambit](references/modes/norberts-gambit.md) | "Norbert's gambit" | Converts CAD and USD inside the account with the DLR.TO / DLR.U pair, no bank FX spread |

## Verification

- Order draft: the owner explicitly confirmed in chat before `create_order_instruction` was dispatched.
- Deposit: `Get Balances` shows the account's CAD cash up by the deposit, and `python3 investment_screener/backend/py_services/cash_flow_cli.py --list --account TFSA` shows the new row.
- Norbert's gambit: `Get Balances` shows the source currency down and the target currency up by about the converted amount (less the journal fee).
- Routing cases for every mode are in `evals/evals.json`.

## References

- [Questrade Submission Steps](references/norberts-gambit-questrade.md): journal submission instructions, fees and settlement settings.
- The `syncing-questrade-accounts` skill: sign-in, balances, tool schemas and portfolio sync.
