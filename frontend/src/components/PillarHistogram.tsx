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

// Import actual and target pillar allocations from JSON for accuracy
// @ts-ignore
import report from '../../../TargetPortfolio/portfolio_thesis_alignment_report.json';

const pillarOrder = [
  'ASI / Compute',
  'Cash',
  'Power / Energy',
  'Data Infra / Supply Chain',
  'AI Titans / Cloud',
  'Sovereign Finance',
  'Security / Data OS',
  'Applied AI / Robotics',
  'Other',
];

const actualPillars = pillarOrder.map(pillar => {
  // Use the actual % from the report, calculated as (pillar total / totalMarketValue) * 100
  const value = report.pillarTotals[pillar] || 0;
  return { pillar, pct: (value / report.totalMarketValue) * 100 };
});

const targetPillars = pillarOrder.map(pillar => {
  // Use the target % from the report
  const value = report.targetAllocations[pillar] || 0;
  return { pillar, pct: value };
});

const labels = pillarOrder;
const data = {
  labels,
  datasets: [
    {
      label: 'Actual %',
      data: actualPillars.map(p => p.pct),
      backgroundColor: 'rgba(54, 162, 235, 0.7)',
    },
    {
      label: 'Target %',
      data: targetPillars.map(p => p.pct),
      backgroundColor: 'rgba(255, 99, 132, 0.7)',
    },
  ],
};

const options = {
  indexAxis: 'y' as const,
  responsive: true,
  plugins: {
    legend: { position: 'top', labels: { font: { size: 11 }, padding: 8 } },
    title: { display: true, text: 'Portfolio by Investment Pillar: Actual vs. Target', font: { size: 14 } },
  },
  layout: {
    padding: { left: 0, right: 2, top: 0, bottom: 0 },
  },
  scales: {
    x: {
      max: Math.max(...actualPillars.map(p => p.pct), ...targetPillars.map(p => p.pct)) + 5,
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
    bar: { borderRadius: 2, borderSkipped: false },
  },
  barThickness: 12,
  categoryPercentage: 0.7,
  barPercentage: 0.8,
};

export default function PillarHistogram() {
  return (
    <div className="bg-white rounded shadow p-1 mb-4">
      <Bar data={data} options={options} height={Math.max(120, labels.length * 18)} />
    </div>
  );
}
