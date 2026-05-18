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
 * Save the current TradingView chart layout.
 *
 * Strategy: look for a toolbar "Save" button, fall back to Meta+S / Ctrl+S.
 * If a naming modal appears (first-time save), fill the name and confirm.
 *
 * @param {object} client - CDP client instance
 * @param {string} [name] - optional layout name (used if a naming modal appears)
 * @returns {{ success: true, layoutName: string } | { success: false, error: string }}
 */
export async function saveLayout(client, name) {
  try {
    const safeName = name ? JSON.stringify(String(name)) : JSON.stringify('InvestmentToolkit');

    // 1. Click toolbar Save / cloud-save button, or fall back to Meta+S
    await client.Runtime.evaluate({
      expression: `(function() {
        var saveBtn = [...document.querySelectorAll('button, [role="button"]')].find(function(b) {
          if (!b.offsetParent) return false;
          var t = (
            b.title ||
            b.getAttribute('aria-label') ||
            b.getAttribute('data-tooltip') ||
            b.getAttribute('data-name') ||
            ''
          ).toLowerCase();
          return (t.includes('save') && (t.includes('layout') || t.includes('chart'))) ||
                 t === 'save';
        });
        if (saveBtn) { saveBtn.click(); return; }
        // Fallback: Cmd+S (Mac) or Ctrl+S (Windows/Linux)
        var isMac = /mac/i.test(navigator.platform);
        document.body.dispatchEvent(new KeyboardEvent('keydown', {
          key: 's', code: 'KeyS',
          metaKey: isMac, ctrlKey: !isMac,
          bubbles: true, cancelable: true,
        }));
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    await new Promise(r => setTimeout(r, 700));

    // 2. Check for a naming/confirm modal
    const modalResult = await client.Runtime.evaluate({
      expression: `(function() {
        var modal = [...document.querySelectorAll('[class*="modal"], [class*="dialog"], [role="dialog"]')]
          .find(function(m) {
            return m.offsetParent && m.textContent.toLowerCase().includes('save');
          });
        if (!modal) return JSON.stringify({ modalVisible: false });
        var input = modal.querySelector('input[type="text"], input:not([type="hidden"]):not([type="checkbox"])');
        return JSON.stringify({ modalVisible: true, hasInput: !!input });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const modalData = JSON.parse(modalResult.result.value);

    if (modalData.modalVisible) {
      if (modalData.hasInput) {
        // Fill the name using React's native input setter
        await client.Runtime.evaluate({
          expression: `(function() {
            var modal = [...document.querySelectorAll('[class*="modal"], [class*="dialog"], [role="dialog"]')]
              .find(function(m) { return m.offsetParent && m.textContent.toLowerCase().includes('save'); });
            if (!modal) return;
            var input = modal.querySelector('input[type="text"], input:not([type="hidden"]):not([type="checkbox"])');
            if (!input) return;
            input.focus();
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, ${safeName});
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
          })()`,
          returnByValue: true,
          awaitPromise: false,
        });
        await new Promise(r => setTimeout(r, 300));
      }

      // Click Save / OK / Confirm in the modal
      await client.Runtime.evaluate({
        expression: `(function() {
          var modal = [...document.querySelectorAll('[class*="modal"], [class*="dialog"], [role="dialog"]')]
            .find(function(m) { return m.offsetParent && m.textContent.toLowerCase().includes('save'); });
          if (!modal) return;
          var confirmBtn = [...modal.querySelectorAll('button')].find(function(b) {
            var t = b.textContent.trim().toLowerCase();
            return t === 'save' || t === 'ok' || t === 'confirm' || t === 'apply';
          });
          if (confirmBtn) { confirmBtn.click(); return; }
          modal.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        })()`,
        returnByValue: true,
        awaitPromise: false,
      });

      await new Promise(r => setTimeout(r, 500));
    }

    return { success: true, layoutName: name || 'saved' };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
