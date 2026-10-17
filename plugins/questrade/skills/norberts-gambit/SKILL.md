---
name: norberts-gambit
plugin: questrade
description: Guides the user through Norbert's Gambit to convert cash between CAD and USD inside a brokerage account using DLR.TO/DLR.U ETF pairs without bank FX spreads.
---

# Norbert's Gambit

## Contents
- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Journaling shares is a manual brokerage request; no autonomous order execution.
- Ensure the brokerage currency settlement preference is set to "Currency of transaction" prior to execution.
- Trade direction dictates starting ETF: USD->CAD buys DLR.U; CAD->USD buys DLR.TO.
- Await full trade settlement (1-2 business days) before submitting the journal request.
- **Size and timing check first**: the whole conversion takes up to 5 business days (about a week) and the journal costs $9.95 unless Questrade Plus. On about $3,000 it saves only about $30–45 over Questrade's own conversion (about a 1.5–2% spread), so recommend it mainly for larger amounts or money that won't be deployed for a week anyway.

## Quick start
```text
# Review current cash balances before initiating conversion (Questrade MCP, signed in via questrade-setup)
Get Balances(accountId=<id from List Accounts>)  -> balances.cash.cad / balances.cash.usd
```

## Workflow
1. **Identify Direction**: Confirm starting and target currencies to determine whether to purchase DLR.TO or DLR.U.
2. **Confirm Settings**: Verify account currency preference to prevent automatic conversion on settlement.
3. **Execute Purchase**: User purchases required ETF shares in the source currency.
4. **Submit Journal**: Once trades settle, user submits share journal request via broker portal per reference guide.
5. **Sell & Settle**: Sell journaled shares in target currency to finalize conversion.

## Verification
- `Get Balances` for the account shows the source-currency cash down and the target-currency cash up by about the converted amount (less the journal fee).
- Run `/tv-portfolio-sync` afterwards: DLR.TO/DLR.U are transient conversion vehicles, so they should appear and then disappear, not become a position with a target.

## References
- [Questrade Submission Steps](references/questrade.md) - Step-by-step journal submission instructions, fees, and settlement settings for Questrade.
- [Questrade Deposit Funds](../questrade-deposit-funds/SKILL.md) - Getting the CAD into the account first.
