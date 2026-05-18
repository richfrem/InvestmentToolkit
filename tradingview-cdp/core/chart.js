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
        // TradingView "Object tree and data window" panel — data-name="object_tree"
        var dw = document.querySelector('[class*="widgetbar-widget-object_tree"]');
        if (!dw || !dw.offsetParent) {
          return JSON.stringify({ success: false, error: 'Data Window panel not visible — open it via View > Data Window' });
        }

        // Read items via stable data-test-id-value-title attribute (TV's semantic hook)
        var items = {};
        dw.querySelectorAll('[data-test-id-value-title]').forEach(function(el) {
          var key = el.getAttribute('data-test-id-value-title') || el.textContent.trim();
          var itemEl = el.closest('[class]');
          var valueEl = itemEl ? itemEl.nextElementSibling : null;
          if (!valueEl) valueEl = el.parentElement ? el.parentElement.querySelector('span') : null;
          var val = valueEl ? valueEl.textContent.trim() : '';
          if (key) items[key] = val;
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

/**
 * Open the TradingView Data Window panel if not already visible.
 *
 * Strategy: check if visible, then try right-sidebar toggle button,
 * then fall back to Alt+W keyboard shortcut.
 *
 * @param {object} client - CDP client instance
 * @returns {{ success: true, wasAlreadyOpen: boolean } | { success: false, error: string }}
 */
export async function openDataWindow(client) {
  try {
    // TradingView uses "Object tree and data window" panel — data-name="object_tree"
    const DW_PANEL_SEL = '[class*="widgetbar-widget-object_tree"]';
    const DW_BTN_SEL = '[data-name="object_tree"]';

    const isVisible = async () => {
      const r = await client.Runtime.evaluate({
        expression: `(function() {
          var dw = document.querySelector(${JSON.stringify(DW_PANEL_SEL)});
          return JSON.stringify({ visible: !!(dw && dw.offsetParent) });
        })()`,
        returnByValue: true,
        awaitPromise: false,
      });
      return JSON.parse(r.result.value).visible;
    };

    // 1. Check if already visible — if so, still ensure we're on "Data window" tab
    if (await isVisible()) {
      await client.Runtime.evaluate({
        expression: `(function() {
          var tab = document.querySelector('button[id="data-window"]');
          if (tab && tab.getAttribute('aria-selected') !== 'true') tab.click();
        })()`,
        returnByValue: true,
        awaitPromise: false,
      });
      await new Promise(r => setTimeout(r, 400));
      return { success: true, wasAlreadyOpen: true };
    }

    // 2. Click the right-sidebar toggle button, fall back to Alt+W
    await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector(${JSON.stringify(DW_BTN_SEL)});
        if (btn) { btn.click(); return; }
        // Fallback: Alt+W shortcut
        document.dispatchEvent(
          new KeyboardEvent('keydown', { key: 'w', altKey: true, bubbles: true })
        );
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    await new Promise(r => setTimeout(r, 800));

    // 3. Verify it opened
    if (!(await isVisible())) {
      return {
        success: false,
        error: 'Data Window did not open — click "Object tree and data window" in TV\'s right sidebar, then re-run',
      };
    }

    // 4. Switch to the "Data window" tab (panel defaults to "Object tree" tab)
    await client.Runtime.evaluate({
      expression: `(function() {
        var tab = document.querySelector('button[id="data-window"]');
        if (tab && tab.getAttribute('aria-selected') !== 'true') tab.click();
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 400));
    return { success: true, wasAlreadyOpen: false };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Save (create or switch to) a named TradingView chart layout.
 *
 * Idempotent: if already on the named layout, saves in-place and returns.
 * If the layout exists in the dropdown's recently-used list, switches to it.
 * Otherwise creates it via Manage layouts → "Create new layout…" → dialog.
 *
 * @param {object} client - CDP client instance
 * @param {string} [name] - layout name (default: 'agent-layout')
 * @returns {{ success: true, layoutName: string, action: string } | { success: false, error: string }}
 */
export async function saveLayout(client, name) {
  try {
    const targetName = name || 'agent-layout';
    const safeName = JSON.stringify(targetName);

    // 0. Already on this layout? — just Cmd+S and return
    const activeCheck = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = [...document.querySelectorAll('button')].find(function(b) {
          return (b.getAttribute('aria-label') || '').includes('Active layout:');
        });
        if (!btn) return JSON.stringify({ activeLayout: null });
        var m = (btn.getAttribute('aria-label') || '').match(/Active layout:\\s*(.+)/);
        return JSON.stringify({ activeLayout: m ? m[1].trim() : null });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const { activeLayout } = JSON.parse(activeCheck.result.value);
    if (activeLayout === targetName) {
      await client.Runtime.evaluate({
        expression: `(function() {
          var isMac = /mac/i.test(navigator.platform);
          document.body.dispatchEvent(new KeyboardEvent('keydown', {
            key: 's', code: 'KeyS', metaKey: isMac, ctrlKey: !isMac, bubbles: true, cancelable: true,
          }));
        })()`,
        returnByValue: true, awaitPromise: false,
      });
      await new Promise(r => setTimeout(r, 500));
      return { success: true, layoutName: targetName, action: 'saved' };
    }

    // 1. Open "Manage layouts" dropdown
    await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('[data-name="save-load-menu"]') ||
          [...document.querySelectorAll('button')].find(function(b) {
            return b.offsetParent && (b.getAttribute('aria-label') || '').includes('Manage layouts');
          });
        if (btn) btn.click();
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 700));

    // 2+3. In a single eval (dropdown may close between calls):
    //      switch if exists, otherwise click "Create new layout…"
    const menuResult = await client.Runtime.evaluate({
      expression: `(function() {
        var target = ${safeName};

        // Switch if the layout exists in recently-used
        var link = [...document.querySelectorAll('a')].find(function(a) {
          return a.isConnected && a.textContent.trim().startsWith(target);
        });
        if (link) { link.click(); return JSON.stringify({ action: 'switched' }); }

        // Not found — click "Create new layout…"
        var el = document.querySelector('[aria-label="Create new layout"]') ||
                 document.querySelector('[aria-label="Create new layout\\u2026"]') ||
                 [...document.querySelectorAll('*')].find(function(e) {
                   var t = e.textContent.trim();
                   return e.isConnected && (t === 'Create new layout…' || t === 'Create new layout...');
                 });
        if (!el) return JSON.stringify({ action: 'notFound' });
        (el.closest('button') || el.closest('a') || el).click();
        return JSON.stringify({ action: 'create' });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const { action: menuAction } = JSON.parse(menuResult.result.value);

    if (menuAction === 'switched') {
      await new Promise(r => setTimeout(r, 800));
      return { success: true, layoutName: targetName, action: 'switched' };
    }
    if (menuAction === 'notFound') {
      return { success: false, error: 'Could not find "Create new layout" in the Manage layouts menu' };
    }
    // menuAction === 'create' — dialog should now be open
    await new Promise(r => setTimeout(r, 800));

    // 4. Fill name in "Create layout" dialog (React setter required)
    await client.Runtime.evaluate({
      expression: `(function() {
        var input = [...document.querySelectorAll('input')].find(function(i) {
          return i.isConnected && i.offsetParent;
        });
        if (!input) return;
        input.focus(); input.select();
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, ${safeName});
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 400));

    // 5. Click "Create" button
    await client.Runtime.evaluate({
      expression: `(function() {
        var btn = [...document.querySelectorAll('button')].find(function(b) {
          return b.offsetParent && b.textContent.trim() === 'Create';
        });
        if (btn) { btn.click(); return; }
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 1000));

    return { success: true, layoutName: targetName, action: 'created' };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// ── Chart type map — friendly alias → TV aria-label ───────────────────────
// Note: TV Desktop has no "Candlestick" button — it is the default type.
// Use alias 'candle'/'candlestick' to trigger the "Undo change series style" button,
// which reverts to the last known default (candlestick).
const CHART_TYPE_LABELS = {
  candle: '__undo__',
  candlestick: '__undo__',
  bars: 'Bars',
  hollow: 'Hollow candles',
  'hollow-candle': 'Hollow candles',
  'volume-candle': 'Volume candles',
  line: 'Line',
  'line-markers': 'Line with markers',
  step: 'Step line',
  area: 'Area',
  hlc: 'HLC area',
  baseline: 'Baseline',
  columns: 'Columns',
  'high-low': 'High-low',
  renko: 'Renko',
  'line-break': 'Line break',
  kagi: 'Kagi',
  'point-figure': 'Point & figure',
  range: 'Range',
  'heikin-ashi': 'Heikin Ashi',
  ha: 'Heikin Ashi',
};

/**
 * Change the active chart type (candle style).
 *
 * Args:
 *   client: CDP client instance
 *   type: friendly name — e.g. "heikin-ashi", "line", "area", "renko",
 *         or any TV aria-label like "Hollow candles"
 *
 * Returns:
 *   { success: true, type: string }
 *   { success: false, error: string }
 */
export async function changeChartType(client, type) {
  try {
    const key = String(type).trim().toLowerCase().replace(/\s+/g, '-');
    const label = CHART_TYPE_LABELS[key] || String(type).trim();
    const safeLabel = JSON.stringify(label);

    // 'candle'/'candlestick': TV has no explicit button — revert via Undo
    if (label === '__undo__') {
      await client.Runtime.evaluate({
        expression: `(function() {
          var btn = document.querySelector('button[aria-label="Undo change series style"]') ||
            [...document.querySelectorAll('button')].find(function(b) {
              return b.offsetParent && (b.getAttribute('aria-label') || '').includes('Undo change series');
            });
          if (btn) btn.click();
        })()`,
        returnByValue: true, awaitPromise: false,
      });
      await new Promise(r => setTimeout(r, 500));
      return { success: true, type: 'Candlestick (reverted)' };
    }

    const result = await client.Runtime.evaluate({
      expression: `(function() {
        var label = ${safeLabel};
        var btn = document.querySelector('button[aria-label="' + label + '"]') ||
          [...document.querySelectorAll('button')].find(function(b) {
            return b.offsetParent && (b.getAttribute('aria-label') || '').toLowerCase() === label.toLowerCase();
          });
        if (!btn) return JSON.stringify({ success: false, error: 'Chart type button not found: ' + label });
        btn.click();
        return JSON.stringify({ success: true, type: label });
      })()`,
      returnByValue: true, awaitPromise: false,
    });

    const data = JSON.parse(result.result.value);
    if (data.success) await new Promise(r => setTimeout(r, 500));
    return data;
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Change the active chart symbol.
 *
 * Strategy: click the "Change symbol" button in the chart header, type the
 * symbol in the search box that appears, then confirm with Enter.
 *
 * Args:
 *   client: CDP client instance
 *   symbol: ticker string — e.g. "AAPL", "TSLA", "NVDA"
 *
 * Returns:
 *   { success: true, symbol: string }
 *   { success: false, error: string }
 */
export async function changeSymbol(client, symbol) {
  try {
    const safeSymbol = JSON.stringify(String(symbol).trim().toUpperCase());

    // 1. Click the symbol display button to open search
    const btnResult = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('button[aria-label="Change symbol"]') ||
          [...document.querySelectorAll('button')].find(function(b) {
            return b.offsetParent && (b.getAttribute('aria-label') || '').includes('Change symbol');
          });
        if (btn) { btn.click(); return JSON.stringify({ found: true }); }
        return JSON.stringify({ found: false });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    if (!JSON.parse(btnResult.result.value).found) {
      return { success: false, error: 'Symbol button not found in chart header' };
    }
    await new Promise(r => setTimeout(r, 700));

    // 2. Type symbol into search input
    await client.Runtime.evaluate({
      expression: `(function() {
        var sym = ${safeSymbol};
        // TV symbol search input — try multiple selectors
        var input = document.querySelector('input[data-role="search"]') ||
          document.querySelector('[class*="search"] input') ||
          [...document.querySelectorAll('input')].find(function(i) {
            return i.offsetParent && i.type !== 'checkbox' && i.type !== 'radio';
          });
        if (!input) return;
        input.focus();
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, sym);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 900));

    // 3. Press Enter to confirm first result
    await client.Runtime.evaluate({
      expression: `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 800));

    return { success: true, symbol: String(symbol).trim().toUpperCase() };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Add a built-in TradingView indicator to the active chart.
 *
 * Opens the Indicators dialog, searches by name, and clicks the first result.
 *
 * Args:
 *   client: CDP client instance
 *   name: indicator name — e.g. "RSI", "MACD", "Bollinger Bands", "Volume"
 *
 * Returns:
 *   { success: true, added: string }
 *   { success: false, error: string }
 */
export async function addIndicator(client, name) {
  try {
    const safeName = JSON.stringify(name);

    // 1. Open Indicators dialog
    await client.Runtime.evaluate({
      expression: `document.querySelector('[data-name="open-indicators-dialog"]').click()`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 700));

    // 2. Search for indicator
    await client.Runtime.evaluate({
      expression: `(function() {
        var input = [...document.querySelectorAll('input')].find(function(i) {
          return i.offsetParent && i.placeholder === 'Search';
        });
        if (!input) return;
        input.focus();
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, ${safeName});
        input.dispatchEvent(new Event('input', { bubbles: true }));
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 900));

    // 3. Click first result
    const clickResult = await client.Runtime.evaluate({
      expression: `(function() {
        // Results appear as list items — find the first visible one
        var item = [...document.querySelectorAll('[role="option"], [class*="listItem"], [class*="item-"]')]
          .find(function(el) { return el.offsetParent && el.textContent.trim().length > 0; });
        if (item) {
          item.click();
          return JSON.stringify({ clicked: true, text: item.textContent.trim().substring(0, 50) });
        }
        return JSON.stringify({ clicked: false });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const data = JSON.parse(clickResult.result.value);
    await new Promise(r => setTimeout(r, 500));

    // 4. Close dialog
    await client.Runtime.evaluate({
      expression: `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 300));

    if (!data.clicked) return { success: false, error: `No results found for "${name}"` };
    return { success: true, added: data.text };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * List currently loaded indicators on the active chart.
 *
 * Reads indicator names from the chart legend (top-left overlay).
 *
 * Args:
 *   client: CDP client instance
 *
 * Returns:
 *   { success: true, indicators: string[] }
 */
export async function listIndicators(client) {
  try {
    const result = await client.Runtime.evaluate({
      expression: `(function() {
        var dw = document.querySelector('[class*="widgetbar-widget-object_tree"]');
        if (dw && dw.offsetParent) {
          var keys = [];
          dw.querySelectorAll('[data-test-id-value-title]').forEach(function(el) {
            var k = el.getAttribute('data-test-id-value-title') || el.textContent.trim();
            if (k) keys.push(k);
          });
          return JSON.stringify({ success: true, indicators: [...new Set(keys)], source: 'data-window' });
        }
        // Data Window not open — read from chart legend aria-labels
        var hideBtn = [...document.querySelectorAll('button[aria-label="Hide indicator legend"]')]
          .filter(b => b.offsetParent);
        var count = hideBtn.length;
        // Walk each hide-btn's parent to find the indicator name span
        var names = [];
        hideBtn.forEach(function(btn) {
          var row = btn.parentElement;
          if (!row) return;
          var spans = [...row.querySelectorAll('span, div')].filter(function(el) {
            return el.childElementCount === 0 && el.textContent.trim().length > 1;
          });
          if (spans.length > 0) names.push(spans[0].textContent.trim());
        });
        return JSON.stringify({ success: true, indicators: [...new Set(names)], count, source: 'legend', hint: 'Open Data Window for richer names' });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    return JSON.parse(result.result.value);
  } catch (e) {
    return { success: false, error: e.message };
  }
}
