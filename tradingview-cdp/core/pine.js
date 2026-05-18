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

    // 4. Wait for TV to recompile, then click "Add to chart" OR "Update on chart".
    //    New/blank tabs show "Add to chart"; user-owned tabs that had a prior script
    //    show "Update on chart". Both mean "put this script on the chart now".
    await new Promise(r => setTimeout(r, 1200));
    const clickResult = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = [...document.querySelectorAll('button')].find(function(b) {
          return b.offsetParent && /(?:add|update).*(?:to|on).*chart/i.test(b.textContent + b.title);
        });
        if (btn) { btn.click(); return JSON.stringify({ clicked: true, text: btn.textContent.trim() }); }
        return JSON.stringify({ clicked: false });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    const clickData = JSON.parse(clickResult.result.value);
    if (!clickData.clicked) {
      // Fallback: try title-based match
      await client.Runtime.evaluate({
        expression: `(function() {
          var btn = document.querySelector('[title="Update on chart"], [title="Add to chart"]');
          if (btn && btn.offsetParent) btn.click();
        })()`,
        returnByValue: true,
        awaitPromise: false,
      });
    }

    // 4.5. Handle "Cannot add a script with unsaved changes to chart" save modal.
    //      Appears when a user-owned tab already has prior unsaved content.
    //      Click "Save and add to chart" to save the new script and add it.
    await new Promise(r => setTimeout(r, 700));
    await client.Runtime.evaluate({
      expression: `(function() {
        // Primary: "Save and add to chart" button
        var confirmBtn = [...document.querySelectorAll('button')].find(function(b) {
          return b.offsetParent && /save.*and.*add|save.*chart/i.test(b.textContent);
        });
        if (confirmBtn) { confirmBtn.click(); return; }
        // Fallback: any visible dialog with a Save/OK button
        var modal = [...document.querySelectorAll('[class*="dialog"], [role="dialog"]')]
          .find(function(m) { return m.offsetParent; });
        if (!modal) return;
        var saveBtn = [...modal.querySelectorAll('button')].find(function(b) {
          var t = b.textContent.trim().toLowerCase();
          return t.includes('save') || t === 'ok';
        });
        if (saveBtn) saveBtn.click();
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    // 5. Wait for indicator to load onto chart
    await new Promise(r => setTimeout(r, 1500));

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
        // TradingView "Object tree and data window" panel — data-name="object_tree"
        var dw = document.querySelector('[class*="widgetbar-widget-object_tree"]');
        var items = {};
        if (dw && dw.offsetParent) {
          dw.querySelectorAll('[data-test-id-value-title]').forEach(function(el) {
            var key = el.getAttribute('data-test-id-value-title') || el.textContent.trim();
            var itemEl = el.closest('[class]');
            var valueEl = itemEl ? itemEl.nextElementSibling : null;
            if (!valueEl) valueEl = el.parentElement ? el.parentElement.querySelector('span') : null;
            var val = valueEl ? valueEl.textContent.trim() : '';
            if (key) items[key] = val;
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

/**
 * Save the current Pine Script to TradingView's personal library.
 *
 * Sends Cmd+S / Ctrl+S within the Pine Editor context. Handles the "Save as"
 * naming dialog if the script has never been saved before.
 *
 * Args:
 *   client: CDP client instance
 *   scriptName: display name to save under (used if naming dialog appears)
 *
 * Returns:
 *   { success: true, name: string, action: 'saved' | 'named-and-saved' }
 *   { success: false, error: string }
 */
export async function savePineToLibrary(client, scriptName) {
  try {
    const safeName = JSON.stringify(String(scriptName || 'Untitled Script').trim());

    // 1. Ensure Pine Editor is open/focused
    const edCheck = await client.Runtime.evaluate({
      expression: `(function() {
        var ed = document.querySelector('.pine-editor-monaco');
        if (ed && ed.offsetParent) return JSON.stringify({ open: true });
        var btn = document.querySelector('[data-name="pine-dialog-button"]');
        if (btn) { btn.click(); return JSON.stringify({ opened: true }); }
        return JSON.stringify({ open: false });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const edData = JSON.parse(edCheck.result.value);
    if (edData.opened) await new Promise(r => setTimeout(r, 800));

    // 2. Send Cmd+S / Ctrl+S to save
    await client.Runtime.evaluate({
      expression: `(function() {
        var edEl = document.querySelector('.pine-editor-monaco');
        if (edEl) edEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        var isMac = /mac/i.test(navigator.platform);
        document.dispatchEvent(new KeyboardEvent('keydown', {
          key: 's', code: 'KeyS', metaKey: isMac, ctrlKey: !isMac, bubbles: true, cancelable: true,
        }));
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 700));

    // 3. Handle "Save as" naming dialog if it appeared
    const dialogResult = await client.Runtime.evaluate({
      expression: `(function() {
        var input = [...document.querySelectorAll('input')].find(function(i) {
          return i.offsetParent && (i.placeholder || '').toLowerCase().includes('name');
        });
        if (!input) return JSON.stringify({ dialog: false });
        input.focus(); input.select();
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, ${safeName});
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        return JSON.stringify({ dialog: true });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const dialogData = JSON.parse(dialogResult.result.value);

    if (dialogData.dialog) {
      await new Promise(r => setTimeout(r, 300));
      // Confirm with Save/OK button
      await client.Runtime.evaluate({
        expression: `(function() {
          var btn = [...document.querySelectorAll('button')].find(function(b) {
            if (!b.offsetParent) return false;
            var t = b.textContent.trim().toLowerCase();
            return t === 'save' || t === 'ok';
          });
          if (btn) { btn.click(); return; }
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        })()`,
        returnByValue: true, awaitPromise: false,
      });
      await new Promise(r => setTimeout(r, 600));
      return { success: true, name: scriptName, action: 'named-and-saved' };
    }

    return { success: true, name: scriptName, action: 'saved' };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
