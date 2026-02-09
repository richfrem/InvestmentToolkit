import fs from 'fs';
import path from 'path';
import { updateMasterData } from '../backend/src/utils/portfolioUtils.ts';

// Input and output file paths
const __dirname = path.dirname(new URL(import.meta.url).pathname);
const dataPath = path.resolve(__dirname, '../backend/exportedData.json');
const masterDataPath = path.resolve(__dirname, '../TargetPortfolio/portfolio_master_data.json');



/**
 * Main script entry point. Loads data, aggregates holdings, updates master data file.
 */
function main(): void {
  updateMasterData(masterDataPath, dataPath);
  console.log('Portfolio data updated in master file:', masterDataPath);
}

main();
