/**
 * chart.js — TradingView chart control and data extraction via CDP
 *
 * Provides timeframe switching and Data Window reading.
 * Functions accept an explicit CDP client for testability; production callers
 * should pass the result of getClient() from connection.js.
 *
 * Timeframe approach: clicks the interval button in the chart header by matching
 * the resolution text (e.g., "D", "1D", "60", "240"). Falls back to the interval
 * dialog button if no direct match is found in the toolbar.
 *
 * Data Window approach: traverses all visible rows in the Data Window panel
 * and returns every label/value pair as a flat object.
 *
 * process.exit() is NOT needed here — the CLI router (execute() in router.js)
 * handles exit after awaiting the handler result.
 */

/**
 * Change the active chart timeframe.
 *
 * Args:
 *   client: CDP client instance (from connection.js getClient())
 *   resolution: timeframe string — e.g. "1D", "D", "W", "60", "240", "15"
 *
 * Returns:
 *   { success: true, resolution: string } on success
 *   { success: false, error: string } on failure
 */
export async function changeTimeframe(client, resolution) {
  try {
    const safeRes = JSON.stringify(String(resolution).trim().toUpperCase());

    const result = await client.Runtime.evaluate({
      expression: `(function() {
        var res = ${safeRes};

        // 1. Try to find a toolbar interval button matching the resolution text.
        //    TV Desktop renders these as buttons inside a header/toolbar area.
        var toolbarSelectors = [
          '[class*="toolbar"] button',
          '[class*="header"] button',
          '[class*="chart-toolbar"] button',
        ];
        var btn = null;
        for (var si = 0; si < toolbarSelectors.length; si++) {
          var candidates = Array.from(document.querySelectorAll(toolbarSelectors[si]));
          btn = candidates.find(function(b) {
            var text = b.textContent.trim().toUpperCase();
            return text === res || text === res.replace('1', '') || b.getAttribute('data-value') === res;
          });
          if (btn && btn.offsetParent) break;
        }

        if (btn) {
          btn.click();
          return JSON.stringify({ success: true, resolution: res, method: 'toolbar-button' });
        }

        // 2. Fallback: open the interval dialog via the active chart header display.
        //    The interval display is typically a button showing the current resolution.
        var dialogSelectors = [
          '[data-name="time-interval"]',
          '[class*="interval-dialog-button"]',
          '[class*="timeframe"]',
        ];
        var dialogBtn = null;
        for (var di = 0; di < dialogSelectors.length; di++) {
          dialogBtn = document.querySelector(dialogSelectors[di]);
          if (dialogBtn && dialogBtn.offsetParent) break;
        }
        if (!dialogBtn) {
          return JSON.stringify({ success: false, error: 'No interval button found in toolbar or header' });
        }
        dialogBtn.click();

        // Wait a tick for the dialog/dropdown to render, then find the matching item.
        return JSON.stringify({ success: false, error: 'Interval dialog opened but async item selection not supported in sync eval — use the toolbar button path' });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const data = JSON.parse(result.result.value);
    if (data.success) return data;

    // 3. Async fallback: open dialog, wait, then click matching item.
    const asyncResult = await client.Runtime.evaluate({
      expression: `(async function() {
        var res = ${safeRes};
        var dialogSelectors = [
          '[data-name="time-interval"]',
          '[class*="interval-dialog-button"]',
          '[class*="timeframe"]',
        ];
        var dialogBtn = null;
        for (var di = 0; di < dialogSelectors.length; di++) {
          dialogBtn = document.querySelector(dialogSelectors[di]);
          if (dialogBtn && dialogBtn.offsetParent) break;
        }
        if (!dialogBtn) return JSON.stringify({ success: false, error: 'No interval dialog button found' });

        dialogBtn.click();
        await new Promise(function(r) { setTimeout(r, 500); });

        // Find the menu item matching the resolution
        var items = Array.from(document.querySelectorAll('[class*="menu"] [class*="item"], [class*="dropdown"] [class*="item"]'));
        var match = items.find(function(el) {
          var text = el.textContent.trim().toUpperCase();
          return text === res || text.startsWith(res + ' ');
        });
        if (match) {
          match.click();
          return JSON.stringify({ success: true, resolution: res, method: 'dialog-menu' });
        }
        // Close the dialog to avoid leaving UI in a bad state
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        return JSON.stringify({ success: false, error: 'Resolution "' + res + '" not found in interval menu' });
      })()`,
      returnByValue: true,
      awaitPromise: true,
    });

    return JSON.parse(asyncResult.result.value);
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Read all active indicator values from the TradingView Data Window panel.
 *
 * Traverses every visible row in the Data Window and returns all label/value
 * pairs as a flat object. Works with both built-in and custom indicators.
 *
 * Args:
 *   client: CDP client instance
 *
 * Returns:
 *   { success: true, data: object } keyed by indicator label
 *   { success: false, error: string } if the Data Window panel is not visible
 */
export async function readDataWindow(client) {
  try {
    const result = await client.Runtime.evaluate({
      expression: `(function() {
        var selectors = [
          '[class*="data-window"]',
          '[class*="dataWindow"]',
          '[class*="DataWindow"]',
        ];
        var dw = null;
        for (var i = 0; i < selectors.length; i++) {
          dw = document.querySelector(selectors[i]);
          if (dw && dw.offsetParent) break;
        }
        if (!dw) {
          return JSON.stringify({ success: false, error: 'Data Window panel not visible — open it via View > Data Window' });
        }

        var items = {};
        var rows = dw.querySelectorAll('tr, [class*="row"]');
        rows.forEach(function(row) {
          var cells = row.querySelectorAll('td, [class*="cell"], [class*="value"]');
          if (cells.length >= 2) {
            var key = cells[0].textContent.trim();
            var val = cells[1].textContent.trim();
            if (key) items[key] = val;
          }
        });
        return JSON.stringify({ success: true, data: items });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    return JSON.parse(result.result.value);
  } catch (e) {
    return { success: false, error: e.message };
  }
}
