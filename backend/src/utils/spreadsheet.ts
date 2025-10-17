import * as XLSX from 'xlsx';
import type { Holding } from '../types/index.ts';

export const saveHoldingsToXLSX = (holdings: Holding[], filePath: string = 'portfolio.xlsx') => {
  const worksheet = XLSX.utils.json_to_sheet(holdings);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Holdings');
  XLSX.writeFile(workbook, filePath);
};

export const loadHoldingsFromXLSX = (filePath: string = 'portfolio.xlsx'): Holding[] => {
  const workbook = XLSX.readFile(filePath);
  const worksheet = workbook.Sheets['Holdings'];
  return XLSX.utils.sheet_to_json(worksheet);
};