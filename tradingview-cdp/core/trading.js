/**
 * trading.js — TradingView broker order automation via CDP DOM
 *
 * Automates order placement through TradingView's built-in broker integration
 * (Questrade connected via TradingView's native broker panel). Uses CDP to:
 *   1. Verify Questrade is connected and user is authenticated
 *   2. Read buying power and available accounts from the broker panel DOM
 *   3. Open the floating order dialog by clicking the chart Buy/Sell overlay
 *   4. Fill shares, order type, limit price via React-safe input injection
 *   5. Screenshot the filled form for HITL review
 *   6. Click the submit button on confirmation
 *
 * Architecture note: TradingView's order dialog is triggered by clicking the
 * bid/ask price overlay buttons on the left of the chart (not the bottom panel).
 * These appear when a broker is connected and a chart is open.
 */

import { evaluate, evaluateAsync, getClient } from '../connection.js';
import { captureScreenshot } from './capture.js';
import { appendAuditEvent } from './audit.js';

// ── symbol switching ──────────────────────────────────────────────────────────

/**
 * switchChartSymbol(ticker) — navigates the active TradingView chart to the
 * specified ticker before opening the order dialog. The order dialog always
 * opens for whatever symbol is currently displayed on the chart, so this must
 * run before openOrderDialog(). Uses CDP Input events to type into TV's symbol
 * search and confirm with Enter.
 */
export async function switchChartSymbol(ticker) {
  const client = await getClient();
  const tickerUpper = ticker.toUpperCase();

  // Step 1: Try clicking the ticker title in the chart legend to open symbol search
  await evaluate(`(function() {
    var selectors = [
      '[data-name="legend-source-title"]',
      '[class*="pane-legend"] [class*="title-"]',
      '[class*="chart-markup-table"] [class*="title-"]',
    ];
    for (var i = 0; i < selectors.length; i++) {
      var els = document.querySelectorAll(selectors[i]);
      for (var j = 0; j < els.length; j++) {
        var el = els[j];
        if (el.offsetParent !== null && /^[A-Z0-9]{1,10}/.test(el.textContent.trim())) {
          el.click();
          return;
        }
      }
    }
    // No ticker element found — click chart body to focus it, then typing will open search
    var chart = document.querySelector('[class*="chart-markup-table"]') || document.body;
    chart.click();
  })()`);

  await sleep(400);

  // Step 2: Type the ticker via CDP Input events (reliable cross-platform key injection)
  for (const char of tickerUpper) {
    let code;
    if (/[A-Z]/.test(char)) code = 'Key' + char;
    else if (/[0-9]/.test(char)) code = 'Digit' + char;
    else if (char === '-') code = 'Minus';
    else if (char === '.') code = 'Period';
    else code = char;

    const keyCode = char.charCodeAt(0);
    await client.Input.dispatchKeyEvent({ type: 'keyDown', key: char, code, text: char, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await sleep(40);
    await client.Input.dispatchKeyEvent({ type: 'keyUp', key: char, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await sleep(40);
  }

  await sleep(800); // wait for search suggestions to load

  // Step 3: Confirm selection with Enter
  await client.Input.dispatchKeyEvent({ type: 'keyDown', key: 'Enter', code: 'Enter', keyCode: 13, windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
  await sleep(100);
  await client.Input.dispatchKeyEvent({ type: 'keyUp', key: 'Enter', code: 'Enter', keyCode: 13, windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });

  await sleep(1500); // wait for chart to fully render the new symbol
  return { switched: true, ticker: tickerUpper };
}

const REACT_INPUT_SETTER = `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set`;

// ── broker status ────────────────────────────────────────────────────────────

export async function getBrokerStatus() {
  return evaluate(`(function() {
    var questradeSvg = [...document.querySelectorAll('img')].find(function(i) {
      return /questrade/i.test(i.src);
    });
    var brokerBlock = document.querySelector('[class*="brokerBlock"]');
    var connected = !!(questradeSvg && brokerBlock);

    // Buying power: title labels and values are on separate lines in innerText
    var bodyText = document.body.innerText || document.body.textContent || '';
    var cadMatch = bodyText.match(/Buying Power\\s*-\\s*CAD[\\s\\n\\r]*\\$([\\d,\\.]+)/);
    var usdMatch = bodyText.match(/Buying Power\\s*-\\s*USD[\\s\\n\\r]*\\$([\\d,\\.]+)/);
    var cadBP = cadMatch ? parseFloat(cadMatch[1].replace(/,/g,'')) : null;
    var usdBP = usdMatch ? parseFloat(usdMatch[1].replace(/,/g,'')) : null;

    // Account dropdown — find the one showing TFSA/RRSP (not the broker dropdown)
    var accountBtn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
      return /TFSA|RRSP|Margin|Individual/i.test(b.textContent);
    });
    var accountText = accountBtn ? accountBtn.textContent.trim() : null;
    var accountMatch = accountText && accountText.match(/(TFSA|RRSP|Margin|Individual)[\\s\\-]+(\\d{4,})/i);
    var accountType = accountMatch ? accountMatch[1].toUpperCase() : null;
    var accountId   = accountMatch ? accountMatch[2] : null;

    return JSON.stringify({
      connected: connected,
      broker: connected ? 'Questrade' : null,
      accountType: accountType,
      accountId: accountId,
      buyingPowerCAD: cadBP,
      buyingPowerUSD: usdBP,
    });
  })()`).then(JSON.parse);
}

// ── account selection ────────────────────────────────────────────────────────

export async function selectAccount(targetType) {
  // Click the account dropdown button — must be the one showing TFSA/RRSP/Cash,
  // not the broker selector. Use same heuristic as getBrokerStatus.
  const opened = await evaluate(`(function() {
    var btn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
      return /TFSA|RRSP|Margin|Individual|Cash/i.test(b.textContent);
    }) || document.querySelector('[class*="dropdownButton"]');
    if (!btn) return JSON.stringify({ error: 'Account dropdown not found' });
    btn.click();
    return JSON.stringify({ opened: true, current: btn.textContent.trim().substring(0,40) });
  })()`).then(JSON.parse);

  if (opened.error) throw new Error(opened.error);

  // Wait briefly for dropdown to render
  await sleep(300);

  // Find and click the target account option
  const selected = await evaluate(`(function() {
    var target = ${JSON.stringify(targetType.toUpperCase())};
    var items = [...document.querySelectorAll('[class*="item"], [role="option"], [class*="option"]')].filter(function(el) {
      return el.textContent.trim().toUpperCase().indexOf(target) !== -1;
    });
    if (items.length === 0) {
      // Try closing dropdown and check if already on the right account
      document.querySelector('[class*="dropdownButton"]')?.click();
      return JSON.stringify({ error: 'Account type not found: ' + target });
    }
    items[0].click();
    return JSON.stringify({ selected: items[0].textContent.trim().substring(0,40) });
  })()`).then(JSON.parse);

  if (selected.error) throw new Error(selected.error);
  await sleep(300);
  return selected;
}

// ── open order dialog ────────────────────────────────────────────────────────

export async function openOrderDialog(action) {
  // The Buy/Sell overlay buttons on the chart left margin trigger the floating
  // order dialog. They have classes buyButton-* and sellButton-* (hashed suffix).
  // They are NOT standard <button> elements — they are clickable divs/spans.
  const isBuy = /buy/i.test(action);

  const result = await evaluate(`(function() {
    var isBuy = ${isBuy};
    var classFragment = isBuy ? 'buyButton' : 'sellButton';

    // Strategy 1: the chart overlay bid/ask buttons (confirmed selectors)
    var btn = document.querySelector('[class*="' + classFragment + '"]');
    if (btn && btn.offsetParent) {
      btn.click();
      return JSON.stringify({ method: 'chart-overlay-class', clicked: btn.textContent.trim().substring(0,30) });
    }

    // Strategy 2: title-SXMXfs_Z spans labeled "Buy" or "Sell" at the top of the overlay
    var label = isBuy ? 'Buy' : 'Sell';
    var spans = [...document.querySelectorAll('[class*="title-"]')].filter(function(el) {
      return el.textContent.trim() === label && el.offsetParent !== null;
    });
    if (spans.length > 0) {
      // Click the clickable parent (the button wrapper)
      var parent = spans[0].closest('[class*="button-"]') || spans[0].parentElement;
      parent.click();
      return JSON.stringify({ method: 'title-span-parent', clicked: parent.textContent.trim().substring(0,30) });
    }

    // Strategy 3: any visible element with exactly "Buy" or "Sell" text that is clickable
    var el = [...document.querySelectorAll('[class*="buy"], [class*="sell"]')].find(function(el) {
      return el.textContent.trim() === label && el.offsetParent !== null;
    });
    if (el) {
      el.click();
      return JSON.stringify({ method: 'class-text-match', clicked: el.textContent.trim() });
    }

    return JSON.stringify({ error: 'Could not find Buy/Sell overlay button. Ensure TradingView chart is open with Questrade broker connected.' });
  })()`).then(JSON.parse);

  if (result.error) throw new Error(result.error);

  // Wait for dialog to appear
  await sleep(500);
  return result;
}

// ── verify order dialog is open ──────────────────────────────────────────────

export async function getOrderDialogState() {
  return evaluate(`(function() {
    // Find the floating order dialog
    // It has a ticker header, Sell/Buy toggle, and order type tabs
    var dialog = null;

    // Look for the dialog by its structural characteristics
    var candidates = [...document.querySelectorAll('[class*="dialog"], [class*="Dialog"]')].filter(function(el) {
      return el.querySelector('input') && el.offsetParent !== null;
    });

    // Also look for the order entry panel directly
    var orderEntry = document.querySelector('[class*="orderEntry"], [class*="order-entry"]');
    if (orderEntry && orderEntry.offsetParent) candidates.unshift(orderEntry);

    // Find the one with Market/Limit/Stop tabs
    for (var i = 0; i < candidates.length; i++) {
      var text = candidates[i].textContent;
      if (/Market|Limit|Stop/i.test(text)) { dialog = candidates[i]; break; }
    }

    if (!dialog) {
      // Try finding by the submit button "Buy N TICKER MARKET"
      var submitBtn = [...document.querySelectorAll('button')].find(function(b) {
        return /^(Buy|Sell)\\s+\\d+/i.test(b.textContent.trim());
      });
      if (submitBtn) dialog = submitBtn.closest('[class*="dialog"], [class*="panel"], [class*="widget"], [class*="entry"]') || submitBtn.parentElement;
    }

    if (!dialog) return JSON.stringify({ open: false });

    // Read current state
    var inputs = [...dialog.querySelectorAll('input')].map(function(i) {
      return { placeholder: i.placeholder, value: i.value, ariaLabel: i.getAttribute('aria-label'), class: i.className.substring(0,60) };
    });
    var activeTabs = [...dialog.querySelectorAll('[class*="tab"], [role="tab"]')].filter(function(t) {
      return t.getAttribute('aria-selected') === 'true' || /active|selected/i.test(t.className);
    }).map(function(t) { return t.textContent.trim(); });
    var submitBtn2 = [...dialog.querySelectorAll('button')].find(function(b) {
      return /^(Buy|Sell)\\s+\\d+/i.test(b.textContent.trim());
    });
    var submitText = submitBtn2 ? submitBtn2.textContent.trim() : null;
    var ticker = dialog.textContent.match(/^([A-Z]{1,6})/)?.[1] || null;

    return JSON.stringify({
      open: true,
      ticker: ticker,
      inputs: inputs,
      activeTabs: activeTabs,
      submitButtonText: submitText,
      dialogClass: dialog.className.substring(0,80),
    });
  })()`).then(JSON.parse);
}

// ── select order type tab ────────────────────────────────────────────────────

export async function selectOrderType(orderType) {
  // orderType: 'Market' | 'Limit' | 'Stop' | 'Stop Limit'
  const result = await evaluate(`(function() {
    var target = ${JSON.stringify(orderType)};
    var tabs = [...document.querySelectorAll('[class*="tab"], [role="tab"]')].filter(function(t) {
      return t.offsetParent !== null && t.textContent.trim() === target;
    });
    if (tabs.length === 0) return JSON.stringify({ error: 'Tab not found: ' + target });
    tabs[0].click();
    return JSON.stringify({ selected: tabs[0].textContent.trim() });
  })()`).then(JSON.parse);

  if (result.error) throw new Error(result.error);
  await sleep(200);
  return result;
}

// ── set shares ───────────────────────────────────────────────────────────────

export async function setShares(shares) {
  const result = await evaluate(`(function() {
    var val = ${JSON.stringify(String(shares))};
    var setter = ${REACT_INPUT_SETTER};

    // Anchor search to the order dialog panel using the submit button
    var submitBtn = [...document.querySelectorAll('button')].find(function(b) {
      return /^(Buy|Sell)\\s+/i.test(b.textContent.trim()) && b.offsetParent !== null;
    });
    var root = submitBtn
      ? (submitBtn.closest('[class*="dialog"], [class*="entry"], [class*="panel"], [class*="widget"], [class*="order"]') || document)
      : document;

    var inputs = [...root.querySelectorAll('input')].filter(function(i) {
      return i.offsetParent !== null;
    });

    // Prefer an input explicitly labelled as qty/shares
    var sharesInput = inputs.find(function(i) {
      var label = (i.placeholder || '') + ' ' + (i.getAttribute('aria-label') || '') + ' ' + (i.name || '');
      return /shares|qty|quantity|amount/i.test(label);
    });

    // For Market orders qty is FIRST; for Limit orders qty is LAST (price comes first).
    // Prefer the first input with a small positive numeric value (the default qty = 1).
    // Fall back to first input if nothing else matches.
    if (!sharesInput && inputs.length > 0) {
      sharesInput = inputs.find(function(i) { return /^\d+(\.\d+)?$/.test((i.value||'').trim()); })
                    || inputs[0];
    }

    if (!sharesInput) return JSON.stringify({ error: 'Shares input not found' });

    sharesInput.focus();
    sharesInput.select();
    setter.call(sharesInput, val);
    sharesInput.dispatchEvent(new Event('input', { bubbles: true }));
    sharesInput.dispatchEvent(new Event('change', { bubbles: true }));
    return JSON.stringify({ set: val, placeholder: sharesInput.placeholder, ariaLabel: sharesInput.getAttribute('aria-label') });
  })()`).then(JSON.parse);

  if (result.error) throw new Error(result.error);
  await sleep(200);
  return result;
}

// ── set limit price ──────────────────────────────────────────────────────────

export async function setLimitPrice(price) {
  const result = await evaluate(`(function() {
    var val = ${JSON.stringify(String(price))};
    var setter = ${REACT_INPUT_SETTER};

    // Anchor search to the order dialog panel using the submit button
    var submitBtn = [...document.querySelectorAll('button')].find(function(b) {
      return /^(Buy|Sell)\\s+/i.test(b.textContent.trim()) && b.offsetParent !== null;
    });
    var root = submitBtn
      ? (submitBtn.closest('[class*="dialog"], [class*="entry"], [class*="panel"], [class*="widget"], [class*="order"]') || document)
      : document;

    var inputs = [...root.querySelectorAll('input')].filter(function(i) {
      return i.offsetParent !== null;
    });

    // Prefer an input explicitly labelled as price/limit
    var priceInput = inputs.find(function(i) {
      var label = (i.placeholder || '') + ' ' + (i.getAttribute('aria-label') || '') + ' ' + (i.name || '');
      return /limit\\s*price|price|limit/i.test(label);
    });

    // In TV's Limit order form the price field is always FIRST (qty comes after)
    if (!priceInput && inputs.length > 0) priceInput = inputs[0];

    if (!priceInput) return JSON.stringify({ error: 'Limit price input not found' });

    priceInput.focus();
    priceInput.select();
    setter.call(priceInput, val);
    priceInput.dispatchEvent(new Event('input', { bubbles: true }));
    priceInput.dispatchEvent(new Event('change', { bubbles: true }));
    return JSON.stringify({ set: val, placeholder: priceInput.placeholder, ariaLabel: priceInput.getAttribute('aria-label') });
  })()`).then(JSON.parse);

  if (result.error) throw new Error(result.error);
  await sleep(200);
  return result;
}

// ── submit order ─────────────────────────────────────────────────────────────

export async function submitOrder() {
  // Step 1: click the primary "Buy N TICKER MARKET" button
  const result = await evaluate(`(function() {
    var submitBtn = [...document.querySelectorAll('button')].find(function(b) {
      return /^(Buy|Sell)\\s+/i.test(b.textContent.trim()) && b.offsetParent !== null;
    });
    if (!submitBtn) return JSON.stringify({ error: 'Submit button not found. Is the order dialog open?' });
    var text = submitBtn.textContent.trim();
    submitBtn.click();
    return JSON.stringify({ clicked: text });
  })()`).then(JSON.parse);

  if (result.error) throw new Error(result.error);

  // Step 2: wait for secondary TradingView confirmation dialog and click it.
  // TradingView shows a secondary "Confirm Order" or "Place Order" modal
  // after the primary button click. We poll for up to 3 seconds.
  await sleep(600);
  for (let attempt = 0; attempt < 6; attempt++) {
    const confirmed = await evaluate(`(function() {
      // Look for any visible "Confirm", "Place Order", "OK", or "Yes" button
      // that appeared in a new dialog after the primary click
      var btn = [...document.querySelectorAll('button')].find(function(b) {
        if (!b.offsetParent) return false;
        var text = b.textContent.trim();
        // Match confirmation patterns — short, affirmative text
        return /^(Confirm|Place Order|Place order|Send Order|OK|Yes|Submit|Send)$/i.test(text)
          || /confirm/i.test(b.getAttribute('aria-label') || '');
      });
      if (!btn) return JSON.stringify({ found: false });
      var text = btn.textContent.trim();
      btn.click();
      return JSON.stringify({ found: true, clicked: text });
    })()`).then(JSON.parse);

    if (confirmed.found) {
      result.secondaryConfirm = confirmed.clicked;
      break;
    }
    await sleep(400);
  }

  return result;
}

// ── close order dialog ────────────────────────────────────────────────────────

export async function closeOrderDialog() {
  return evaluate(`(function() {
    var closeBtn = [...document.querySelectorAll('button, [role="button"]')].find(function(b) {
      var al = b.getAttribute('aria-label') || '';
      var text = b.textContent.trim();
      return /close|dismiss|cancel/i.test(al) && b.offsetParent !== null;
    });
    if (!closeBtn) {
      // Try pressing Escape
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      return JSON.stringify({ method: 'escape' });
    }
    closeBtn.click();
    return JSON.stringify({ method: 'close-button' });
  })()`).then(JSON.parse);
}

// ── pre-submission form verification ─────────────────────────────────────────

/**
 * verifyOrderForm() — reads the dialog state after filling and compares to intended values.
 * Throws if shares is unreadable or mismatched; warns if limit price deviates by >$0.01.
 * Call after setShares/setLimitPrice, before screenshot.
 */
export async function verifyOrderForm({ intendedShares, intendedLimitPrice = null } = {}) {
  const state = await getOrderDialogState();
  if (!state.open) {
    appendAuditEvent('FORM_MISMATCH_ABORTED', { reason: 'Order dialog closed unexpectedly during form fill.' });
    throw new Error('Order dialog closed unexpectedly during form fill.');
  }

  // Shares is always the LAST input in TV's order form (price inputs come first)
  const sharesInput = state.inputs.find(i =>
    /shares|qty|quantity|amount/i.test((i.placeholder || '') + ' ' + (i.ariaLabel || ''))
  ) || state.inputs[state.inputs.length - 1];

  if (!sharesInput) {
    appendAuditEvent('FORM_MISMATCH_ABORTED', { reason: 'Could not read shares field from order dialog after fill.' });
    throw new Error('Could not read shares field from order dialog after fill.');
  }

  const readShares = Number(sharesInput.value);
  if (!isNaN(readShares) && readShares !== intendedShares) {
    const msg = `Order form mismatch: intended ${intendedShares} shares, dialog shows ${readShares}. Aborting — do not submit.`;
    appendAuditEvent('FORM_MISMATCH_ABORTED', { intendedShares, readShares, reason: msg });
    throw new Error(msg);
  }

  if (intendedLimitPrice != null && state.inputs.length > 1) {
    // Price is always the FIRST input in TV's Limit order form
    const priceInput = state.inputs.find(i =>
      /limit\s*price|price|limit/i.test((i.placeholder || '') + ' ' + (i.ariaLabel || ''))
    ) || state.inputs[0];
    if (priceInput) {
      const readPrice = Number(priceInput.value);
      if (!isNaN(readPrice) && Math.abs(readPrice - intendedLimitPrice) > 0.01) {
        throw new Error(`Order form mismatch: intended limit $${intendedLimitPrice}, dialog shows $${readPrice}. Aborting.`);
      }
    }
  }

  return state;
}

// ── full order flow ───────────────────────────────────────────────────────────

/**
 * preflight() — checks broker connection, account, and buying power.
 * Does NOT open any dialog. Returns a confirmation card.
 */
export async function preflight({ ticker, action, shares, orderType, limitPrice, accountType }) {
  appendAuditEvent('ORDER_REQUESTED', { ticker, action, shares, orderType, limitPrice, accountType });

  const status = await getBrokerStatus();

  if (!status.connected) {
    appendAuditEvent('ORDER_ABORTED', { reason: 'No broker connected', ticker, action, shares });
    throw new Error('No broker connected to TradingView. Log in via the Questrade integration in TradingView first.');
  }

  // Currency heuristic: .TO suffix = CAD, otherwise USD
  const currency = ticker.toUpperCase().endsWith('.TO') ? 'CAD' : 'USD';
  const buyingPower = currency === 'CAD' ? status.buyingPowerCAD : status.buyingPowerUSD;

  const costEstimate = orderType === 'Limit' && limitPrice != null
    ? shares * limitPrice
    : null;

  const sufficient = costEstimate === null || buyingPower === null || (action === 'sell') || (buyingPower >= costEstimate);

  const card = {
    ticker: ticker.toUpperCase(),
    action: action.charAt(0).toUpperCase() + action.slice(1).toLowerCase(),
    shares,
    currency,
    orderType,
    limitPrice: limitPrice ?? null,
    priceDisplay: orderType === 'Limit' && limitPrice != null
      ? `$${limitPrice.toFixed(2)} ${currency} (Limit)`
      : `Market (${currency})`,
    accountType: (accountType || status.accountType || '?').toUpperCase(),
    accountId: status.accountId,
    buyingPower: buyingPower,
    buyingPowerDisplay: buyingPower != null ? `$${buyingPower.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}` : 'Unknown',
    costEstimate,
    costEstimateDisplay: costEstimate != null
      ? `$${costEstimate.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`
      : `~Market × ${shares} shares`,
    coverage: {
      sufficient,
      warning: sufficient ? null : `Insufficient ${currency} buying power. Need $${costEstimate?.toFixed(2)}, have $${buyingPower?.toFixed(2)}.`,
    },
    broker: status.broker,
    _warning: sufficient ? null : `Insufficient ${currency} buying power.`,
  };
  appendAuditEvent('PREFLIGHT_PASSED', {
    ticker: card.ticker, action: card.action, shares, orderType,
    limitPrice: limitPrice ?? null, accountType: card.accountType,
    costEstimate, buyingPower, sufficient,
  });
  return card;
}

/**
 * executeOrder() — switches chart to ticker, opens dialog, fills form, screenshots.
 * Returns { screenshot, submitText, status }.
 */
export async function executeOrder({ ticker, action, shares, orderType, limitPrice, accountType }) {
  // 0. Switch chart to the target ticker — the order dialog opens for the active chart symbol,
  //    so this must happen before openOrderDialog().
  if (ticker) {
    appendAuditEvent('CHART_SWITCH', { ticker });
    await switchChartSymbol(ticker);
  }

  // 1. Switch account if needed
  const status = await getBrokerStatus();
  if (accountType && status.accountType && status.accountType.toUpperCase() !== accountType.toUpperCase()) {
    await selectAccount(accountType);
    await sleep(400);
  }

  // 2. Open the order dialog
  await openOrderDialog(action);
  await sleep(600);

  // 3. Verify dialog opened
  let dialogState = await getOrderDialogState();
  if (!dialogState.open) {
    // Retry once — sometimes the click doesn't register immediately
    await openOrderDialog(action);
    await sleep(800);
    dialogState = await getOrderDialogState();
    if (!dialogState.open) {
      throw new Error('Order dialog did not open. Try clicking the Buy/Sell price button on your chart manually first.');
    }
  }

  // 4. Select order type
  const orderTypeLabel = orderType.charAt(0).toUpperCase() + orderType.slice(1).toLowerCase();
  // Map 'market' → 'Market', 'limit' → 'Limit', 'stop' → 'Stop', 'stop_limit' → 'Stop Limit'
  const tabLabel = orderType.toLowerCase() === 'stop_limit' ? 'Stop Limit'
    : orderTypeLabel;
  await selectOrderType(tabLabel);

  // 5. Set limit price first — it's the first input in TV's form (price above qty)
  if ((orderType.toLowerCase() === 'limit' || orderType.toLowerCase() === 'stop_limit') && limitPrice != null) {
    await setLimitPrice(limitPrice);
  }

  // 6. Set shares — always the last input in TV's form
  await setShares(shares);

  // 7. Verify form values match intent before screenshotting (throws on mismatch)
  await verifyOrderForm({ intendedShares: shares, intendedLimitPrice: limitPrice ?? null });

  // 8. Screenshot the filled form for HITL review
  await sleep(300);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const shot = await captureScreenshot({ region: 'full', filename: `order_review_${ts}` });

  // 9. Read the submit button text (shows "Buy 1 WYFI MARKET")
  const state = await getOrderDialogState();

  appendAuditEvent('FORM_FILLED', {
    action, shares, orderType, limitPrice: limitPrice ?? null,
    submitButtonText: state.submitButtonText,
    screenshot: shot,
  });

  return {
    screenshot: shot,
    submitButtonText: state.submitButtonText,
    dialogState: state,
  };
}

/**
 * verifyOrderInBrokerPanel() — reads the Questrade Orders panel in TradingView
 * after submission to confirm the order appears. Navigates to the Orders tab,
 * clicks the Inactive/Working sub-tab, and searches for the most recent matching row.
 */
export async function verifyOrderInBrokerPanel({ ticker, action, limitPrice } = {}) {
  // Navigate to the Orders tab in the broker panel
  await evaluate(`(function() {
    var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
      return b.offsetParent !== null && /^Orders(\\s*\\d+)?$/i.test(b.textContent.trim());
    });
    if (tabs.length > 0) tabs[0].click();
  })()`);
  await sleep(600);

  // Click Inactive sub-tab — new limit orders land here before they fill
  await evaluate(`(function() {
    var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
      return b.offsetParent !== null && /^(Inactive|Working)(\\s*\\d+)?$/i.test(b.textContent.trim());
    });
    if (tabs.length > 0) tabs[0].click();
  })()`);
  await sleep(500);

  return evaluate(`(function() {
    var tickerUpper = ${JSON.stringify((ticker || '').toUpperCase())};
    var actionUpper = ${JSON.stringify((action || 'buy').toUpperCase())};
    var targetPrice = ${JSON.stringify(limitPrice ?? null)};

    // Find all visible rows that contain the ticker symbol
    var rows = [...document.querySelectorAll('tr, [class*="row"]')].filter(function(r) {
      return r.offsetParent !== null && r.textContent.includes(tickerUpper)
        && !/Symbol.*Side.*Type/i.test(r.textContent); // skip header rows
    });

    if (rows.length === 0) return JSON.stringify({ found: false, reason: 'No rows for ' + tickerUpper + ' in Inactive tab' });

    var parsed = rows.map(function(row) {
      var text = row.textContent.replace(/\\s+/g, ' ').trim();
      var orderIdMatch = text.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
      var prices = (text.match(/[\\d,]+\\.\\d{2}/g) || []).map(Number);
      var timeMatch = text.match(/\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2}:\\d{2}/);
      return {
        text: text.substring(0, 200),
        orderId: orderIdMatch ? orderIdMatch[0] : null,
        prices: prices,
        time: timeMatch ? timeMatch[0] : null,
        hasSide: text.toUpperCase().includes(actionUpper),
        priceMatch: targetPrice != null ? prices.some(function(p) { return Math.abs(p - targetPrice) < 0.05; }) : true,
      };
    });

    // Prefer a row that matches both side and price; fall back to first with side match
    var best = parsed.find(function(r) { return r.hasSide && r.priceMatch; })
      || parsed.find(function(r) { return r.hasSide; })
      || parsed[0];

    return JSON.stringify({ found: true, best: best, totalRows: parsed.length });
  })()`).then(JSON.parse);
}

/**
 * confirmAndSubmit() — clicks the submit button after HITL approval,
 * then reads the broker panel to confirm the order was registered.
 */
export async function confirmAndSubmit({ ticker, action, limitPrice } = {}) {
  appendAuditEvent('USER_CONFIRMED_SUBMIT', {});
  const result = await submitOrder();
  appendAuditEvent('ORDER_SUBMITTED', { clicked: result.clicked, secondaryConfirm: result.secondaryConfirm ?? null });

  // Give TV a moment to register the order before reading the panel
  await sleep(1500);
  try {
    const verification = await verifyOrderInBrokerPanel({ ticker, action, limitPrice });
    result.brokerVerification = verification;
    if (verification.found && verification.best?.orderId) {
      appendAuditEvent('ORDER_CONFIRMED_IN_BROKER_PANEL', {
        orderId: verification.best.orderId,
        time: verification.best.time,
        priceMatch: verification.best.priceMatch,
      });
    } else {
      appendAuditEvent('ORDER_BROKER_PANEL_NOT_FOUND', { reason: verification.reason ?? 'No matching row' });
    }
  } catch (e) {
    result.brokerVerification = { found: false, reason: e.message };
  }

  return result;
}

// ── cancel order ─────────────────────────────────────────────────────────────

/**
 * cancelOrder({ orderId, ticker, action, limitPrice }) — locates an order in
 * TradingView's Inactive or Working sub-tab by UUID and clicks its cancel ×
 * button. Handles a secondary confirmation dialog if TV shows one.
 * Returns { cancelled, verified, orderId, ticker, reason }.
 */
// Shared helper: find an order row and click its cancel (×) or edit (✏) button.
// Returns the CDP evaluate result JSON.
async function _findOrderRowAndAct({ orderId, ticker, buttonIndex }) {
  return evaluate(`(function() {
    var targetId = ${JSON.stringify(orderId || '')};
    var tickerUp = ${JSON.stringify((ticker || '').toUpperCase())};
    var btnIdx   = ${JSON.stringify(buttonIndex)}; // -1 = last (cancel), -2 = second-to-last (edit)

    var rows = [...document.querySelectorAll('tr, [class*="row"]')].filter(function(r) {
      if (!r.offsetParent) return false;
      var text = r.textContent;
      if (targetId && text.includes(targetId)) return true;
      if (!targetId && tickerUp && text.includes(tickerUp)) return true;
      return false;
    });

    if (rows.length === 0) return JSON.stringify({ found: false });

    var row = rows[0];
    var extractedId = (row.textContent.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i) || [])[0] || targetId;

    var btns = [...row.querySelectorAll('button, [role="button"], svg')].filter(function(b) {
      return b.offsetParent !== null && (b.tagName === 'BUTTON' || b.getAttribute('role') === 'button');
    });

    var idx = btnIdx < 0 ? btns.length + btnIdx : btnIdx;
    var btn = btns[idx];
    if (!btn) {
      // Fallback: search by aria-label
      if (btnIdx === -1) btn = btns.find(function(b) { return /cancel|dismiss|close|remove/i.test(b.getAttribute('aria-label') || ''); });
      if (btnIdx === -2) btn = btns.find(function(b) { return /edit|modify|pencil/i.test(b.getAttribute('aria-label') || ''); });
    }

    if (!btn) return JSON.stringify({ found: true, orderId: extractedId, clickable: false, reason: 'Button not found (idx=' + idx + ', total=' + btns.length + ')' });

    btn.click();
    return JSON.stringify({ found: true, orderId: extractedId, clickable: true, btnLabel: btn.getAttribute('aria-label') || btn.textContent.trim().substring(0, 10) });
  })()`).then(JSON.parse);
}

export async function cancelOrder({ orderId, ticker, action, limitPrice } = {}) {
  // Strategy 1: find the row directly without navigating tabs.
  // Rows may already be visible if the broker panel is open.
  // Navigating to "Orders" tab can TOGGLE the panel closed — so try without first.
  let result = await _findOrderRowAndAct({ orderId, ticker, buttonIndex: -1 });

  // Strategy 2: try clicking Orders tab, then Inactive / Working sub-tabs
  if (!result.found) {
    await evaluate(`(function() {
      var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
        return b.offsetParent !== null && /^Orders(\\s*\\d+)?$/i.test(b.textContent.trim());
      });
      if (tabs.length > 0) tabs[0].click();
    })()`);
    await sleep(700);

    for (const subTab of ['Inactive', 'Working']) {
      await evaluate(`(function() {
        var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
          return b.offsetParent !== null && /^(${subTab})(\\s*\\d+)?$/i.test(b.textContent.trim());
        });
        if (tabs.length > 0) tabs[0].click();
      })()`);
      await sleep(500);

      result = await _findOrderRowAndAct({ orderId, ticker, buttonIndex: -1 });
      if (result.found) break;
    }
  }

  if (!result.found) {
    appendAuditEvent('CANCEL_ORDER_NOT_FOUND', { orderId, ticker });
    return { cancelled: false, orderId, ticker, reason: 'Order row not found in broker panel' };
  }

  if (!result.clickable) {
    appendAuditEvent('CANCEL_BUTTON_MISSING', { orderId, ticker, reason: result.reason });
    return { cancelled: false, orderId: result.orderId, ticker, reason: result.reason };
  }

  appendAuditEvent('CANCEL_CLICKED', { orderId: result.orderId, ticker });

  // Poll for a secondary confirmation dialog ("Cancel this order? Yes / No")
  await sleep(400);
  for (let i = 0; i < 5; i++) {
    const confirmed = await evaluate(`(function() {
      var btn = [...document.querySelectorAll('button')].find(function(b) {
        if (!b.offsetParent) return false;
        return /^(Yes|Confirm|Cancel Order|OK)$/i.test(b.textContent.trim());
      });
      if (!btn) return JSON.stringify({ found: false });
      btn.click();
      return JSON.stringify({ found: true, clicked: btn.textContent.trim() });
    })()`).then(JSON.parse);
    if (confirmed.found) { appendAuditEvent('CANCEL_CONFIRMED', { clicked: confirmed.clicked }); break; }
    await sleep(300);
  }

  // Verify the row is gone
  await sleep(1000);
  const gone = await evaluate(`(function() {
    var targetId = ${JSON.stringify(result.orderId || orderId || '')};
    var rows = [...document.querySelectorAll('tr, [class*="row"]')].filter(function(r) {
      return r.offsetParent !== null && targetId && r.textContent.includes(targetId);
    });
    return JSON.stringify({ remaining: rows.length });
  })()`).then(JSON.parse);

  const verified = gone.remaining === 0;
  appendAuditEvent(verified ? 'ORDER_CANCELLED' : 'CANCEL_UNVERIFIED', { orderId: result.orderId, ticker, verified });
  return { cancelled: true, verified, orderId: result.orderId, ticker, action };
}

// ── modify order ─────────────────────────────────────────────────────────────

/**
 * modifyOrder({ orderId, ticker, newLimitPrice, newShares }) — clicks the pencil
 * edit button on an existing Working/Inactive order, updates price/qty via
 * React-safe input injection, and screenshots the filled edit form.
 * Caller must invoke submitModify() to confirm the change.
 */
export async function modifyOrder({ orderId, ticker, action, newLimitPrice, newShares } = {}) {
  // Strategy 1: find row directly without nav (same fix as cancelOrder)
  let clickResult = await _findOrderRowAndAct({ orderId, ticker, buttonIndex: -2 });

  // Strategy 2: navigate to Orders tab → Inactive/Working if not found directly
  if (!clickResult.found) {
    await evaluate(`(function() {
      var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
        return b.offsetParent !== null && /^Orders(\\s*\\d+)?$/i.test(b.textContent.trim());
      });
      if (tabs.length > 0) tabs[0].click();
    })()`);
    await sleep(700);

    for (const subTab of ['Inactive', 'Working']) {
      await evaluate(`(function() {
        var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
          return b.offsetParent !== null && /^(${subTab})(\\s*\\d+)?$/i.test(b.textContent.trim());
        });
        if (tabs.length > 0) tabs[0].click();
      })()`);
      await sleep(500);
      clickResult = await _findOrderRowAndAct({ orderId, ticker, buttonIndex: -2 });
      if (clickResult.found) break;
    }
  }

  if (!clickResult.found) return { modified: false, orderId, ticker, reason: 'Order row not found in broker panel' };
  if (!clickResult.clickable) return { modified: false, orderId: clickResult.orderId, ticker, reason: clickResult.reason };

  appendAuditEvent('MODIFY_PENCIL_CLICKED', { orderId: clickResult.orderId, ticker });
  await sleep(900); // wait for edit form to open

  const c = await getClient();

  // Snapshot inputs before filling
  const formBefore = await evaluate(`(function() {
    var inputs = [...document.querySelectorAll('input')].filter(function(i) { return i.offsetParent !== null; });
    return JSON.stringify(inputs.map(function(i) { return { placeholder: i.placeholder, value: i.value, label: i.getAttribute('aria-label') || '' }; }));
  })()`).then(s => { try { return JSON.parse(s); } catch { return []; } });

  // Helper: focus an input and type a value using real keyboard events.
  // This is more reliable than the React property setter for modify dialogs
  // because TV's modify form may use different React state bindings.
  async function typeIntoInput(inputFinder, valueStr) {
    // Focus the target input
    await evaluate(`(function() {
      var inputs = [...document.querySelectorAll('input')].filter(function(i) { return i.offsetParent !== null; });
      var inp = ${inputFinder};
      if (inp) { inp.focus(); inp.click(); }
    })()`);
    await sleep(80);

    // Select all existing text (Ctrl+A)
    await c.Input.dispatchKeyEvent({ type: 'keyDown', key: 'a', code: 'KeyA', modifiers: 2, windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
    await sleep(30);
    await c.Input.dispatchKeyEvent({ type: 'keyUp',   key: 'a', code: 'KeyA', modifiers: 2, windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65 });
    await sleep(50);

    // Type the new value character by character
    await c.Input.insertText({ text: valueStr });
    await sleep(80);

    // Tab out to trigger blur/change
    await c.Input.dispatchKeyEvent({ type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9 });
    await sleep(50);
    await c.Input.dispatchKeyEvent({ type: 'keyUp',   key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9, nativeVirtualKeyCode: 9 });
    await sleep(100);
  }

  // Fill limit price
  if (newLimitPrice != null) {
    await typeIntoInput(
      `inputs.find(function(i) { return /price|limit/i.test((i.placeholder||'')+(i.getAttribute('aria-label')||'')); }) || inputs[0]`,
      String(newLimitPrice)
    );
  }

  // Fill shares if needed
  if (newShares != null) {
    await typeIntoInput(
      `inputs.find(function(i) { return /shares|qty|quantity/i.test((i.placeholder||'')+(i.getAttribute('aria-label')||'')); }) || inputs[inputs.length - 1]`,
      String(newShares)
    );
  }

  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const shot = await captureScreenshot({ region: 'full', filename: `order_modify_${ts}` });
  appendAuditEvent('ORDER_MODIFY_FORM_FILLED', { orderId: clickResult.orderId, ticker, newLimitPrice, newShares });

  return {
    modified: true,
    needsSubmit: true,
    orderId: clickResult.orderId,
    ticker,
    screenshot: shot,
    formBefore,
  };
}

/**
 * submitModify() — clicks the submit/save button after the modify form is filled.
 * TV reuses the same order dialog for modifications; the button patterns are
 * the same as submitOrder() but also matches "Save", "Modify", "Apply".
 */
export async function submitModify({ ticker, action, limitPrice } = {}) {
  // Primary button — same pattern as initial order form
  const result = await evaluate(`(function() {
    // Try "Buy/Sell N TICKER TYPE" pattern (TV reuses initial dialog)
    var btn = [...document.querySelectorAll('button')].find(function(b) {
      return /^(Buy|Sell)\\s+/i.test(b.textContent.trim()) && b.offsetParent !== null;
    });
    // Fallback: Save / Modify / Apply / Change / Confirm
    if (!btn) btn = [...document.querySelectorAll('button')].find(function(b) {
      if (!b.offsetParent) return false;
      return /^(Save|Modify|Apply|Change|Confirm|Place Order|Place)$/i.test(b.textContent.trim());
    });
    if (!btn) return JSON.stringify({ error: 'No submit button found for modify' });
    var text = btn.textContent.trim();
    btn.click();
    return JSON.stringify({ clicked: text });
  })()`).then(JSON.parse);

  if (result.error) throw new Error(result.error);

  // Poll for secondary confirmation dialog
  await sleep(600);
  for (let i = 0; i < 6; i++) {
    const confirmed = await evaluate(`(function() {
      var btn = [...document.querySelectorAll('button')].find(function(b) {
        if (!b.offsetParent) return false;
        return /^(Confirm|Place Order|Place|OK|Yes|Modify|Save|Change|Apply)$/i.test(b.textContent.trim());
      });
      if (!btn) return JSON.stringify({ found: false });
      btn.click();
      return JSON.stringify({ found: true, clicked: btn.textContent.trim() });
    })()`).then(JSON.parse);
    if (confirmed.found) { result.secondaryConfirm = confirmed.clicked; break; }
    await sleep(400);
  }

  appendAuditEvent('ORDER_MODIFY_SUBMITTED', { ticker, action, limitPrice, ...result });
  await sleep(1500);

  // Verify new price appears in broker panel
  try {
    const verification = await verifyOrderInBrokerPanel({ ticker, action, limitPrice });
    result.brokerVerification = verification;
    if (verification.found) {
      appendAuditEvent('ORDER_MODIFY_CONFIRMED', { priceMatch: verification.best?.priceMatch });
    }
  } catch (e) {
    result.brokerVerification = { found: false, reason: e.message };
  }

  return result;
}

/**
 * listOpenOrders() — returns ALL open orders from TradingView broker panel.
 * Navigates to Orders tab, reads Working + Inactive sub-tabs, returns every
 * row as { orderId, ticker, side, limitPrice, status, text }.
 * Used by tv_get_orders.py and the trade-log sync-from-TV endpoint.
 *
 * Returns: { found: true, orders: [{orderId, ticker, side, limitPrice, status, text}] }
 *       or { found: false, error: string }
 */
export async function listOpenOrders() {
  // Click the Orders tab in the broker panel
  await evaluate(`(function() {
    var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
      return b.offsetParent !== null && /^Orders(\\s*\\d+)?$/i.test(b.textContent.trim());
    });
    if (tabs.length > 0) tabs[0].click();
  })()`);
  await sleep(600);

  const allOrders = [];

  for (const subTab of ['Working', 'Inactive']) {
    await evaluate(`(function() {
      var tabs = [...document.querySelectorAll('[role="tab"], button')].filter(function(b) {
        return b.offsetParent !== null && new RegExp('^${subTab}(\\\\s*\\\\d+)?$', 'i').test(b.textContent.trim());
      });
      if (tabs.length > 0) tabs[0].click();
    })()`);
    await sleep(500);

    const rows = await evaluate(`(function() {
      var rows = [...document.querySelectorAll('tr, [class*="row"]')].filter(function(r) {
        return r.offsetParent !== null && !/Symbol.*Side.*Type/i.test(r.textContent);
      });
      return JSON.stringify(rows.map(function(row) {
        var text = row.textContent.replace(/\\s+/g, ' ').trim();
        if (!text || text.length < 5) return null;
        var orderIdMatch = text.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
        var prices = (text.match(/[\\d,]+\\.\\d{2}/g) || []).map(Number);
        // Extract ticker: first 1-5 uppercase word at start of row text
        var tickerMatch = text.match(/^([A-Z]{1,6}(?:\\.[A-Z]{1,3})?)/);
        return {
          orderId: orderIdMatch ? orderIdMatch[0] : null,
          ticker: tickerMatch ? tickerMatch[1] : null,
          side: /\\bBuy\\b/i.test(text) ? 'buy' : /\\bSell\\b/i.test(text) ? 'sell' : null,
          limitPrice: prices.length > 0 ? prices[0] : null,
          status: '${subTab.toLowerCase()}',
          text: text.substring(0, 200),
        };
      }).filter(Boolean));
    })()`).then(JSON.parse);

    for (const row of rows) {
      if (row.orderId && !allOrders.find(o => o.orderId === row.orderId)) {
        allOrders.push(row);
      }
    }
  }

  return { found: true, orders: allOrders };
}

// ── helpers ───────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
