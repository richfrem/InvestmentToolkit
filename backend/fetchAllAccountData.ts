/**
 * Fetch all Questrade account, positions, and balances data
 *
 * How to run:
 *   cd backend
 *   npx ts-node --esm fetchAllAccountData.ts
 *
 * The server does NOT need to be running to use this script.
 */
import { getAllAccountData } from './src/services/questradeService.ts';

(async () => {
  try {
  const result = await getAllAccountData();
    console.log('Fetched all account data:', result);
  } catch (err) {
  console.error('Error getting all account data:', err);
  }
})();
