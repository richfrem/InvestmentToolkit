

import * as fs from 'fs';
import * as path from 'path';
import { getAccounts } from './src/data/accounts';
import { getPositions } from './src/data/positions';
import { getBalances } from './src/data/balances';
import { getOrders } from './src/data/orders';
import { getCurrentHoldings } from './src/data/currentHoldings';

// __dirname workaround for ts-node
const dirname = path.dirname(__filename);
const exportPath = path.resolve(dirname, 'exportedData.json');

const data = {
  accounts: getAccounts(),
  positions: getPositions(),
  balances: getBalances(),
  orders: getOrders(),
  holdings: getCurrentHoldings(),
};

fs.writeFileSync(exportPath, JSON.stringify(data, null, 2), 'utf-8');
console.log(`Exported all data to ${exportPath}`);
