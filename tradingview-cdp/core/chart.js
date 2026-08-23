/**
 * chart.js - TradingView chart control and data extraction via CDP.
 * 
 * Purpose:
 *   Provides timeframe switching, symbol changes, layout saving, indicator loading/unloading,
 *   and Data Window values extraction via CDP.
 * 
 * Key Input Dependencies:
 *   None (reads live state from TradingView Desktop on port 9222 via CDP)
 * 
 * Key Output Dependencies:
 *   None (manipulates the active chart layouts in the user's browser)
 */

/**
 * Change the active chart timeframe.
 * 
 * Clicks the interval button in the chart header by matching
 * the resolution text (e.g., "D", "1D", "60", "240"). Falls back to the interval
 * dialog button if no direct match is found in the toolbar.
 *
 * @param {object} client - CDP client instance (from connection.js getClient())
 * @param {string|number} resolution - Timeframe string (e.g. "1D", "W", "60", "240")
 * @returns {Promise<object>} Status report containing success status and timeframe changed
 */
export async function changeTimeframe(client, resolution) {
  /**
   * Evaluates UI toolbar buttons matching the resolution, falls back to interval dropdown dialog,
   * clicks matching row, and closes dialog via Escape on failure.
   */
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
            var label = (b.getAttribute('aria-label') || '').toUpperCase();
            var dataVal = (b.getAttribute('data-value') || '').toUpperCase();
            
            // Match text ("1D", "D", "1H", "H")
            if (text === res || text === res.replace('1', '')) return true;
            // Match label ("1 DAY", "1 HOUR", "4 HOURS")
            if (label.includes(res)) return true;
            // Match data-value
            if (dataVal === res) return true;
            
            return false;
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
 * @param {object} client - CDP client instance
 * @returns {Promise<object>} Status report mapping indicator name keys to value strings
 */
export async function readDataWindow(client) {
  /**
   * Asserts the Data Window panel element is visible in the DOM, then uses
   * data-test-id semantic attribute queries to parse and accumulate loaded values.
   */
  try {
    const result = await client.Runtime.evaluate({
      expression: `(function() {
        // TradingView "Object tree and data window" panel — data-name="object_tree"
        var dw = document.querySelector('[class*="widgetbar-widget-object_tree"]');
        if (!dw || !dw.offsetParent) {
          return JSON.stringify({ success: false, error: 'Data Window panel not visible — open it via View > Data Window' });
        }

        // Read items via stable data-test-id-value-title attribute (TV's semantic hook)
        // or fallback to all visible rows
        var items = {};
        
        // Strategy 1: Data-test-id (Semantic)
        dw.querySelectorAll('[data-test-id-value-title]').forEach(function(el) {
          var key = el.getAttribute('data-test-id-value-title') || el.textContent.trim();
          var itemEl = el.closest('[class]');
          var valueEl = itemEl ? itemEl.nextElementSibling : null;
          if (!valueEl) valueEl = el.parentElement ? el.parentElement.querySelector('span') : null;
          var val = valueEl ? valueEl.textContent.trim() : '';
          if (key) items[key] = val;
        });

        // Strategy 2: Label/Value list (Structural Fallback)
        if (Object.keys(items).length < 5) {
           var rows = dw.querySelectorAll('[class*="item"]');
           rows.forEach(function(row) {
              var spans = row.querySelectorAll('span');
              if (spans.length >= 2) {
                 var key = spans[0].textContent.trim().replace(':', '');
                 var val = spans[1].textContent.trim();
                 if (key && !items[key]) items[key] = val;
              }
           });
        }
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
 * @returns {Promise<object>} Status report showing wasAlreadyOpen indicator
 */
export async function openDataWindow(client) {
  /**
   * Evaluates if object_tree widget is displayed, clicks sidebar button/triggers
   * Alt+W if closed, verifies visibility, and switches tab focus to "data-window".
   */
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
 * @returns {Promise<object>} Status report showing layoutName, action taken ('saved', 'switched', 'created')
 */
export async function saveLayout(client, name) {
  /**
   * Checks current active layout name, presses Cmd/Ctrl+S if matches, otherwise
   * clicks layout menu to switch or enters name and clicks "Create" in dialog.
   */
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
 * Friendly names mapped include: "heikin-ashi", "line", "area", "renko", or any
 * explicit TV aria-label like "Hollow candles".
 *
 * @param {object} client - CDP client instance
 * @param {string} type - Friendly chart type name
 * @returns {Promise<object>} Status report showing the changed chart type
 */
export async function changeChartType(client, type) {
  /**
   * Translates the chart type name into TV aria-label representation, clicks the layout
   * button with matching label, or clicks Undo if candle style has no button.
   */
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
 * @param {object} client - CDP client instance
 * @param {string} symbol - Ticker symbol string to search for (e.g. "NVDA")
 * @returns {Promise<object>} Status report showing the updated symbol
 */
export async function changeSymbol(client, symbol) {
  /**
   * Clicks 'Change symbol' toolbar button, focuses and fills the search input
   * with the target symbol name, and triggers Enter to submit.
   */
  try {
    const safeSymbol = JSON.stringify(String(symbol).trim().toUpperCase());

    // 1. Click the symbol display button to open search
    const btnResult = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('#header-toolbar-symbol-search') ||
          document.querySelector('button[aria-label="Change symbol"]') ||
          [...document.querySelectorAll('button')].find(function(b) {
            var label = (b.getAttribute('aria-label') || '').toLowerCase();
            return b.offsetParent && (label.includes('change symbol') || label.includes('symbol search'));
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
          document.querySelector('input[placeholder*="Symbol"]') ||
          document.querySelector('input[placeholder*="ISIN"]') ||
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
      expression: `(function() {
        var input = document.querySelector('input[placeholder*="Symbol"]') || 
                    document.querySelector('input[data-role="search"]');
        if (input) {
            input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, which: 13, bubbles: true }));
            input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        } else {
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        }
      })()`,
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
 * @param {object} client - CDP client instance
 * @param {string} name - Indicator name to load (e.g. "RSI")
 * @returns {Promise<object>} Status report showing the name of the added indicator
 */
export async function addIndicator(client, name) {
  /**
   * Dispatches left mouse click Center-coordinates of the Indicators button in the toolbar,
   * types search term, clicks the best-matching result row, and presses Escape.
   */
  try {
    const safeName = JSON.stringify(name);

    // 1. Get the Indicators button bounding rect for a reliable mouse-event click.
    //    JavaScript .click() doesn't always fire TradingView's React handler for this button;
    //    Input.dispatchMouseEvent at the computed center coordinates is the reliable path.
    const btnRect = await client.Runtime.evaluate({
      expression: `JSON.stringify((function() {
        var btn = [...document.querySelectorAll('button[data-name="open-indicators-dialog"]')]
          .find(function(b) { return b.offsetParent && b.textContent.trim() === 'Indicators'; });
        if (!btn) return null;
        var r = btn.getBoundingClientRect();
        return { cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) };
      })())`,
      returnByValue: true, awaitPromise: false,
    });
    const btnPos = JSON.parse(btnRect.result.value);
    if (!btnPos) return { success: false, error: 'Indicators button not found in toolbar' };

    // 2. Open Indicators dialog via mouse event (reliable; .click() is flaky on this button)
    await client.Input.dispatchMouseEvent({ type: 'mousePressed', x: btnPos.cx, y: btnPos.cy, button: 'left', clickCount: 1 });
    await client.Input.dispatchMouseEvent({ type: 'mouseReleased', x: btnPos.cx, y: btnPos.cy, button: 'left', clickCount: 1 });
    await new Promise(r => setTimeout(r, 1500));

    // 3. Type search term
    const typeResult = await client.Runtime.evaluate({
      expression: `(function() {
        var input = [...document.querySelectorAll('input')].find(function(i) {
          return i.offsetParent && (i.placeholder === 'Search' || i.placeholder === 'Find indicator...');
        });
        if (!input) return 'no-input';
        input.focus();
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, ${safeName});
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'typed';
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    if (typeResult.result.value === 'no-input') {
      return { success: false, error: `Indicators dialog did not open (no search input found for "${name}")` };
    }
    await new Promise(r => setTimeout(r, 1400));

    // 4. Click the best-matching result in the Indicators dialog.
    //    TV search ranks the most relevant indicator first — that is usually the right pick.
    //    Priority: (a) exact name match, (b) first result (TV's top match), (c) contains match.
    //    NOTE: all result rows share platform-WeNdU0sq so that class cannot distinguish built-in vs community.
    const clickResult = await client.Runtime.evaluate({
      expression: `(function() {
        var searchTerm = ${safeName}.toLowerCase();
        var all = [...document.querySelectorAll('div[class*="container-WeNdU0sq"]')]
          .filter(function(el) { return el.offsetParent && el.textContent.trim().length > 0; });
        // (a) exact text match (indicator name only — strip author/count suffix by checking start)
        var match = all.find(function(el) { return el.textContent.trim().toLowerCase() === searchTerm; })
          // (b) first result — TV ranks most relevant first
          || all[0]
          // (c) contains match as last resort
          || all.find(function(el) { return el.textContent.trim().toLowerCase().includes(searchTerm); });
        if (match) {
          match.click();
          return JSON.stringify({ clicked: true, text: match.textContent.trim().substring(0, 60) });
        }
        return JSON.stringify({ clicked: false });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const data = JSON.parse(clickResult.result.value);
    await new Promise(r => setTimeout(r, 600));

    // 5. Close dialog
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
 * Remove a named indicator from the active chart by clicking the legend Remove button.
 *
 * Strategy:
 *   1. Find the legend title element whose text matches `name` (class titleWrapper-l31H9iuA).
 *   2. Dispatch a synthetic mouseover to reveal the legend action buttons.
 *   3. Find the button with aria-label="Remove" in the same vertical band and click it.
 *
 * @param {object} client - CDP client instance
 * @param {string} name - Indicator name as shown in the chart legend (e.g. "RSI")
 * @returns {Promise<object>} Status report showing the name of the removed indicator
 */
export async function removeIndicator(client, name) {
  /**
   * Finds matching indicator title block in chart legend, dispatches a mouseMoved
   * hover center coordinate event to reveal buttons, and clicks the Remove button.
   */
  try {
    const safeName = JSON.stringify(name.toLowerCase());

    // 1. Find the legend title element matching the indicator name
    const findResult = await client.Runtime.evaluate({
      expression: `(function() {
        var target = [...document.querySelectorAll('[class*="titleWrapper-l31H9iuA"]')]
          .find(function(el) {
            return el.offsetParent && el.textContent.trim().toLowerCase().includes(${safeName});
          });
        if (!target) return JSON.stringify({ found: false });
        var r = target.getBoundingClientRect();
        return JSON.stringify({ found: true, x: r.x, y: r.y, cx: r.x + r.width / 2, cy: r.y + r.height / 2, text: target.textContent.trim() });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const pos = JSON.parse(findResult.result.value);
    if (!pos.found) return { success: false, error: `Indicator "${name}" not found in chart legend` };

    // 2. Physical mousemove to legend row — programmatic mouseover doesn't trigger TV's React hover
    await client.Input.dispatchMouseEvent({ type: 'mouseMoved', x: pos.cx, y: pos.cy });
    await new Promise(r => setTimeout(r, 600));

    // 3. Find Remove button in same vertical band — use Input.dispatchMouseEvent (TV ignores .click())
    const cy = pos.cy;
    const removeBtnPos = await client.Runtime.evaluate({
      expression: `(function() {
        var band = 25; // px tolerance above/below
        var btn = [...document.querySelectorAll('button[aria-label="Remove"]')]
          .find(function(el) {
            if (!el.offsetParent) return false;
            var r = el.getBoundingClientRect();
            return Math.abs((r.y + r.height / 2) - ${cy}) < band;
          });
        if (!btn) return JSON.stringify({ found: false });
        var r = btn.getBoundingClientRect();
        return JSON.stringify({ found: true, cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const removeBtn = JSON.parse(removeBtnPos.result.value);
    if (!removeBtn.found) return { success: false, error: `Remove button not found for "${name}" — try hovering the chart legend manually` };
    await client.Input.dispatchMouseEvent({ type: 'mousePressed', x: removeBtn.cx, y: removeBtn.cy, button: 'left', clickCount: 1 });
    await client.Input.dispatchMouseEvent({ type: 'mouseReleased', x: removeBtn.cx, y: removeBtn.cy, button: 'left', clickCount: 1 });
    const removeData = { clicked: true };

    return { success: true, removed: pos.text };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * List currently loaded indicators on the active chart.
 *
 * Reads indicator names from the chart legend (top-left overlay).
 *
 * @param {object} client - CDP client instance
 * @returns {Promise<object>} Status report mapping active indicators names list
 */
export async function listIndicators(client) {
  /**
   * Reads indicators from the Data Window if available, or falls back to scraping
   * indicator names out of the top-left chart legend DOM.
   */
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
        // Data Window not open — read from chart legend title elements
        var titleNodes = [...document.querySelectorAll('[class*="titleWrapper-"], [data-name="legend-series-item"]')];
        var names = [];
        titleNodes.forEach(function(el) {
          if (!el.offsetParent) return;
          var t = el.textContent.trim();
          if (t && t.length > 1 && isNaN(Number(t))) {
            names.push(t);
          }
        });
        var unique = [...new Set(names)];
        return JSON.stringify({ success: true, indicators: unique, count: unique.length, source: 'legend' });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    return JSON.parse(result.result.value);
  } catch (e) {
    return { success: false, error: e.message };
  }
}
