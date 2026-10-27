# Mode: deposit-funds (`/questrade-deposit-funds`)

Walks the owner through a deposit in the Questrade portal, then records it so returns are not overstated. Trigger on `/questrade-deposit-funds`, "add money to my TFSA", "deposit to questrade" or "fund my account".
Allowed tools: Bash, Read.

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

4. **Confirm it landed.** Questrade quotes up to 30 minutes; deposits often arrive within moments. In the portal, **Move money → Deposit history → Interac e-Transfer** shows the deposit with status **COMPLETE** (its **See details** popup reads "Deposit complete — your money is now available"). From the agent side, with the Questrade MCP signed in (the [setup mode](../../../syncing-questrade-accounts/references/modes/setup.md) of `syncing-questrade-accounts`), call `Get Balances` for the account and check the CAD cash rose by the deposit. The deposit appears under `Get Account Activities` with `transactionTypes=["Deposits"]`.

5. **Record the contribution:**
   ```bash
   python3 investment_screener/backend/py_services/cash_flow_cli.py --add --date YYYY-MM-DD --type deposit \
       --amount-cad AMOUNT --account TFSA --portfolio-value-before-flow-cad VALUE
   ```
   `VALUE` is the whole portfolio's broker-reported total in CAD just before the deposit (the latest sync's `broker_reported_total.total_cad`, or `Get Balances` `totalEquity.combinedCad` summed over accounts minus this deposit). Never compute it from shares × price.

6. **Sync the portfolio** with `/tv-portfolio-sync` (or the [sync-portfolio mode](../../../syncing-questrade-accounts/references/modes/sync-portfolio.md) of `syncing-questrade-accounts`) so cash and totals include the deposit.

7. **Convert to USD if it will buy USD-listed stocks.** Three routes; pick by **when the owner needs to buy**, not only by fee:

   | Route | Cost on $3,000 CAD | When the USD is usable | Use when |
   |---|---|---|---|
   | **Buy the US stock directly with CAD cash** (Questrade converts at execution) | Questrade's FX conversion at trade time; confirm the current rate/fee in Questrade's FX disclosure before relying on it | **Immediately**: the order executes now | The owner wants to act on a move **today** |
   | **Exchange request** (Move money → Exchange) | 1.5% built into the rate (stated by Questrade): $45 | **Not immediate.** A queued request processed by Questrade staff, not an instant conversion: New → Approved → executed. A request made on a weekend may still not have posted by the end of the next trading day. | Conversion can be done **at least one business day before** the buy |
   | **Norbert's gambit** ([norberts-gambit mode](norberts-gambit.md)) | ~$13–15 ($9.95 journal fee unless Questrade Plus, plus DLR spread) | Up to 5 business days; plan on a calendar week | Larger amounts, or money that won't be deployed for a week |

   - **Never combine routes for the same money.** Don't buy US stocks with CAD while an Exchange request for that CAD is pending: the trade converts it and the queued request then converts again or fails. Cancel the request first (Move money history → Exchange, while it is still cancellable).
   - **"Approved" is not "posted".** Confirm USD cash with `Get Balances` before placing a USD order; don't plan a trade at the open around a conversion submitted the weekend before.
   - **Avoid the problem:** keep a small USD cash buffer in the account (or in a USD money-market fund) so a dip can be bought immediately, or deposit USD directly by pre-authorized deposit or wire.

8. **Exchange steps** (portal as of October 2026):
   1. Log in to Questrade.
   2. Open **Move money**.
   3. Choose **Exchange** ("Exchange between CAD and USD in self-directed margin and registered accounts").
   4. Pick the account (e.g. Individual TFSA), **Transaction: Exchange CAD to USD**, and **Action: Specify the amount of CAD to sell**. Alternatively, "Buy USD" sets the USD amount instead.
   5. Enter the **Amount** and click **Submit**.
   6. Check the **Review and confirm** popup (account, transaction, action, amount), then click **Confirm**. No rate is shown; it's set when Questrade processes the request.
   7. Questrade shows **"We're processing your fund exchange"** with a reference number (don't record it). The request can be reviewed or cancelled under **Move money history → Exchange** until it's processed.

   - **Processing time:** Questrade says requests before **2:30 p.m. ET** on a business day should be processed the same day and later ones are best-effort. In practice a weekend request moved to Approved early on the next trading day and still had not posted by that day's close. Treat the Exchange as a next-business-day route at best, and confirm the USD with `Get Balances` before placing an order.
   - **Registered accounts:** to exchange or hold USD, currency settlement must be "Currency of transaction" or "USD" (Management → Account management → Currency settlement → Change).

## Verification

- `Get Balances` shows the account's CAD cash up by the deposit amount.
- `python3 investment_screener/backend/py_services/cash_flow_cli.py --list --account TFSA` shows the new deposit row.
- Validate routing cases against `evals/evals.json`.

## References

- [Norbert's Gambit](norberts-gambit.md): converting the deposited CAD to USD without the FX spread.
- [Questrade Tool Schemas](../../../syncing-questrade-accounts/references/questrade-tool-schemas.md): `get_balances` and `get_account_activities` shapes.
