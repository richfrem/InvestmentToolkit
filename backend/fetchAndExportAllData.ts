import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
/**
 * Fetch and export all Questrade account, positions, balances, and orders data
 *
 * How to run:
 *   cd backend
 *   npx ts-node --esm fetchAndExportAllData.ts
 *
 * The server does NOT need to be running to use this script.
 */

/**
 * Script: fetchAndExportAllData.ts
 * --------------------------------
 * Purpose:
 *   - Fetches all account-related data from Questrade via backend service functions.
 *   - Aggregates in-memory data stores for accounts, positions, balances, orders, and holdings.
 *   - Exports the aggregated data to a local JSON file for prompt/AI analysis, spreadsheet export, or external review.
 *
 * Workflow:
 *   1. Calls getAllAccountData() to refresh all data from Questrade API and update local stores.
 *   2. Reads all in-memory data stores using getAccounts, getPositions, getBalances, getOrders, getCurrentHoldings.
 *   3. Aggregates the data into a single object.
 *   4. Writes the object to exportedData.json in the backend directory.
 *   5. Logs completion and export path.
 */

import { getAllAccountData } from './src/services/questradeService.ts';
import { getAccounts } from './src/data/accounts.ts';
import { getPositions } from './src/data/positions.ts';
import { getBalances } from './src/data/balances.ts';
import { getOrders } from './src/data/orders.ts';
import { getCurrentHoldings } from './src/data/currentHoldings.ts';
import { logger } from './src/utils/logger.ts';
import * as fs from 'fs';

// Function to fetch current data from Questrade API
async function fetchCurrentData() {
  logger.info('Fetching current data from Questrade API...');
  logger.debug('Calling getAllAccountData() to refresh all data stores');

  await getAllAccountData();

  const data = {
    accounts: getAccounts(),
    positions: getPositions(),
    balances: getBalances(),
    orders: getOrders(),
    holdings: getCurrentHoldings(),
  };

  logger.debug('Data fetched successfully', {
    accounts: data.accounts.length,
    positions: data.positions.length,
    balances: data.balances.length,
    orders: data.orders.length,
    holdings: data.holdings.length
  });

  return data;
}


// Main execution: fetch, aggregate, and export all data
(async () => {
  try {
    logger.info('Starting data export process...');

    // Step 1: Fetch and refresh all account data from Questrade API
    const data = await fetchCurrentData();

    // Step 2: Write aggregated data to JSON file
    const exportPath = path.resolve(__dirname, 'exportedData.json');
    fs.writeFileSync(exportPath, JSON.stringify(data, null, 2), 'utf-8');

    // Step 3: Log completion
    logger.success(`Successfully fetched and exported all data to ${exportPath}`);
    logger.info(`📊 Accounts: ${data.accounts.length}`);
    logger.info(`📈 Positions: ${data.positions.length}`);
    logger.info(`💰 Balances: ${data.balances.length}`);
    logger.info(`📋 Orders: ${data.orders.length}`);
    logger.info(`🏦 Holdings: ${data.holdings.length}`);

  } catch (error) {
    logger.error('Error fetching and exporting data:', error);
    process.exit(1);
  }
})();
