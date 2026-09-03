# Evolution Log — TradingView Plugin

Append-only record of every self-evolution event. Written by the `self-evolution` skill.
Do not edit manually except to correct a factual error.

| Date | Tier | Failure | Patch | Edit Type | Outcome |
|------|------|---------|-------|-----------|---------|
| 2026-05-27 | Regression | Account selection dropdown option click failed (remained in previous TFSA account) | Changed `.click()` to dispatch sequence of `mousedown`, `mouseup`, and `click` MouseEvents to both `match` and `match.parentElement`. | Modified `selectAccount` in `trading.js` | Successfully switched account to RRSP and executed PSU.U order |
| 2026-06-08 | Tier 2 (Failure) | `addIndicator` clicked timezone display instead of indicator — `[class*="item-"]` matched a time element. Dialog not opening reliably because `.click()` opened timezone dropdown instead of Indicators dialog. Wrong result selected because `includes("rsi")` matched a longer title before RSI. | (1) Changed Indicators button click to `Input.dispatchMouseEvent` at `getBoundingClientRect()` center. (2) Changed result selector from `[class*="item-"]` to `div[class*="container-WeNdU0sq"]`. (3) Changed match priority to exact → first result (TV's top rank) → contains. | Modified `addIndicator` in `core/chart.js` | Indicators dialog opens reliably; correct indicator selected |
| 2026-06-08 | Tier 1 (Gap) | No `removeIndicator` function existed — could not remove indicators from chart via CDP. | Built `removeIndicator(client, name)` using mouseover dispatch to legend row + `button[aria-label="Remove"]` selector within ±15px cy band of legend title. Added `chart removeIndicator` command to `cli.js`. | Added `removeIndicator` to `core/chart.js` and routing to `cli.js` | Successfully removes named indicator from chart legend |
| 2026-06-08 | Tier 2 (Failure) | `addIndicator` fails with "no search input found" when Pine Editor dialog is open — Pine Editor class `editorBaseLayoutContainer-dialog-z_CXxRZA` overlays screen and blocks Indicators dialog. `pine-dialog-button` toggle had `aria-pressed=false` but dialog was still visible — unreliable state signal. | Documented workaround: after `pine inject` + `pine save`, click "Update on chart" button (title attr, matched by `/(?:add|update).*(?:to|on).*chart/i`) via `Input.dispatchMouseEvent`. No need to close Pine Editor first. Updated CLAUDE.md Pitfall 23 with this path. | Pattern change — document-only; no chart.js code change needed | Successfully added AI TA Levels v2 to chart via "Update on chart" button |

## 2026-07-01 — Tier 1 Gap: 15m timeframe not accessible via toolbar

**Tier: 1 (Gap)** — `chart timeframe 15` returns `"No interval dialog button found"`.

**Root cause:** TradingView toolbar only shows quick-access buttons (1s, 1m, 5m, 1h, 4h, D).
The 15m timeframe requires clicking the dropdown chevron ("v") to expand more options.
`chart.js` tries toolbar buttons and an interval dialog button — neither matches the dropdown.

**Workaround used:** Proceeded with 1m, 5m, 1H, 1D (sufficient for the analysis).

**Fix required:** In `tradingview-cdp/core/chart.js` `changeTimeframe()`, add Step 3:
click the "show more intervals" chevron button (`[data-name="time-interval-more"]` or
button following the last visible toolbar interval button), wait for the dropdown menu to
appear, then click the matching resolution row. Close the dropdown after selection.

**Standing permission:** Auto-approved to patch `tradingview-cdp/core/chart.js` for this fix.

## 2026-09-02 — Tier 1 Gap: Batch TA sweep lacked notification when DCF baseline aged past earnings cycle

**Tier: 1 (Gap)** — TA sweep did not alert when a ticker's fundamental DCF was over 90 days old (past a quarterly earnings release).
**Fix:** Added `analyzedAt` and `daysSinceDCF` tracking to `load_dcf` in `ta_sweep_batch.py`, triggering an `EARNINGS_DCF_DUE` flag and HITL reminder when `daysSinceDCF >= 90`.

