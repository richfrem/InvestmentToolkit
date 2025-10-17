import express from 'express';
import axios from 'axios';
import { getHoldings, getAllAccountData, getAccounts, getBalances } from '../services/questradeService.ts';
import { getCurrentHoldings } from '../data/currentHoldings.ts';

const router = express.Router();

// Get balances for all accounts
router.get('/balances', async (req, res) => {
  try {
    const accounts = await getAccounts();
    const tokens = await import('../services/questradeService.ts').then(m => m.getBearerToken());
    const apiServer = tokens.api_server;
    const accessToken = tokens.access_token;
    let allBalances: any[] = [];
    for (const account of accounts) {
      const balances = await getBalances(account.number, apiServer, accessToken);
      allBalances = allBalances.concat(balances);
    }
    res.json(allBalances);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch balances' });
  }
});
/**
 * Questrade API Routes
 *
 * This router:
 * 1. Connects to the Questrade API.
 * 2. Retrieves account data (/accounts).
 * 3. Retrieves holdings data (/holdings).
 * 4. Retrieves balances data (via /refresh, included in response).
 * 5. Provides a /refresh endpoint to update all local data from Questrade.
 *
 * Example: Get accounts
 *   curl http://localhost:3001/api/accounts
 */
/**
 * Questrade API Routes
 *
 * This router:
 * 1. Connects to the Questrade API.
 * 2. Retrieves account data (/accounts).
 * 3. Retrieves holdings data (/holdings).
 * 4. Retrieves balances data (via /refresh, included in response).
 * 5. Provides a /refresh endpoint to update all local data from Questrade.
 */
// ...existing code...

// Refresh all account, holdings, and balances data from Questrade
router.get('/refresh', async (req, res) => {
  try {
    const result = await getAllAccountData();
    res.json({ success: true, ...result });
  } catch (error) {
    res.status(500).json({ success: false, error: error instanceof Error ? error.message : String(error) });
  }
});

// Manual auth: Generate token in Questrade API Centre, redeem via https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token=<TOKEN>, update .env with tokens.

// Remove callback since manual
// router.get('/auth/callback', ...

router.get('/holdings', async (req, res) => {
  try {
    const holdings = await getHoldings();
    res.json(holdings);
  } catch (error) {
    res.status(500).json({ error: 'Failed to get holdings' });
  }
});

router.get('/accounts', async (req, res) => {
  try {
    const data = await getAccounts();
    res.json(data);
  } catch (error) {
    console.error('Error fetching accounts:', error instanceof Error ? error.message : error);
    res.status(500).json({ error: 'Failed to fetch accounts' });
  }
});

export default router;