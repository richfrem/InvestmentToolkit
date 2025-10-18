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
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

// Import data from master data file
// @ts-ignore
import masterData from '../../../TargetPortfolio/portfolio_master_data.json';

const pillarOrder = masterData.pillars.map((p: any) => p.name);

const actualPillars = pillarOrder.map(pillar => {
  const value = (masterData.pillarTotals as any)[pillar] || 0;
  return { pillar, pct: masterData.totalMarketValue > 0 ? (value / masterData.totalMarketValue) * 100 : 0 };
});

const targetPillars = masterData.pillars.map((pillar: any) => ({
  pillar: pillar.name,
  pct: pillar.targetAllocation
}));

const pillarData = {
  labels: pillarOrder,
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

const pillarOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' as const },
    title: { display: true, text: 'Portfolio Allocation by Pillar: Actual vs. Target', font: { size: 22 } },
  },
};

// Get top 10 holdings by market value
const topHoldings = masterData.currentHoldings
  .sort((a: any, b: any) => b.totalMarketValue - a.totalMarketValue)
  .slice(0, 10);

const holdingsData = {
  labels: topHoldings.map((h: any) => h.symbol),
  datasets: [
    {
      label: '% of Portfolio',
      data: topHoldings.map((h: any) => h.pctPortfolio),
      backgroundColor: 'rgba(75, 192, 192, 0.7)',
    },
    {
      label: 'Target %',
      data: topHoldings.map((h: any) => h.targetPct),
      backgroundColor: 'rgba(255, 205, 86, 0.7)',
    },
  ],
};

const holdingsOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' as const },
    title: { display: true, text: 'Top Holdings: Actual vs. Target Allocation', font: { size: 20 } },
  },
};

const pieData = {
  labels: pillarOrder,
  datasets: [
    {
      data: actualPillars.map(p => p.pct),
      backgroundColor: [
        '#36A2EB', '#FFCE56', '#FF6384', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#FF6384', '#B2FF66'
      ],
    },
  ],
};

export default function PortfolioCharts() {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card>
          <CardContent className="p-6">
            <Bar data={pillarData} options={pillarOptions} height={350} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <Pie data={pieData} />
            <div className="text-center mt-4 font-medium text-gray-700">Current Portfolio Allocation</div>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardContent className="p-6">
          <Bar data={holdingsData} options={holdingsOptions} height={300} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Holdings Table</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="min-w-full text-sm text-left border">
            <thead className="bg-muted">
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
              {topHoldings.map((holding: any) => {
                const gap = holding.pctPortfolio - holding.targetPct;
                return (
                  <tr key={holding.symbol} className="border-b hover:bg-muted/50">
                    <td className="px-3 py-2 font-mono font-semibold">{holding.symbol}</td>
                    <td className="px-3 py-2">{holding.pillar}</td>
                    <td className="px-3 py-2">${holding.totalMarketValue.toLocaleString()}</td>
                    <td className="px-3 py-2">{holding.pctPortfolio.toFixed(2)}%</td>
                    <td className="px-3 py-2">{holding.targetPct.toFixed(2)}%</td>
                    <td className={`px-3 py-2 font-bold ${gap < 0 ? 'text-red-600' : gap > 0 ? 'text-green-600' : ''}`}>{gap > 0 ? '+' : ''}{gap.toFixed(2)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
