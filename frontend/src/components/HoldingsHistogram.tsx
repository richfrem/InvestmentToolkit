import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// Holdings data from portfolio_thesis_alignment_report.json
const symbolTargets: Record<string, number> = {
  "USD_CASH": 0.0625,
  "PSU.U": 0.1241,
  "INTC": 0.1070,
  "AVGO": 0.07,
  "GOOG": 0.0571,
  "VST": 0.046,
  "CEG": 0.04,
  "ETHA": 0.04,
  "MSFT": 0.037,
  "IBIT": 0.03,
  "CORZ": 0.03,
  "PANW": 0.03,
  "EQIX": 0.029,
  "HUMN": 0.0273,
  "NVDA": 0.03,
  "KOID": 0.0245,
  "COIN": 0.03,
  "SNPS": 0.025,
  "CRWD": 0.026,
  "AMD": 0.03,
  "ANET": 0.0153,
  "CRWV": 0.0144,
  "VRT": 0.02,
  "OKLO": 0.014,
  "CDNS": 0.021,
  "ZS": 0.0198
};

// Map PSU.U.TO to PSU.U for target lookup
function getTargetPct(symbol: string) {
  if (symbol === 'PSU.U.TO') return symbolTargets['PSU.U'] ? symbolTargets['PSU.U'] * 100 : 0;
  return symbolTargets[symbol] ? symbolTargets[symbol] * 100 : 0;
}

const holdings = [
  { symbol: 'USD_CASH', pctPortfolio: 14.10 },
  { symbol: 'PSU.U.TO', pctPortfolio: 12.47 },
  { symbol: 'INTC', pctPortfolio: 9.92 },
  { symbol: 'AVGO', pctPortfolio: 6.26 },
  { symbol: 'GOOG', pctPortfolio: 5.37 },
  { symbol: 'VST', pctPortfolio: 4.48 },
  { symbol: 'CEG', pctPortfolio: 4.24 },
  { symbol: 'ETHA', pctPortfolio: 3.85 },
  { symbol: 'IBIT', pctPortfolio: 3.27 },
  { symbol: 'CORZ', pctPortfolio: 3.12 },
  { symbol: 'MSFT', pctPortfolio: 3.63 },
  { symbol: 'PANW', pctPortfolio: 2.91 },
  { symbol: 'EQIX', pctPortfolio: 2.90 },
  { symbol: 'HUMN', pctPortfolio: 2.74 },
  { symbol: 'KOID', pctPortfolio: 2.42 },
  { symbol: 'NVDA', pctPortfolio: 2.58 },
  { symbol: 'SNPS', pctPortfolio: 2.34 },
  { symbol: 'AMD', pctPortfolio: 1.66 },
  { symbol: 'CRWD', pctPortfolio: 1.71 },
  { symbol: 'ANET', pctPortfolio: 1.56 },
  { symbol: 'CRWV', pctPortfolio: 1.51 },
  { symbol: 'ZS', pctPortfolio: 1.06 },
  { symbol: 'VRT', pctPortfolio: 1.26 },
  { symbol: 'OKLO', pctPortfolio: 1.15 },
  { symbol: 'CDNS', pctPortfolio: 1.15 },
  { symbol: 'COIN', pctPortfolio: 2.34 }
].map(h => ({ ...h, targetPct: getTargetPct(h.symbol) }));

// Sort by actual % descending
const sorted = [...holdings].sort((a, b) => b.pctPortfolio - a.pctPortfolio);

const data = {
  labels: sorted.map(h => h.symbol),
  datasets: [
    {
      label: 'Actual %',
      data: sorted.map(h => h.pctPortfolio),
      backgroundColor: 'rgba(54, 162, 235, 0.7)',
    },
    {
      label: 'Target %',
      data: sorted.map(h => h.targetPct),
      backgroundColor: 'rgba(255, 99, 132, 0.7)',
    },
  ],
};

const options = {
  indexAxis: 'y' as const,
  responsive: true,
  plugins: {
    legend: { position: 'top', labels: { font: { size: 10 }, padding: 8 } },
    title: { display: true, text: 'All Holdings: Actual vs. Target Allocation', font: { size: 13 } },
  },
  layout: {
    padding: { left: 0, right: 2, top: 0, bottom: 0 },
  },
  scales: {
    x: {
      max: Math.max(...sorted.map(h => h.pctPortfolio), ...sorted.map(h => h.targetPct)) + 2,
      title: { display: false },
      grid: { drawOnChartArea: false },
      ticks: { padding: 1, font: { size: 10 } },
    },
    y: {
      title: { display: false },
      grid: { drawOnChartArea: false },
      ticks: { padding: 1, font: { size: 10 } },
    },
  },
  elements: {
    bar: { borderRadius: 1, borderSkipped: false },
  },
  barThickness: 6,
  categoryPercentage: 0.5,
  barPercentage: 0.7,
};

export default function HoldingsHistogram() {
  return (
    <div className="bg-white rounded shadow p-1 mb-2">
      <Bar data={data} options={options} height={Math.max(180, sorted.length * 7)} />
    </div>
  );
}
