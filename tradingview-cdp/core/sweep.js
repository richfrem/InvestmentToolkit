/**
 * Batch portfolio TA sweep — scans multiple tickers in one CDP session.
 *
 * For each ticker: switches chart symbol, waits for data, reads Data Window,
 * and computes technical flags. Returns a structured JSON array.
 *
 * Flags emitted:
 *   RSI_OB        RSI > 72 — overbought, watch for fade
 *   RSI_OS        RSI < 30 — oversold, potential entry
 *   RSI_COOLING   RSI < RSI-MA and RSI-MA > 62 — was extended, momentum fading
 *   ADX_STRONG    ADX > 30 — trend confirmed, don't fade
 *   ADX_WEAK      ADX < 20 — ranging / no trend conviction
 *   SQUEEZE_ON    Squeeze = 1 — compression building, big move pending
 *   DIST_SIGNAL   Vol Bias < -50 — distribution (selling into strength)
 *   ACCUM_SIGNAL  Vol Bias > +50 — accumulation (buying into weakness)
 *   VOLUME_SPIKE  Volume > 1.8× MA — institutional activity
 *   VOLUME_DRY    Volume < 0.5× MA AND day move > 2% — weak conviction
 *   BIG_DAY       |daily %| > 4 — outsized move, needs context
 */

import { changeSymbol, openDataWindow, readDataWindow } from './chart.js';

/**
 * Parse a Data Window value string to float.
 * Handles commas, % signs, unicode minus (−), and K/M/B suffixes.
 *
 * TV shows large numbers with suffixes (e.g. "363K", "1.29M") — these must be
 * converted to their true magnitude before dividing vol/volMA, otherwise a ratio
 * of 363K/1.29M = 281× (false spike) appears instead of the correct 0.28×.
 *
 * Args:
 *   raw: raw string from Data Window (e.g. "23.74%", "1,234.56", "−108.51%", "363K", "1.29M")
 *
 * Returns:
 *   Parsed float, or null if unparseable.
 */
function parseNum(raw) {
  if (raw === null || raw === undefined || raw === '') return null;
  const s = String(raw)
    .replace(/,/g, '')
    .replace(/%/g, '')
    .replace(/−/g, '-')
    .trim();
  // Handle K / M / B magnitude suffixes (case-insensitive)
  const suffixMatch = s.match(/^([-\d.]+)([KMBkmb])$/);
  if (suffixMatch) {
    const n = parseFloat(suffixMatch[1]);
    const m = suffixMatch[2].toUpperCase();
    const mult = m === 'K' ? 1e3 : m === 'M' ? 1e6 : 1e9;
    return isNaN(n) ? null : n * mult;
  }
  const cleaned = s.replace(/[^\d.\-]/g, '');
  const n = parseFloat(cleaned);
  return isNaN(n) ? null : n;
}

/**
 * Extract the percentage change from a TV "Change" field.
 * e.g. "+82.68 (+5.30%)" → 5.30
 *
 * Args:
 *   changeStr: raw Change or "Last day change" string from Data Window
 *
 * Returns:
 *   Change percent as a float (signed), or null.
 */
function extractChangePct(changeStr) {
  if (!changeStr) return null;
  const m = String(changeStr).match(/\(([-+]?\d+\.?\d*)%\)/);
  return m ? parseFloat(m[1]) : null;
}

/**
 * Compute technical flags from parsed Data Window values.
 *
 * Args:
 *   rsi, rsima, volBias, adx: numeric values (may be null)
 *   squeezeOn: boolean
 *   volumeRatio: vol / volMA (may be null)
 *   changePct: daily % change (may be null)
 *
 * Returns:
 *   Array of flag strings.
 */
function computeFlags({ rsi, rsima, volBias, adx, squeezeOn, volumeRatio, changePct }) {
  const flags = [];

  if (rsi !== null) {
    if (rsi > 72) flags.push('RSI_OB');
    if (rsi < 30) flags.push('RSI_OS');
    if (rsima !== null && rsi < rsima && rsima > 62) flags.push('RSI_COOLING');
  }
  if (adx !== null) {
    if (adx > 30) flags.push('ADX_STRONG');
    if (adx < 20) flags.push('ADX_WEAK');
  }
  if (squeezeOn) flags.push('SQUEEZE_ON');
  if (volBias !== null) {
    if (volBias < -50) flags.push('DIST_SIGNAL');
    if (volBias > 50)  flags.push('ACCUM_SIGNAL');
  }
  if (volumeRatio !== null) {
    if (volumeRatio > 1.8) flags.push('VOLUME_SPIKE');
    if (volumeRatio < 0.5 && changePct !== null && Math.abs(changePct) > 2) flags.push('VOLUME_DRY');
  }
  if (changePct !== null && Math.abs(changePct) > 4) flags.push('BIG_DAY');

  return flags;
}

/**
 * Scan multiple tickers sequentially in one CDP session.
 *
 * Opens the Data Window once, then for each ticker: switches symbol,
 * waits for data to load, reads the Data Window, and computes flags.
 *
 * Args:
 *   client:              connected CDP client
 *   tickers:             array of ticker strings
 *   options.delayMs:     ms to wait after symbol switch (default 1500)
 *   options.onProgress:  optional callback(ticker, index, total)
 *
 * Returns:
 *   Array of per-ticker result objects.
 */
export async function scanPortfolio(client, tickers, { delayMs = 1500, onProgress } = {}) {
  await openDataWindow(client);
  await new Promise(r => setTimeout(r, 400));

  const results = [];

  for (let i = 0; i < tickers.length; i++) {
    const ticker = tickers[i];
    if (onProgress) onProgress(ticker, i + 1, tickers.length);

    try {
      const switchResult = await changeSymbol(client, ticker);
      if (!switchResult.success) {
        results.push({ ticker, error: switchResult.error, flags: [] });
        continue;
      }

      await new Promise(r => setTimeout(r, delayMs));

      const read = await readDataWindow(client);
      if (!read.success || !read.data) {
        results.push({ ticker, error: 'data window read failed', flags: [] });
        continue;
      }

      const d = read.data;
      const close      = parseNum(d['Close']);
      const changePct  = extractChangePct(d['Change'] || d['Last day change']);
      const rsi        = parseNum(d['RSI']);
      const rsima      = parseNum(d['RSI-based MA']);
      const volBias    = parseNum(d['Vol Bias %']);
      const adx        = parseNum(d['ADX']);
      const squeezeRaw = parseNum(d['Squeeze']);
      const vol        = parseNum(d['Volume']);
      const volMA      = parseNum(d['Volume MA']);

      // squeezeRaw > 0: actual value of 1 shows as "1.0" or "100%" in % mode;
      // actual value of 0 shows as "0.0" or "-100%" — both parse to ≤ 0.
      const squeezeOn    = squeezeRaw !== null && squeezeRaw > 0;
      const volumeRatio  = (vol !== null && volMA !== null && volMA > 0)
        ? Math.round((vol / volMA) * 100) / 100
        : null;

      const flags = computeFlags({ rsi, rsima, volBias, adx, squeezeOn, volumeRatio, changePct });

      results.push({
        ticker,
        close,
        changePct,
        rsi:         rsi   !== null ? Math.round(rsi   * 10) / 10 : null,
        rsima:       rsima !== null ? Math.round(rsima * 10) / 10 : null,
        volBias:     volBias !== null ? Math.round(volBias * 10) / 10 : null,
        adx:         adx  !== null ? Math.round(adx  * 10) / 10 : null,
        squeezeOn,
        vol,
        volMA,
        volumeRatio,
        flags,
      });
    } catch (e) {
      results.push({ ticker, error: e.message, flags: [] });
    }
  }

  return results;
}
