import React, { useState, useMemo } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

// Extract holdings data from master data with enhanced information
export default function HoldingsTable() {
  const [masterData, setMasterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
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

  const holdings = masterData ? masterData.currentHoldings.map((holding: any) => {
    const allocation = masterData.symbolAllocations.find((a: any) => a.symbol === holding.symbol);
    return {
      symbol: holding.symbol,
      pctPortfolio: holding.pctPortfolio,
      targetPct: (allocation?.targetAllocation || 0) * 100,
      pillarCode: allocation?.pillarCode || 'OTHER',
      openQuantity: allocation?.openQuantity || 0,
      currentPrice: allocation?.currentPrice || 0,
      averageEntryPrice: allocation?.averageEntryPrice || 0,
      totalCost: allocation?.totalCost || 0,
      currentMarketValue: allocation?.currentMarketValue || 0,
      currentAllocation: allocation?.currentAllocation || 0,
      targetAllocation: (allocation?.targetAllocation || 0) * 100,
      gap: allocation?.gap || 0,
      targetQuantity: allocation?.targetQuantity || 0
    };
  }) : [];

  const [sortField, setSortField] = useState<'symbol' | 'pctPortfolio' | 'targetPct'>('pctPortfolio');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const sortedHoldings = useMemo(() => {
    return [...holdings].sort((a, b) => {
      let aVal: string | number = a[sortField];
      let bVal: string | number = b[sortField];

      if (sortField === 'symbol') {
        aVal = aVal.toString().toLowerCase();
        bVal = bVal.toString().toLowerCase();
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [sortField, sortDirection]);

  const handleSort = (field: 'symbol' | 'pctPortfolio' | 'targetPct') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Helper function to get pillar name
  const getPillarName = (code: string) => {
    if (!masterData) return code;
    const pillar = masterData.pillars.find((p: any) => p.code === code);
    return pillar ? pillar.name : code;
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Portfolio Holdings</CardTitle>
        </CardHeader>
        <CardContent>
          <div>Loading holdings data...</div>
        </CardContent>
      </Card>
    );
  }

  if (!masterData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>All Holdings: Actual vs. Target Allocation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Portfolio data not available. Please refresh the portfolio master data first.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>All Holdings: Actual vs. Target Allocation</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleSort('symbol')}
              >
                Symbol {sortField === 'symbol' && (sortDirection === 'asc' ? '↑' : '↓')}
              </TableHead>
              <TableHead>Pillar</TableHead>
              <TableHead className="text-right">Open Qty</TableHead>
              <TableHead className="text-right">Current Price</TableHead>
              <TableHead className="text-right">Avg Entry</TableHead>
              <TableHead className="text-right">Gain %</TableHead>
              <TableHead className="text-right">Total Cost</TableHead>
              <TableHead className="text-right">Market Value</TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50 text-right"
                onClick={() => handleSort('pctPortfolio')}
              >
                Actual % {sortField === 'pctPortfolio' && (sortDirection === 'asc' ? '↑' : '↓')}
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50 text-right"
                onClick={() => handleSort('targetPct')}
              >
                Target % {sortField === 'targetPct' && (sortDirection === 'asc' ? '↑' : '↓')}
              </TableHead>
              <TableHead className="text-right">Gap %</TableHead>
              <TableHead className="text-right">Target Shares</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedHoldings.map((holding) => {
              const gap = holding.pctPortfolio - holding.targetPct;
              const gainPct = holding.currentPrice > 0 ? ((holding.currentPrice - holding.averageEntryPrice) / holding.currentPrice) * 100 : 0;
              return (
                <TableRow key={holding.symbol}>
                  <TableCell className="font-medium">{holding.symbol}</TableCell>
                  <TableCell>{getPillarName(holding.pillarCode)}</TableCell>
                  <TableCell className="text-right">{holding.openQuantity?.toLocaleString() || 0}</TableCell>
                  <TableCell className="text-right">${holding.currentPrice?.toFixed(2) || '0.00'}</TableCell>
                  <TableCell className="text-right">${holding.averageEntryPrice?.toFixed(2) || '0.00'}</TableCell>
                  <TableCell className={`text-right ${gainPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right">${holding.totalCost?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || '0.00'}</TableCell>
                  <TableCell className="text-right">${holding.currentMarketValue?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || '0.00'}</TableCell>
                  <TableCell className="text-right">{holding.pctPortfolio.toFixed(2)}%</TableCell>
                  <TableCell className="text-right">{holding.targetPct.toFixed(2)}%</TableCell>
                  <TableCell className={`text-right font-medium ${gap > 0 ? 'text-green-600' : gap < 0 ? 'text-red-600' : ''}`}>
                    {gap > 0 ? '+' : ''}{gap.toFixed(2)}%
                  </TableCell>
                  <TableCell className="text-right">{holding.targetQuantity?.toLocaleString(undefined, {maximumFractionDigits: 0}) || 0}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}