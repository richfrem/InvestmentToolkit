# ADR-035: Recent-trade context and Questrade trade import

Date: 2026-10-08
Status: Proposed

## Problem

The canonical action (ADR-032) is recomputed from price and fair value alone. A
position the owner trimmed this week keeps reading TRIM while any shares remain
above the band, with no sign the trade happened. The trade log could not help:
executed broker trades were never written to it. The Questrade activities skill
only displays trades in chat, and the newest `trade_log_entry` rows were
cancelled entries from May.

## Decision

1. `plugins/questrade/scripts/questrade_trades_import.py` writes executed
   Questrade trades to `trade_log_entry` as `filled`, `source = questrade` rows.
   The Questrade MCP is only callable by an agent, so the agent stages a payload
   and the script persists it, the same pattern as `questrade_sync.py`. Entry ids
   are derived from the broker's fill id, or from the fill's details when there is
   none, so re-imports never duplicate. Existing rows are skipped untouched, which
   preserves owner edits. Invalid trades are rejected with a reason; nothing is
   estimated.
2. `trade_log_entry_repository.list_filled_trades_since()` is the one query for
   executed trades in a date range. Only `filled` rows count.
3. `plugins/portfolio-advisor/scripts/recent_trades.py` summarises filled trades
   in the last `RECENT_TRADE_DAYS` (14) and classifies them against the action:
   ACTED (a TRIM/EXIT with sells, or ACCUMULATE/INITIATE with buys), OPPOSED (the
   opposite trade), RECENT (a trade under a neutral action) or NONE. Every
   `recommendation.py` record carries it as `recent_trades`.
4. Both holdings tables show a recent-trade tag beside the action. The
   `questrade-sync-portfolio` skill imports trades with every sync, and
   `daily-loop` and `weekly-review` route to it when a Questrade session is
   connected.

5. Order type, limit price and, for market orders only, the order time come from
   `get_order_history`. The time is stored in `trade_date` as an ISO timestamp in
   US Eastern time whose first ten characters are always the trade date, so every
   reader that compares or slices the date keeps working and no schema migration
   is needed. Questrade's `lastModified` is not a fill time, so it is never used
   for limit orders.
6. The importer rejects symbols that are not already investments unless told
   otherwise, because the activity feed includes broker-only symbols.
7. The Trade Log page orders by trade date, shows the 100 newest rows with a
   "Show all" control, shows fill price and total on the All tab, reports the
   newest executed trade, and offers the `/questrade-sync-portfolio` command as a
   reminder chip. Executed trades cannot be fetched by a page button: the
   Questrade connection exists only in an agent session with the owner signed in.

## Consequences

- The action rule is unchanged: a trimmed position still reads TRIM, now with
  "Sold 3 · Oct 6" beside it. Suppressing or resizing the action after a trade is
  a separate policy decision.
- Questrade stays an optional augment (local-broker-augment-policy): the core
  reads only `trade_log_entry`, which manual and TradingView-logged entries also
  fill.
- A planned entry and its later imported fill appear as two rows; reconciling
  them is not part of this decision.
