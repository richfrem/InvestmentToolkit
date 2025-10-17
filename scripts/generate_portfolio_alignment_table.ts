import fs from 'fs';
import path from 'path';
import Ajv from 'ajv';

// Load schema

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const schemaPath = path.resolve(__dirname, '../TargetPortfolio/portfolio_alignment_schema.json');
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));

// Input and output file paths

const dataPath = path.resolve(__dirname, '../backend/exportedData.json');
const jsonOutputPath = path.resolve(__dirname, '../TargetPortfolio/portfolio_thesis_alignment_report.json');


// Helper: Read JSON data from a file
function readJson(filePath: string) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

// Helper: Write markdown content to a file, creating directories as needed
function writeMarkdown(filePath: string, content: string) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf-8');
}

/**
 * Map a symbol to its thesis pillar using an external mapping file.
 * Falls back to 'Other' if no mapping is found or matches.
 */
function getPillarForSymbol(symbol: string): string {
  const mappingPath = path.resolve(__dirname, '../TargetPortfolio/symbol_pillar_mappings.json');
  let pillarMap: Record<string, string> = {};
  try {
    pillarMap = JSON.parse(fs.readFileSync(mappingPath, 'utf-8')).symbolToPillar;
  } catch (err) {
    // fallback to default
    pillarMap = {};
  }
  // If mapping exists, use it; else fallback to 'Other'
  const mapped = pillarMap[symbol];
  // If mapped pillar matches a targetAllocations key, use it; else fallback to 'Other'
  const targetCategories = [
    'ASI / Compute',
    'Cash',
    'Power / Energy',
    'Data Infra / Supply Chain',
    'AI Titans / Cloud',
    'Sovereign Finance',
    'Security / Data OS',
    'Applied AI / Robotics',
    'Other'
  ];
  if (targetCategories.includes(mapped)) {
    return mapped;
  }
  // If mapped pillar contains a target category as substring, use that
  for (const cat of targetCategories) {
    if (mapped && mapped.includes(cat)) return cat;
  }
  return 'Other';
}

interface Position {
  symbol: string;
  name?: string;
  quantity: number;
  currentMarketValue: number;
  currentBookValue: number;
  accountNumber: string;
}

interface Holding {
  symbol: string;
  name: string;
  pillar: string;
  totalShares: number;
  totalMarketValue: number;
  totalBookValue: number;
  accounts: string[];
}

/**
 * Aggregate holdings across all accounts and positions.
 * Sums up shares, market value, and book value for each symbol.
 * Also aggregates all cash balances into a single USD_CASH holding.
 */
function aggregateHoldings(data: { positions?: Position[], accounts?: any[], balances?: any[] }): Holding[] {
  const holdingsMap: { [key: string]: Holding } = {};
  const positions: Position[] = data.positions || [];
  positions.forEach((pos: Position | any) => {
    const key = pos.symbol;
    if (!holdingsMap[key]) {
      holdingsMap[key] = {
        symbol: pos.symbol,
        name: pos.name || '',
        pillar: getPillarForSymbol(pos.symbol),
        totalShares: 0,
        totalMarketValue: 0,
        totalBookValue: 0,
        accounts: [],
      };
    }
    // Use openQuantity if quantity is not present
    const quantity = Number(pos.quantity ?? pos.openQuantity) || 0;
    const marketValue = Number(pos.currentMarketValue) || 0;
    // Use currentBookValue if present, else averageEntryPrice * openQuantity, else totalCost
    let bookValue = 0;
    if (typeof pos.currentBookValue === 'number') {
      bookValue = pos.currentBookValue;
    } else if (typeof pos.averageEntryPrice === 'number' && typeof pos.openQuantity === 'number') {
      bookValue = pos.averageEntryPrice * pos.openQuantity;
    } else if (typeof pos.totalCost === 'number') {
      bookValue = pos.totalCost;
    }
    holdingsMap[key].totalShares += quantity;
    holdingsMap[key].totalMarketValue += marketValue;
    holdingsMap[key].totalBookValue += bookValue;
    // Ensure accountNumber is always a string (fallback to empty if not present)
    holdingsMap[key].accounts.push(String(pos.accountNumber || ''));
  });

  // Aggregate all balances (CAD and USD) into a single USD_CASH holding
  const balances = data.balances || [];
  // Read USD_CAD_EXCHANGE_RATE from .env, fallback to 1.405049 if not set
  const USD_CAD_EXCHANGE_RATE = parseFloat(process.env.USD_CAD_EXCHANGE_RATE || '1.405049');
  const USD_PER_CAD = 1 / USD_CAD_EXCHANGE_RATE;
  let totalCashUSD = 0;
  balances.forEach((bal: any) => {
    if (typeof bal.cash === 'number' && bal.cash > 0) {
      if (bal.currency === 'USD') {
        totalCashUSD += bal.cash;
      } else if (bal.currency === 'CAD') {
        totalCashUSD += bal.cash * USD_PER_CAD;
      }
    }
  });
  if (totalCashUSD > 0) {
    holdingsMap['USD_CASH'] = {
      symbol: 'USD_CASH',
      name: 'USD Cash (all accounts)',
      pillar: 'Cash',
      totalShares: totalCashUSD,
      totalMarketValue: totalCashUSD,
      totalBookValue: totalCashUSD,
      accounts: []
    };
  }

  // Ensure all output fields are numbers and set defaults if needed
  return Object.values(holdingsMap).map(h => ({
    ...h,
    totalShares: typeof h.totalShares === 'number' && isFinite(h.totalShares) ? h.totalShares : 0,
    totalMarketValue: typeof h.totalMarketValue === 'number' && isFinite(h.totalMarketValue) ? h.totalMarketValue : 0,
    totalBookValue: typeof h.totalBookValue === 'number' && isFinite(h.totalBookValue) ? h.totalBookValue : 0,
  }));
}

/**
 * Calculate total market value of the portfolio from holdings.
 */
function getPortfolioTotals(holdings: Holding[]): { totalMarketValue: number } {
  const totalMarketValue = holdings.reduce((sum, h) => sum + h.totalMarketValue, 0);
  return { totalMarketValue };
}

/**
 * Generate a markdown table and CSV string from holdings.
 * Each row summarizes all accounts for a symbol.
 */
function generateMarkdownTable(holdings: Holding[], totalMarketValue: number): { md: string; csv: string } {
  // Load symbol-to-pillar mapping
  const mappingPath = path.resolve(__dirname, '../TargetPortfolio/symbol_pillar_mappings.json');
  let pillarMap: Record<string, string> = {};
  try {
    pillarMap = JSON.parse(fs.readFileSync(mappingPath, 'utf-8')).symbolToPillar;
  } catch (err) {
    pillarMap = {};
  }
  let md = `| SYMBOL | pillar | #Shares | Total Book | Average | % ACCT MARKET |\n|--------|------------------------------|---------|-----------|---------|---------------|\n`;
  let csv = 'SYMBOL,pillar,#Shares,Total Book,Average,% ACCT MARKET\n';
  holdings.forEach(h => {
    const avgValue = h.totalShares > 0 ? h.totalBookValue / h.totalShares : 0;
    const pctPortfolio = ((h.totalMarketValue / totalMarketValue) * 100).toFixed(2) + '%';
    // Format currency values
    const totalBookFmt = `$${h.totalBookValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    const avgFmt = `$${avgValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    // Use mapping for pillar, fallback to h.pillar
    const pillar = pillarMap[h.symbol] || h.pillar;
    md += `| ${h.symbol} | ${pillar} | ${h.totalShares} | ${totalBookFmt} | ${avgFmt} | ${pctPortfolio} |\n`;
    csv += `${h.symbol},${pillar},${h.totalShares},${h.totalBookValue.toFixed(2)},${avgValue.toFixed(2)},${pctPortfolio}\n`;
  });
  return { md, csv };
}

/**
 * Write the exported markdown and CSV tables to disk.
 */
function writeExportedTable(md: string, csv: string) {
  const mdPath = path.resolve(__dirname, '../TargetPortfolio/ExportedTable.md');
  const csvPath = path.resolve(__dirname, '../TargetPortfolio/ExportedTable.csv');
  writeMarkdown(mdPath, md);
  fs.writeFileSync(csvPath, csv, 'utf-8');
}

/**
 * Main script entry point. Loads data, aggregates holdings, validates output, and writes tables.
 */
function main(): void {
  if (!fs.existsSync(dataPath)) {
    console.error('Portfolio data not found:', dataPath);
    process.exit(1);
  }
  const data = readJson(dataPath);
  const holdings = aggregateHoldings(data);
  const safeHoldings = holdings.map(h => ({
    ...h,
    totalShares: typeof h.totalShares === 'number' && isFinite(h.totalShares) ? h.totalShares : 0,
    totalBookValue: typeof h.totalBookValue === 'number' && isFinite(h.totalBookValue) ? h.totalBookValue : 0,
    totalMarketValue: typeof h.totalMarketValue === 'number' && isFinite(h.totalMarketValue) ? h.totalMarketValue : 0,
  }));
  const { totalMarketValue } = getPortfolioTotals(safeHoldings);

  const targetAllocations: { [pillar: string]: number } = {
    'ASI / Compute': 32.0,
    'Cash': 18.66,
    'Power / Energy': 10.0,
    'Data Infra / Supply Chain': 9.47,
    'AI Titans / Cloud': 9.3,
    'Sovereign Finance': 7.91,
    'Security / Data OS': 7.48,
    'Applied AI / Robotics': 5.18,
    'Other': 0.0
  };

  // Aggregate by pillar, ensure all targetAllocations keys are present
  const pillarTotals: { [pillar: string]: number } = {};
  Object.keys(targetAllocations).forEach(pillar => {
    pillarTotals[pillar] = 0;
  });
  safeHoldings.forEach((h: Holding) => {
    pillarTotals[h.pillar] += h.totalMarketValue;
  });

  // Prepare JSON output strictly matching schema
  const jsonOutput = {
    totalMarketValue,
    pillarTotals,
    targetAllocations,
    holdings: safeHoldings.map((h: Holding) => {
      const totalShares = typeof h.totalShares === 'number' && isFinite(h.totalShares) ? h.totalShares : 0;
      const totalBookValue = typeof h.totalBookValue === 'number' && isFinite(h.totalBookValue) ? h.totalBookValue : 0;
      const totalMarketValueH = typeof h.totalMarketValue === 'number' && isFinite(h.totalMarketValue) ? h.totalMarketValue : 0;
      const pctPortfolio = totalMarketValue > 0 ? (totalMarketValueH / totalMarketValue) * 100 : 0;
      const targetPct = targetAllocations[h.pillar] || 0;
      const gapPct = pctPortfolio - targetPct;
      const avgPrice = totalShares > 0 ? totalBookValue / totalShares : 0;
      return {
        symbol: h.symbol,
        name: h.name,
        pillar: h.pillar,
        totalShares,
        totalBookValue,
        totalMarketValue: totalMarketValueH,
        avgPrice,
        pctPortfolio,
        targetPct,
        gapPct,
        accounts: [...new Set(h.accounts.map(a => String(a)))]
      };
    })
  };

  // Validate JSON output against schema
  const ajv = new Ajv();
  const validate = ajv.compile(schema);
  const valid = validate(jsonOutput);
  if (!valid) {
    console.error('JSON output does not match schema:', validate.errors);
    process.exit(1);
  }

  fs.mkdirSync(path.dirname(jsonOutputPath), { recursive: true });
  fs.writeFileSync(jsonOutputPath, JSON.stringify(jsonOutput, null, 2), 'utf-8');

  // Markdown and CSV output
  const { md, csv } = generateMarkdownTable(safeHoldings, totalMarketValue);
  const header = `# Portfolio Alignment Table\n\nGenerated from: exportedData.json\n\nTotal Portfolio Market Value: $${totalMarketValue.toFixed(2)}\n\n`;
  // Write table directly after header, no code block
  const outputMd = header + md;
  // Write to ExportedTable.md and ExportedTable.csv
  const exportedMdPath = path.resolve(__dirname, '../TargetPortfolio/ExportedTable.md');
  const exportedCsvPath = path.resolve(__dirname, '../TargetPortfolio/ExportedTable.csv');
  writeMarkdown(exportedMdPath, outputMd);
  fs.writeFileSync(exportedCsvPath, csv, 'utf-8');
  // Also write legacy markdown table for compatibility
  const legacyMdPath = path.resolve(__dirname, '../TargetPortfolio/portfolio_alignment_table.md');
  writeMarkdown(legacyMdPath, outputMd);
  console.log('Portfolio alignment table generated at: ExportedTable.md, ExportedTable.csv');
  console.log('Portfolio alignment JSON generated at:', jsonOutputPath);
}

main();
