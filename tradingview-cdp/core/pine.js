/**
 * pine.js - TradingView Pine Script editor automation via CDP.
 * 
 * Purpose:
 *   Automates operations inside the Pine Editor pane, enabling injection of custom indicators,
 *   saving scripts to the user's library, and reading open-source Pine Script source files.
 * 
 * Key Input Dependencies:
 *   None (reads live state from TradingView Desktop on port 9222 via CDP)
 * 
 * Key Output Dependencies:
 *   None (manipulates the user's active TradingView Pine Editor in the browser)
 *
 * Key Functions (Index):
 *   - scriptTitles(source) - indicator title/shorttitle declared by a Pine script
 *   - sameFamily(a, b) - true for generated overlays sharing a "Prefix - " title
 *   - injectPineScript(client, scriptContent) - guarded inject; success only when verified on chart
 *   - readIndicatorValues(client, indicatorName) - read Data Window values
 *   - removePineScript(client, indicatorName) - remove an indicator from the chart
 *   - savePineToLibrary(client, scriptName) - save the active script
 *   - readSourceFromDialog(client, name) - read a script's source
 */

// Browser-side snippet: resolves the active Pine Editor's Monaco instance via
// its React fiber into a local `editor` (or sets `editorError`). Shared by the
// overwrite guard and the inject step so both look at the same tab.
const FIND_EDITOR_JS = `
  var editor = null, editorError = null;
  var edEl = document.querySelector('textarea.inputarea') ||
             document.querySelector('[class*="editorWrapper-"]') ||
             document.querySelector('.pine-editor-monaco');
  if (!edEl) { editorError = 'Monaco input element not found'; }
  var el = edEl, fk = null;
  for (var depth = 0; edEl && depth < 15; depth++) {
    if (!el) break;
    fk = Object.keys(el).find(function(k) { return k.startsWith('__reactFiber'); });
    if (fk) break;
    el = el.parentElement;
  }
  if (edEl && !fk) { editorError = 'React fiber not found within 15 ancestors'; }
  if (fk) {
    try {
      var controller = el[fk].return.memoizedState.memoizedState.current;
      editor = controller._editor;
      if (!editor || typeof editor.getModel !== 'function') { editor = null; editorError = 'Monaco editor not found via fiber'; }
    } catch (e) { editorError = e.message; }
  }
`;

// Titles TradingView may show for a script: indicator("title", shorttitle="st").
export function scriptTitles(source) {
  const title = (source.match(/indicator\s*\(\s*["']([^"']+)["']/i) || [])[1];
  const short = (source.match(/shorttitle\s*=\s*["']([^"']+)["']/i) || [])[1];
  return [title, short].filter(Boolean).map(t => t.trim());
}

// A blank tab holds TradingView's "My script" template, which is safe to replace.
const REPLACEABLE_TITLES = ['my script'];

// Generated overlays share a family prefix ("AI Thesis Overlay - NBIS" and
// "AI Thesis Overlay - APLD"); replacing one with another is the intended use.
export function sameFamily(a, b) {
  const prefix = t => (t || '').split(' - ')[0].trim().toLowerCase();
  return Boolean(a && b && a.includes(' - ') && b.includes(' - ') && prefix(a) === prefix(b));
}

const VERIFY_ATTEMPTS = 3;
const VERIFY_INTERVAL_MS = 1500;

/**
 * Inject a Pine Script into the active TradingView chart.
 * 
 * Clicks the Pine Editor dialog tab, adds a new editor workspace if current is read-only,
 * replaces text content via Monaco editor React fiber controller, and triggers update/add.
 *
 * @param {object} client - CDP client instance (from connection.js getClient())
 * @param {string} scriptContent - Pine Script v5/v6 source code string to compile
 * @returns {Promise<object>} Status report
 */
export async function injectPineScript(client, scriptContent) {
  /**
   * Asserts editor visibility, checks read-only status and expands tabs if needed,
   * traverses react fiber elements to extract Monaco instance, and applies executeEdits.
   */
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
        // Check for read-only banner OR historical version banner
        var readOnly = [...document.querySelectorAll('*')].some(function(el) {
          return el.offsetParent && (
            el.textContent.includes('This script is read-only') ||
            el.textContent.includes('This is a historical version of the script')
          );
        });

        // If historical version, click 'restore this version' if visible
        var allEls = [...document.querySelectorAll('button, a, span, div')];
        var restoreBtn = allEls.find(function(el) {
          return el.offsetParent && el.children.length === 0 && el.textContent.trim().toLowerCase() === 'restore this version';
        }) || allEls.find(function(el) {
          return el.offsetParent && el.textContent.trim().toLowerCase().includes('restore this version') && el.textContent.length < 50;
        });

        if (restoreBtn) {
          restoreBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
          restoreBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
          restoreBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
          return JSON.stringify({ needsNewTab: false, restored: true });
        }

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

    // 2.5 Overwrite guard: the active tab may hold one of the user's saved
    //     scripts (e.g. "AI TA Levels v6"). Step 4 clicks Save, so injecting
    //     into it would replace that script. Fail closed instead.
    const targetTitles = scriptTitles(scriptContent).map(t => t.toLowerCase());
    const guardResult = await client.Runtime.evaluate({
      expression: `(function() {
        ${FIND_EDITOR_JS}
        if (!editor) return JSON.stringify({ activeSource: '', error: editorError });
        return JSON.stringify({ activeSource: editor.getValue() });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    const guard = JSON.parse(guardResult.result.value || '{}');
    const activeTitles = scriptTitles(guard.activeSource || '');
    const activeTitle = activeTitles[0];
    if (activeTitle
        && !REPLACEABLE_TITLES.includes(activeTitle.toLowerCase())
        && !activeTitles.some(t => targetTitles.includes(t.toLowerCase()))
        && !sameFamily(activeTitle, scriptTitles(scriptContent)[0])) {
      return {
        success: false,
        error: `Active Pine tab holds a different script; refusing to overwrite '${activeTitle}'. Open a blank Pine tab and retry.`,
      };
    }

    // 2.6 Clear old instances from the chart legend (write-once replace protocol).
    //     Runs only after the overwrite guard passed, so a refused inject never
    //     removes anything from the chart.
    await client.Runtime.evaluate({
      expression: `(function() {
        var raw = ${safeContent};
        var titleMatch = raw.match(/indicator\\s*\\(\\s*["']([^"']+)["']/i);
        var shortMatch = raw.match(/shorttitle\\s*=\\s*["']([^"']+)["']/i);
        var targetNames = [];
        if (titleMatch && titleMatch[1]) targetNames.push(titleMatch[1].trim().toLowerCase());
        if (shortMatch && shortMatch[1]) targetNames.push(shortMatch[1].trim().toLowerCase());
        // Own family only (e.g. "ai thesis overlay" for "AI Thesis Overlay - APLD")
        // plus the legacy "ai thesis" name. Other AI indicators such as
        // "AI TA Levels v6" are left alone.
        var family = ${JSON.stringify(((scriptTitles(scriptContent)[0] || '').split(' - ')[0] || '').trim().toLowerCase())};
        if (family) targetNames.push(family);
        targetNames.push('ai thesis');

        var items = [...document.querySelectorAll('[data-name="legend-series-item"], [class*="item-"], [class*="legend-"]')];
        items.forEach(function(item) {
          if (!item.offsetParent) return;
          var titleEl = item.querySelector('[class*="titleWrapper-"]') || item.querySelector('[class*="title-"]');
          var text = (titleEl ? titleEl.textContent : item.textContent).trim().toLowerCase();
          var isMatch = targetNames.some(function(n) { return text.includes(n); });
          if (isMatch) {
            item.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true, view: window }));
            var btn = item.querySelector('button[aria-label="Remove"]') || 
                      item.querySelector('[data-name="remove"]') ||
                      item.querySelector('button[title="Remove"]');
            if (btn) {
              btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
              btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
              btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
            }
          }
        });
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 600));

    // 3. Inject via executeEdits — fires onDidChangeModelContent so TV recompiles.
    //    editor.focus() ensures the blank tab's editor is active before edits.
    const injectResult = await client.Runtime.evaluate({
      expression: `(function() {
        var script = ${safeContent};
        ${FIND_EDITOR_JS}
        if (!editor) return JSON.stringify({ success: false, error: editorError });
        try {
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
    const injectData = JSON.parse(injectResult.result.value || '{}');
    if (!injectData.success) {
      return { success: false, error: injectData.error || 'Pine inject failed' };
    }

    // 4. Click Save in toolbar (ensures script is compiled and saved in user library)
    await client.Runtime.evaluate({
      expression: `(function() {
        var btns = [...document.querySelectorAll('button')];
        var saveBtn = btns.find(function(b) {
          return b.offsetParent && (b.textContent.trim().toLowerCase().startsWith('save') || (b.title && b.title.toLowerCase().includes('save')));
        });
        if (saveBtn) {
          saveBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
          saveBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
          saveBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        }
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 1200));

    // 5. Click "Add to chart" / "Update on chart"
    await client.Runtime.evaluate({
      expression: `(function() {
        var btns = [...document.querySelectorAll('button')];
        var addBtn = btns.find(function(b) {
          return b.offsetParent && /(?:add|update).*(?:to|on).*chart/i.test(b.textContent + b.title);
        });
        if (addBtn) {
          addBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
          addBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
          addBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        }
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 1000));

    // 5.1 If a "Save this script before adding?" confirmation modal popped up, confirm it
    await client.Runtime.evaluate({
      expression: `(function() {
        var modal = [...document.querySelectorAll('[class*="dialog"], [role="dialog"]')]
          .find(function(m) { return m.offsetParent; });
        if (modal) {
          var saveBtn = [...modal.querySelectorAll('button')].find(function(b) {
            var t = b.textContent.trim().toLowerCase();
            return b.offsetParent && (t === 'save' || t.includes('save and add') || t === 'ok');
          });
          if (saveBtn) {
            saveBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
            saveBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
            saveBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
          }
        }
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });

    // 6. Wait for compilation & chart rendering
    await new Promise(r => setTimeout(r, 2000));

    // 7. Strict Cleanup & Dismissal: Close Pine Editor panel and dismiss any open modals/dialogs
    await client.Runtime.evaluate({
      expression: `(function() {
        // Close Pine Editor top right close button
        var pineClose = [...document.querySelectorAll('button[title="Close"], button[aria-label="Close"], button[data-name="close"]')]
          .find(function(b) { return b.offsetParent && b.closest('[class*="pine"], [class*="dialog-"], [class*="editorBaseLayout"]'); });
        if (pineClose) {
          pineClose.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
          pineClose.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
          pineClose.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        } else {
          var bottomPine = document.querySelector('[data-name="pine-dialog-button"]');
          if (bottomPine && bottomPine.getAttribute('aria-pressed') === 'true') bottomPine.click();
        }

        // Close any lingering dialogs (Indicators search modal, alerts, etc.)
        var dialogClose = [...document.querySelectorAll('[data-name="indicators-dialog"] button[data-name="close"], [data-name="close"]')];
        dialogClose.forEach(function(b) {
          if (b.offsetParent) b.click();
        });

        // Dispatch Escape key to clear any active popovers
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
      })()`,
      returnByValue: true,
      awaitPromise: false,
    });
    await new Promise(r => setTimeout(r, 600));

    // 8. Verify the indicator actually reached the chart. Clicking "Add to
    //    chart" is fire-and-forget; without this check a compile error or a
    //    missed button still reported success (DEBT-20260927-01).
    let studyNames = [];
    for (let attempt = 0; attempt < VERIFY_ATTEMPTS; attempt++) {
      const verifyResult = await client.Runtime.evaluate({
        expression: `(function() {
          try {
            return JSON.stringify({ studies: window.TradingViewApi.activeChart().getAllStudies() });
          } catch (e) { return JSON.stringify({ studies: [], error: e.message }); }
        })()`,
        returnByValue: true,
        awaitPromise: false,
      });
      studyNames = (JSON.parse(verifyResult.result.value || '{}').studies || []).map(st => st.name);
      const match = studyNames.find(n => targetTitles.includes(String(n).trim().toLowerCase()));
      if (match) return { success: true, verified: true, study: match };
      await new Promise(r => setTimeout(r, VERIFY_INTERVAL_MS));
    }
    return {
      success: false,
      error: `Indicator '${scriptTitles(scriptContent)[0] || '(untitled)'}' not found on chart after injection`,
      studies: studyNames,
    };
  } catch (e) {
    return { success: false, error: e.message || 'Pine inject failed' };
  }
}

/**
 * Read current indicator values from the TradingView Data Window.
 * 
 * @param {object} client - CDP client instance
 * @param {string} indicatorName - Display name of the indicator to read values for
 * @returns {Promise<object>} Status report mapping current indicator values
 */
export async function readIndicatorValues(client, indicatorName) {
  /**
   * Evaluates the DOM to query items in the widgetbar-widget-object_tree panel
   * containing indicator titles and extracts value strings.
   */
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
 * @param {object} client - CDP client instance
 * @param {string} indicatorName - Exact display name of the indicator to remove
 * @returns {Promise<object>} Status report
 */
export async function removePineScript(client, indicatorName) {
  /**
   * Queries legends matching indicator name, clicks its remove/close/delete button.
   */
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
 * Save the current Pine Script in the editor to TradingView's personal library.
 *
 * Sends Cmd+S / Ctrl+S within the Pine Editor context. Handles the "Save as"
 * naming dialog if the script has never been saved before.
 *
 * @param {object} client - CDP client instance
 * @param {string} scriptName - Display name to save under (used if naming dialog appears)
 * @returns {Promise<object>} Status report showing the name of saved script and action taken
 */
export async function savePineToLibrary(client, scriptName) {
  /**
   * Asserts editor open state, dispatches Keydown 's' event with meta/ctrl key,
   * queries naming dialog input, inputs script name, and confirms save.
   */
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

/**
 * Open an indicator's Pine Script source code in the Pine Editor via the Indicators dialog.
 * 
 * Navigates to the "Top" list (or searches by name), hovers the matching row to expose the
 * "Source code" { } button, clicks it, then reads and returns the full source from Monaco.
 *
 * @param {object} client - CDP client instance
 * @param {string} name - Indicator name to search for (partial match). Pass null/"" to read active script.
 * @returns {Promise<object>} Status report mapping source string and Pine version
 */
export async function readSourceFromDialog(client, name) {
  /**
   * Opens indicators dialog, clicks 'Top' tab, types indicator name, hovers result,
   * clicks source button, traverses react fiber to find editor controller, and gets content.
   */
  try {
    const delay = (ms) => new Promise(r => setTimeout(r, ms));

    // Helper: read Monaco editor content via React fiber traversal
    const readEditor = async () => {
      const r = await client.Runtime.evaluate({
        expression: `(function() {
          var edEl = document.querySelector('.pine-editor-monaco');
          if (!edEl) return null;
          var el = edEl, fk = null;
          for (var d = 0; d < 10; d++) {
            el = el.parentElement; if (!el) break;
            fk = Object.keys(el).find(function(k) { return k.startsWith('__reactFiber'); });
            if (fk) break;
          }
          if (!fk) return null;
          try { return el[fk].return.memoizedState.memoizedState.current._editor.getValue(); }
          catch(e) { return null; }
        })()`,
        returnByValue: true, awaitPromise: false,
      });
      return r.result.value;
    };

    // If no name given, read what is currently open
    if (!name) {
      const src = await readEditor();
      if (!src) return { success: false, error: 'Pine Editor not open or empty' };
      const ver = (src.match(/\/\/@version=\d+/) || ['unknown'])[0];
      return { success: true, name: '(current)', source: src, version: ver };
    }

    const safeName = JSON.stringify(name);

    // 1. Open Indicators dialog
    await client.Runtime.evaluate({
      expression: `(function() {
        var btns = [...document.querySelectorAll('[data-name="open-indicators-dialog"]')];
        var visible = btns.filter(function(b) { return b.offsetParent; });
        (visible[0] || btns[0]).click();
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await delay(1200);

    // 2. Click "Top" sidebar item for popularity sort
    await client.Runtime.evaluate({
      expression: `(function() {
        var dialog = document.querySelector('[data-name="indicators-dialog"]');
        if (!dialog) return;
        var top = [...dialog.querySelectorAll('*')].find(function(el) {
          return el.offsetParent && el.textContent.trim() === 'Top' && el.children.length === 0;
        });
        if (top) top.click();
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    await delay(800);

    // 3. Type search term to filter results
    const typeRes = await client.Runtime.evaluate({
      expression: `(function() {
        var dialog = document.querySelector('[data-name="indicators-dialog"]');
        if (!dialog) return 'no-dialog';
        var input = dialog.querySelector('input[placeholder="Search"]') || dialog.querySelector('input');
        if (!input) return 'no-input';
        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, ${safeName});
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'typed';
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    if (typeRes.result.value !== 'typed') {
      return { success: false, error: `Could not type search term: ${typeRes.result.value}` };
    }
    await delay(1800);

    // 4. Hover over the first result row and click its "Source code" button
    const clickRes = await client.Runtime.evaluate({
      expression: `(function() {
        var dialog = document.querySelector('[data-name="indicators-dialog"]');
        if (!dialog) return JSON.stringify({ error: 'no-dialog' });

        // Hover over first row to make action icons visible
        var rows = [...dialog.querySelectorAll('[class*="container-WeNdU0sq"]')]
          .filter(function(e) { return e.offsetParent; });
        if (rows.length === 0) return JSON.stringify({ error: 'no-rows' });
        var row = rows[0];
        row.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
        row.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));

        // Click the "Source code" { } button (title attribute is stable)
        var srcBtn = row.querySelector('[title="Source code"]') ||
          [...dialog.querySelectorAll('[title="Source code"]')].filter(function(e){ return e.offsetParent; })[0];
        if (!srcBtn) return JSON.stringify({ error: 'no-source-btn' });

        var nameEl = row.querySelector('[class*="title-cIIj4HrJ"]');
        var rowName = nameEl ? nameEl.textContent.trim() : 'unknown';
        srcBtn.click();
        return JSON.stringify({ clicked: true, rowName: rowName });
      })()`,
      returnByValue: true, awaitPromise: false,
    });
    const click = JSON.parse(clickRes.result.value);
    if (!click.clicked) return { success: false, error: click.error || 'Source code button not found' };
    await delay(2000);

    // 5. Read Pine Editor
    const source = await readEditor();
    if (!source) return { success: false, error: 'Pine Editor did not open after clicking source code' };

    const ver = (source.match(/\/\/@version=\d+/) || ['unknown'])[0];
    return { success: true, name: click.rowName, source, version: ver };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
