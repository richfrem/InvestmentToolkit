---
name: questrade-deposit-funds
plugin: questrade
description: Guides the owner through depositing money into a Questrade account (TFSA, RRSP or Cash), including Interac e-Transfer, records the deposit as a contribution, and converts CAD to USD with Questrade Exchange (1.5% fee in the rate) or Norbert's gambit. Trigger on /questrade-deposit-funds, "add money to my TFSA", "deposit to questrade" or "fund my account".
allowed-tools: Bash, Read
---

# Questrade Deposit Funds

Walks the owner through a deposit in the Questrade portal, then records it so returns are not overstated.

## Contents

- [Constraints](#constraints)
- [Quick start](#quick-start)
- [Workflow](#workflow)
- [Verification](#verification)
- [References](#references)

## Constraints

- **The owner moves the money.** The agent never logs in, approves a transfer or handles bank credentials; it guides, checks and records.
- **Never record account numbers or Interac reference numbers** in skills, notes, logs or chat summaries. Name the account by type (TFSA, RRSP, Cash).
- **TFSA room first.** Confirm room in CRA My Account, not a self-kept tally: room from a withdrawal returns only on January 1 of the next year, and over-contributions cost 1% a month on the excess.
- **Record every deposit** with `cash_flow_cli.py` once it lands. An unrecorded deposit looks like an investment gain and corrupts return and drawdown figures.
- **Phishing check before bank login.** The approval page must be on `etransfer.interac.ca`, and the requester email must end in `@questrade.com`; the amount and expiry must match what the owner entered. If any of these differ, stop.

## Quick start

Questrade portal: **Move money → Deposit → Interac e-Transfer** (`myportal.questrade.com/investing/money-movement/deposit`).

## Workflow

1. **Choose the method.** Questrade's deposit methods, as shown on 2026-10-17 (recheck the page, since terms change):

   | Method | Fees | Time | Currency | Limit |
   |---|---|---|---|---|
   | Bill payment | None | 1–2 days | CAD | No maximum |
   | Pre-authorized deposit | None | 3–7 days | CAD & USD | Up to $100K |
   | Visa Debit card | None | Instant | CAD | $3K–10K |
   | **Interac e-Transfer** | None (the bank may charge) | Up to 30 minutes | CAD | Usually $3,000; up to $10,000 if the bank allows |
   | Wire transfer | None | 1–2 days | CAD & USD | No maximum |
   | Transfer between Questrade accounts | None | 1–2 days | CAD & USD | No maximum |

   - Above the owner's bank e-Transfer limit, use bill payment or split the deposit.
   - Holdings are USD-listed. Depositing USD by pre-authorized deposit or wire from a USD bank account avoids a currency conversion entirely.

2. **Start the deposit in Questrade** (Interac e-Transfer):
   1. Log in to Questrade.
   2. Open **Move money**.
   3. Choose **Deposit**.
   4. Pick **Interac e-Transfer**.
   5. Under **To Questrade account**, pick the account (e.g. Self-directed TFSA). The page shows its current cash balance.
   6. Enter the **Amount** in CAD (minimum $10; maximum usually $3,000, up to $10,000 if the bank allows it). The bank account name must match the Questrade account name.
   7. Click **Next**.
   8. A popup says **"Check your email for an Interac e-Transfer approval request."** The link expires in **48 hours**. **Done** only closes the popup; nothing moves until the request is approved.

3. **Approve it from the bank:**
   9. Open the Interac email ("…has requested $X (CAD) from you"). It opens Interac's **Request For Money** page. Run the phishing check from the Constraints, then under **Select Your Financial Institution** pick the bank. Alternatively, approve the request inside the bank's own app or website.
   10. **Accept the request** in the bank: opening the Interac email on a phone usually launches the bank's app. Accept the request, pick the account to pay from, then **review** (amount, payee Questrade) and **confirm**.

4. **Confirm it landed.** Questrade quotes up to 30 minutes; deposits often arrive within moments. In the portal, **Move money → Deposit history → Interac e-Transfer** shows the deposit with status **COMPLETE** (its **See details** popup reads "Deposit complete — your money is now available"). From the agent side, with the Questrade MCP signed in (`questrade-setup`), call `Get Balances` for the account and check the CAD cash rose by the deposit. The deposit appears under `Get Account Activities` with `transactionTypes=["Deposits"]`.

5. **Record the contribution:**
   ```bash
   python3 investment_screener/backend/py_services/cash_flow_cli.py --add --date YYYY-MM-DD --type deposit \
       --amount-cad AMOUNT --account TFSA --portfolio-value-before-flow-cad VALUE
   ```
   `VALUE` is the whole portfolio's broker-reported total in CAD just before the deposit (the latest sync's `broker_reported_total.total_cad`, or `Get Balances` `totalEquity.combinedCad` summed over accounts minus this deposit). Never compute it from shares × price.

6. **Sync the portfolio** with `/tv-portfolio-sync` (or `questrade-sync-portfolio`) so cash and totals include the deposit.

7. **Convert to USD if it will buy USD-listed stocks.** Compare the options with the owner:
   - **Questrade Exchange:** a flat **1.5% fee built into the exchange rate**, stated on Questrade's Exchange page. The CAD sold drops by exactly the amount entered, and the fee shows up as fewer USD; there is no separate deduction, so no extra CAD buffer is needed. On $3,000 CAD that's $45.
   - **Norbert's gambit** (`norberts-gambit` skill): about $13–15 on $3,000 ($9.95 journal fee unless Questrade Plus, plus a few dollars of DLR spread), but the owner's July 2026 conversion took the full 5 business days.
   - **Decision rule:** the ~$30 saving on $3,000 is small next to a week out of the market, so when the owner wants to buy within the week, use Exchange. Norbert's gambit pays off on larger amounts or money that will sit for a week anyway.

8. **Exchange steps** (portal as of October 2026):
   1. Log in to Questrade.
   2. Open **Move money**.
   3. Choose **Exchange** ("Exchange between CAD and USD in self-directed margin and registered accounts").
   4. Pick the account (e.g. Individual TFSA), **Transaction: Exchange CAD to USD**, and **Action: Specify the amount of CAD to sell**. Alternatively, "Buy USD" sets the USD amount instead.
   5. Enter the **Amount** and click **Submit**.
   6. Check the **Review and confirm** popup (account, transaction, action, amount), then click **Confirm**. No rate is shown; it's set when Questrade processes the request.
   7. Questrade shows **"We're processing your fund exchange"** with a reference number (don't record it). The request can be reviewed or cancelled under **Move money history → Exchange** until it's processed.

   - **Processing time:** requests before **2:30 p.m. ET** on a business day are processed the same day; later ones are best-effort. A weekend request waits for the next business day, so plan a Monday buy around it and confirm the USD with `Get Balances` before placing an order.
   - **Registered accounts:** to exchange or hold USD, currency settlement must be "Currency of transaction" or "USD" (Management → Account management → Currency settlement → Change).

## Verification

- `Get Balances` shows the account's CAD cash up by the deposit amount.
- `python3 investment_screener/backend/py_services/cash_flow_cli.py --list --account TFSA` shows the new deposit row.
- Validate routing cases against `evals/evals.json`.

## References

- [Norbert's Gambit](../norberts-gambit/SKILL.md): converting the deposited CAD to USD without the FX spread.
- [Questrade Tool Schemas](references/questrade-tool-schemas.md): `get_balances` and `get_account_activities` shapes.
