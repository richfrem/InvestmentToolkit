/**
 * watchlist.js — TradingView Watchlist automation via CDP DOM.
 */

// Helper to wait
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

/**
 * Open/select a watchlist by name in the sidebar.
 */
export async function openWatchlist(client, name) {
  try {
    const safeName = JSON.stringify(name);
    
    // 0. Already active? Just return success immediately
    const checkActive = await client.Runtime.evaluate({
      expression: `(function() {
        var activeBtn = document.querySelector('[data-name="watchlists-button"] [class*="titleRow-"]');
        return activeBtn && activeBtn.textContent.trim().toLowerCase() === ${safeName}.toLowerCase();
      })()`,
      returnByValue: true, awaitPromise: false
    });
    if (checkActive.result && checkActive.result.value) {
      return { success: true, name: name };
    }
    
    // 1. Ensure Watchlist/Detail side panel is active.
    await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('[data-name="watchlist"]');
        if (btn && btn.getAttribute('aria-selected') !== 'true') {
          btn.click();
        }
      })()`,
      returnByValue: true, awaitPromise: false
    });
    await sleep(600);

    // 2. Click Watchlist selector dropdown
    const clickDropdown = await client.Runtime.evaluate({
      expression: `(function() {
        var dropdown = document.querySelector('[data-name="watchlists-button"]');
        if (dropdown) {
          dropdown.click();
          return true;
        }
        return false;
      })()`,
      returnByValue: true, awaitPromise: false
    });
    if (!clickDropdown.result.value) {
      return { success: false, error: 'Watchlist dropdown button not found' };
    }
    await sleep(800);

    // 3. Find and click the named watchlist row in the menuBox
    const clickItem = await client.Runtime.evaluate({
      expression: `(function() {
        var name = ${safeName}.toLowerCase();
        var items = Array.from(document.querySelectorAll('[class*="menuBox"] [class*="buttonContent-"]'));
        var match = items.find(function(el) {
          return el.textContent.trim().toLowerCase() === name;
        });
        if (match) {
          var clickEl = match;
          while(clickEl) {
            if (clickEl.getAttribute('role') === 'menuitem' || clickEl.className.includes('medium-OxBZfgw8')) {
              clickEl.click();
              return JSON.stringify({ success: true });
            }
            clickEl = clickEl.parentElement;
          }
          match.click();
          return JSON.stringify({ success: true });
        }
        return JSON.stringify({ success: false, error: 'Watchlist name not found in dropdown: ' + ${safeName} });
      })()`,
      returnByValue: true, awaitPromise: false
    });

    const parsed = JSON.parse(clickItem.result.value);
    if (!parsed.success) {
      // Close dropdown if search failed
      await client.Runtime.evaluate({ expression: 'document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))' });
      return { success: false, error: parsed.error };
    }
    await sleep(1000); // Wait for list to load
    return { success: true, name: name };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Read current watchlist tickers, prices, and change percentages.
 */
export async function getWatchlist(client) {
  try {
    const result = await client.Runtime.evaluate({
      expression: `(function() {
        var currentWatchlist = 'Unknown';
        var activeBtn = document.querySelector('[data-name="watchlists-button"] [class*="titleRow-"]');
        if (activeBtn) {
          currentWatchlist = activeBtn.textContent.trim();
        }

        var rows = Array.from(document.querySelectorAll('[class*="symbol-RsFlttSS"]'));
        if (rows.length === 0) {
          // Fallback if class changes
          rows = Array.from(document.querySelectorAll('[data-symbol-short]'));
        }

        var items = rows.map(function(el) {
          var symText = el.querySelector('[class*="symbolNameText-"]');
          var priceEl = el.querySelector('[class*="cell-"][class*="last-"]') || el.querySelector('[class*="last-"]');
          var chgEl = el.querySelector('[class*="changeInPercents-"]');
          
          var priceVal = 0.0;
          if (priceEl) {
            var pText = priceEl.textContent.trim().replace(/[$,\\s]/g, '');
            priceVal = parseFloat(pText) || 0.0;
          }

          var chgVal = 0.0;
          if (chgEl) {
            var cText = chgEl.textContent.trim().replace(/[%\\u2212\\s]/g, function(m) {
              return m === '\\u2212' ? '-' : '';
            });
            chgVal = parseFloat(cText) || 0.0;
          }

          return {
            symbol: symText ? symText.textContent.trim() : el.getAttribute('data-symbol-short') || '',
            price: priceVal,
            changePercent: chgVal
          };
        }).filter(function(item) { return item.symbol !== ''; });

        return JSON.stringify({
          success: true,
          watchlist: currentWatchlist,
          items: items
        });
      })()`,
      returnByValue: true,
      awaitPromise: false
    });
    return JSON.parse(result.result.value);
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Add a symbol to the specified watchlist.
 */
export async function addWatchlistItem(client, watchlistName, symbol) {
  try {
    // 1. Switch to the watchlist
    const openRes = await openWatchlist(client, watchlistName);
    if (!openRes.success) return openRes;

    const safeSymbol = JSON.stringify(symbol.trim().toUpperCase());

    // 2. Click "Add symbol" button
    const clickAddBtn = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('[data-name="add-symbol-button"]');
        if (btn) {
          btn.click();
          return true;
        }
        return false;
      })()`,
      returnByValue: true, awaitPromise: false
    });
    if (!clickAddBtn.result.value) {
      return { success: false, error: 'Add symbol button not found' };
    }
    await sleep(800);

    // 3. Type symbol and press Enter
    await client.Runtime.evaluate({
      expression: `(function() {
        var input = document.querySelector('input[placeholder*="Search"], input[class*="input-"]');
        if (!input) {
          input = [...document.querySelectorAll('input')].find(function(i) { return i.offsetParent; });
        }
        if (input) {
          input.focus();
          var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
          setter.call(input, ${safeSymbol});
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        }
        return false;
      })()`,
      returnByValue: true, awaitPromise: false
    });
    await sleep(800);

    // Press Enter to submit/add
    await client.Runtime.evaluate({
      expression: `(function() {
        var input = [...document.querySelectorAll('input')].find(function(i) { return i.offsetParent; });
        if (input) {
          input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        }
      })()`
    });
    await sleep(600);

    // Close search box via Escape
    await client.Runtime.evaluate({
      expression: `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`
    });

    return { success: true, symbol: symbol };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Remove a symbol from the specified watchlist.
 */
export async function removeWatchlistItem(client, watchlistName, symbol) {
  try {
    const openRes = await openWatchlist(client, watchlistName);
    if (!openRes.success) return openRes;

    const safeSymbol = JSON.stringify(symbol.trim().toUpperCase());

    // 1. Find the symbol row coordinates to click its "x" end button
    const getRemoveCoords = await client.Runtime.evaluate({
      expression: `(function() {
        var targetSymbol = ${safeSymbol};
        var rows = Array.from(document.querySelectorAll('[class*="symbol-RsFlttSS"]'));
        var match = rows.find(function(el) {
          var symText = el.querySelector('[class*="symbolNameText-"]');
          var s = symText ? symText.textContent.trim() : el.getAttribute('data-symbol-short') || '';
          return s.toUpperCase() === targetSymbol;
        });
        if (!match) return null;
        
        var removeBtn = match.querySelector('[class*="removeButton-"]');
        if (removeBtn) {
          var r = removeBtn.getBoundingClientRect();
          return JSON.stringify({ cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) });
        }
        return null;
      })()`,
      returnByValue: true, awaitPromise: false
    });

    if (!getRemoveCoords.result.value) {
      return { success: false, error: `Symbol "${symbol}" or its Remove button not found in watchlist` };
    }

    const coords = JSON.parse(getRemoveCoords.result.value);

    // 2. Dispatch mouse hover / mouse click events at coordinate points
    await client.Input.dispatchMouseEvent({ type: 'mousePressed', x: coords.cx, y: coords.cy, button: 'left', clickCount: 1 });
    await client.Input.dispatchMouseEvent({ type: 'mouseReleased', x: coords.cx, y: coords.cy, button: 'left', clickCount: 1 });
    await sleep(600);

    return { success: true, symbol: symbol };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Create a new watchlist.
 */
export async function createWatchlist(client, name) {
  try {
    // 1. Ensure Watchlist/Detail side panel is active.
    await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('[data-name="watchlist"]');
        if (btn && btn.getAttribute('aria-selected') !== 'true') {
          btn.click();
        }
      })()`
    });
    await sleep(600);

    // 2. Click Watchlist selector dropdown
    await client.Runtime.evaluate({
      expression: `document.querySelector('[data-name="watchlists-button"]')?.click()`
    });
    await sleep(800);

    // 3. Get coordinates for "Create new list..." option
    const getCreateCoords = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = Array.from(document.querySelectorAll('[class*="menuBox"] [class*="buttonContent-"]'))
          .find(function(el) { return el.textContent.includes("Create new list"); });
        if (btn) {
          var r = btn.getBoundingClientRect();
          return JSON.stringify({ cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) });
        }
        return null;
      })()`,
      returnByValue: true, awaitPromise: false
    });

    if (!getCreateCoords.result.value) {
      // Close dropdown
      await client.Runtime.evaluate({ expression: 'document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))' });
      return { success: false, error: '"Create new list..." button not found in dropdown menu' };
    }

    const coords = JSON.parse(getCreateCoords.result.value);

    // 4. Click the Create menu option
    await client.Input.dispatchMouseEvent({ type: 'mousePressed', x: coords.cx, y: coords.cy, button: 'left', clickCount: 1 });
    await client.Input.dispatchMouseEvent({ type: 'mouseReleased', x: coords.cx, y: coords.cy, button: 'left', clickCount: 1 });
    await sleep(1000);

    // 5. Fill input with the target name
    const safeName = JSON.stringify(name);
    await client.Runtime.evaluate({
      expression: `(function() {
        var input = document.querySelector('input[data-qa-id="ui-lib-Input-input"]');
        if (input) {
          input.focus();
          var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
          setter.call(input, ${safeName});
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        }
        return false;
      })()`,
      returnByValue: true, awaitPromise: false
    });
    await sleep(600);

    // Confirm dialog via Enter key
    await client.Runtime.evaluate({
      expression: `(function() {
        var input = document.querySelector('input[data-qa-id="ui-lib-Input-input"]');
        if (input) {
          input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        }
      })()`
    });
    await sleep(1000);

    return { success: true, name: name };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Delete a watchlist.
 */
export async function deleteWatchlist(client, name) {
  try {
    const safeName = JSON.stringify(name);

    // 1. Ensure Watchlist/Detail side panel is active.
    await client.Runtime.evaluate({
      expression: `(function() {
        var btn = document.querySelector('[data-name="watchlist"]');
        if (btn && btn.getAttribute('aria-selected') !== 'true') {
          btn.click();
        }
      })()`,
      returnByValue: true, awaitPromise: false
    });
    await sleep(600);

    // 2. Click Watchlist selector dropdown
    const clickDropdown = await client.Runtime.evaluate({
      expression: `(function() {
        var dropdown = document.querySelector('[data-name="watchlists-button"]');
        if (dropdown) {
          dropdown.click();
          return true;
        }
        return false;
      })()`,
      returnByValue: true, awaitPromise: false
    });
    if (!clickDropdown.result.value) {
      return { success: false, error: 'Watchlist dropdown button not found' };
    }
    await sleep(800);

    // 3. Find and click 'Open list...' button
    const getOpenListCoords = await client.Runtime.evaluate({
      expression: `(function() {
        var btn = Array.from(document.querySelectorAll('[class*="menuBox"] [class*="buttonContent-"]'))
          .find(function(el) { return el.textContent.includes("Open list"); });
        if (btn) {
          var r = btn.getBoundingClientRect();
          return JSON.stringify({ cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) });
        }
        return null;
      })()`,
      returnByValue: true, awaitPromise: false
    });

    if (!getOpenListCoords.result.value) {
      // Close dropdown
      await client.Runtime.evaluate({ expression: 'document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))' });
      return { success: false, error: '"Open list..." button not found in watchlists dropdown' };
    }

    const openListCoords = JSON.parse(getOpenListCoords.result.value);
    await client.Input.dispatchMouseEvent({ type: 'mousePressed', x: openListCoords.cx, y: openListCoords.cy, button: 'left', clickCount: 1 });
    await client.Input.dispatchMouseEvent({ type: 'mouseReleased', x: openListCoords.cx, y: openListCoords.cy, button: 'left', clickCount: 1 });
    await sleep(1200); // Wait for the dialog to open

    // 4. Find the row for target watchlist in the dialog and get its coordinates
    const getRowCoords = await client.Runtime.evaluate({
      expression: `(function() {
        var targetName = ${safeName}.toLowerCase();
        var rows = Array.from(document.querySelectorAll('[class*="container-ODL8WA9K"]'));
        var match = rows.find(function(row) {
          var titleEl = row.querySelector('[class*="title-ODL8WA9K"]');
          return titleEl && titleEl.textContent.trim().toLowerCase() === targetName;
        });
        if (!match) return null;

        var r = match.getBoundingClientRect();
        return JSON.stringify({ cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) });
      })()`,
      returnByValue: true, awaitPromise: false
    });

    if (!getRowCoords.result.value) {
      // Close dialog
      await client.Runtime.evaluate({ expression: 'document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))' });
      return { success: false, error: 'Watchlist "' + name + '" row not found in Open list dialog' };
    }

    const rowCoords = JSON.parse(getRowCoords.result.value);

    // 5. Hover mouse over the row to reveal action buttons
    await client.Input.dispatchMouseEvent({ type: 'mouseMoved', x: rowCoords.cx, y: rowCoords.cy });
    await sleep(500);

    // 6. Find and click the "remove-button" trash icon for that row
    const getRemoveBtnCoords = await client.Runtime.evaluate({
      expression: `(function() {
        var targetName = ${safeName}.toLowerCase();
        var rows = Array.from(document.querySelectorAll('[class*="container-ODL8WA9K"]'));
        var match = rows.find(function(row) {
          var titleEl = row.querySelector('[class*="title-ODL8WA9K"]');
          return titleEl && titleEl.textContent.trim().toLowerCase() === targetName;
        });
        if (!match) return null;

        var removeBtn = match.querySelector('[data-name="remove-button"]');
        if (!removeBtn) return null;

        var r = removeBtn.getBoundingClientRect();
        return JSON.stringify({ cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) });
      })()`,
      returnByValue: true, awaitPromise: false
    });

    if (!getRemoveBtnCoords.result.value) {
      // Close dialog
      await client.Runtime.evaluate({ expression: 'document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))' });
      return { success: false, error: 'Remove/Delete trash button not found for watchlist "' + name + '"' };
    }

    const removeBtnCoords = JSON.parse(getRemoveBtnCoords.result.value);
    await client.Input.dispatchMouseEvent({ type: 'mousePressed', x: removeBtnCoords.cx, y: removeBtnCoords.cy, button: 'left', clickCount: 1 });
    await client.Input.dispatchMouseEvent({ type: 'mouseReleased', x: removeBtnCoords.cx, y: removeBtnCoords.cy, button: 'left', clickCount: 1 });
    await sleep(800);

    // 7. Confirm delete popup dialog if it appears
    await client.Runtime.evaluate({
      expression: `(function() {
        var yesBtn = Array.from(document.querySelectorAll('button')).find(function(b) {
          return b.offsetParent && (b.textContent.toLowerCase() === 'yes' || b.textContent.toLowerCase().includes('delete'));
        });
        if (yesBtn) {
          yesBtn.click();
        } else {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        }
      })()`
    });
    await sleep(1000);

    // Close the "Open list..." dialog using Escape if it's still open
    await client.Runtime.evaluate({
      expression: `(function() {
        var dialog = document.querySelector('[class*="dialog-"]');
        if (dialog) {
          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        }
      })()`
    });
    await sleep(500);

    return { success: true, name: name };
  } catch (e) {
    return { success: false, error: e.message };
  }
}
