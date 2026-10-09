/**
 * paths.ts - Canonical filesystem path definitions for the Express backend.
 * 
 * Purpose:
 *   Centralizes resolution of the SQLite database, data folders, markdown thesis notes and
 *   reviews relative to the compiled backend directory structure. Portfolio data itself lives
 *   only in domain_model.sqlite (DOMAIN_MODEL_DB_FILE).
 * 
 * Key Input Dependencies:
 *   None
 * 
 * Key Output Dependencies:
 *   None
 */

import path from 'path';

export const DATA_DIR              = path.resolve(__dirname, '../../data');
export const YTD_PERFORMANCE_REPORT_FILE = path.join(DATA_DIR, 'ytd_performance_report.json');
export const ETF_ANALYSIS_DIR      = path.join(__dirname, '../../data/etf_analysis');
export const RESEARCH_DIR          = path.join(__dirname, '../../data/research');
export const PORTFOLIO_REVIEWS_DIR = path.resolve(__dirname, '../../../../PortfolioAnalysis/strategic-reviews');
export const THESIS_DOC_PATH       = path.resolve(__dirname, '../../data/theses/investment_thesis.md');
export const AGENT_GUIDE_PATH      = path.resolve(__dirname, '../../../../plugins/toolkit-manager/references/agent-quick-reference.md');
export const PORTFOLIO_CONFIG_FILE = path.join(__dirname, '../../data/portfolio-config.json');
export const DOMAIN_MODEL_DB_FILE  = path.resolve(__dirname, '../../data/domain_model.sqlite');
