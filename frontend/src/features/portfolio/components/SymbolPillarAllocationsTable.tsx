import { useState, useMemo, useEffect } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { Input } from "../../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { Button } from "../../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";

export const SymbolPillarAllocationsTable: React.FC = () => {
  const [masterData, setMasterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<any[]>([]);

  useEffect(() => {
    fetch('/TargetPortfolio/portfolio_master_data.json')
      .then(r => r.json())
      .then(d => {
        setMasterData(d);
        // Normalize allocations to fractions (0-1) for internal calculations
        const normalized = d.symbolAllocations.map((row: any, id: number) => ({
          id,
          ...row,
          targetAllocation: typeof row.targetAllocation === 'number' ? row.targetAllocation / 100 : 0,
          currentAllocation: typeof row.currentAllocation === 'number' ? row.currentAllocation / 100 : 0,
        }));
        setRows(normalized);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error loading master data for editing:', err);
        setLoading(false);
      });
  }, []);

  const pillarName = (code: string) => {
    if (!masterData) return code;
    const p = masterData.pillars.find((p: any) => p.code === code);
    return p ? p.name : code;
  };
  const allPillarCodes = masterData ? masterData.pillars.map((p: any) => p.code) : [];

  // Allocation sum validation
  const total = useMemo(() => rows.reduce((sum: number, r: any) => sum + Number(r.targetAllocation), 0), [rows]);
  const allocationError = Math.abs(total - 1) > 0.0001;

  const handlePillarChange = (id: number, newPillarCode: string) => {
    setRows((prev: any[]) => prev.map((row: any) => row.id === id ? { ...row, pillarCode: newPillarCode } : row));
  };

  const handleAllocationChange = (id: number, newAllocation: string) => {
    const value = parseFloat(newAllocation) || 0;
    setRows((prev: any[]) => prev.map((row: any) => row.id === id ? { ...row, targetAllocation: value / 100 } : row));
  };

  const save = () => {
    // TODO: POST to backend or save to file
    alert("Saved! (stub)");
  };

  if (loading) {
    return (
      <Card className="w-full max-w-6xl mx-auto">
        <CardHeader>
          <CardTitle>Loading Allocations...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (!masterData) {
    return (
      <Card className="w-full max-w-6xl mx-auto">
        <CardHeader>
          <CardTitle>Edit Symbol-Pillar Allocations</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Portfolio data not available. Please refresh the portfolio master data first.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-6xl mx-auto">
      <CardHeader>
        <CardTitle>Edit Symbol-Pillar Allocations</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Pillar</TableHead>
                <TableHead className="text-right">Mkt Value</TableHead>
                <TableHead className="text-right">Current %</TableHead>
                <TableHead className="text-right">Target %</TableHead>
                <TableHead className="text-right">Gap %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row: any) => {
                const currentPct = Number(row.currentAllocation) || 0;
                const targetPct = Number(row.targetAllocation) || 0;
                const gapPct = (currentPct - targetPct) * 100;
                return (
                  <TableRow key={row.id}>
                    <TableCell className="font-medium">{row.symbol}</TableCell>
                    <TableCell>
                      <Select value={row.pillarCode} onValueChange={(newValue) => handlePillarChange(row.id, newValue)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {allPillarCodes.map((code: string) => (
                            <SelectItem key={code} value={code}>{pillarName(code)}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-right">{new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(Number(row.currentMarketValue || 0))}</TableCell>
                    <TableCell className="text-right">{(currentPct * 100).toFixed(2)}%</TableCell>
                    <TableCell className="text-right">
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={Number((targetPct * 100).toFixed(2))}
                        onChange={(e) => handleAllocationChange(row.id, e.target.value)}
                        className="max-w-[110px] ml-auto"
                      />
                    </TableCell>
                    <TableCell className={`text-right ${gapPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {gapPct >= 0 ? '+' : ''}{gapPct.toFixed(2)}%
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm">
            <strong>Total Allocation:</strong> {(total * 100).toFixed(2)}%
            {allocationError && <span className="text-red-600 ml-2">Must sum to 100%</span>}
          </p>
          <Button onClick={save} disabled={allocationError}>
            Save
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
