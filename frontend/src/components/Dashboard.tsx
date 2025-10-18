import { useState } from 'react';
import HoldingsTable from '@/components/HoldingsTable';
import PillarHistogram from '@/components/PillarHistogram';
import PillarTreemap from '@/components/PillarTreemap';
import { Button } from './ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { usePortfolio } from '../features/portfolio/hooks/usePortfolio';
import axios from 'axios';

interface DashboardProps {
  onAuth: () => void;
}

const Dashboard = ({ onAuth }: DashboardProps) => {
  const { holdings, error } = usePortfolio();
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [updateLoading, setUpdateLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);

  const handleRefreshData = async () => {
    setRefreshLoading(true);
    try {
      const response = await axios.get('/api/refresh');
      console.log('✅ Data refreshed from Questrade:', response.data);
      alert('✅ Data successfully refreshed from Questrade API');
    } catch (err) {
      console.error('❌ Error refreshing data:', err);
      alert('❌ Failed to refresh data from Questrade');
      onAuth(); // Trigger auth if needed
    } finally {
      setRefreshLoading(false);
    }
  };

  const handleUpdatePortfolio = async () => {
    setUpdateLoading(true);
    try {
      const response = await axios.post('/api/update-portfolio-data');
      console.log('✅ Portfolio data updated:', response.data);
      alert(`✅ Portfolio data updated successfully!\nTotal Value: $${response.data.totalMarketValue?.toLocaleString()}\nHoldings: ${response.data.holdingsCount}`);
      // Don't refresh the page immediately - let user see the result
    } catch (err) {
      console.error('❌ Error updating portfolio data:', err);
      alert('❌ Failed to update portfolio data');
      onAuth(); // Trigger auth if needed
    } finally {
      setUpdateLoading(false);
    }
  };

  const handleSyncAll = async () => {
    setSyncLoading(true);
    try {
      // First refresh data from Questrade
      console.log('🔄 Step 1: Refreshing data from Questrade...');
      await axios.get('/api/refresh');

      // Then update portfolio calculations
      console.log('📊 Step 2: Updating portfolio calculations...');
      const response = await axios.post('/api/update-portfolio-data');

      console.log('✅ Sync completed successfully:', response.data);
      alert(`✅ Sync completed successfully!\nTotal Value: $${response.data.totalMarketValue?.toLocaleString()}\nHoldings: ${response.data.holdingsCount}`);
      // Refresh the page to show updated data
      window.location.reload();
    } catch (err) {
      console.error('❌ Error during sync:', err);
      alert('❌ Failed to sync data');
      onAuth(); // Trigger auth if needed
    } finally {
      setSyncLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Data Management Buttons */}
      <div className="flex flex-wrap gap-4 p-6 bg-card rounded-lg border">
        <div className="flex flex-col gap-2">
          <h3 className="text-lg font-semibold">Data Management</h3>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={handleRefreshData}
              disabled={refreshLoading}
              variant="outline"
            >
              {refreshLoading ? '🔄 Refreshing...' : '📡 Get Questrade Data'}
            </Button>
            <Button
              onClick={handleUpdatePortfolio}
              disabled={updateLoading}
              variant="outline"
            >
              {updateLoading ? '📊 Updating...' : '🔄 Refresh Portfolio Master Data'}
            </Button>
            <Button
              onClick={handleSyncAll}
              disabled={syncLoading}
              variant="default"
            >
              {syncLoading ? '🔄 Syncing...' : '⚡ Sync All (Both Steps)'}
            </Button>
          </div>
        </div>
      </div>

      {/* Portfolio components - HoldingsTable handles its own loading state */}
      <HoldingsTable />
      <PillarHistogram />
      <PillarTreemap />
      {error && <p className="text-destructive">{error}</p>}

      {/* Legacy holdings table - can be removed if not needed */}
      {holdings.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Raw Holdings Data</h2>
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
      )}
    </div>
  );
};

export default Dashboard;