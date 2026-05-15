/**
 * broker_data.js — TradingView broker panel data reader via CDP DOM
 *
 * Reads accounts, positions, balances, and orders from TradingView's broker panel.
 * Works with any broker connected to TradingView (Questrade, IBKR, etc.)
 *
 * DOM structure confirmed via live inspection (TradingView Desktop, 2026-05-15):
 *   Tabs:     class "underline-tab-* size-xsmall-*" — compound selector avoids container match
 *   Rows:     class "ka-tr ka-row row-*" — shared by both Positions and Account Summary tables
 *   Pos cells: 9 <td class="ka-cell"> — Symbol|Long/Short|Qty|AvgFill|Profit|Time|Borrow|UUID|empty
 *   Acct cells: 6 <td class="ka-cell"> — label|CAD|USD|CAD-combined|USD-combined|empty
 *   Pos vs Acct: first td of a position row has class "leftFixedColumn-*"
 *   Account btn: class "dropdownButton-*" — renders name twice (visual+aria); use "accountName-*" span
 *   Dropdown:  account options appear as <span class=""> (empty class) matching TFSA|RRSP|Cash + digits
 *
 * Exports:
 *   getAccounts()    → [{ accountType, accountId, displayText }]
 *   getBalances()    → { totalEquityCAD, totalEquityUSD, buyingPowerCAD, buyingPowerUSD, ... }
 *   getPositions()   → { positions: [...], rowCount }
 *   getOrders()      → [{ symbol, action, qty, orderType, status, limitPrice }]
 *   getPortfolio()   → { accounts, balances, positions, orders, dataSource, timestamp }
 *   inspectBrokerPanel() → raw DOM dump for selector debugging
 */

import { evaluate } from '../connection.js';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── tab navigation ────────────────────────────────────────────────────────────

/**
 * clickTab(label) — clicks the named broker panel tab.
 * Tabs use compound class "underline-tab-* size-xsmall-*" to distinguish individual
 * tabs from their container element. Text is normalized to handle non-breaking spaces.
 */
async function clickTab(tabLabel) {
  const result = await evaluate(`(function() {
    var label = ${JSON.stringify(tabLabel)};
    // Compound selector: only individual tabs have BOTH underline-tab AND size-xsmall classes
    var tabs = [...document.querySelectorAll('[class*="underline-tab"][class*="size-xsmall"]')]
      .filter(function(t) {
        if (!t.offsetParent) return false;
        var text = t.textContent.replace(/[\\u00A0\\u2007\\u202F]/g, ' ').trim();
        return text === label || text.startsWith(label + ' ') || text.startsWith(label + '\\u00A0');
      });
    if (tabs.length === 0) return JSON.stringify({ error: 'Tab not found: ' + label });
    tabs[0].click();
    return JSON.stringify({ clicked: tabs[0].textContent.trim().substring(0, 40) });
  })()`).then(JSON.parse);
  await sleep(500);
  return result;
}

// ── accounts ──────────────────────────────────────────────────────────────────

/**
 * getAccounts() — reads the active account plus any additional accounts from the dropdown.
 * Opens the account dropdown, collects option spans (class=""), then closes it.
 */
export async function getAccounts() {
  // Step 1: Read the active account from the accountName span (single, not doubled)
  const active = await evaluate(`(function() {
    var span = document.querySelector('[class*="accountName"]');
    return JSON.stringify(span ? span.textContent.trim() : null);
  })()`).then(JSON.parse);

  // Step 2: Open the dropdown to enumerate all accounts
  const opened = await evaluate(`(function() {
    var btn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
      return b.offsetParent !== null && /TFSA|RRSP|Margin|Individual|Cash|\\d{6,}/i.test(b.textContent);
    });
    if (!btn) return JSON.stringify({ error: 'Account dropdown not found' });
    ['mousedown', 'mouseup', 'click'].forEach(function(type) {
      btn.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true }));
    });
    return JSON.stringify({ opened: true });
  })()`).then(JSON.parse);

  await sleep(500);

  // Step 3: Collect option spans — dropdown items appear as <span class=""> (empty className)
  const options = await evaluate(`(function() {
    var pattern = /^(TFSA|RRSP|Margin|Individual|Cash)\\s*[\\-\\u2013]\\s*\\d{4,}$/i;
    var spans = [...document.querySelectorAll('span')].filter(function(s) {
      return s.className === '' && pattern.test(s.textContent.trim());
    });
    return JSON.stringify(spans.map(function(s) { return s.textContent.trim(); }));
  })()`).then(JSON.parse);

  // Close dropdown
  await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
  await sleep(200);

  // Parse account text into structured objects
  function parseAccount(text) {
    var m = text.match(/^(TFSA|RRSP|Margin|Individual|Cash)\s*[-–]\s*(\d+)/i);
    return {
      accountType: m ? m[1].toUpperCase() : text.split(/[\s\-–]/)[0].toUpperCase(),
      accountId: m ? m[2] : (text.match(/\d{6,}/) || [null])[0],
      displayText: text,
    };
  }

  // Deduplicate: options from dropdown, fallback to active account
  const texts = options.length > 0 ? options : (active ? [active] : []);
  const seen = new Set();
  return texts.filter(function(t) {
    if (seen.has(t)) return false;
    seen.add(t); return true;
  }).map(parseAccount);
}

/**
 * switchAccount(targetType) — switches the broker panel to a different account.
 * targetType: 'TFSA' | 'RRSP' | 'CASH' | 'MARGIN'
 */
export async function switchAccount(targetType) {
  // Open the dropdown
  await evaluate(`(function() {
    var btn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
      return b.offsetParent !== null && /TFSA|RRSP|Margin|Individual|Cash|\\d{6,}/i.test(b.textContent);
    });
    if (btn) ['mousedown','mouseup','click'].forEach(function(t) {
      btn.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true }));
    });
  })()`);
  await sleep(400);

  // Click the matching option span's clickable parent
  const result = await evaluate(`(function() {
    var target = ${JSON.stringify(targetType.toUpperCase())};
    var span = [...document.querySelectorAll('span')].find(function(s) {
      return s.className === '' && s.textContent.trim().toUpperCase().startsWith(target);
    });
    if (!span) return JSON.stringify({ error: 'Account not found: ' + target });
    // Walk up to find the clickable parent
    var el = span;
    for (var i = 0; i < 5; i++) {
      if (!el.parentElement) break;
      el = el.parentElement;
      if (window.getComputedStyle(el).cursor === 'pointer' || el.tagName === 'BUTTON' || el.getAttribute('role') === 'option') break;
    }
    el.click();
    return JSON.stringify({ switched: span.textContent.trim() });
  })()`).then(JSON.parse);

  await sleep(400);
  return result;
}

// ── balances ──────────────────────────────────────────────────────────────────

/**
 * getBalances() — reads the Account Summary tab for full balance detail.
 *
 * Account Summary table: <td class="ka-cell"> (use td only — nested divs would double values)
 * Columns: label | CAD | USD | CAD (combined) | USD (combined) | empty(hidden)
 */
export async function getBalances() {
  await clickTab('Account summary');

  const detail = await evaluate(`(function() {
    var result = {};

    // Select only position-less rows (Account summary rows do NOT have leftFixedColumn)
    var rows = [...document.querySelectorAll('[class*="ka-row"]')].filter(function(r) {
      if (!r.offsetParent) return false;
      var firstTd = r.querySelector('td');
      return firstTd && !firstTd.className.includes('leftFixedColumn');
    });

    rows.forEach(function(row) {
      // Use td only — [class*="cell"] would double-count nested div.ka-cell-text elements
      var tds = [...row.querySelectorAll('td')];
      if (tds.length < 2) return;

      var label = tds[0].textContent.trim().toLowerCase()
        .replace(/\\s+/g, '_')
        .replace(/[&]/g, 'and');

      // Parse values from cells 1-4 (skip cell 0=label, cell 5=empty)
      var values = tds.slice(1, 5).map(function(td) {
        var t = td.textContent.trim().replace(/[$,]/g, '');
        var n = parseFloat(t);
        return isNaN(n) ? null : n;
      });

      // Map known row labels to result keys [CAD, USD, CAD-combined, USD-combined]
      var labelMap = {
        'cash':               ['cashCAD', 'cashUSD', 'cashCADCombined', 'cashUSDCombined'],
        'market_value':       ['marketValueCAD', 'marketValueUSD', 'marketValueCADCombined', 'marketValueUSDCombined'],
        'total_equity':       ['totalEquityCAD', 'totalEquityUSD', 'totalEquityCADCombined', 'totalEquityUSDCombined'],
        'buying_power':       ['buyingPowerCAD', 'buyingPowerUSD', 'buyingPowerCADCombined', 'buyingPowerUSDCombined'],
        'total_buying_power': ['totalBPCAD', 'totalBPUSD', 'totalBPCADCombined', 'totalBPUSDCombined'],
        'max_buying_power':   ['maxBPCAD', 'maxBPUSD', 'maxBPCADCombined', 'maxBPUSDCombined'],
        'open_pand_l':        ['openPnLCAD', 'openPnLUSD', 'openPnLCADCombined', 'openPnLUSDCombined'],
        'closed_pand_l':      ['closedPnLCAD', 'closedPnLUSD', 'closedPnLCADCombined', 'closedPnLUSDCombined'],
      };

      // Fuzzy label match
      var keys = labelMap[label];
      if (!keys) {
        if (/^cash$/.test(label)) keys = labelMap['cash'];
        else if (/market/.test(label)) keys = labelMap['market_value'];
        else if (/total_equity/.test(label)) keys = labelMap['total_equity'];
        else if (/buying_power$/.test(label) || /^buying/.test(label)) keys = labelMap['buying_power'];
        else if (/total_buying/.test(label)) keys = labelMap['total_buying_power'];
        else if (/max_buying/.test(label)) keys = labelMap['max_buying_power'];
        else if (/open/.test(label)) keys = labelMap['open_pand_l'];
        else if (/closed/.test(label)) keys = labelMap['closed_pand_l'];
      }

      if (keys) {
        values.forEach(function(v, i) { if (keys[i] && v !== null) result[keys[i]] = v; });
      }
    });

    return JSON.stringify(result);
  })()`).then(JSON.parse);

  // Navigate back to Positions
  await clickTab('Positions');

  return detail;
}

// ── positions ─────────────────────────────────────────────────────────────────

/**
 * getPositions() — reads all position rows from the Positions tab.
 *
 * Position rows: class "ka-tr ka-row row-*" WHERE first td has "leftFixedColumn-*"
 * Cells (9 td): Symbol | Long/Short | Qty | AvgFillPrice | Profit | UpdateTime | BorrowRate | UUID | empty
 * Note: TradingView uses U+2212 MINUS SIGN (−) for negative profits, not hyphen-minus.
 * Handles "Show more" pagination to load all positions.
 */
export async function getPositions() {
  // Ensure Positions tab is active
  await clickTab('Positions');

  // Click "Show more" until all positions are loaded
  for (let i = 0; i < 15; i++) {
    const more = await evaluate(`(function() {
      var btn = [...document.querySelectorAll('button, [role="button"]')].find(function(b) {
        return b.offsetParent !== null && /show more/i.test(b.textContent);
      });
      if (!btn) return JSON.stringify({ found: false });
      btn.click();
      return JSON.stringify({ found: true, text: btn.textContent.trim() });
    })()`).then(JSON.parse);
    if (!more.found) break;
    await sleep(400);
  }

  return evaluate(`(function() {
    // Position rows have leftFixedColumn in the first td (distinguishes from Account Summary rows)
    var rows = [...document.querySelectorAll('[class*="ka-row"]')].filter(function(r) {
      if (!r.offsetParent) return false;
      var firstTd = r.querySelector('td');
      return firstTd && firstTd.className.includes('leftFixedColumn');
    });

    var positions = [];

    rows.forEach(function(row) {
      var tds = [...row.querySelectorAll('td')];
      if (tds.length < 3) return;

      var texts = tds.map(function(t) { return t.textContent.trim(); });
      // td[0]=Symbol, td[1]=Long/Short, td[2]=Qty, td[3]=AvgFillPrice, td[4]=Profit, td[7]=UUID

      var symbol = texts[0];
      if (!symbol || !/^[A-Z]{1,6}(\.[A-Z]{1,3})?$/.test(symbol)) return;

      var direction = /^(Long|Short)$/i.test(texts[1]) ? texts[1] : null;

      function parseNum(s) {
        // Handle U+2212 MINUS SIGN (TradingView uses this for negative values)
        if (!s) return null;
        s = s.replace(/\\u2212/g, '-').replace(/[$,+]/g, '');
        var n = parseFloat(s);
        return isNaN(n) ? null : n;
      }

      var qty = parseNum(texts[2]);
      var avgFillPrice = parseNum(texts[3]);

      // Profit can be positive (+) or negative (U+2212)
      var profitText = texts[4] || '';
      var profit = parseNum(profitText.replace(/\\u2212/, '-'));

      // UUID is in td[7] — matches 8hex-4hex pattern
      var positionId = null;
      for (var i = 5; i < tds.length; i++) {
        if (/^[0-9a-f]{8}-/i.test(texts[i])) { positionId = texts[i]; break; }
      }

      positions.push({
        symbol: symbol,
        direction: direction,
        quantity: qty,
        avgFillPrice: avgFillPrice,
        profit: profit,
        positionId: positionId,
      });
    });

    return JSON.stringify({ positions: positions, rowCount: rows.length });
  })()`).then(JSON.parse);
}

// ── orders ────────────────────────────────────────────────────────────────────

/**
 * getOrders() — reads open orders from the Orders tab.
 * Order rows also use ka-row + leftFixedColumn structure.
 */
export async function getOrders() {
  await clickTab('Orders');
  await sleep(300);

  const result = await evaluate(`(function() {
    var rows = [...document.querySelectorAll('[class*="ka-row"]')].filter(function(r) {
      if (!r.offsetParent) return false;
      var firstTd = r.querySelector('td');
      return firstTd && firstTd.className.includes('leftFixedColumn');
    });

    return JSON.stringify(rows.map(function(row) {
      var tds = [...row.querySelectorAll('td')];
      var texts = tds.map(function(t) { return t.textContent.trim(); });
      return {
        symbol: texts[0] || null,
        action: texts.find(function(t) { return /^(Buy|Sell)$/i.test(t); }) || null,
        qty: parseFloat((texts[2] || '').replace(/[^-\d.]/g,'')) || null,
        orderType: texts.find(function(t) { return /^(Market|Limit|Stop|Stop Limit)$/i.test(t); }) || null,
        status: texts.find(function(t) { return /Working|Filled|Cancelled|Pending|Open|Queued/i.test(t); }) || null,
        limitPrice: null,
      };
    }).filter(function(o) { return o.symbol && /^[A-Z]{1,6}(\.[A-Z]{1,3})?$/.test(o.symbol); }));
  })()`).then(JSON.parse);

  await clickTab('Positions');
  return result;
}

// ── per-account data fetch ────────────────────────────────────────────────────

/**
 * getAccountData(accountType) — switches to a specific account and reads its
 * positions and balances. Returns combined snapshot for that account.
 */
export async function getAccountData(accountType) {
  await switchAccount(accountType);
  await sleep(600);

  const [positionsRaw, balances] = await Promise.all([
    getPositions(),
    getBalances(),
  ]);

  // Read the current account ID from the button
  const accountId = await evaluate(`(function() {
    var span = document.querySelector('[class*="accountName"]');
    if (!span) return JSON.stringify(null);
    var m = span.textContent.trim().match(/\\d{6,}/);
    return JSON.stringify(m ? m[0] : null);
  })()`).then(JSON.parse);

  return {
    accountType: accountType.toUpperCase(),
    accountId,
    balances,
    positions: positionsRaw.positions || [],
  };
}

// ── full portfolio snapshot ───────────────────────────────────────────────────

/**
 * getPortfolio() — reads all accounts and fetches positions + balances for each.
 * Schema is compatible with portfolio.json.
 */
export async function getPortfolio() {
  // Get all available accounts
  const accounts = await getAccounts();

  const accountSnapshots = [];
  for (const acct of accounts) {
    try {
      const data = await getAccountData(acct.accountType);
      accountSnapshots.push(data);
    } catch (e) {
      accountSnapshots.push({ accountType: acct.accountType, accountId: acct.accountId, error: e.message });
    }
  }

  // Return to the first account (TFSA) after iteration
  if (accounts.length > 0) {
    await switchAccount(accounts[0].accountType).catch(() => {});
  }

  // Flatten all positions across accounts (tagged with accountType)
  const allPositions = [];
  for (const snap of accountSnapshots) {
    for (const pos of (snap.positions || [])) {
      allPositions.push({ ...pos, accountType: snap.accountType, accountId: snap.accountId });
    }
  }

  return {
    dataSource: 'tradingview-cdp',
    timestamp: new Date().toISOString(),
    accounts,
    accountSnapshots,
    positions: allPositions,
  };
}

// ── DOM inspector ─────────────────────────────────────────────────────────────

export async function inspectBrokerPanel() {
  return evaluate(`(function() {
    var tabs = [...document.querySelectorAll('[class*="underline-tab"][class*="size-xsmall"]')]
      .filter(function(t) { return t.offsetParent !== null; })
      .map(function(t) { return { text: t.textContent.trim(), cls: t.className.substring(0, 80) }; });

    var rows = [...document.querySelectorAll('[class*="ka-row"]')]
      .filter(function(r) { return r.offsetParent !== null; })
      .slice(0, 6)
      .map(function(r) {
        var tds = [...r.querySelectorAll('td')];
        var firstTd = tds[0];
        return {
          isPositionRow: !!(firstTd && firstTd.className.includes('leftFixedColumn')),
          tdCount: tds.length,
          texts: tds.slice(0, 6).map(function(t) { return t.textContent.trim().substring(0, 20); }),
          cls: r.className.substring(0, 60),
        };
      });

    var acctName = document.querySelector('[class*="accountName"]');
    var dropdownBtns = [...document.querySelectorAll('[class*="dropdownButton"]')]
      .filter(function(b) { return b.offsetParent; })
      .map(function(b) { return { text: b.textContent.trim().substring(0, 50), cls: b.className.substring(0, 60) }; });

    return JSON.stringify({ tabs, rows, dropdownBtns, activeAccount: acctName ? acctName.textContent.trim() : null });
  })()`).then(JSON.parse);
}
