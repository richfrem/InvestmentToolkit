#!/usr/bin/env node

/**
 * Owned TradingView CDP CLI for InvestmentToolkit.
 * Outputs JSON to stdout. All errors → stderr.
 * Exit codes: 0 success, 1 error, 2 connection failure.
 *
 * Commands:
 *   status                    — health check (CDP connection + chart state)
 *   quote [SYMBOL]            — current price from active chart
 *   alert list                — list active alerts
 *   alert create --price P --condition C [--message M]
 *   screenshot [--region R] [--output NAME]
 */

import { register, run } from './router.js';
import * as health from './core/health.js';
import * as data from './core/data.js';
import * as alerts from './core/alerts.js';
import * as capture from './core/capture.js';
import * as pine from './core/pine.js';
import * as chart from './core/chart.js';

// --- status ---
register('status', {
  description: 'Check CDP connection to TradingView',
  handler: () => health.healthCheck(),
});

// --- quote ---
register('quote', {
  description: 'Get real-time price quote from active chart',
  handler: (opts, positionals) => data.getQuote({ symbol: positionals[0] }),
});

// --- alert ---
register('alert', {
  description: 'Alert tools (list, create)',
  subcommands: new Map([
    ['list', {
      description: 'List active alerts',
      handler: () => alerts.list(),
    }],
    ['create', {
      description: 'Create a price alert',
      options: {
        price: { type: 'string', short: 'p', description: 'Price level' },
        condition: { type: 'string', short: 'c', description: 'Condition: crossing, greater_than, less_than' },
        message: { type: 'string', short: 'm', description: 'Alert message' },
      },
      handler: (opts) => alerts.create({
        price: Number(opts.price),
        condition: opts.condition || 'crossing',
        message: opts.message,
      }),
    }],
    ['delete', {
      description: 'Delete all alerts',
      options: {
        all: { type: 'boolean', description: 'Delete all alerts' },
      },
      handler: (opts) => alerts.deleteAlerts({ delete_all: opts.all }),
    }],
  ]),
});

// --- screenshot ---
register('screenshot', {
  description: 'Take a screenshot of the chart',
  options: {
    region: { type: 'string', short: 'r', description: 'Region: full, chart' },
    output: { type: 'string', short: 'o', description: 'Custom filename (without .png)' },
  },
  handler: (opts) => capture.captureScreenshot({
    region: opts.region,
    filename: opts.output,
  }),
});

// --- pine ---
register('pine', {
  description: 'Pine Script editor automation (inject, read, remove)',
  subcommands: new Map([
    ['inject', {
      description: 'Inject a Pine Script file into the active chart',
      options: {
        file: { type: 'string', short: 'f', description: 'Path to .pine script file' },
        content: { type: 'string', short: 'c', description: 'Inline Pine Script content string' },
      },
      handler: async (opts) => {
        const { readFileSync, existsSync } = await import('fs');
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        let scriptContent;
        if (opts.content) {
          scriptContent = opts.content;
        } else if (opts.file) {
          if (!existsSync(opts.file)) throw new Error(`Script file not found: ${opts.file}`);
          scriptContent = readFileSync(opts.file, 'utf8');
        } else {
          throw new Error('Provide --file (-f) or --content (-c)');
        }
        return pine.injectPineScript(client, scriptContent);
      },
    }],
    ['read', {
      description: 'Read indicator values from the Data Window',
      options: {
        indicator: { type: 'string', short: 'i', description: 'Indicator display name' },
      },
      handler: async (opts) => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return pine.readIndicatorValues(client, opts.indicator);
      },
    }],
    ['remove', {
      description: 'Remove a named indicator from the chart',
      options: {
        indicator: { type: 'string', short: 'i', description: 'Indicator display name' },
      },
      handler: async (opts) => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return pine.removePineScript(client, opts.indicator);
      },
    }],
  ]),
});

// --- chart ---
register('chart', {
  description: 'Chart control — change timeframe, read Data Window',
  subcommands: new Map([
    ['timeframe', {
      description: 'Change the active chart timeframe (e.g. 1D, 60, 240, W)',
      options: {
        resolution: { type: 'string', short: 'r', description: 'Resolution: 1D, D, W, 60, 240, 15, ...' },
      },
      handler: async (opts, positionals) => {
        const resolution = opts.resolution || positionals[0];
        if (!resolution) throw new Error('Resolution required — e.g. chart timeframe 1D or -r 1D');
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return chart.changeTimeframe(client, resolution);
      },
    }],
    ['read', {
      description: 'Read all active indicator values from the Data Window panel',
      handler: async () => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return chart.readDataWindow(client);
      },
    }],
    ['openDataWindow', {
      description: 'Open the Data Window panel if not already visible',
      handler: async () => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return chart.openDataWindow(client);
      },
    }],
    ['saveLayout', {
      description: 'Save the current chart layout (optional --name)',
      options: {
        name: { type: 'string', short: 'n', description: 'Layout name (used if a naming dialog appears)' },
      },
      handler: async (opts) => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return chart.saveLayout(client, opts.name);
      },
    }],
  ]),
});

await run(process.argv);
