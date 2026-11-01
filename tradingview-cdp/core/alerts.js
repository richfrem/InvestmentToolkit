/**
 * alerts.js - Core alert logic — create, list, and delete TradingView price alerts.
 * 
 * Purpose:
 *   Handles DOM automation and API queries for managing TradingView alerts.
 * 
 * Key Input Dependencies:
 *   None (reads live state from TradingView Desktop on port 9222 via CDP)
 * 
 * Key Output Dependencies:
 *   None (returns JSON data structures)
 */
import { evaluate, evaluateAsync, getClient, safeString } from '../connection.js';

/**
 * Create a new price alert in TradingView via DOM click and key injection.
 * 
 * @param {object} params Parameter object
 * @param {string} params.condition Alert condition type
 * @param {number} params.price Price trigger level
 * @param {string} params.message Message label to assign to the alert
 * @returns {Promise<object>} Status report of creation
 */
export async function create({ condition, price, message }) {
  /**
   * Triggers the alert creation modal by either clicking the DOM button
   * or falling back to the keyboard shortcut (Option + A), clears and types
   * the exact price via CDP key injection, and submits.
   */
  const client = await getClient();
  const opened = await evaluate(`
    (function() {
      var btn = document.querySelector('[aria-label="Create Alert"]')
        || document.querySelector('[data-name="alerts"]');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);

  if (!opened) {
    await client.Input.dispatchKeyEvent({ type: 'keyDown', modifiers: 1, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
    await client.Input.dispatchKeyEvent({ type: 'keyUp', key: 'a', code: 'KeyA' });
  }

  await new Promise(r => setTimeout(r, 900));

  // Focus and select the price input
  const focused = await evaluate(`
    (function() {
      var input = document.querySelector('[data-qa-id*="end-band-range-input"]')
        || Array.from(document.querySelectorAll('input')).find(function(i) {
          var v = (i.value || '').replace(/,/g, '').trim();
          return i.offsetParent && v !== '' && !isNaN(Number(v)) && (i.type === 'text' || i.type === 'number');
        });
      if (input) {
        input.focus();
        input.select();
        return true;
      }
      return false;
    })()
  `);

  if (!focused) {
    return { success: false, error: 'Price input not found in Create Alert dialog' };
  }

  // Clear existing input with backspaces
  for (let i = 0; i < 10; i++) {
    await client.Input.dispatchKeyEvent({ type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
    await client.Input.dispatchKeyEvent({ type: 'keyUp', key: 'Backspace', code: 'Backspace' });
  }

  // Type price via CDP text insertion
  await client.Input.insertText({ text: String(price) });

  // If message provided, set message in textarea
  if (message) {
    await evaluate(`
      (function() {
        var textarea = Array.from(document.querySelectorAll('textarea')).find(function(t) { return t.offsetParent; })
          || document.querySelector('[class*="alert"] textarea')
          || document.querySelector('textarea[placeholder*="message"]');
        if (textarea) {
          textarea.value = ${JSON.stringify(message)};
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
          textarea.dispatchEvent(new Event('change', { bubbles: true }));
        }
      })()
    `);
  }

  // Submit via Enter
  await client.Input.dispatchKeyEvent({ type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  await client.Input.dispatchKeyEvent({ type: 'keyUp', key: 'Enter', code: 'Enter' });
  await new Promise(r => setTimeout(r, 800));

  // Fallback: click Create button if dialog still open
  await evaluate(`
    (function() {
      var btn = Array.from(document.querySelectorAll('button')).find(function(b) {
        return b.offsetParent && /^create$/i.test(b.textContent.trim());
      });
      if (btn) btn.click();
    })()
  `);

  return { success: true, price: Number(price), condition: condition || 'crossing', message: message || '(none)', price_set: true, source: 'cdp_keyboard' };
}

/**
 * Retrieve active alerts from TradingView internal API and optionally filter by watchlist symbols.
 * 
 * @param {string[]} symbols List of uppercase symbols to filter by
 * @returns {Promise<object>} Active alerts payload
 */
export async function list(symbols = []) {
  /**
   * Evaluates a fetch request in the browser context to retrieve live alerts,
   * extracts details (including synthetic condition objects to avoid truncation),
   * and filters them in the browser.
   */
  const result = await evaluateAsync(`
    fetch('https://pricealerts.tradingview.com/list_alerts', { credentials: 'include' })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.s !== 'ok' || !Array.isArray(data.r)) return { alerts: [], error: data.errmsg || 'Unexpected response' };
        
        var filterSet = new Set(${JSON.stringify(symbols.map(s => s.toUpperCase()))});
        var filteredAlerts = data.r;
        
        if (filterSet.size > 0) {
          filteredAlerts = data.r.filter(function(a) {
            var cleanSym = a.symbol.replace(/^=/, '');
            try { cleanSym = JSON.parse(cleanSym).symbol || cleanSym; } catch(e) {}
            var baseSym = cleanSym.split(':')[1] || cleanSym.split(':')[0] || cleanSym;
            baseSym = baseSym.split('.')[0].split('-')[0].toUpperCase();
            return filterSet.has(baseSym);
          });
        }
        
        return {
          alerts: filteredAlerts.map(function(a) {
            var sym = '';
            try { sym = JSON.parse(a.symbol.replace(/^=/, '')).symbol || a.symbol; } catch(e) { sym = a.symbol; }
            
            var price = null;
            if (a.condition && Array.isArray(a.condition.series) && a.condition.series[1]) {
              price = a.condition.series[1].value;
            }
            
            return {
              alert_id: a.alert_id,
              symbol: sym,
              type: a.type,
              message: a.message,
              active: a.active,
              price: price,
              condition: {
                type: a.condition && a.condition.type ? a.condition.type : 'cross',
                series: [
                  { type: 'barset' },
                  { type: 'value', value: price }
                ]
              },
              resolution: a.resolution,
              created: a.create_time,
              last_fired: a.last_fire_time,
              expiration: a.expiration,
            };
          })
        };
      })
      .catch(function(e) { return { alerts: [], error: e.message }; })
  `);
  return { success: true, alert_count: result?.alerts?.length || 0, source: 'internal_api', alerts: result?.alerts || [], error: result?.error };
}

/**
 * Request deletion of TradingView alerts.
 * 
 * @param {object} params Parameter object
 * @param {boolean} params.delete_all Toggle to trigger bulk deletion of all alerts
 * @returns {Promise<object>} Status report of deletion attempt
 */
export async function deleteAlerts({ delete_all }) {
  /**
   * Automates clearing all alerts via the TradingView options menu:
   * 1. Pauses all active alerts (and auto-confirms the 'Yes' modal).
   * 2. Deletes all inactive alerts (and auto-confirms the 'Yes' modal).
   */
  if (delete_all) {
    const result = await evaluate(`
      (async function() {
        var btn = document.querySelector('[data-name="alerts-settings-button"]');
        if (!btn) {
          var tab = document.querySelector('button[data-name="alerts"]') || document.querySelector('button[aria-label="Alerts"]');
          if (tab) tab.click();
          await new Promise(r => setTimeout(r, 600));
          btn = document.querySelector('[data-name="alerts-settings-button"]');
        }
        if (!btn) return { success: false, error: 'Alerts panel settings button not found' };

        // 1. Pause all alerts
        btn.click();
        await new Promise(r => setTimeout(r, 600));
        var items = Array.from(document.querySelectorAll('[role="menuitem"], [class*="item-"]')).filter(el => el.offsetParent);
        var pauseAll = items.find(el => /pause all/i.test(el.textContent));
        if (pauseAll) {
          pauseAll.click();
          await new Promise(r => setTimeout(r, 800));
          var yesPause = Array.from(document.querySelectorAll('button')).find(b => b.offsetParent && /^yes$|^pause$/i.test(b.textContent.trim()));
          if (yesPause) yesPause.click();
          await new Promise(r => setTimeout(r, 600));
        }

        // 2. Delete all inactive alerts
        btn.click();
        await new Promise(r => setTimeout(r, 600));
        items = Array.from(document.querySelectorAll('[role="menuitem"], [class*="item-"]')).filter(el => el.offsetParent);
        var deleteAll = items.find(el => /delete all inactive/i.test(el.textContent));
        if (deleteAll) {
          deleteAll.click();
          await new Promise(r => setTimeout(r, 800));
          var yesDelete = Array.from(document.querySelectorAll('button')).find(b => b.offsetParent && /^yes$|^delete$/i.test(b.textContent.trim()));
          if (yesDelete) yesDelete.click();
          await new Promise(r => setTimeout(r, 600));
          return { success: true, cleared: true };
        }
        return { success: false, error: 'Delete all inactive menu option not found' };
      })()
    `);
    return { success: !!result?.success, ...result, source: 'cdp_automated' };
  }
  throw new Error('Individual alert deletion not yet supported. Use delete_all: true.');
}
