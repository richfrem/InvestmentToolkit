/**
 * pine.js — TradingView Pine Script editor automation via CDP
 *
 * Provides inject/read/remove operations on the Pine Editor and Data Window.
 * Functions accept an explicit CDP client for testability; production callers
 * should pass the result of getClient() from connection.js.
 *
 * Editor access path (confirmed live 2026-05-17, TV Desktop):
 *   - Open via: [data-name="pine-dialog-button"].click()
 *   - Editor el: .pine-editor-monaco (class stable across TV deployments so far)
 *   - Controller: parentElement.__reactFiber.return.memoizedState.memoizedState.current
 *   - Monaco instance: controller._editor  (has setValue / getValue / getModel)
 *   - Add to chart: button matching /add\s*to\s*chart/i text
 *
 * process.exit() is NOT needed here — the CLI router (execute() in router.js)
 * handles exit after awaiting the handler result.
 */

/**
 * Inject a Pine Script into the active TradingView chart.
 *
 * Args:
 *   client: CDP client instance (from connection.js getClient())
 *   scriptContent: Pine Script v5 source string
 *
 * Returns:
 *   { success: true } on success
 *   { success: false, error: string } on failure
 */
export async function injectPineScript(client, scriptContent) {
  try {
    const safeContent = JSON.stringify(scriptContent);

    // 1. Click the Pine Editor toggle button in the bottom bar
    const openResult = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('[data-name="pine-dialog-button"]');
        if (!btn) return JSON.stringify({ clicked: false, reason: 'button not found' });
        btn.click();
        return JSON.stringify({ clicked: true });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const openData = JSON.parse(openResult.result.value);
    if (!openData.clicked) throw new Error('Pine Editor tab not found');

    // Wait for Pine Editor panel to open and Monaco to initialize
    await new Promise(r => setTimeout(r, 900));

    // 2. Access Monaco editor via React fiber traversal
    //    Path: .pine-editor-monaco parent → __reactFiber → .return (depth 1)
    //          → memoizedState.memoizedState.current (state[0] ref = TV controller)
    //          → ._editor (Monaco ICodeEditor instance)
    const injectResult = await client.Runtime.evaluate({
      expression: `(function() {
        var script = ${safeContent};
        var edEl = document.querySelector('.pine-editor-monaco');
        if (!edEl) return JSON.stringify({ success: false, error: 'pine-editor-monaco not found' });

        var parent = edEl.parentElement;
        var fk = Object.keys(parent).find(function(k) { return k.startsWith('__reactFiber'); });
        if (!fk) return JSON.stringify({ success: false, error: 'React fiber not found on editor parent' });

        try {
          var fiber = parent[fk].return;
          var controller = fiber.memoizedState.memoizedState.current;
          var editor = controller._editor;
          if (!editor || typeof editor.setValue !== 'function') {
            return JSON.stringify({ success: false, error: 'Monaco editor._editor missing setValue' });
          }
          editor.setValue(script);
          return JSON.stringify({ success: true, method: 'fiber-controller-editor' });
        } catch (e) {
          return JSON.stringify({ success: false, error: e.message });
        }
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const injectData = JSON.parse(injectResult.result.value);
    if (!injectData.success) throw new Error(injectData.error || 'Monaco injection failed');

    // 3. Click "Add to chart"
    await new Promise(r => setTimeout(r, 400));
    await client.Runtime.evaluate({
      expression: `(function() {
        var btn = [...document.querySelectorAll('button')].find(function(b) {
          return b.offsetParent && /add\\s*to\\s*chart/i.test(b.textContent);
        });
        if (btn) btn.click();
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    // 4. Handle "unsaved changes" confirmation modal — click "Save and add to chart"
    await new Promise(r => setTimeout(r, 600));
    await client.Runtime.evaluate({
      expression: `(function() {
        // Modal appears when the editor has unsaved changes.
        // Button text is "Save and add to chart" — find and click it.
        var modalBtn = [...document.querySelectorAll('button')].find(function(b) {
          return b.offsetParent && /save\\s*and\\s*add/i.test(b.textContent);
        });
        if (modalBtn) { modalBtn.click(); return 'modal-dismissed'; }
        return 'no-modal';
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    // 5. Wait for indicator to load onto chart
    await new Promise(r => setTimeout(r, 1000));

    return { success: true };
  } catch (e) {
    return { success: false, error: 'Pine Editor not found' };
  }
}

/**
 * Read current indicator values from the TradingView Data Window.
 *
 * Args:
 *   client: CDP client instance
 *   indicatorName: display name of the indicator to read values for
 *
 * Returns:
 *   { success: true, data: object } with indicator key/value pairs
 *   { success: false, error: string } on failure
 */
export async function readIndicatorValues(client, indicatorName) {
  try {
    const result = await client.Runtime.evaluate({
      expression: `(function() {
        // Try Data Window panel — class names vary; text/structure-based fallback
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

        var items = {};
        if (dw) {
          var rows = dw.querySelectorAll('tr, [class*="row"]');
          rows.forEach(function(row) {
            var cells = row.querySelectorAll('td, [class*="cell"], [class*="value"]');
            if (cells.length >= 2) {
              var key = cells[0].textContent.trim();
              var val = cells[1].textContent.trim();
              if (key) items[key] = val;
            }
          });
        }
        return JSON.stringify(items);
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const data = JSON.parse(result.result.value || '{}');
    return { success: true, data };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Remove a named custom indicator from the active TradingView chart.
 *
 * Args:
 *   client: CDP client instance
 *   indicatorName: exact display name of the indicator to remove
 *
 * Returns:
 *   { success: true } on success
 *   { success: false, error: string } on failure
 */
export async function removePineScript(client, indicatorName) {
  try {
    const safeName = JSON.stringify(indicatorName);
    await client.Runtime.evaluate({
      expression: `(function() {
        // Find indicator in chart legend by name, click its × remove button
        var name = ${safeName};
        var legends = [...document.querySelectorAll('[class*="legend"], [class*="indicator"]')]
          .filter(function(el) {
            return el.offsetParent && el.textContent.includes(name);
          });
        if (legends.length === 0) return false;
        var removeBtn = legends[0].querySelector('[class*="remove"], [class*="close"], [title*="Remove"], [class*="delete"]');
        if (removeBtn) { removeBtn.click(); return true; }
        return false;
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    return { success: true };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
