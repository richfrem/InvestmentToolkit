/**
 * Questrade API Routes
 *
 * This router provides endpoints for interacting with the Questrade API:
 * 1. Connects to the Questrade API.
 * 2. Retrieves account data (/accounts).
 * 3. Retrieves holdings data (/holdings).
 * 4. Retrieves balances data (/balances, via /refresh).
 * 5. Provides a /refresh endpoint to update all local data from Questrade.
 * 6. Provides a /update-portfolio-data endpoint to process holdings and update master data file.
 * 7. Provides a /portfolio-data endpoint to retrieve current master portfolio data.
 *
 * Usage Examples:
 * - Get accounts: curl http://localhost:3001/api/accounts
 * - Refresh data from Questrade: curl -X GET http://localhost:3001/api/refresh
 * - Update portfolio calculations: curl -X POST http://localhost:3001/api/update-portfolio-data
 * - Get portfolio master data: curl http://localhost:3001/api/portfolio-data
 */

import express from 'express';
import axios from 'axios';
import { getHoldings, getAllAccountData, getAccounts, getBalances } from '../services/questradeService.ts';
import { getCurrentHoldings } from '../data/currentHoldings.ts';
import { getPositions } from '../data/positions.ts';
import { getBalances as getBalancesData } from '../data/balances.ts';
import { logger } from '../utils/logger.ts';
import { aggregateHoldings, getPortfolioTotals, getPillarForSymbol, readJson, updateMasterData, generateAnalysisPrompt } from '../utils/portfolioUtils.ts';
import { runChatCompletion } from '../services/aiService.ts';
import fs from 'fs';
import path from 'path';

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
// ...existing code...

// Refresh all account, holdings, and balances data from Questrade
router.get('/refresh', async (req, res) => {
  try {
    logger.info('🔄 Refreshing data from Questrade API...');
    logger.debug('Calling getAllAccountData() to fetch latest data');

    const result = await getAllAccountData();

    logger.success('✅ Data refresh completed');
    logger.debug('Refresh result:', result);

    res.json({
      success: true,
      message: 'Data refreshed successfully from Questrade API',
      ...result
    });
  } catch (error) {
    logger.error('❌ Error refreshing data:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : String(error)
    });
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


// Update portfolio master data with current holdings (replicates scripts/generate_portfolio_alignment_table.ts)
router.post('/update-portfolio-data', async (req, res) => {
  try {
    logger.info('📊 Starting portfolio data update process...');

    // Read data from exportedData.json (same as command-line script)
    const dataPath = path.resolve(process.cwd(), 'exportedData.json');
    logger.debug('Reading exported data file:', dataPath);

    if (!fs.existsSync(dataPath)) {
      throw new Error(`Portfolio data not found: ${dataPath}. Please run /api/refresh first.`);
    }

    // Update master data using the same function as the script
    const masterDataPath = path.resolve(process.cwd(), '../TargetPortfolio/portfolio_master_data.json');
    logger.debug('Updating master data file:', masterDataPath);

    updateMasterData(masterDataPath, dataPath);

    // Read the updated master data to get totals for response
    const updatedMasterData = readJson(masterDataPath);

    logger.success('✅ Portfolio data updated successfully');
    logger.info(`💰 Total Market Value: $${updatedMasterData.totalMarketValue.toLocaleString()}`);
    logger.info(`📊 Holdings Count: ${updatedMasterData.currentHoldings.length}`);

    res.json({
      success: true,
      message: 'Portfolio data updated successfully',
      totalMarketValue: updatedMasterData.totalMarketValue,
      holdingsCount: updatedMasterData.currentHoldings.length,
      lastUpdated: updatedMasterData.lastUpdated
    });

  } catch (error) {
    logger.error('❌ Error updating portfolio data:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : String(error)
    });
  }
});

// Get current portfolio master data
router.get('/portfolio-data', async (req, res) => {
  try {
    const masterDataPath = path.resolve(__dirname, '../../TargetPortfolio/portfolio_master_data.json');
    const masterData = readJson(masterDataPath);
    res.json(masterData);
  } catch (error) {
    console.error('Error reading portfolio data:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : String(error)
    });
  }
});

// Read a file from TargetPortfolio (simple file browser for frontend)
router.get('/file-content', async (req, res) => {
  try {
    const file = req.query.file as string || 'portfolio_master_data.json';
    const targetPath = path.resolve(process.cwd(), '../TargetPortfolio', file);
    if (!fs.existsSync(targetPath)) {
      return res.status(404).json({ error: 'File not found' });
    }
    const contents = fs.readFileSync(targetPath, 'utf-8');
    res.json({ success: true, content: contents });
  } catch (error) {
    res.status(500).json({ success: false, error: error instanceof Error ? error.message : String(error) });
  }
});

// Run AI analysis on current portfolio and optional thesis text
router.post('/run-analysis', async (req, res) => {
  try {
    const { thesis = '' } = req.body || {};
    const masterDataPath = path.resolve(process.cwd(), '../TargetPortfolio/portfolio_master_data.json');
    if (!fs.existsSync(masterDataPath)) {
      return res.status(400).json({ success: false, error: 'Master data not found. Run /update-portfolio-data first.' });
    }
    const masterData = readJson(masterDataPath);
    const prompt = generateAnalysisPrompt(masterData, thesis);
    try {
      const aiResponse = await runChatCompletion(prompt, { maxTokens: 1000, temperature: 0.2 });
      res.json({ success: true, analysis: aiResponse });
    } catch (aiErr: any) {
      // Surface friendly message to caller
      const msg = aiErr?.message || 'AI request failed';
      logger.error('AI error:', aiErr);
      res.status(500).json({ success: false, error: msg });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error instanceof Error ? error.message : String(error) });
  }
});

// Save thesis content to TargetPortfolio/Thesis.md
router.post('/save-thesis', async (req, res) => {
  try {
    const { content = '' } = req.body || {};
    const targetPath = path.resolve(process.cwd(), '../TargetPortfolio/Thesis.md');
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    fs.writeFileSync(targetPath, String(content), 'utf-8');
    res.json({ success: true, path: targetPath });
  } catch (error) {
    res.status(500).json({ success: false, error: error instanceof Error ? error.message : String(error) });
  }
});

// Save prompt template to TargetPortfolio/Prompt.md
router.post('/save-prompt', async (req, res) => {
  try {
    const { content = '' } = req.body || {};
    const targetPath = path.resolve(process.cwd(), '../TargetPortfolio/Prompt.md');
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    fs.writeFileSync(targetPath, String(content), 'utf-8');
    res.json({ success: true, path: targetPath });
  } catch (error) {
    res.status(500).json({ success: false, error: error instanceof Error ? error.message : String(error) });
  }
});

export default router;