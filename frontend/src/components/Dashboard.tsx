import { useState } from 'react';
import PortfolioCharts from './PortfolioCharts';
import HoldingsHistogram from './HoldingsHistogram';
import PillarHistogram from './PillarHistogram';
import { Button } from './ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { usePortfolio } from '../features/portfolio/hooks/usePortfolio';

interface DashboardProps {
  onAuth: () => void;
}

const Dashboard = ({ onAuth }: DashboardProps) => {
  const { holdings, loading, error, fetchHoldings } = usePortfolio();

  const handleFetch = async () => {
    try {
      await fetchHoldings();
    } catch (err) {
      onAuth(); // Trigger auth if needed
    }
  };

  return (
    <div className="space-y-8">
  <HoldingsHistogram />
  <PillarHistogram />
      {/* Optionally keep pillar and pie charts below, or remove if too busy */}
      {/* <PortfolioCharts /> */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Portfolio Holdings</h2>
        <Button onClick={handleFetch} disabled={loading}>
          {loading ? 'Fetching...' : 'Fetch Holdings'}
        </Button>
      </div>
      {error && <p className="text-destructive">{error}</p>}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Quantity</TableHead>
            <TableHead>Book Value</TableHead>
            <TableHead>Market Value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {holdings.map((holding, index) => (
            <TableRow key={index}>
              <TableCell>{holding.symbol}</TableCell>
              <TableCell>{holding.quantity}</TableCell>
              <TableCell>${holding.bookValue.toFixed(2)}</TableCell>
              <TableCell>${holding.marketValue.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default Dashboard;