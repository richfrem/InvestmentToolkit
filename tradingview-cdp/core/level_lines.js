/**
 * level_lines.js - Draw stored price levels as horizontal lines on each symbol's own chart.
 *
 * Purpose:
 *   TradingView keeps drawings with the symbol they were drawn on, so a line drawn on SMCI shows
 *   only on SMCI. Indicator inputs belong to the chart layout and show the last ticker drawn on
 *   every symbol. Drawing the levels as lines therefore batches: each symbol is switched to, its
 *   old level lines are cleared, and one labelled line per stored level is drawn. Lines this tool
 *   draws carry the LINE_PREFIX label so the clear step can tell them from the owner's drawings.
 *
 * Layer: TradingView CDP engine
 *
 * Usage Examples:
 *   node cli.js chart levelLines --plan /tmp/plan.json              # {"SMCI": [{price, label, color}], ...}
 *   node cli.js chart levelLines --plan /tmp/plan.json --dry-run
 *   node cli.js chart levelLines --plan /tmp/plan.json --all-lines  # also remove the owner's own lines
 *
 * Key Functions (Index):
 *   - planClear(): ids of the drawings the clear step removes
 *   - syncSymbolLevels(): switch to one symbol, clear its level lines, draw and verify the new ones
 *   - syncLevelPlan(): syncSymbolLevels for every symbol in a plan
 *
 * Key Input Dependencies:
 *   - window.TradingViewApi.activeChart(): setSymbol, getAllShapes, createShape, removeEntity
 */

export const LINE_PREFIX = 'AI-L:';
const LINE_SHAPE = /line|ray/i;   // horizontal_line, horizontal_ray, trend_line, ray, ...

/**
 * Ids of the drawings the clear step removes.
 *
 * @param {Array<{id: string, name: string, text: string}>} shapes - drawings on the chart
 * @param {{allLines?: boolean}} opts - allLines: remove every line drawing, not only this tool's
 * @returns {string[]} ids to remove
 */
export function planClear(shapes, { allLines = false } = {}) {
  return shapes
    .filter((s) => LINE_SHAPE.test(s.name || ''))
    .filter((s) => allLines || String(s.text || '').startsWith(LINE_PREFIX))
    .map((s) => s.id);
}

function lineText(line) {
  return `${LINE_PREFIX} ${line.label} $${Number(line.price).toFixed(2)}`;
}

function sameTicker(chartSymbol, symbol) {
  const bare = String(chartSymbol || '').split(':').pop().toUpperCase();
  const want = String(symbol).split(':').pop().toUpperCase();
  return bare === want || bare === want.replace(/\.TO$/, '');
}

async function evaluate(client, expression) {
  const r = await client.Runtime.evaluate({ expression, returnByValue: true, awaitPromise: true });
  return JSON.parse(r.result.value);
}

/**
 * Switch the chart to `symbol`, clear its level lines and draw one labelled line per level.
 *
 * @param {object} client - CDP client
 * @param {string} symbol - ticker, e.g. "SMCI" or "TSX:PSU.U"
 * @param {Array<{price: number, label: string, color: string}>} lines - levels to draw
 * @param {{allLines?: boolean, dryRun?: boolean, settleMs?: number}} opts
 * @returns {Promise<object>} {success, symbol, chartSymbol, removed, drawn} or {success:false, error}
 */
export async function syncSymbolLevels(client, symbol, lines, { allLines = false, dryRun = false, settleMs = 1500 } = {}) {
  try {
    const target = /\.TO$/i.test(symbol) ? `TSX:${symbol.replace(/\.TO$/i, '')}` : symbol;
    const state = await evaluate(client, `new Promise(function(res) {
      var c = window.TradingViewApi.activeChart();
      var done = false;
      function list() {
        if (done) return; done = true;
        res(JSON.stringify({ success: true, symbol: c.symbol(), shapes: c.getAllShapes().map(function(s) {
          var p = {}; try { p = c.getShapeById(s.id).getProperties() || {}; } catch (e) {}
          return { id: s.id, name: s.name, text: p.text || '' };
        }) }));
      }
      c.setSymbol(${JSON.stringify(target)}, function() { setTimeout(list, ${Number(settleMs)}); });
      setTimeout(list, ${Number(settleMs) + 8000});
    })`);
    if (!state.success) return { success: false, symbol, error: state.error || 'could not read the chart' };
    if (!sameTicker(state.symbol, symbol)) {
      return { success: false, symbol, error: `chart is on ${state.symbol}, not ${symbol}; nothing drawn` };
    }
    const remove = planClear(state.shapes, { allLines });
    const drawable = lines.filter((l) => Number(l.price) > 0);
    if (dryRun) {
      const ownTagged = planClear(state.shapes).length;
      return { success: true, dryRun: true, symbol, chartSymbol: state.symbol, wouldRemove: remove.length,
        wouldDraw: drawable.length, otherLines: planClear(state.shapes, { allLines: true }).length - ownTagged };
    }
    const shapes = drawable.map((l) => ({ price: Number(l.price), text: lineText(l), color: l.color || '#ffffff' }));
    const res = await evaluate(client, `(async function() {
      var c = window.TradingViewApi.activeChart();
      var remove = ${JSON.stringify(remove)}, shapes = ${JSON.stringify(shapes)}, prefix = ${JSON.stringify(LINE_PREFIX)};
      remove.forEach(function(id) { c.removeEntity(id); });
      var now = Math.floor(Date.now() / 1000), drawn = 0;
      for (var i = 0; i < shapes.length; i++) {
        var s = shapes[i];
        var id = await Promise.resolve(c.createShape({ time: now, price: s.price }, {
          shape: 'horizontal_line', text: s.text, lock: true, disableSave: false,
          overrides: { linecolor: s.color, textcolor: s.color, linewidth: 1, linestyle: 2,
                       showLabel: true, horzLabelsAlign: 'right', vertLabelsAlign: 'bottom', fontsize: 11 },
        }));
        if (id) drawn++;
      }
      var tagged = c.getAllShapes().filter(function(x) {
        var p = {}; try { p = c.getShapeById(x.id).getProperties() || {}; } catch (e) {}
        return String(p.text || '').indexOf(prefix) === 0;
      }).length;
      return JSON.stringify({ success: true, removed: remove.length, drawn: drawn, tagged: tagged });
    })()`);
    if (res.tagged !== shapes.length) {
      return { success: false, symbol, error: `${res.tagged} of ${shapes.length} level lines are on the ${symbol} chart` };
    }
    return { success: true, symbol, chartSymbol: state.symbol, removed: res.removed, drawn: res.drawn };
  } catch (e) {
    return { success: false, symbol, error: e.message };
  }
}

/**
 * Sync the level lines of every symbol in `plan`.
 *
 * @param {object} client - CDP client
 * @param {Object<string, Array<{price: number, label: string, color: string}>>} plan - symbol -> lines
 * @param {{allLines?: boolean, dryRun?: boolean, settleMs?: number}} opts
 * @returns {Promise<object>} {success, total, synced: [symbols], failed: [{symbol, error}], results}
 */
export async function syncLevelPlan(client, plan, opts = {}) {
  const synced = [], failed = [], results = [];
  for (const symbol of Object.keys(plan)) {
    const out = await syncSymbolLevels(client, symbol, plan[symbol], opts);
    results.push(out);
    if (out.success) synced.push(symbol); else failed.push({ symbol, error: out.error });
  }
  return { success: failed.length === 0, total: Object.keys(plan).length, synced, failed, results };
}
