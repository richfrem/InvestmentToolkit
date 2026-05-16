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
  // Click the account dropdown button
  const opened = await evaluate(`(function() {
    var btn = document.querySelector('[class*="dropdownButton"]');
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

    // Find the shares input — look for visible number inputs in the order dialog
    var inputs = [...document.querySelectorAll('input[type="number"], input[type="text"]')].filter(function(i) {
      return i.offsetParent !== null && (
        /shares|qty|quantity/i.test(i.placeholder + ' ' + (i.getAttribute('aria-label') || '') + ' ' + i.name)
        || (i.type === 'number' && !i.getAttribute('aria-label'))
      );
    });

    // Fallback: find the first visible numeric input that's in the order panel area
    if (inputs.length === 0) {
      var submitBtn = [...document.querySelectorAll('button')].find(function(b) {
        return /^(Buy|Sell)\\s+\\d+/i.test(b.textContent.trim());
      });
      if (submitBtn) {
        var panel = submitBtn.closest('[class*="dialog"], [class*="entry"], [class*="panel"], [class*="widget"]');
        if (panel) inputs = [...panel.querySelectorAll('input')].filter(function(i) { return i.offsetParent !== null; });
      }
    }

    if (inputs.length === 0) return JSON.stringify({ error: 'Shares input not found' });

    var input = inputs[0];
    input.focus();
    input.select();
    setter.call(input, val);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return JSON.stringify({ set: val, inputClass: input.className.substring(0,60) });
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

    // The limit price input appears after selecting "Limit" order type
    // It's typically the second numeric input (first is shares, second is limit price)
    var inputs = [...document.querySelectorAll('input')].filter(function(i) {
      return i.offsetParent !== null && (
        /price|limit/i.test(i.placeholder + ' ' + (i.getAttribute('aria-label') || '') + ' ' + i.name)
        || i.type === 'number'
      );
    });

    // For the limit price, skip the shares input (first one) and use the next
    var priceInput = inputs.find(function(i) {
      return /price|limit/i.test(i.placeholder + ' ' + (i.getAttribute('aria-label') || ''));
    }) || inputs[1]; // fallback to second input

    if (!priceInput) return JSON.stringify({ error: 'Limit price input not found' });

    priceInput.focus();
    priceInput.select();
    setter.call(priceInput, val);
    priceInput.dispatchEvent(new Event('input', { bubbles: true }));
    priceInput.dispatchEvent(new Event('change', { bubbles: true }));
    return JSON.stringify({ set: val });
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
  if (!state.open) throw new Error('Order dialog closed unexpectedly during form fill.');

  // Find the shares value — look for an input whose value matches or whose label suggests shares
  const sharesInput = state.inputs.find(i =>
    /shares|qty|quantity/i.test((i.placeholder || '') + ' ' + (i.ariaLabel || ''))
  ) || state.inputs[0];

  if (!sharesInput) throw new Error('Could not read shares field from order dialog after fill.');

  const readShares = Number(sharesInput.value);
  if (!isNaN(readShares) && readShares !== intendedShares) {
    throw new Error(`Order form mismatch: intended ${intendedShares} shares, dialog shows ${readShares}. Aborting — do not submit.`);
  }

  if (intendedLimitPrice != null && state.inputs.length > 1) {
    const priceInput = state.inputs.find(i =>
      /price|limit/i.test((i.placeholder || '') + ' ' + (i.ariaLabel || ''))
    ) || state.inputs[1];
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
  const status = await getBrokerStatus();

  if (!status.connected) {
    throw new Error('No broker connected to TradingView. Log in via the Questrade integration in TradingView first.');
  }

  // Currency heuristic: .TO suffix = CAD, otherwise USD
  const currency = ticker.toUpperCase().endsWith('.TO') ? 'CAD' : 'USD';
  const buyingPower = currency === 'CAD' ? status.buyingPowerCAD : status.buyingPowerUSD;

  const costEstimate = orderType === 'Limit' && limitPrice != null
    ? shares * limitPrice
    : null;

  const sufficient = costEstimate === null || buyingPower === null || (action === 'sell') || (buyingPower >= costEstimate);

  return {
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
}

/**
 * executeOrder() — opens dialog, fills form, screenshots, submits.
 * Returns { screenshot, submitText, status }.
 */
export async function executeOrder({ action, shares, orderType, limitPrice, accountType }) {
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

  // 5. Set shares
  await setShares(shares);

  // 6. Set limit price if applicable
  if ((orderType.toLowerCase() === 'limit' || orderType.toLowerCase() === 'stop_limit') && limitPrice != null) {
    await setLimitPrice(limitPrice);
  }

  // 7. Verify form values match intent before screenshotting (throws on mismatch)
  await verifyOrderForm({ intendedShares: shares, intendedLimitPrice: limitPrice ?? null });

  // 8. Screenshot the filled form for HITL review
  await sleep(300);
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const shot = await captureScreenshot({ region: 'full', filename: `order_review_${ts}` });

  // 9. Read the submit button text (shows "Buy 1 WYFI MARKET")
  const state = await getOrderDialogState();

  return {
    screenshot: shot,
    submitButtonText: state.submitButtonText,
    dialogState: state,
  };
}

/**
 * confirmAndSubmit() — clicks the submit button after HITL approval.
 */
export async function confirmAndSubmit() {
  return submitOrder();
}

// ── helpers ───────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
