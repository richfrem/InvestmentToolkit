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
import { LineElement, PointElement, LineController } from 'chart.js';
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getPillarColor } from '@/lib/colors';

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, LineController, Title, Tooltip, Legend);

type PillarHistogramProps = {
  selectedPillar?: string | null;
  onPillarSelect?: (pillarName: string | null) => void;
}

export default function PillarHistogram({ onPillarSelect }: PillarHistogramProps) {
  const [masterData, setMasterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/TargetPortfolio/portfolio_master_data.json')
      .then(response => response.json())
      .then(data => {
        setMasterData(data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error loading master data:', error);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <p className="text-muted-foreground">Loading chart...</p>
      </div>
    );
  }

  if (!masterData) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <p className="text-muted-foreground">Portfolio data not available. Please refresh the portfolio master data first.</p>
      </div>
    );
  }

  // --- DATA TRANSFORMATION FOR STACKED BARS ---
  const chartData = (masterData?.pillars || []).map((pillar: any) => {
    const actual = (pillar.currentAllocation || 0) * 100;
    const target = (pillar.targetAllocation || 0) * 100;
    const gap = actual - target;
    return { name: pillar.name, code: pillar.code, actual, target, gap };
  }).sort((a: any, b: any) => b.target - a.target);

  const labels = chartData.map((p: any) => p.name);

  const data = {
    labels,
    datasets: [
      {
        label: 'Actual (up to Target)',
        data: chartData.map((p: any) => Math.min(p.actual, p.target)),
        backgroundColor: chartData.map((p: any) => getPillarColor(p.code)),
      },
      {
        label: 'Over Target',
        data: chartData.map((p: any) => p.actual > p.target ? p.actual - p.target : 0),
        backgroundColor: '#6ee7b7',
      },
      {
        label: 'Under Target',
        data: chartData.map((p: any) => p.actual < p.target ? p.target - p.actual : 0),
        backgroundColor: '#fda4af',
      }
    ],
  };

  const options = {
    indexAxis: 'y' as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { stacked: true, grid: { display: false } },
      y: { stacked: true, grid: { display: false } }
    },
    onClick: (_event: any, elements: any[]) => {
      if (elements && elements.length > 0) {
        const clickedIndex = elements[0].index;
        const pillarCode = chartData[clickedIndex]?.code || chartData[clickedIndex]?.name;
        if (onPillarSelect) onPillarSelect(pillarCode);
      }
    }
  };

  return (
    <Card className="border-none shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Pillar Allocation</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <Bar data={data as any} options={options} />
        </div>
      </CardContent>
    </Card>
  );
}
