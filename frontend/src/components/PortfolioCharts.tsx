import React from 'react';
import { Bar, Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

const pillarLabels = [
  'ASI / Compute', 'Cash', 'Power / Energy', 'Data Infra / Supply Chain',
  'AI Titans / Cloud', 'Sovereign Finance', 'Security / Data OS', 'Applied AI / Robotics', 'Other'
];
const actualPillar = [23.9, 14.1, 9.9, 10.3, 9.0, 9.5, 5.7, 5.2, 12.5];
const targetPillar = [32.0, 18.66, 10.0, 9.47, 9.3, 7.91, 7.48, 5.18, 0];

const pillarData = {
  labels: pillarLabels,
  datasets: [
    {
      label: 'Actual %',
      data: actualPillar,
      backgroundColor: 'rgba(54, 162, 235, 0.7)',
    },
    {
      label: 'Target %',
      data: targetPillar,
      backgroundColor: 'rgba(255, 99, 132, 0.7)',
    },
  ],
};

const pillarOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' },
    title: { display: true, text: 'Portfolio Allocation by Pillar: Actual vs. Target', font: { size: 22 } },
  },
};

const holdingsLabels = [
  'PSU.U.TO', 'INTC', 'AVGO', 'GOOG', 'HUMN', 'EQIX', 'MSFT', 'ETHA', 'IBIT', 'PANW'
];
const holdingsActual = [12.47, 9.92, 6.26, 5.37, 2.74, 2.90, 3.63, 3.85, 3.27, 2.91];
const holdingsTarget = [0, 32, 32, 9.3, 5.18, 9.47, 9.3, 7.91, 7.91, 7.48];

const holdingsData = {
  labels: holdingsLabels,
  datasets: [
    {
      label: '% of Portfolio',
      data: holdingsActual,
      backgroundColor: 'rgba(75, 192, 192, 0.7)',
    },
    {
      label: 'Target %',
      data: holdingsTarget,
      backgroundColor: 'rgba(255, 205, 86, 0.7)',
    },
  ],
};

const holdingsOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' },
    title: { display: true, text: 'Top Holdings: Actual vs. Target Allocation', font: { size: 20 } },
  },
};

const pieData = {
  labels: pillarLabels,
  datasets: [
    {
      data: actualPillar,
      backgroundColor: [
        '#36A2EB', '#FFCE56', '#FF6384', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#FF6384', '#B2FF66'
      ],
    },
  ],
};

export default function PortfolioCharts() {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
        <div className="bg-white rounded-xl shadow p-6">
          <Bar data={pillarData} options={pillarOptions} height={350} />
        </div>
        <div className="bg-white rounded-xl shadow p-6">
          <Pie data={pieData} />
          <div className="text-center mt-4 font-medium text-gray-700">Current Portfolio Allocation</div>
        </div>
      </div>
      <div className="bg-white rounded-xl shadow p-6 mb-10">
        <Bar data={holdingsData} options={holdingsOptions} height={300} />
      </div>
      <div className="bg-white rounded-xl shadow p-6">
        <h3 className="text-lg font-bold mb-4">Top 10 Holdings Table</h3>
        <table className="min-w-full text-sm text-left border">
          <thead className="bg-blue-100">
            <tr>
              <th className="px-3 py-2">Symbol</th>
              <th className="px-3 py-2">Pillar</th>
              <th className="px-3 py-2">Market Value</th>
              <th className="px-3 py-2">% Portfolio</th>
              <th className="px-3 py-2">Target %</th>
              <th className="px-3 py-2">Gap %</th>
            </tr>
          </thead>
          <tbody>
            {[
              { symbol: 'PSU.U.TO', pillar: 'Other', value: 3508.05, pct: 12.47, target: 0, gap: 12.47 },
              { symbol: 'INTC', pillar: 'ASI / Compute', value: 2790.72, pct: 9.92, target: 32, gap: -22.08 },
              { symbol: 'AVGO', pillar: 'ASI / Compute', value: 1761.25, pct: 6.26, target: 32, gap: -25.74 },
              { symbol: 'GOOG', pillar: 'AI Titans / Cloud', value: 1510.62, pct: 5.37, target: 9.3, gap: -3.93 },
              { symbol: 'HUMN', pillar: 'Applied AI / Robotics', value: 770.9, pct: 2.74, target: 5.18, gap: -2.44 },
              { symbol: 'EQIX', pillar: 'Data Infra / Supply Chain', value: 815, pct: 2.90, target: 9.47, gap: -6.57 },
              { symbol: 'MSFT', pillar: 'AI Titans / Cloud', value: 1021, pct: 3.63, target: 9.3, gap: -5.67 },
              { symbol: 'ETHA', pillar: 'Sovereign Finance', value: 1082.25, pct: 3.85, target: 7.91, gap: -4.06 },
              { symbol: 'IBIT', pillar: 'Sovereign Finance', value: 918.75, pct: 3.27, target: 7.91, gap: -4.64 },
              { symbol: 'PANW', pillar: 'Security / Data OS', value: 819, pct: 2.91, target: 7.48, gap: -4.57 },
            ].map((row) => (
              <tr key={row.symbol} className="border-b hover:bg-blue-50">
                <td className="px-3 py-2 font-mono font-semibold">{row.symbol}</td>
                <td className="px-3 py-2">{row.pillar}</td>
                <td className="px-3 py-2">${row.value.toLocaleString()}</td>
                <td className="px-3 py-2">{row.pct}%</td>
                <td className="px-3 py-2">{row.target}%</td>
                <td className={`px-3 py-2 font-bold ${row.gap < 0 ? 'text-red-600' : 'text-green-700'}`}>{row.gap > 0 ? '+' : ''}{row.gap}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
