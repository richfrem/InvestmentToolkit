import fs from 'fs';
import path from 'path';

/**
 * Shared portfolio processing utilities used by both the API and scripts.
 * This ensures consistency between different parts of the application.
 */

// Helper: Read JSON data from a file
export function readJson(filePath: string) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

// Helper: Write markdown content to a file, creating directories as needed
export function writeMarkdown(filePath: string, content: string) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf-8');
}

/**
 * Map a symbol to its thesis pillar using an external mapping file.
 * Falls back to 'Other' if no mapping is found or matches.
 */
export function getPillarForSymbol(symbol: string): string {
  const mappingPath = path.resolve(process.cwd(), './TargetPortfolio/symbol_pillar_target_allocations.json');
  let symbolToPillarCode: Record<string, string> = {};
  let pillarCodeToName: Record<string, string> = {};
  try {
    const data = JSON.parse(fs.readFileSync(mappingPath, 'utf-8'));
    // Build symbol to pillarCode map
    data.symbolPillarAllocations.forEach((item: any) => {
      symbolToPillarCode[item.symbol] = item.pillarCode;
    });
    // Build pillarCode to name map
    data.pillars.forEach((p: any) => {
      pillarCodeToName[p.code] = p.pillar || p.name;
    });
  } catch (err) {
    // fallback to default
    symbolToPillarCode = {};
    pillarCodeToName = {};
  }
  const pillarCode = symbolToPillarCode[symbol];
  if (pillarCode) {
    return pillarCodeToName[pillarCode] || 'Other';
  }
  return 'Other';
}

export interface Position {
  symbol: string;
  name?: string;
  quantity: number;
  currentMarketValue: number;
  currentBookValue: number;
  accountNumber: string;
}

export interface Holding {
  symbol: string;
  name: string;
  pillar: string;
  totalShares: number;
  totalMarketValue: number;
  totalBookValue: number;
  averageBookPrice: number;
  accounts: string[];
}

/**
 * Aggregate holdings across all accounts and positions.
 * Sums up shares, market value, and book value for each symbol.
 * Also aggregates all cash balances into a single USD_CASH holding.
 */
export function aggregateHoldings(data: { positions?: Position[], accounts?: any[], balances?: any[] }): Holding[] {
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
        averageBookPrice: 0,
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
      averageBookPrice: 1, // Cash has $1 per unit
      accounts: []
    };
  }

  // Ensure all output fields are numbers and set defaults if needed
  return Object.values(holdingsMap).map(h => {
    // Calculate weighted average book price across all positions
    // Need to track individual position data for proper averaging
    const positions = data.positions?.filter((p: any) => p.symbol === h.symbol) || [];
    let totalWeightedBookValue = 0;
    let totalSharesForAvg = 0;

    positions.forEach((pos: any) => {
      const quantity = Number(pos.quantity ?? pos.openQuantity) || 0;
      let bookValue = 0;
      if (typeof pos.currentBookValue === 'number') {
        bookValue = pos.currentBookValue;
      } else if (typeof pos.averageEntryPrice === 'number' && quantity > 0) {
        bookValue = pos.averageEntryPrice * quantity;
      } else if (typeof pos.totalCost === 'number') {
        bookValue = pos.totalCost;
      }

      if (quantity > 0 && bookValue > 0) {
        totalWeightedBookValue += bookValue;
        totalSharesForAvg += quantity;
      }
    });

    const averageBookPrice = totalSharesForAvg > 0 ? totalWeightedBookValue / totalSharesForAvg : 0;

    return {
      ...h,
      totalShares: typeof h.totalShares === 'number' && isFinite(h.totalShares) ? h.totalShares : 0,
      totalBookValue: typeof h.totalBookValue === 'number' && isFinite(h.totalBookValue) ? h.totalBookValue : 0,
      totalMarketValue: typeof h.totalMarketValue === 'number' && isFinite(h.totalMarketValue) ? h.totalMarketValue : 0,
      averageBookPrice: typeof averageBookPrice === 'number' && isFinite(averageBookPrice) ? averageBookPrice : 0,
    };
  });
}

/**
 * Calculate total market value of the portfolio from holdings.
 */
export function getPortfolioTotals(holdings: Holding[]): { totalMarketValue: number } {
  const totalMarketValue = holdings.reduce((sum, h) => sum + h.totalMarketValue, 0);
  return { totalMarketValue };
}

/**
 * Generate a markdown table and CSV string from holdings.
 * Each row summarizes all accounts for a symbol.
 */
export function generateMarkdownTable(holdings: Holding[], totalMarketValue: number): { md: string; csv: string } {
  // Load symbol-to-pillar mapping
  const mappingPath = path.resolve(process.cwd(), '../TargetPortfolio/symbol_pillar_mappings.json');
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
export function writeExportedTable(md: string, csv: string) {
  const mdPath = path.resolve(process.cwd(), '../TargetPortfolio/ExportedTable.md');
  const csvPath = path.resolve(process.cwd(), '../TargetPortfolio/ExportedTable.csv');
  writeMarkdown(mdPath, md);
  fs.writeFileSync(csvPath, csv, 'utf-8');
}

/**
 * Update master data file with current portfolio holdings and calculations.
 * This is the core logic shared between the API and script.
 * Follows ADR 013: Data Mapping Requirements
 */
export function updateMasterData(masterDataPath: string, dataPath: string): void {
  if (!fs.existsSync(dataPath)) {
    throw new Error(`Portfolio data not found: ${dataPath}`);
  }
  if (!fs.existsSync(masterDataPath)) {
    console.log('Master data file not found, creating from template...');
    // Create basic structure from schema
    const masterData = {
      pillars: [
        { code: "ASI_COMPUTE", name: "ASI / Compute", description: "Advanced silicon, semiconductors, and compute infrastructure powering AI and next-generation workloads.", targetAllocation: 0.32 },
        { code: "CASH", name: "Cash", description: "Cash and cash-equivalent holdings for liquidity and risk management.", targetAllocation: 0.1866 },
        { code: "POWER_ENERGY", name: "Power / Energy", description: "Companies and assets involved in energy generation, storage, and distribution, including next-gen power sources.", targetAllocation: 0.1 },
        { code: "DATA_INFRA_SUPPLY_CHAIN", name: "Data Infra / Supply Chain", description: "Data centers, networking, and supply chain infrastructure enabling digital and AI economies.", targetAllocation: 0.0947 },
        { code: "AI_TITANS_CLOUD", name: "AI Titans / Cloud", description: "Major cloud and AI platform providers driving the AI revolution at scale.", targetAllocation: 0.093 },
        { code: "SOVEREIGN_FINANCE_DIGITAL_ASSETS", name: "Sovereign Finance", description: "Digital assets, blockchain, and decentralized finance platforms transforming global finance.", targetAllocation: 0.0791 },
        { code: "SECURITY_DATA_OS", name: "Security / Data OS", description: "Cybersecurity, data operating systems, and platforms ensuring digital trust and resilience.", targetAllocation: 0.0748 },
        { code: "APPLIED_AI_ROBOTICS", name: "Applied AI / Robotics", description: "Companies applying AI to real-world problems, including robotics, automation, and intelligent systems.", targetAllocation: 0.0518 }
      ],
      symbolAllocations: [], // Will be populated below
      currentHoldings: [],
      pillarTotals: {},
      totalMarketValue: 0,
      lastUpdated: new Date().toISOString()
    };
    fs.writeFileSync(masterDataPath, JSON.stringify(masterData, null, 2), 'utf-8');
  }

  // Read master data and current portfolio data
  const masterData = readJson(masterDataPath);
  const data = readJson(dataPath);

  // Aggregate current holdings (ADR 013: Questrade API → Internal Holdings)
  const holdings = aggregateHoldings(data);
  const safeHoldings = holdings.map(h => ({
    ...h,
    totalShares: typeof h.totalShares === 'number' && isFinite(h.totalShares) ? h.totalShares : 0,
    totalBookValue: typeof h.totalBookValue === 'number' && isFinite(h.totalBookValue) ? h.totalBookValue : 0,
    totalMarketValue: typeof h.totalMarketValue === 'number' && isFinite(h.totalMarketValue) ? h.totalMarketValue : 0,
  }));

  const { totalMarketValue } = getPortfolioTotals(safeHoldings);

  // Update master data with current holdings (ADR 013: Holdings Aggregation → Portfolio Master Data)
  masterData.currentHoldings = safeHoldings.map((h: Holding) => {
    // ADR 013: getPillarForSymbol(symbol) → currentHoldings[].pillar
    let pillarName = getPillarForSymbol(h.symbol);
    // If the pillar name doesn't match any defined pillar, try to find it by mapping
    const foundPillar = masterData.pillars.find((p: any) => p.name === pillarName);
    if (!foundPillar) {
      // Try to find pillar by code from symbolAllocations
      const alloc = masterData.symbolAllocations.find((a: any) => a.symbol === h.symbol);
      if (alloc) {
        const pillar = masterData.pillars.find((p: any) => p.code === alloc.pillarCode);
        if (pillar) {
          pillarName = pillar.name;
        }
      }
    }
    return {
      symbol: h.symbol, // ADR 013: positions[].symbol → currentHoldings[].symbol
      name: h.name, // ADR 013: positions[].name → currentHoldings[].name
      pillar: pillarName, // ADR 013: getPillarForSymbol(symbol) → currentHoldings[].pillar
      totalShares: h.totalShares, // ADR 013: positions[].openQuantity → currentHoldings[].totalShares
      totalBookValue: h.totalBookValue, // ADR 013: positions[].averageEntryPrice * openQuantity → currentHoldings[].totalBookValue
      totalMarketValue: h.totalMarketValue, // ADR 013: positions[].currentMarketValue → currentHoldings[].totalMarketValue
      pctPortfolio: totalMarketValue > 0 ? (h.totalMarketValue / totalMarketValue) * 100 : 0, // ADR 013: totalMarketValue / current.totalMarketValue → currentHoldings[].pctPortfolio
      accounts: [...new Set(h.accounts.map((a: any) => String(a)))] // ADR 013: positions[].accountNumber → currentHoldings[].accounts[]
    };
  });

  // Calculate pillar totals from current holdings grouped by pillar (ADR 013: aggregatedHoldings → pillarTotals[pillar])
  const pillarTotals: { [key: string]: number } = {};
  masterData.pillars.forEach((pillar: any) => {
    pillarTotals[pillar.name] = 0;
  });
  safeHoldings.forEach((holding: Holding) => {
    // Map symbol to pillar using the same logic as getPillarForSymbol
    let pillarName = getPillarForSymbol(holding.symbol);
    // If the pillar name doesn't match any defined pillar, try to find it by mapping
    const foundPillar = masterData.pillars.find((p: any) => p.name === pillarName);
    if (!foundPillar) {
      // Try to find pillar by code from symbolAllocations
      const alloc = masterData.symbolAllocations.find((a: any) => a.symbol === holding.symbol);
      if (alloc) {
        const pillar = masterData.pillars.find((p: any) => p.code === alloc.pillarCode);
        if (pillar) {
          pillarName = pillar.name;
        }
      }
    }
    if (pillarTotals[pillarName] !== undefined) {
      pillarTotals[pillarName] += holding.totalMarketValue;
    }
  });
  masterData.pillarTotals = pillarTotals;

  // Load symbol-pillar mapping data
  const symbolPillarMappingPath = path.resolve(process.cwd(), './TargetPortfolio/symbol_pillar_target_allocations.json');
  const symbolPillarData = readJson(symbolPillarMappingPath);
  console.log('symbolPillarData loaded: ' + !!symbolPillarData);
  console.log('symbolPillarAllocations: ' + !!symbolPillarData.symbolPillarAllocations);
  console.log('number of mappings: ' + symbolPillarData.symbolPillarAllocations.length);

  // Initialize symbolAllocations if empty (create entries for all current holdings)
  if (!masterData.symbolAllocations || masterData.symbolAllocations.length === 0) {
    masterData.symbolAllocations = safeHoldings.map((holding: Holding) => {
      // Find symbol in mapping data - exact match lookup
      console.log(`Looking for symbol: ${holding.symbol}`);
      const symbolMapping = symbolPillarData.symbolPillarAllocations.find((mapping: any) => {
        console.log(`Checking mapping: ${mapping.symbol} === ${holding.symbol}? ${mapping.symbol === holding.symbol}`);
        return mapping.symbol === holding.symbol;
      });

      let pillarCode = 'OTHER'; // default
      let targetAllocation = 0;

      if (symbolMapping) {
        pillarCode = symbolMapping.pillarCode;
        targetAllocation = symbolMapping.allocation * 100; // Convert to percentage
        console.log(`✓ Found mapping for ${holding.symbol}: ${pillarCode}, ${targetAllocation}%`);
      } else {
        console.log(`✗ No mapping found for ${holding.symbol}`);
      }

      return {
        symbol: holding.symbol,
        pillarCode: pillarCode,
        targetAllocation: targetAllocation,
        currentAllocation: totalMarketValue > 0 ? (holding.totalMarketValue / totalMarketValue) * 100 : 0,
        openQuantity: holding.totalShares,
        closedQuantity: 0,
        targetQuantity: 0,
        currentMarketValue: holding.totalMarketValue,
        totalCost: holding.totalBookValue,
        averageEntryPrice: holding.averageBookPrice,
        currentPrice: holding.totalShares > 0 ? holding.totalMarketValue / holding.totalShares : 0,
        dayPnl: 0,
        closedPnl: 0,
        openPnl: holding.totalMarketValue - holding.totalBookValue,
        symbolId: 0,
        isRealTime: true,
        isUnderReorg: false,
        gap: 0 // Will be calculated after target allocation is set
      };
    });

    // Calculate gaps now that target allocations are set
    masterData.symbolAllocations.forEach((alloc: any) => {
      alloc.gap = alloc.currentAllocation - alloc.targetAllocation;
    });
      } else {
    console.log('Updating existing symbolAllocations, length: ' + masterData.symbolAllocations.length);
    // Update existing symbol allocations with current data and calculate gaps (ADR 013: various mappings)
    masterData.symbolAllocations.forEach((alloc: any) => {
      console.log(`Checking alloc ${alloc.symbol}`);
      const current = safeHoldings.find(h => h.symbol === alloc.symbol);
      console.log(`Found current: ${!!current}`);
      if (current) {
        // Update pillarCode and targetAllocation from mapping data
        const symbolMapping = symbolPillarData.symbolPillarAllocations.find((mapping: any) => mapping.symbol === alloc.symbol);
        console.log(`Updating ${alloc.symbol}: mapping found: ${!!symbolMapping}`);
        if (symbolMapping) {
          alloc.pillarCode = symbolMapping.pillarCode;
          alloc.targetAllocation = symbolMapping.allocation * 100; // Convert to percentage
          console.log(`Set ${alloc.symbol} to ${alloc.pillarCode}, ${alloc.targetAllocation}%`);
        } else if (!alloc.pillarCode || alloc.pillarCode === 'OTHER') {
          alloc.pillarCode = 'OTHER';
          alloc.targetAllocation = 0;
        }

        alloc.currentAllocation = totalMarketValue > 0 ? (current.totalMarketValue / totalMarketValue) * 100 : 0; // ADR 013: currentMarketValue / totalMarketValue → symbolAllocations[].currentAllocation
        alloc.openQuantity = current.totalShares; // ADR 013: openQuantity → symbolAllocations[].openQuantity
        alloc.closedQuantity = 0; // Initialize to 0, can be updated from source data
        alloc.currentMarketValue = current.totalMarketValue; // ADR 013: currentMarketValue → symbolAllocations[].currentMarketValue
        alloc.totalCost = current.totalBookValue; // ADR 013: totalCost → symbolAllocations[].totalCost
        alloc.averageEntryPrice = current.averageBookPrice; // ADR 013: averageEntryPrice → symbolAllocations[].averageEntryPrice
        alloc.currentPrice = current.totalShares > 0 ? current.totalMarketValue / current.totalShares : 0; // ADR 013: currentPrice → symbolAllocations[].currentPrice
        alloc.dayPnl = 0; // Initialize to 0, can be updated from source data
        alloc.closedPnl = 0; // Initialize to 0, can be updated from source data
        alloc.openPnl = current.totalMarketValue - current.totalBookValue; // ADR 013: totalMarketValue - totalBookValue → symbolAllocations[].openPnl
        alloc.symbolId = 0; // Initialize to 0, can be updated from source data
        alloc.isRealTime = true; // Initialize to true
        alloc.isUnderReorg = false; // Initialize to false
        alloc.gap = alloc.currentAllocation - alloc.targetAllocation; // ADR 013: currentAllocation - targetAllocation → symbolAllocations[].gap

        // Calculate target number of shares based on target allocation
        alloc.targetQuantity = totalMarketValue > 0 ? (alloc.targetAllocation / 100) * totalMarketValue / (current.totalMarketValue / current.totalShares) : 0;
      } else {
        alloc.currentAllocation = 0;
        alloc.openQuantity = 0;
        alloc.closedQuantity = 0;
        alloc.currentMarketValue = 0;
        alloc.totalCost = 0;
        alloc.averageEntryPrice = 0;
        alloc.currentPrice = 0;
        alloc.dayPnl = 0;
        alloc.closedPnl = 0;
        alloc.openPnl = 0;
        alloc.symbolId = 0;
        alloc.isRealTime = true;
        alloc.isUnderReorg = false;
        alloc.targetQuantity = 0;
        alloc.gap = -alloc.targetAllocation;
      }
    });
  }

  // Calculate current allocation for each pillar by summing symbol allocations
  masterData.pillars.forEach((pillar: any) => {
    const pillarSymbols = masterData.symbolAllocations.filter((alloc: any) => alloc.pillarCode === pillar.code);
    pillar.currentAllocation = pillarSymbols.reduce((sum: number, alloc: any) => sum + alloc.currentAllocation, 0) / 100; // Convert back to decimal
  });

  // Update totals and timestamp (ADR 013: aggregatedHoldings → totalMarketValue, new Date().toISOString() → lastUpdated)
  masterData.totalMarketValue = totalMarketValue;
  masterData.lastUpdated = new Date().toISOString();

  // Write back to master data file
  fs.writeFileSync(masterDataPath, JSON.stringify(masterData, null, 2), 'utf-8');

  console.log('Portfolio data updated in master file:', masterDataPath);
}

/**
 * Generate a concise analysis prompt for the AI service.
 * Accepts the masterData object and optional thesis text.
 * Returns a string suitable for passing to the LLM.
 */
export function generateAnalysisPrompt(masterData: any, thesisText = ''): string {
  // Create a minimal portfolio summary: pillars with current vs target %, top holdings
  const pillars = (masterData.pillars || []).map((p: any) => ({ code: p.code, name: p.name, target: p.targetAllocation || p.targetAllocationPercent || 0 }));
  const pillarLines = pillars.map((p: any) => {
    const t = Number(p.target || 0);
    return `- ${p.name}: target ${(t * 100).toFixed(2)}%`;
  }).join('\n');

  // Top 10 holdings by market value
  const holdings = (masterData.currentHoldings || []).slice().sort((a: any, b: any) => (b.totalMarketValue || b.currentMarketValue || 0) - (a.totalMarketValue || a.currentMarketValue || 0)).slice(0, 10);
  const holdingsLines = holdings.map((h: any) => `- ${h.symbol}: ${h.totalMarketValue ? '$' + Number(h.totalMarketValue).toFixed(2) : h.currentMarketValue}`).join('\n');

  // Compact instruction set
  const instructions = `You are an expert portfolio analyst. Given the portfolio summary and the investor thesis, provide a concise (<= 300 words) analysis that: \n1) identifies any material allocation mismatches vs targets; \n2) highlights top risks and concentration by pillar or position; \n3) suggests one to three actionable adjustments (rebalancing or research) prioritized by impact and feasibility.\nOutput in markdown with short headings.`;

  const prompt = `Portfolio Summary:\nPillars:\n${pillarLines}\n\nTop Holdings:\n${holdingsLines}\n\nTotal Market Value: $${(masterData.totalMarketValue || 0).toFixed(2)}\n\nInvestor Thesis:\n${thesisText}\n\nInstructions:\n${instructions}`;
  return prompt;
}