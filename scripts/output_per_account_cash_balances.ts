// This script outputs the cash balances for each account (CAD and USD) independently to a JSON file for debugging.
import fs from 'fs';
import path from 'path';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const dataPath = path.resolve(__dirname, '../backend/exportedData.json');
const outputPath = path.resolve(__dirname, '../TargetPortfolio/per_account_cash_balances.json');

const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
const balances = data.balances || [];

// Group balances by currency and index (since account mapping is not explicit in balances array)
const cashBalances = balances.map((bal, idx) => ({
  index: idx,
  currency: bal.currency,
  cash: bal.cash
}));

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(cashBalances, null, 2), 'utf-8');
console.log('Per-account cash balances written to:', outputPath);
