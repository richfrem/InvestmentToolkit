/**
 * paths.ts - Canonical filesystem path definitions for the Express backend.
 * 
 * Purpose:
 *   Centralizes resolution of JSON data files, markdown thesis notes, and reviews
 *   relative to the compiled backend directory structure.
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 */

import path from 'path';

export const PORTFOLIO_FILE        = path.join(__dirname, '../../data/portfolio.json');
export const PORTFOLIO_EXAMPLE     = PORTFOLIO_FILE + '.example';
export const ETF_ANALYSIS_DIR      = path.join(__dirname, '../../data/etf_analysis');
export const THESIS_FILE           = path.join(__dirname, '../../data/theses/target-portfolio.json');
export const TARGET_PORTFOLIO_FILE = path.resolve(__dirname, '../../data/theses/target-portfolio.json');
export const RESEARCH_DIR          = path.join(__dirname, '../../data/research');
export const PORTFOLIO_REVIEWS_DIR = path.resolve(__dirname, '../../../../PortfolioAnalysis/strategic-reviews');
export const THESIS_DOC_PATH       = path.resolve(__dirname, '../../data/theses/investment_thesis.md');
export const AGENT_GUIDE_PATH      = path.resolve(__dirname, '../../../../plugins/toolkit-manager/references/agent-quick-reference.md');
export const PORTFOLIO_CONFIG_FILE = path.join(__dirname, '../../data/portfolio-config.json');
export const TRADE_LOG_FILE        = path.join(__dirname, '../../data/trade-log.json');
export const DOMAIN_MODEL_DB_FILE  = path.resolve(__dirname, '../../data/domain_model.sqlite');
// WATCHLIST_FILE (data/watchlist.json) removed 2026-07-19: last read-side consumer,
// WatchlistService.getWatchlist(), was rewired onto domain_model.sqlite via
// InvestmentRepository.listWatchlisted() in Wave 2 Task 10/11. Confirmed via
// `grep -rn "WATCHLIST_FILE" src/ tests/` returning zero hits before removal.
// data/watchlist.json itself is untouched on disk (not deleted, per migration rules).

