/**============================================================================
 * FUNCTION: getPositions
 * Fetches all positions for a given account number.
 * Calls getBearerToken for authentication (if needed).
 * Dependencies: getBearerToken()
 * @param {string} accountNumber - The Questrade account number.
 * @param {string} apiServer - The Questrade API server URL.
 * @param {string} accessToken - The Questrade access token.
 * @returns {Promise<QuestradePosition[]>}
 *   An array of QuestradePosition objects.
 * ============================================================================*/
export const getPositions = async (accountNumber: string, apiServer: string, accessToken: string): Promise<QuestradePosition[]> => {
  const response = await axios.get(`${apiServer}v1/accounts/${accountNumber}/positions`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data.positions || [];
};

/**============================================================================
 * FUNCTION: getBalances
 * Fetches all balances for a given account number.
 * Calls getBearerToken for authentication (if needed).
 * Dependencies: getBearerToken()
 * @param {string} accountNumber - The Questrade account number.
 * @param {string} apiServer - The Questrade API server URL.
 * @param {string} accessToken - The Questrade access token.
 * @returns {Promise<QuestradeBalance[]>}
 *   An array of QuestradeBalance objects.
 * ============================================================================*/
export const getBalances = async (accountNumber: string, apiServer: string, accessToken: string): Promise<QuestradeBalance[]> => {
  const response = await axios.get(`${apiServer}v1/accounts/${accountNumber}/balances`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data.perCurrencyBalances || [];
};
/**
 * Questrade Service
 *
 * This service:
 * 1. Connects to the Questrade API and manages authentication tokens.  getBearerToken()
 * 2. Retrieves and updates account data. fetchAccounts()
 * 3. Retrieves and updates holdings, positions, and balances data.   fetchHoldings()
 * 4. Provides functions to refresh all data and persist it to local stores.
 */
import type { QuestradeAccount, QuestradePosition, QuestradeBalance } from '../types/index.ts';
import { updateAccounts } from '../data/accounts.ts';
import { updatePositions } from '../data/positions.ts';
import { updateBalances } from '../data/balances.ts';
import axios from 'axios';
import fs from 'fs';
import path from 'path';
import type { Holding, QuestradePositionsResponse } from '../types/index.ts';
import { updateCurrentHoldings } from '../data/currentHoldings.ts';
import { logger } from '../utils/logger.ts';


/**============================================================================
 * FUNCTION: getBearerToken
 * Retrieves a fresh Questrade API bearer token using the refresh token in .env.
 * Updates the .env file if a new refresh token is issued.
 * Dependencies: fs, path, axios
 * @returns {Promise<{ access_token: string; api_server: string; refresh_token?: string }>}
 *   The new access token, API server URL, and (optionally) new refresh token.
 * ============================================================================*/
export const getBearerToken = async (): Promise<{ access_token: string; api_server: string; refresh_token?: string }> => {

  // Always read refresh token from project root .env file
  const envPath = path.resolve(process.cwd(), '../.env');
  let REFRESH_TOKEN: string | undefined;
  try {
    const envContent = fs.readFileSync(envPath, 'utf-8');
    const m = envContent.match(/QUESTRADE_REFRESH_TOKEN=(.*)/);
    if (m && m[1]) {
      REFRESH_TOKEN = m[1].trim();
    }
  } catch (err) {
    logger.error('Failed to read .env file:', err);
  }

  if (!REFRESH_TOKEN) {
    logger.error('No QUESTRADE_REFRESH_TOKEN available in .env');
    throw new Error('No QUESTRADE_REFRESH_TOKEN available in .env');
  }

  // Use GET request with query parameters, matching manual browser test
  const url = `https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=${encodeURIComponent(REFRESH_TOKEN)}`;

  try {
    logger.questrade('Redeeming refresh token for fresh access token (GET request)...');
    logger.debug('Request URL:', url);
    logger.debug('Using refresh token:', REFRESH_TOKEN.substring(0, 10) + '...'); // Don't log full token

    const response = await axios.get(url, {
      timeout: 10000,
    });

    logger.success(`Redemption successful (status: ${response.status})`);

    // Update .env and in-memory env with new refresh_token if it changes
    if (response.data.refresh_token && response.data.refresh_token !== REFRESH_TOKEN) {
      // update process.env so subsequent calls in this process use the new token
      process.env.QUESTRADE_REFRESH_TOKEN = response.data.refresh_token;
      // Also update .env file with new refresh token
      try {
        let envContent = fs.readFileSync(envPath, 'utf-8');
        const newEnvContent = envContent.replace(/QUESTRADE_REFRESH_TOKEN=.*/, `QUESTRADE_REFRESH_TOKEN=${response.data.refresh_token}`);
        fs.writeFileSync(envPath, newEnvContent, { encoding: 'utf-8' });
        logger.info('Updated .env file with new refresh token');
      } catch (envErr) {
        logger.warn('Failed to update .env file with new refresh token:', envErr instanceof Error ? envErr.message : String(envErr));
      }
    }

    logger.debug('Bearer token retrieved successfully');
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      logger.error('Error redeeming refresh token - axios error:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
    } else {
      logger.error('Error redeeming refresh token:', error instanceof Error ? error.message : String(error));
    }
    throw error;
  }
};


/**============================================================================
 * FUNCTION: getAllAccountData
 * Main function to get and update all account data.
 * Calls getAccounts, getBalances, getPositions for each account.
 * Updates local stores for accounts, positions, and balances.
 * Dependencies: getAccounts(), getBalances(), getPositions(), updateAccounts(), updatePositions(), updateBalances()
 * @returns {Promise<{accounts: QuestradeAccount[], positions: QuestradePosition[], balances: QuestradeBalance[]}>}
 *   An object containing all accounts, positions, and balances.
 * ============================================================================*/
export const getAllAccountData = async () => {
  logger.info('🏦 Starting comprehensive account data fetch...');

  // Get all accounts
  const accounts: QuestradeAccount[] = await getAccounts();
  logger.info(`📊 Found ${accounts.length} accounts`);

  // Get tokens/apiServer for subsequent calls
  const tokens = await getBearerToken();
  const apiServer = tokens.api_server;
  const accessToken = tokens.access_token;

  // Get all positions and balances for each account
  let allPositions: QuestradePosition[] = [];
  let allBalances: QuestradeBalance[] = [];
  for (const account of accounts) {
    logger.debug(`Processing account: ${account.number}`);
    const positions = await getPositions(account.number, apiServer, accessToken);
    allPositions = allPositions.concat(positions);
    const balances = await getBalances(account.number, apiServer, accessToken);
    allBalances = allBalances.concat(balances);
  }

  logger.info(`📈 Total positions: ${allPositions.length}`);
  logger.info(`💰 Total balances: ${allBalances.length}`);

  updatePositions(allPositions);
  updateBalances(allBalances);

  logger.success('✅ All account data fetched and updated successfully');

  return {
    accounts,
    positions: allPositions,
    balances: allBalances,
  };
}


/**============================================================================
 * FUNCTION: getAccounts
 * Fetches all Questrade accounts and updates the local accounts store.
 * Calls getBearerToken for authentication.
 * Dependencies: getBearerToken(), updateAccounts()
 * @returns {Promise<QuestradeAccount[]>}
 *   An array of QuestradeAccount objects.
 * ============================================================================*/
export const getAccounts = async () => {
  logger.debug('Fetching accounts from Questrade API...');
  const tokens = await getBearerToken();
  const apiUrl = `${tokens.api_server}v1/accounts`;

  try {
    const response = await axios.get(apiUrl, {
      headers: {
        'Authorization': `Bearer ${tokens.access_token}`,
      },
    });

    // Map to QuestradeAccount type
    const accounts = response.data.accounts.map((acc: any) => ({
      type: acc.type,
      number: acc.number,
      status: acc.status,
      isPrimary: acc.isPrimary,
      isBilling: acc.isBilling,
      clientAccountType: acc.clientAccountType,
      userId: acc.userId,
    }));

    logger.info(`✅ Retrieved ${accounts.length} accounts`);
    logger.debug('Account numbers:', accounts.map((a: any) => a.number));

    updateAccounts(accounts);
    return accounts;
  } catch (error) {
    logger.error('Failed to fetch accounts:', error instanceof Error ? error.message : String(error));
    throw new Error(`Failed to fetch accounts: ${error instanceof Error ? error.message : String(error)}`);
  }
};

/**============================================================================
 * FUNCTION: getHoldings
 * Gets holdings (positions) for the first Questrade account and updates the local holdings store.
 * Calls getAccounts and getPositions for data.
 * Dependencies: getAccounts(), getPositions(), updateCurrentHoldings()
 * @returns {Promise<Holding[]>}
 *   An array of Holding objects for the first account.
 * ============================================================================*/
export const getHoldings = async (): Promise<Holding[]> => {
  const accounts: QuestradeAccount[] = await getAccounts();
  const tokens = await getBearerToken();
  const apiServer = tokens.api_server;
  const accessToken = tokens.access_token;
  const accountId = accounts[0]?.number; // Use first account
  if (!accountId) return [];

  const positions = await getPositions(accountId, apiServer, accessToken);
  const holdings: Holding[] = positions.map(pos => ({
    symbol: pos.symbol,
    quantity: pos.openQuantity,
    bookValue: pos.averageEntryPrice * pos.openQuantity,
    marketValue: pos.currentMarketValue,
  }));
  updateCurrentHoldings(holdings); // Update V1 storage
  return holdings;
};