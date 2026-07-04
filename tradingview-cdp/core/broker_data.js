/**
 * broker_data.js — TradingView broker panel data reader via CDP DOM
 *
 * Broker-agnostic abstraction layer that reads accounts, positions, balances,
 * and orders from TradingView's built-in broker panel DOM via CDP.
 * Works with any broker connected to TradingView (Questrade, IBKR, etc.)
 *
 * DOM structure confirmed via live inspection (TradingView Desktop, 2026-05-15):
 *   Tabs:       [class*="underline-tab"][class*="size-xsmall"] — compound to avoid container match
 *   ka-rows:    Shared by Positions AND Account Summary tables (class "ka-tr ka-row row-*")
 *   Pos rows:   First <td> has class "leftFixedColumn-*"
 *   Acct rows:  First <td> does NOT have "leftFixedColumn-*"
 *   Cells:      <td class="ka-cell"> — use td-only (not [class*="cell"], which doubles nested divs)
 *   Pos cols:   9 td — Symbol|Side|Qty|AvgFillPrice|Profit|UpdateTime|BorrowRate|UUID|empty
 *   Acct cols:  6 td — label|CAD|USD|CAD-combined|USD-combined|hidden
 *   Acct btn:   [class*="dropdownButton"] — button text is doubled (visual+aria); use [class*="accountName"] span
 *   Dropdown:   Items appear as <span class=""> — MUST use MutationObserver to capture before blur closes popup
 */

import { evaluate, evaluateAsync } from '../connection.js';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── tab navigation ────────────────────────────────────────────────────────────

async function clickTab(tabLabel) {
  const result = await evaluate(`(function() {
    var label = ${JSON.stringify(tabLabel)};
    // TV updated tab class from underline-tab/size-xsmall → roundTabButton-* (2026-06 UI update)
    // offsetParent is null on TV broker tabs even when visible — do not use it as visibility guard
    var tabs = [...document.querySelectorAll('[class*="roundTabButton"], [class*="underline-tab"]')]
      .filter(function(t) {
        var text = t.textContent.replace(/[\\u00A0\\u2007\\u202F]/g, ' ').trim();
        return text === label || text.startsWith(label + ' ') || text.startsWith(label + '\\u00A0');
      });
    if (tabs.length === 0) return JSON.stringify({ error: 'Tab not found: ' + label });
    // Plain .click() does not register on TV's React tab buttons (same class of issue as the
    // broker account dropdown — React's synthetic event system needs real mouse events).
    // Dispatch mousedown + mouseup + click to both the tab and its parentElement.
    var targets = [tabs[0], tabs[0].parentElement].filter(Boolean);
    targets.forEach(function(el) {
      ['mousedown', 'mouseup', 'click'].forEach(function(type) {
        el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
      });
    });
    return JSON.stringify({ clicked: tabs[0].textContent.trim().substring(0, 40) });
  })()`).then(JSON.parse);
  await sleep(500);
  return result;
}

// ── accounts ──────────────────────────────────────────────────────────────────

/**
 * getAccounts() — enumerates all broker accounts.
 *
 * TV CSS-toggles dropdown visibility (no DOM insertion) so MutationObserver childList/attribute
 * events fire before items are queryable. Proven fix (2026-06-19): click → fixed wait → query,
 * mirroring the pattern from debug_spans.js which reliably finds all three accounts.
 * Also removed offsetParent guard — broker panel layout can set offsetParent null on the button
 * even when the panel is visible, causing the button to be skipped.
 */
async function _getAccountsOnce() {
  // Open dropdown
  await evaluate(`(function() {
    var btn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
      return /TFSA|RRSP|Cash|Margin|Individual|\\d{6,}/i.test(b.textContent);
    }) || document.querySelector('[class*="dropdownButton"]');
    if (btn) {
      ['mousedown', 'mouseup', 'click'].forEach(function(t) {
        btn.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true }));
      });
    }
  })()`);

  // Wait for TV to render dropdown items via CSS show (not DOM insertion)
  await sleep(800);

  // Query account spans while dropdown is open
  const raw = await evaluate(`(function() {
    var pattern = /^(TFSA|RRSP|Cash|Margin|Individual)[\\s\\S]*\\d{4,}/i;
    var spans = [...document.querySelectorAll('span')].filter(function(s) {
      return (s.className === '' || /accountName/i.test(s.className)) && pattern.test(s.textContent.trim());
    });
    return JSON.stringify(spans.map(function(s) { return s.textContent.trim(); }));
  })()`).then(JSON.parse);

  // Close dropdown
  await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
  await sleep(200);
  return raw;
}

export async function getAccounts() {
  // Retry up to 3 times — MutationObserver can miss the dropdown on the first attempt
  // if the broker panel is mid-render or switching tabs.
  let raw = [];
  for (let attempt = 0; attempt < 3; attempt++) {
    raw = await _getAccountsOnce();
    if (raw.length > 0) break;
    await sleep(800);
  }

  function parseAccount(text) {
    var m = text.match(/^(TFSA|RRSP|Cash|Margin|Individual)\s*[-–]\s*(\d+)/i);
    return {
      accountType: m ? m[1].toUpperCase() : text.split(/[\s\-–]/)[0].toUpperCase(),
      accountId:   m ? m[2] : (text.match(/\d{6,}/) || [null])[0],
      displayText: text,
    };
  }

  const seen = new Set();
  return raw.filter(t => { if (seen.has(t)) return false; seen.add(t); return true; })
            .map(parseAccount);
}

/**
 * switchAccount(accountType) — switches the broker panel to a specific account.
 *
 * TV CSS-toggles dropdown visibility so MutationObserver misses items. Same fix as
 * _getAccountsOnce: click → wait 800ms → query spans → click match → wait for reload.
 * Also removed offsetParent guard on button (can be null even when panel is visible).
 */
export async function switchAccount(accountType) {
  const target = accountType.toUpperCase();

  // Open dropdown
  await evaluate(`(function() {
    var btn = [...document.querySelectorAll('[class*="dropdownButton"]')].find(function(b) {
      return /TFSA|RRSP|Cash|Margin|Individual|\\d{6,}/i.test(b.textContent);
    }) || document.querySelector('[class*="dropdownButton"]');
    if (btn) {
      ['mousedown', 'mouseup', 'click'].forEach(function(t) {
        btn.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true }));
      });
    }
  })()`);

  await sleep(800);

  // Find and click the target account span
  const result = await evaluate(`(function() {
    var target = ${JSON.stringify(target)};
    var pattern = /^(TFSA|RRSP|Cash|Margin|Individual)[\\s\\S]*\\d{4,}/i;
    var spans = [...document.querySelectorAll('span')].filter(function(s) {
      return (s.className === '' || /accountName/i.test(s.className)) && pattern.test(s.textContent.trim());
    });
    var match = spans.find(function(s) {
      return s.textContent.trim().toUpperCase().startsWith(target);
    });
    if (!match) return JSON.stringify({ error: 'Account not found in dropdown: ' + target });
    // Dispatch mouse events to span and parent — .click() is unreliable on TV dropdown rows
    [match, match.parentElement].filter(Boolean).forEach(function(el) {
      ['mousedown', 'mouseup', 'click'].forEach(function(t) {
        el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true }));
      });
    });
    return JSON.stringify({ switched: match.textContent.trim() });
  })()`).then(JSON.parse);

  await sleep(1200); // wait for account data to reload
  return result;
}

/**
 * activeAccount() — returns the currently selected account type and ID.
 */
export async function activeAccount() {
  return evaluate(`(function() {
    var span = document.querySelector('[class*="accountName"]');
    if (!span) return JSON.stringify({ accountType: null, accountId: null });
    var text = span.textContent.trim();
    var m = text.match(/^(TFSA|RRSP|Cash|Margin|Individual)\\s*[-\\u2013]\\s*(\\d+)/i);
    return JSON.stringify({
      accountType: m ? m[1].toUpperCase() : text,
      accountId:   m ? m[2] : null,
      displayText: text,
    });
  })()`).then(JSON.parse);
}

// ── balances ──────────────────────────────────────────────────────────────────

/**
 * getBalances() — reads Account Summary tab for full balance detail.
 * Uses td-only cell selector to avoid double-counting from nested ka-cell-text divs.
 * Columns: label | CAD | USD | CAD (combined) | USD (combined) | empty
 */
export async function getBalances() {
  await clickTab('Account summary');

  const detail = await evaluate(`(function() {
    var result = {};

    // offsetParent is null on TV broker rows — do not use as visibility guard
    var rows = [...document.querySelectorAll('[class*="ka-row"]')].filter(function(r) {
      var firstTd = r.querySelector('td');
      return firstTd && !firstTd.className.includes('leftFixedColumn');
    });

    rows.forEach(function(row) {
      var tds = [...row.querySelectorAll('td')];
      if (tds.length < 2) return;

      var label = tds[0].textContent.trim().toLowerCase()
        .replace(/\\s+/g, '_').replace(/[&]/g, 'and');

      var values = tds.slice(1, 5).map(function(td) {
        var t = td.textContent.trim().replace(/[$,]/g, '');
        var n = parseFloat(t);
        return isNaN(n) ? null : n;
      });

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

      var keys = labelMap[label];
      if (!keys) {
        if (/^cash$/.test(label))              keys = labelMap['cash'];
        else if (/market/.test(label))          keys = labelMap['market_value'];
        else if (/total_equity/.test(label))    keys = labelMap['total_equity'];
        else if (/^buying/.test(label))         keys = labelMap['buying_power'];
        else if (/total_buying/.test(label))    keys = labelMap['total_buying_power'];
        else if (/max_buying/.test(label))      keys = labelMap['max_buying_power'];
        else if (/open/.test(label))            keys = labelMap['open_pand_l'];
        else if (/closed/.test(label))          keys = labelMap['closed_pand_l'];
      }

      if (keys) {
        values.forEach(function(v, i) { if (keys[i] && v !== null) result[keys[i]] = v; });
      }
    });

    return JSON.stringify(result);
  })()`).then(JSON.parse);

  await clickTab('Positions');
  return detail;
}

// ── positions ─────────────────────────────────────────────────────────────────

/**
 * getPositions() — reads all position rows from the Positions tab.
 * Clicks "Show more" to load all rows before reading.
 * Position rows: ka-row WHERE first td has "leftFixedColumn-*"
 * Cells: Symbol | Side | Qty | AvgFillPrice | Profit | UpdateTime | BorrowRate | UUID | empty
 */
export async function getPositions() {
  await clickTab('Positions');

  // Expand all rows via "Show more"
  for (let i = 0; i < 15; i++) {
    const more = await evaluate(`(function() {
      var btn = [...document.querySelectorAll('button, [role="button"]')].find(function(b) {
        return /show more/i.test(b.textContent);
      });
      if (!btn) return JSON.stringify({ found: false });
      btn.click();
      return JSON.stringify({ found: true });
    })()`).then(JSON.parse);
    if (!more.found) break;
    await sleep(400);
  }

  return evaluate(`(function() {
    // offsetParent is null on TV broker rows — do not use as visibility guard
    var rows = [...document.querySelectorAll('[class*="ka-row"]')].filter(function(r) {
      var firstTd = r.querySelector('td');
      return firstTd && firstTd.className.includes('leftFixedColumn');
    });

    var positions = rows.map(function(row) {
      var tds = [...row.querySelectorAll('td')];
      if (tds.length < 3) return null;
      var texts = tds.map(function(t) { return t.textContent.trim(); });

      var symbol = texts[0];
      if (!symbol || !/^[A-Z0-9_]{1,8}(\.[A-Z0-9_]{1,4})*$/.test(symbol)) return null;

      function parseNum(s) {
        if (!s) return null;
        // Handle U+2212 MINUS SIGN used by TradingView for negative values
        s = s.replace(/\\u2212/g, '-').replace(/[$,+]/g, '');
        var n = parseFloat(s);
        return isNaN(n) ? null : n;
      }

      var positionId = null;
      for (var i = 5; i < tds.length; i++) {
        if (/^[0-9a-f]{8}-/i.test(texts[i])) { positionId = texts[i]; break; }
      }

      return {
        symbol:       symbol,
        direction:    /^(Long|Short)$/i.test(texts[1]) ? texts[1] : null,
        quantity:     parseNum(texts[2]),
        avgFillPrice: parseNum(texts[3]),
        profit:       parseNum(texts[4]),
        positionId:   positionId,
      };
    }).filter(Boolean);

    return JSON.stringify({ positions: positions, rowCount: rows.length });
  })()`).then(JSON.parse);
}

// ── orders ────────────────────────────────────────────────────────────────────

export async function getOrders() {
  await clickTab('Orders');
  await sleep(300);

  const result = await evaluate(`(function() {
    // offsetParent is null on TV broker rows — do not use as visibility guard
    var rows = [...document.querySelectorAll('[class*="ka-row"]')].filter(function(r) {
      var firstTd = r.querySelector('td');
      return firstTd && firstTd.className.includes('leftFixedColumn');
    });

    return JSON.stringify(rows.map(function(row) {
      var tds = [...row.querySelectorAll('td')];
      var texts = tds.map(function(t) { return t.textContent.trim(); });
      return {
        symbol:    texts[0] || null,
        action:    texts.find(function(t) { return /^(Buy|Sell)$/i.test(t); }) || null,
        qty:       parseFloat((texts[2] || '').replace(/[^-\\d.]/g,'')) || null,
        orderType: texts.find(function(t) { return /^(Market|Limit|Stop|Stop Limit)$/i.test(t); }) || null,
        status:    texts.find(function(t) { return /Working|Filled|Cancelled|Pending|Open|Queued/i.test(t); }) || null,
      };
    }).filter(function(o) { return o.symbol && /^[A-Z]{1,6}(\\.[A-Z]{1,3})?$/.test(o.symbol); }));
  })()`).then(JSON.parse);

  await clickTab('Positions');
  return result;
}

// ── per-account snapshot ──────────────────────────────────────────────────────

/**
 * getAccountSnapshot() — reads positions + balances for whichever account is currently active.
 */
async function getAccountSnapshot() {
  const acct    = await activeAccount();
  const posResult = await getPositions();   // sequential — each call clicks a different tab
  const balances  = await getBalances();
  return {
    accountType: acct.accountType,
    accountId:   acct.accountId,
    displayText: acct.displayText,
    balances,
    positions:   posResult.positions || [],
  };
}

// ── full portfolio (all accounts) ─────────────────────────────────────────────

/**
 * getPortfolio() — iterates every available account, reads positions + balances,
 * and returns an aggregated snapshot across all accounts.
 *
 * Positions with the same symbol across accounts are kept separate (tagged with accountType).
 * The caller can aggregate quantities if needed.
 */
export async function getPortfolio() {
  const accounts = await getAccounts();
  const snapshots = [];

  for (const acct of accounts) {
    const switched = await switchAccount(acct.accountType);
    if (switched.error) {
      snapshots.push({ ...acct, error: switched.error, positions: [], balances: {} });
      continue;
    }
    const snap = await getAccountSnapshot();
    snapshots.push(snap);
  }

  // Return to first account
  if (accounts.length > 0) {
    await switchAccount(accounts[0].accountType).catch(() => {});
  }

  // All positions across all accounts, tagged with accountType
  const allPositions = [];
  for (const snap of snapshots) {
    for (const pos of (snap.positions || [])) {
      allPositions.push({ ...pos, accountType: snap.accountType, accountId: snap.accountId });
    }
  }

  return {
    dataSource:  'tradingview-cdp',
    timestamp:   new Date().toISOString(),
    accounts,
    snapshots,
    positions:   allPositions,
  };
}

// ── account totals ────────────────────────────────────────────────────────────

/**
 * getAccountTotals() — reads Total Equity USD from each account's Account Summary tab.
 * Returns per-account breakdown and grand total in USD.
 * Used by the portfolio summary endpoint and the verify_portfolio_total.py audit script.
 */
export async function getAccountTotals() {
  const accounts = await getAccounts();
  const results = [];
  let grandTotalUSD = 0;
  let grandMarketValueUSD = 0;
  let grandCashUSD = 0;

  for (const acct of accounts) {
    const switched = await switchAccount(acct.accountType);
    if (switched.error) {
      results.push({ accountType: acct.accountType, accountId: acct.accountId, error: switched.error });
      continue;
    }
    const balances = await getBalances();
    const equity  = balances.totalEquityUSD  ?? 0;
    const mktVal  = balances.marketValueUSD  ?? 0;
    const cash    = balances.cashUSD         ?? 0;
    results.push({ accountType: acct.accountType, accountId: acct.accountId,
                   totalEquityUSD: equity, marketValueUSD: mktVal, cashUSD: cash });
    grandTotalUSD       += equity;
    grandMarketValueUSD += mktVal;
    grandCashUSD        += cash;
  }

  if (accounts.length > 0) await switchAccount(accounts[0].accountType).catch(() => {});

  return { accounts: results, grandTotalUSD, grandMarketValueUSD, grandCashUSD,
           timestamp: new Date().toISOString() };
}

// ── inspectors ────────────────────────────────────────────────────────────────

export async function inspectBrokerPanel() {
  return evaluate(`(function() {
    // TV updated tab class from underline-tab/size-xsmall → roundTabButton-* (2026-06 UI update)
    // offsetParent is null on TV broker elements — do not use as visibility guard
    var tabs = [...document.querySelectorAll('[class*="roundTabButton"], [class*="underline-tab"]')]
      .map(function(t) { return { text: t.textContent.trim(), cls: t.className.substring(0, 80) }; });

    var rows = [...document.querySelectorAll('[class*="ka-row"]')]
      .slice(0, 6)
      .map(function(r) {
        var tds = [...r.querySelectorAll('td')];
        var firstTd = tds[0];
        return {
          isPositionRow: !!(firstTd && firstTd.className.includes('leftFixedColumn')),
          tdCount: tds.length,
          texts: tds.slice(0, 6).map(function(t) { return t.textContent.trim().substring(0, 20); }),
        };
      });

    var acctName = document.querySelector('[class*="accountName"]');
    return JSON.stringify({
      activeAccount: acctName ? acctName.textContent.trim() : null,
      tabs,
      rows,
    });
  })()`).then(JSON.parse);
}
