import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

// Import holdings data from master data file
// @ts-ignore
import masterData from '../../../TargetPortfolio/portfolio_master_data.json';

// Extract holdings data from master data
const holdings = masterData.currentHoldings.map((holding: any) => ({
  symbol: holding.symbol,
  pctPortfolio: holding.pctPortfolio,
  targetPct: masterData.symbolAllocations.find((a: any) => a.symbol === holding.symbol)?.targetAllocation || 0
}));

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
    legend: { position: 'top' as const, labels: { font: { size: 10 }, padding: 8 } },
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
    <Card>
      <CardHeader>
        <CardTitle>All Holdings: Actual vs. Target Allocation</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="p-0">
          <Bar data={data} options={options} height={Math.max(180, sorted.length * 7)} />
        </div>
      </CardContent>
    </Card>
  );
}
