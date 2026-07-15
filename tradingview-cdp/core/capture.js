/**
 * capture.js - Core screenshot/capture logic.
 * 
 * Purpose:
 *   Handles chart and full-window screenshot captures via the Page.captureScreenshot CDP command.
 * 
 * Key Input Dependencies:
 *   None (reads live state from TradingView Desktop on port 9222 via CDP)
 * 
 * Key Output Dependencies:
 *   - PortfolioAnalysis/screenshots/ (stores generated png screenshots)
 */
import { getClient, evaluate, getChartCollection } from '../connection.js';
import { writeFileSync, mkdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
// core/capture.js → tradingview-cdp/ → repo root → PortfolioAnalysis/screenshots
const screenshotDir = resolve(scriptDir, '../../PortfolioAnalysis/screenshots');

/**
 * Capture a screenshot of either a specific chart element or the full window.
 * 
 * @param {object} params Parameter object
 * @param {string} params.region Screenshot region (full, chart)
 * @param {string} params.filename Base filename to assign to the png file
 * @returns {Promise<object>} Status report with the generated path and file size
 */
export async function captureScreenshot({ region, filename } = {}) {
  /**
   * Resolves target element bounds using DOM query, requests Page.captureScreenshot
   * with clipping from CDP, and writes the base64 output buffer to disk.
   */
  mkdirSync(screenshotDir, { recursive: true });

  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const fname = (filename || `tv_${region || 'chart'}_${ts}`).replace(/[\/\\]/g, '_');
  const filePath = join(screenshotDir, `${fname}.png`);

  const client = await getClient();
  let clip = undefined;

  if (region === 'chart') {
    const bounds = await evaluate(`
      (function() {
        var el = document.querySelector('[data-name="pane-canvas"]')
          || document.querySelector('[class*="chart-container"]')
          || document.querySelector('canvas');
        if (!el) return null;
        var rect = el.getBoundingClientRect();
        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
      })()
    `);
    if (bounds) clip = { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height, scale: 1 };
  }

  const params = { format: 'png' };
  if (clip) params.clip = clip;

  const { data } = await client.Page.captureScreenshot(params);
  writeFileSync(filePath, Buffer.from(data, 'base64'));

  return {
    success: true,
    method: 'cdp',
    file_path: filePath,
    region: region || 'full',
    size_bytes: Buffer.from(data, 'base64').length,
  };
}
