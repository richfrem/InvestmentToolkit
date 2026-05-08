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

await run(process.argv);
