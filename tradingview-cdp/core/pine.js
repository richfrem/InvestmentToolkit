/**
 * pine.js — TradingView Pine Script editor automation via CDP
 *
 * Provides inject/read/remove operations on the Pine Editor and Data Window.
 * Functions accept an explicit CDP client for testability; production callers
 * should pass the result of getClient() from connection.js.
 *
 * Inject flow (confirmed via live DOM probing 2026-05-17, TV Desktop):
 *   1. Open Pine Editor via [data-name="pine-dialog-button"]
 *   2. If current tab is read-only (3rd-party script), click "+" in tab bar
 *      to create a blank user-owned tab — this keeps the panel open, unlike
 *      More → New tab which toggles the panel closed.
 *   3. Inject content via executeEdits (fires onDidChangeModelContent so TV
 *      recompiles; setValue() is silent and TV may not recompile).
 *   4. Click "Add to chart" (new/blank tabs never show a save modal).
 *
 * process.exit() is NOT needed here — the CLI router (execute() in router.js)
 * handles exit after awaiting the handler result.
 */

/**
 * Inject a Pine Script into the active TradingView chart.
 *
 * Args:
 *   client: CDP client instance (from connection.js getClient())
 *   scriptContent: Pine Script v5/v6 source string
 *
 * Returns:
 *   { success: true } on success
 *   { success: false, error: string } on failure
 */
export async function injectPineScript(client, scriptContent) {
  try {
    const safeContent = JSON.stringify(scriptContent);

    // 1. Open Pine Editor if not already visible
    const openResult = await client.Runtime.evaluate({
      expression: `(function() {
        var ed = document.querySelector('.pine-editor-monaco');
        if (ed && ed.offsetParent) return JSON.stringify({ alreadyOpen: true });
        var btn = document.querySelector('[data-name="pine-dialog-button"]');
        if (!btn) return JSON.stringify({ error: 'pine-dialog-button not found' });
        btn.click();
        return JSON.stringify({ clicked: true });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const openData = JSON.parse(openResult.result.value);
    if (openData.error) throw new Error(openData.error);
    if (openData.clicked) await new Promise(r => setTimeout(r, 900));

    // 2. If current tab is read-only (3rd-party script), open a new blank tab
    //    using the "+" button in the Pine Editor tab bar.
    //    "+" stays in panel-open state; More→"New tab" toggles panel closed.
    const tabResult = await client.Runtime.evaluate({
      expression: `(function() {
        // Check for read-only banner
        var readOnly = [...document.querySelectorAll('*')].some(function(el) {
          return el.offsetParent && el.textContent.includes('This script is read-only');
        });
        if (!readOnly) return JSON.stringify({ needsNewTab: false });

        // Find the "+" button in the Pine Editor tab bar.
        // Walk up from Monaco editor to find the tab container, then look for "+" button.
        var edEl = document.querySelector('.pine-editor-monaco');
        if (!edEl) return JSON.stringify({ needsNewTab: true, error: 'no monaco for tab search' });

        var el = edEl;
        for (var i = 0; i < 20; i++) {
          el = el.parentElement;
          if (!el) break;
          // "+" tab button: button inside tab bar area, often with title "New tab", "Add tab", or text "+"
          var plusBtn = [...el.querySelectorAll('button')].find(function(b) {
            if (!b.offsetParent) return false;
            var t = b.textContent.trim();
            var title = (b.title || '').toLowerCase();
            return t === '+' || title.includes('new tab') || title.includes('add tab');
          });
          if (plusBtn) {
            plusBtn.click();
            return JSON.stringify({ needsNewTab: true, plusClicked: true, depth: i });
          }
        }
        return JSON.stringify({ needsNewTab: true, plusNotFound: true });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const tabData = JSON.parse(tabResult.result.value);
    if (tabData.needsNewTab) {
      if (tabData.plusNotFound) {
        // Fallback: More → New tab, then re-open panel
        await client.Runtime.evaluate({
          expression: `(function() {
            var edEl = document.querySelector('.pine-editor-monaco');
            if (!edEl) return;
            var el = edEl;
            for (var i = 0; i < 15; i++) {
              el = el.parentElement;
              if (!el) break;
              var mb = el.querySelector('button[title="More"]');
              if (mb && mb.offsetParent) { mb.click(); return; }
            }
          })()`,
          returnByValue: true,
          awaitPromise: false,
        });
        await new Promise(r => setTimeout(r, 500));
        await client.Runtime.evaluate({
          expression: `[...document.querySelectorAll('[role="menuitem"]')].find(el => el.offsetParent && el.textContent.trim() === 'New tab')?.click()`,
          returnByValue: true,
          awaitPromise: false,
        });
        await new Promise(r => setTimeout(r, 500));
        // Re-open panel (More→New tab toggles it closed)
        await client.Runtime.evaluate({
          expression: `document.querySelector('[data-name="pine-dialog-button"]')?.click()`,
          returnByValue: true,
          awaitPromise: false,
        });
      }
      // Wait for blank tab's Monaco editor to fully initialize
      await new Promise(r => setTimeout(r, 1500));
    }

    // 3. Inject via executeEdits — fires onDidChangeModelContent so TV recompiles.
    //    editor.focus() ensures the blank tab's editor is active before edits.
    const injectResult = await client.Runtime.evaluate({
      expression: `(function() {
        var script = ${safeContent};
        var edEl = document.querySelector('.pine-editor-monaco');
        if (!edEl) return JSON.stringify({ success: false, error: 'pine-editor-monaco not found' });

        var el = edEl;
        var fk = null;
        for (var depth = 0; depth < 5; depth++) {
          el = el.parentElement;
          if (!el) break;
          fk = Object.keys(el).find(function(k) { return k.startsWith('__reactFiber'); });
          if (fk) break;
        }
        if (!fk) return JSON.stringify({ success: false, error: 'React fiber not found within 5 ancestors' });

        try {
          var fiber = el[fk].return;
          var controller = fiber.memoizedState.memoizedState.current;
          var editor = controller._editor;
          if (!editor || typeof editor.getModel !== 'function') {
            return JSON.stringify({ success: false, error: 'Monaco editor not found via fiber' });
          }
          var model = editor.getModel();
          var fullRange = model.getFullModelRange();
          editor.focus();
          editor.executeEdits('pine-inject', [{ range: fullRange, text: script, forceMoveMarkers: true }]);
          return JSON.stringify({ success: true, method: 'executeEdits', preview: editor.getValue().substring(0, 50) });
        } catch (e) {
          return JSON.stringify({ success: false, error: e.message });
        }
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    const injectData = JSON.parse(injectResult.result.value);
    if (!injectData.success) throw new Error(injectData.error || 'Monaco injection failed');

    // 4. Wait for TV to recompile the injected script, then click "Add to chart".
    //    New/blank tabs show "Add to chart" (no save prefix) so no modal appears.
    await new Promise(r => setTimeout(r, 1200));
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

    // 5. Wait for indicator to load onto chart
    await new Promise(r => setTimeout(r, 1200));

    return { success: true };
  } catch (e) {
    return { success: false, error: e.message || 'Pine inject failed' };
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
