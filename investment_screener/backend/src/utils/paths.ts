import path from 'path';

export const PORTFOLIO_FILE        = path.join(__dirname, '../../data/portfolio.json');
export const PORTFOLIO_EXAMPLE     = PORTFOLIO_FILE + '.example';
export const ETF_ANALYSIS_DIR      = path.join(__dirname, '../../data/etf_analysis');
export const THESIS_FILE           = path.join(__dirname, '../../data/theses/target-portfolio.json');
export const TARGET_PORTFOLIO_FILE = path.resolve(__dirname, '../../data/theses/target-portfolio.json');
export const RESEARCH_DIR          = path.join(__dirname, '../../data/research');
export const PORTFOLIO_REVIEWS_DIR = path.resolve(__dirname, '../../../../PortfolioAnalysis/strategic-reviews');
export const THESIS_DOC_PATH       = path.resolve(__dirname, '../../../../plugins/portfolio-advisor/references/investment_thesis.md');
export const AGENT_GUIDE_PATH      = path.resolve(__dirname, '../../../../plugins/toolkit-manager/references/agent-quick-reference.md');
export const PORTFOLIO_CONFIG_FILE = path.join(__dirname, '../../data/portfolio-config.json');
export const TRADE_LOG_FILE        = path.join(__dirname, '../../data/trade-log.json');
export const PORTFOLIO_SNAPSHOT_FILE = path.join(__dirname, '../../data/portfolio_snapshot.json');
