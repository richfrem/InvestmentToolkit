/**
 * connection.js - Core Chrome DevTools Protocol (CDP) WebSocket connection pool.
 * 
 * Purpose:
 *   Handles target discovery, connection initialization, retries, and JS execution
 *   on the active TradingView Desktop page.
 * 
 * Key Input Dependencies:
 *   None (discovers Chrome/TradingView debugging target list on port 9222/9333)
 * 
 * Key Output Dependencies:
 *   None (returns active CDP client connection object)
 */

import CDP from 'chrome-remote-interface';

let client = null;
let targetInfo = null;
const CDP_HOST = 'localhost';
// Read port from env var so the port can be randomized without editing source.
// Launch TradingView with a non-standard port: TV_CDP_PORT=9333 python3 run_investment_toolkit.py
// connection.js and the launch scripts both honour this variable.
const CDP_PORT = parseInt(process.env.TV_CDP_PORT || '9222', 10);
const MAX_RETRIES = 5;
const BASE_DELAY = 500;

const KNOWN_PATHS = {
  chartApi: 'window.TradingViewApi._activeChartWidgetWV.value()',
  chartWidgetCollection: 'window.TradingViewApi._chartWidgetCollection',
  bottomWidgetBar: 'window.TradingView.bottomWidgetBar',
  replayApi: 'window.TradingViewApi._replayApi',
  alertService: 'window.TradingViewApi._alertService',
  chartApiInstance: 'window.ChartApiInstance',
  mainSeriesBars: 'window.TradingViewApi._activeChartWidgetWV.value()._chartWidget.model().mainSeries().bars()',
};

export { KNOWN_PATHS };

/**
 * Sanitize a string for safe interpolation into JavaScript evaluated via CDP.
 * 
 * Uses JSON.stringify to produce a properly escaped JS string literal (with quotes).
 * 
 * @param {string} str Target string to sanitize
 * @returns {string} Sanitized and escaped string literal
 */
export function safeString(str) {
  /**
   * Coerces input to string and delegates to native JSON stringify wrapper.
   */
  return JSON.stringify(String(str));
}

/**
 * Validate that a value is a finite number. Throws if NaN, Infinity, or non-numeric.
 * 
 * @param {*} value Input value to check
 * @param {string} name Variable name to include in error message
 * @returns {number} Validated numeric value
 */
export function requireFinite(value, name) {
  /**
   * Casts value to number, asserts finiteness, and raises an exception if invalid.
   */
  const n = Number(value);
  if (!Number.isFinite(n)) throw new Error(`${name} must be a finite number, got: ${value}`);
  return n;
}

/**
 * Get the active CDP client connection, reconnecting if disconnected.
 * 
 * @returns {Promise<object>} Active CDP client instance
 */
export async function getClient() {
  /**
   * Asserts existing client responsiveness by evaluating a test expression,
   * clearing state and reconnecting if a socket error is encountered.
   */
  if (client) {
    try {
      await client.Runtime.evaluate({ expression: '1', returnByValue: true });
      return client;
    } catch {
      client = null;
      targetInfo = null;
    }
  }
  return connect();
}

/**
 * Establish a new CDP connection to the discovered TradingView chart target.
 * 
 * @returns {Promise<object>} Initialized CDP client instance
 */
export async function connect() {
  /**
   * Loops up to MAX_RETRIES, resolves the url targets list, selects the chart page target,
   * instantiates chrome-remote-interface, and enables Page/Runtime/DOM agents.
   */
  let lastError;
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const target = await findChartTarget();
      if (!target) {
        throw new Error('No TradingView chart target found. Is TradingView open with a chart?');
      }
      targetInfo = target;
      client = await CDP({ host: CDP_HOST, port: CDP_PORT, target: target.id });

      await client.Runtime.enable();
      await client.Page.enable();
      await client.DOM.enable();

      return client;
    } catch (err) {
      lastError = err;
      const delay = Math.min(BASE_DELAY * Math.pow(2, attempt), 30000);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  throw new Error(`CDP connection failed after ${MAX_RETRIES} attempts: ${lastError?.message}`);
}

/**
 * Find the chart target page info from the Chrome DevTools endpoint list.
 * 
 * @returns {Promise<object|null>} Discovered target info object, or null if missing
 */
async function findChartTarget() {
  /**
   * Requests http json list, parses URLs, and searches for page targets matching 'tradingview.com/chart'.
   */
  const resp = await fetch(`http://${CDP_HOST}:${CDP_PORT}/json/list`);
  const targets = await resp.json();
  return targets.find(t => t.type === 'page' && /tradingview\.com\/chart/i.test(t.url))
    || targets.find(t => t.type === 'page' && /tradingview/i.test(t.url))
    || null;
}

/**
 * Retrieve cached target information metadata.
 * 
 * @returns {Promise<object>} Active target info object
 */
export async function getTargetInfo() {
  /**
   * Requests client initialization if cache is empty, then returns cached metadata.
   */
  if (!targetInfo) {
    await getClient();
  }
  return targetInfo;
}

/**
 * Evaluate JavaScript code expression in the context of the active chart page.
 * 
 * @param {string} expression JS string to run in-page
 * @param {object} opts Evaluation configurations (e.g. awaitPromise)
 * @returns {Promise<*>} Evaluated value result
 */
export async function evaluate(expression, opts = {}) {
  /**
   * Retrieves active client connection, passes script expression to Runtime.evaluate,
   * parses exceptionDetails on errors, and returns result value.
   */
  const c = await getClient();
  const result = await c.Runtime.evaluate({
    expression,
    returnByValue: true,
    awaitPromise: opts.awaitPromise ?? false,
    ...opts,
  });
  if (result.exceptionDetails) {
    const msg = result.exceptionDetails.exception?.description
      || result.exceptionDetails.text
      || 'Unknown evaluation error';
    throw new Error(`JS evaluation error: ${msg}`);
  }
  return result.result?.value;
}

/**
 * Evaluate asynchronous JavaScript expression in the context of the active chart page.
 * 
 * @param {string} expression Async JS code string to evaluate
 * @returns {Promise<*>} Evaluated resolved promise result
 */
export async function evaluateAsync(expression) {
  /**
   * Delegates evaluation passing awaitPromise true config.
   */
  return evaluate(expression, { awaitPromise: true });
}

/**
 * Close active CDP connection socket channel.
 * 
 * @returns {Promise<void>}
 */
export async function disconnect() {
  /**
   * Attempts socket client close connection call and resets internal caches.
   */
  if (client) {
    try { await client.close(); } catch {}
    client = null;
    targetInfo = null;
  }
}

/**
 * Verify whether target JS variable expression is defined in window scope.
 * 
 * @param {string} path Variable namespace path to verify
 * @param {string} name Display title of variable
 * @returns {Promise<string>} Target path string verified
 */
async function verifyAndReturn(path, name) {
  /**
   * Checks expression typeof undefined inside browser environment and throws on missing paths.
   */
  const exists = await evaluate(`typeof (${path}) !== 'undefined' && (${path}) !== null`);
  if (!exists) {
    throw new Error(`${name} not available at ${path}`);
  }
  return path;
}

/**
 * Retrieve path path string of Chart API object.
 * 
 * @returns {Promise<string>} Path string namespace
 */
export async function getChartApi() {
  /**
   * Calls verifyAndReturn helper with activeChartWidgetWV namespace.
   */
  return verifyAndReturn(KNOWN_PATHS.chartApi, 'Chart API');
}

/**
 * Retrieve path string of Chart Widget Collection object.
 * 
 * @returns {Promise<string>} Path string namespace
 */
export async function getChartCollection() {
  /**
   * Calls verifyAndReturn helper with _chartWidgetCollection namespace.
   */
  return verifyAndReturn(KNOWN_PATHS.chartWidgetCollection, 'Chart Widget Collection');
}
