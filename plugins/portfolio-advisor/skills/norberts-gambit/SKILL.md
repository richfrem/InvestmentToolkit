---
name: norberts-gambit
plugin: portfolio-advisor
description: >
  Guides the user through Norbert's Gambit — the standard technique for converting
  cash between CAD and USD inside a brokerage account using the DLR.TO/DLR.U ETF
  pair, avoiding a bank or broker's FX spread. Explains the direction to trade,
  the generic buy → journal → withdraw mechanics, and links to broker-specific
  submission steps (Broker today; other brokers added as references/ grows).
  Trigger: "norbert's gambit", "convert CAD to USD", "convert USD to CAD",
  "move money between accounts in a different currency", "/norberts-gambit".
allowed-tools: Read
---

# Norbert's Gambit Skill

## Purpose
A reference/checklist skill — not an automation. Journaling a currency conversion is a
manual request submitted on the broker's own website; there's no CDP or API path to drive
for it. This skill's job is to walk the user through the *concept* and the *generic steps*
correctly, then point at the concrete submission steps for their specific broker.

---

## What Norbert's Gambit Is

Converting cash directly (bank wire, broker's built-in FX conversion) charges a spread —
often 1-2% — on top of the mid-market rate. Norbert's Gambit avoids that spread by using
a single security listed in both currencies: the Horizons US Dollar Currency ETF pair,
**DLR.TO** (CAD-denominated units) and **DLR.U** (USD-denominated units of the *same*
underlying fund). Because they represent the same fund, a broker can convert one into the
other via an internal "journal" request — a bookkeeping transfer, not a trade — at
effectively the mid-market rate, for a flat fee (or free) instead of a percentage spread.

**The bigger the amount, the more this matters.** A 1.5% spread on $3,000 is ~$45; on
$30,000 it's ~$450. Norbert's Gambit's fixed/flat cost structure means the savings scale
with the conversion size.

---

## Which Direction to Trade

| You have | You want | Buy | Journal to | Result |
|----------|----------|-----|-------------|--------|
| USD cash | CAD cash | DLR.U | DLR.TO | Sell the DLR.TO units for CAD (or withdraw as CAD if your account supports it) |
| CAD cash | USD cash | DLR.TO | DLR.U | Sell the DLR.U units for USD (or withdraw as USD) |

A common trigger for the USD→CAD direction: selling a USD-denominated holding (e.g. a
USD-listed cash-equivalent fund) produces USD cash, but you need CAD out of the account.

---

## Generic 3-Step Mechanics (every broker)

1. **Buy** the currency-denominated unit matching what you currently hold (see table
   above) — e.g. holding USD cash → buy DLR.U.
2. **Submit a journal-shares request** on the broker's website/app to convert the
   just-purchased units into the other currency's unit (DLR.U ↔ DLR.TO). This is the step
   that actually performs the conversion — it is *not* a sell order. Broker-specific
   submission steps are in `references/`, listed below.
3. **Withdraw or use the funds** once the journal completes — sell the converted units for
   cash in the target currency, or transfer/withdraw per your broker's process.

**Before step 1, for any broker:** confirm the account's currency settlement preference is
set to keep the transaction in its original currency (not auto-converted) — otherwise the
broker may convert your cash at the very spread this technique exists to avoid, before you
even get to buy DLR.U/DLR.TO. Each broker's reference file below has the exact setting.

---

## Broker-Specific Submission Steps

Pick your broker's reference file for the exact journal-request steps, processing time,
fees, and settings:

- **Broker** → [`references/broker.md`](references/broker.md)
- *(Other brokers not yet documented — if you use TD, Interactive Brokers, Wealthsimple,
  etc., ask to have a reference file added; the broker-agnostic sections above don't
  change, only the "how to submit the request" appendix does.)*

---

## Walking the User Through It

1. Ask which direction they need (CAD→USD or USD→CAD) and roughly how much, if not already
   stated — this determines which symbol to buy first (the table above).
2. Confirm which broker they're using, and open that broker's reference file. If no
   reference file exists yet for their broker, say so plainly and offer to draft one from
   whatever details the user can share (URL, menu path, fees, processing time) rather than
   guessing at broker-specific UI.
3. Walk through the 3 generic steps with that broker's specific submission details filled
   in (URL/menu path, processing time, fee, one-journal-per-symbol limits, the currency
   settlement setting).
4. Remind the user this is not instant — most brokers take multiple business days
   (settlement + journal processing) — so timing matters if the CAD/USD is needed by a
   specific date.
5. Note that until the journal completes, the account will show DLR.U or DLR.TO units
   (not the target-currency cash) — this is expected mid-process state, not an error, if
   the user is checking their portfolio sync in the meantime.

---

## Common Failures

- **Confusing which symbol to buy first.** Buy the unit denominated in the currency you
  *currently hold*, journal to the unit denominated in the currency you *want*. Reversing
  this means buying a currency you don't have cash for.
- **Forgetting the currency-settlement preference.** If the account auto-converts on
  trade settlement, the broker's own FX spread gets applied before Norbert's Gambit ever
  has a chance to help — check this setting first, every time, for every broker.
- **Assuming it's instant.** Share settlement (1-2 days) must complete before the journal
  request can even be submitted; the journal itself then takes further business days.
  Don't diagnose a "missing" conversion as broken before checking the broker's stated
  processing window.
