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
import * as fs from 'fs';


// Main execution: fetch, aggregate, and export all data
(async () => {
  // Step 1: Fetch and refresh all account data from Questrade API
  await getAllAccountData();

  // Step 2: Read all in-memory data stores
  const data = {
    accounts: getAccounts(),      // All account details
    positions: getPositions(),    // All positions for all accounts
    balances: getBalances(),      // All balances for all accounts
    orders: getOrders(),          // All orders for all accounts
    holdings: getCurrentHoldings(), // Current holdings snapshot
  };

  // Step 3: Write aggregated data to JSON file
  const exportPath = path.resolve(__dirname, 'exportedData.json');
  fs.writeFileSync(exportPath, JSON.stringify(data, null, 2), 'utf-8');

  // Step 4: Log completion
  console.log(`Fetched and exported all data to ${exportPath}`);
})();
