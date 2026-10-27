# Mode: norberts-gambit

Guides the user through Norbert's Gambit to convert cash between CAD and USD inside a brokerage account using DLR.TO/DLR.U ETF pairs without bank FX spreads.

## Contents
- [Constraints](#constraints)
- [Common failures](#common-failures)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints
- Journaling shares is a manual brokerage request; no autonomous order execution.
- Ensure the brokerage currency settlement preference is set to "Currency of transaction" prior to execution.
- Trade direction dictates the starting ETF. Buy the unit in the currency you already hold:

  | You hold | You want | Buy | Journal to | Sell |
  |---|---|---|---|---|
  | CAD | USD | DLR.TO | DLR.U | DLR.U for USD |
  | USD | CAD | DLR.U | DLR.TO | DLR.TO for CAD |
- Await full trade settlement (1-2 business days) before submitting the journal request.
- **Pick the route by when the money is needed** (full table in [deposit-funds](deposit-funds.md) step 7): to act **today**, buy the US stock directly with CAD and let Questrade convert at execution; the in-account **Exchange** is a queued request processed by Questrade staff (not instant; a weekend request can take more than the next trading day to post); Norbert's gambit takes up to a week. Never run two routes on the same money at once.
- **Size and timing check first**: the whole conversion takes up to 5 business days (in practice it can take all 5, so plan on a calendar week) and the journal costs $9.95 unless Questrade Plus. On about $3,000 it saves only about $30 over Questrade's Exchange (a stated 1.5% built into the rate), so recommend it mainly for larger amounts or money that won't be deployed for a week anyway.

## Common failures
- **Buying the wrong unit first:** with CAD, buying DLR.U needs USD you don't have. Buy DLR.TO.
- **Journaling before settlement:** submit the journal request only after the purchase settles (1–2 business days).
- **Auto-conversion on settlement:** without "Currency of transaction", Questrade converts and charges the spread anyway.
- **No cash for the fee:** the $9.95 is deducted after processing; leave it in the account.
- **Canadian holidays:** DLR.TO trades on the TSX, which is closed on Canadian holidays even when US markets are open.
- **Timing a market entry around it:** a week out of the market can move a position more than the spread saved; offer Questrade's conversion when the owner wants to buy this week.

## Quick start
```text
# Review current cash balances before initiating conversion (Questrade MCP, signed in via the setup mode of syncing-questrade-accounts)
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
- [Questrade Submission Steps](../norberts-gambit-questrade.md) - Step-by-step journal submission instructions, fees, and settlement settings for Questrade.
- [Deposit funds](deposit-funds.md) - Getting the CAD into the account first.
