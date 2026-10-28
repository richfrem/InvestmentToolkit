# Reading and driving TradingView lists reliably

What goes wrong when automation reads or edits TradingView watchlists and positions through the page, and the rules that keep it right. Read this before changing any code that reads a list, a positions table or the open-list dialog.

## Contents

- [Rows are drawn only when visible](#rows-are-drawn-only-when-visible) · [Selectors](#selectors) · [One copy per list](#one-copy-per-list) · [Symbol spelling](#symbol-spelling) · [Prices outside regular hours](#prices-outside-regular-hours) · [Validation order](#validation-order)

## Rows are drawn only when visible

- TradingView draws only the rows in view. A read of the page returns a fraction of a long list, and every symbol it misses looks unquoted.
- Read by scrolling the list container from top to bottom and merging rows by their position, then restore the scroll position.
- Check the row count against the list's own count (the "Positions N" badge for positions). An unscrolled read is never evidence that a ticker is missing or unquoted.

## Selectors

- Class names carry a hashed suffix (`symbol-XXXXXXXX`, `container-XXXXXXXX`) that changes with TradingView releases, so a selector built on one silently matches nothing and fails as "not found".
- Match rows by stable attributes (`data-symbol-short`) or by a class prefix (`[class*="symbolNameText-"]`). A test should fail if a hashed row class is used.
- Scroll a row into view before taking its coordinates; an off-screen row has none.

## One copy per list

- TradingView accepts several lists with the same name. Creating a list on every sync adds a copy each time.
- Creating must be idempotent: if the name exists, open it. Opening a name that exists more than once must stop and report it, not pick one.
- There are two lists, the full watchlist and the portfolio list, one copy each. Deleting extra copies is the owner's action.

## Symbol spelling

- The broker, TradingView and the database spell some tickers differently (a fund can be `PSU.U`, `PSU.U.TO`, `PSU-U` or `PSU-U.TO`).
- Normalize only through `ticker_aliases.normalize_ticker`, compare in that canonical form, and use TradingView's spelling only when talking to TradingView (for example when removing a row). A second alias map causes rows that look extra and rows that look missing.

## Prices outside regular hours

- The watchlist shows a session-aware price (extended or overnight) after the close, while a broker's total marks positions on the regular session. A small gap between a total built from watchlist prices and the broker total is expected then; judge it against the broker check tolerance, not against zero.

## Validation order

1. Positions and share counts in each account against the broker.
2. The full watchlist against the database: every ticker present, none extra.
3. Prices from the watchlist.
4. Report every unpriced or stale ticker by name; a partial refresh is never reported as a success.
