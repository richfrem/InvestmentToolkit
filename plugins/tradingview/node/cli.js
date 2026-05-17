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
      },
      handler: async (opts) => {
        const { getClient } = await import('./connection.js');
        const client = await getClient();
        return pine.injectPineScript(client, opts.file);
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

await run(process.argv);
