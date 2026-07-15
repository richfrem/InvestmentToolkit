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
   * or falling back to the keyboard shortcut (Option + A), then updates
   * price and message fields via DOM properties.
   */
  const opened = await evaluate(`
    (function() {
      var btn = document.querySelector('[aria-label="Create Alert"]')
        || document.querySelector('[data-name="alerts"]');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);

  if (!opened) {
    const client = await getClient();
    await client.Input.dispatchKeyEvent({ type: 'keyDown', modifiers: 1, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
    await client.Input.dispatchKeyEvent({ type: 'keyUp', key: 'a', code: 'KeyA' });
  }

  await new Promise(r => setTimeout(r, 1000));

  const priceSet = await evaluate(`
    (function() {
      var inputs = document.querySelectorAll('[class*="alert"] input[type="text"], [class*="alert"] input[type="number"]');
      for (var i = 0; i < inputs.length; i++) {
        var label = inputs[i].closest('[class*="row"]')?.querySelector('[class*="label"]');
        if (label && /value|price/i.test(label.textContent)) {
          var nativeSet = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          nativeSet.call(inputs[i], ${safeString(String(price))});
          inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
          inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        }
      }
      if (inputs.length > 0) {
        var nativeSet = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        nativeSet.call(inputs[0], ${safeString(String(price))});
        inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }
      return false;
    })()
  `);

  if (message) {
    await evaluate(`
      (function() {
        var textarea = document.querySelector('[class*="alert"] textarea')
          || document.querySelector('textarea[placeholder*="message"]');
        if (textarea) {
          var nativeSet = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
          nativeSet.call(textarea, ${JSON.stringify(message)});
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
      })()
    `);
  }

  await new Promise(r => setTimeout(r, 500));
  const created = await evaluate(`
    (function() {
      var btns = document.querySelectorAll('button[data-name="submit"], button');
      for (var i = 0; i < btns.length; i++) {
        if (/^create$/i.test(btns[i].textContent.trim())) { btns[i].click(); return true; }
      }
      return false;
    })()
  `);

  return { success: !!created, price, condition, message: message || '(none)', price_set: !!priceSet, source: 'dom_fallback' };
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
   * Triggers the alert deletion context menu in the TradingView GUI,
   * requiring subsequent manual verification by the user to confirm.
   */
  if (delete_all) {
    const result = await evaluate(`
      (function() {
        var alertBtn = document.querySelector('[data-name="alerts"]');
        if (alertBtn) alertBtn.click();
        var header = document.querySelector('[data-name="alerts"]');
        if (header) {
          header.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, clientX: 100, clientY: 100 }));
          return { context_menu_opened: true };
        }
        return { context_menu_opened: false };
      })()
    `);
    return { success: true, note: 'Alert deletion requires manual confirmation in the context menu.', context_menu_opened: result?.context_menu_opened || false, source: 'dom_fallback' };
  }
  throw new Error('Individual alert deletion not yet supported. Use delete_all: true.');
}
