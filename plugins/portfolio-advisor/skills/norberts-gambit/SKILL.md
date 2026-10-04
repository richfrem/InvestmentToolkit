---
name: norberts-gambit
plugin: portfolio-advisor
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

## Quick start
```bash
# Review current cash balances before initiating conversion
python3 plugins/questrade/scripts/questrade_sync.py --balances-only
```

## Workflow
1. **Identify Direction**: Confirm starting and target currencies to determine whether to purchase DLR.TO or DLR.U.
2. **Confirm Settings**: Verify account currency preference to prevent automatic conversion on settlement.
3. **Execute Purchase**: User purchases required ETF shares in the source currency.
4. **Submit Journal**: Once trades settle, user submits share journal request via broker portal per reference guide.
5. **Sell & Settle**: Sell journaled shares in target currency to finalize conversion.

## Verification
```bash
python3 plugins/questrade/scripts/questrade_sync.py --balances-only
```

## References
- [Questrade Submission Steps](references/questrade.md) - Step-by-step journal submission instructions, fees, and settlement settings for Questrade.
