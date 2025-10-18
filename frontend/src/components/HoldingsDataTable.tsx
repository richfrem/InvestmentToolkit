"use client"

import * as React from "react"
import { useEffect } from "react"
import {
  SortingState,
  ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu"
import { SlidersHorizontal } from "lucide-react"
// HoldingsDataTable is headless — parent should wrap it in Card/CardContent
import { HoldingData } from "./HoldingsDataTableColumns"

function transformData(data: any): HoldingData[] {
    if (!data) return [];
  return data.currentHoldings.map((h: any) => {
    const alloc = data.symbolAllocations.find((a: any) => a.symbol === h.symbol) || {};
    const currentPrice = alloc.currentPrice || 0;
    const avgEntry = alloc.averageEntryPrice || 0;
    const gainPct = avgEntry > 0 ? ((currentPrice - avgEntry) / avgEntry) * 100 : 0;

    // Fix: `alloc.targetAllocation` and `h.pctPortfolio` are already percentages (e.g., 6.25)
    const actualPct = parseFloat(String(h.pctPortfolio)) || 0;
    const targetPct = parseFloat(String(alloc.targetAllocation)) || 0;
    const gapPct = Number((actualPct - targetPct).toFixed(2));

    return {
      symbol: h.symbol,
      pillar: alloc.pillarCode || h.pillar || 'OTHER',
      openQuantity: alloc.openQuantity || 0,
      currentPrice: currentPrice,
      avgEntry: avgEntry,
      gainPct: gainPct,
      marketValue: h.totalMarketValue || 0,
      actualPct: Number(actualPct.toFixed(2)),
      targetPct: Number(targetPct.toFixed(2)),
      gapPct: gapPct,
    };
  });
}

interface HoldingsDataTableProps {
  selectedPillar?: string | null;
}

export default function HoldingsDataTable({ selectedPillar = null }: HoldingsDataTableProps) {
  const [sorting, setSorting] = React.useState<SortingState>([{ id: "marketValue", desc: true }])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [masterData, setMasterData] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    fetch('/TargetPortfolio/portfolio_master_data.json')
      .then(r => r.json())
      .then(d => { setMasterData(d); setLoading(false); })
      .catch(e => { console.error(e); setLoading(false); })
  }, [])

  const data = React.useMemo(() => transformData(masterData), [masterData]);

  // fields customization state
  const [showCustomize, setShowCustomize] = React.useState(false);
  const [availableFields, setAvailableFields] = React.useState<string[]>([]);
  const [selectedFields, setSelectedFields] = React.useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('holdings_table_fields');
      return saved ? JSON.parse(saved) : ['symbol','pillar','openQuantity','marketValue','actualPct','targetPct','gapPct'];
    } catch (e) { return ['symbol','pillar','openQuantity','marketValue','actualPct','targetPct','gapPct']; }
  });

  // derive available fields when data loads
  React.useEffect(() => {
    if (data && data.length) {
      const keys = Array.from(new Set(data.flatMap(d => Object.keys(d))));
      setAvailableFields(keys);
      // ensure selectedFields are valid
      setSelectedFields(prev => prev.filter(f => keys.includes(f)).length ? prev.filter(f => keys.includes(f)) : keys.slice(0,7));
    }
  }, [data]);

  // persist selected fields
  React.useEffect(() => {
    try { localStorage.setItem('holdings_table_fields', JSON.stringify(selectedFields)); } catch (e) {}
  }, [selectedFields]);

  // build dynamic columns based on selectedFields and data sample
  const dynamicColumns = React.useMemo(() => {
    const sample: any = data && data.length ? data[0] : {};
    return selectedFields.map((field) => {
      const value = sample ? sample[field] : undefined;
      const isNumber = typeof value === 'number';

      return {
        accessorKey: field,
        header: () => isNumber ? <div className="text-right">{field.replace(/([A-Z])/g, ' $1')}</div> : <div>{field}</div>,
        cell: ({ row }: any) => {
          const v = row.getValue(field);
          if (v == null) return null;
          if (isNumber) {
            // format percentages specially
            if (field.toLowerCase().includes('pct') || field.toLowerCase().includes('percent')) {
              return <div className="text-right">{Number(v).toFixed(2)}%</div>;
            }
            if (field.toLowerCase().includes('market') || field.toLowerCase().includes('value')) {
              const formatted = new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(Number(v));
              return <div className="text-right font-medium">{formatted}</div>;
            }
            return <div className="text-right">{Number(v).toLocaleString()}</div>;
          }
          return <div className="font-medium">{String(v)}</div>;
        }
      };
    });
  }, [selectedFields, data]);

  // derive filtered data based on selectedPillar (map display name to pillar code)
  const filteredData = React.useMemo(() => {
    if (!selectedPillar) return data;
    const pillarFromMaster = masterData?.pillars?.find((p: any) => p.name === selectedPillar || p.code === selectedPillar);
    const pillarCode = pillarFromMaster ? pillarFromMaster.code : selectedPillar;
    return data.filter((row: any) => String(row.pillar) === String(pillarCode) || String(row.pillar) === String(selectedPillar));
  }, [data, selectedPillar, masterData]);

  const table = useReactTable({
    data: filteredData,
    columns: dynamicColumns as any,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    onColumnFiltersChange: setColumnFilters,
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      sorting,
      columnFilters,
    },
  })

  // When selectedPillar changes, programmatically set the pillar column filter
  useEffect(() => {
    try {
      if (!selectedPillar) {
        table.getColumn("pillar")?.setFilterValue(undefined);
        return;
      }

      // Try to map a display name to the internal pillar code stored on rows
      const pillarFromMaster = masterData?.pillars?.find((p: any) => p.name === selectedPillar || p.code === selectedPillar);
      const pillarCode = pillarFromMaster ? pillarFromMaster.code : selectedPillar;

      table.getColumn("pillar")?.setFilterValue(pillarCode);
    } catch (e) {
      // defensive: table may not be initialized yet
    }
  }, [selectedPillar, table, masterData]);

  if (loading) {
    // Headless loading placeholder; parent Card should provide the card shell
    return (
      <div className="w-full py-6">
        <div>Loading holdings data...</div>
      </div>
    )
  }
  // Headless table layout — parent should wrap with Card/CardContent
  return (
    <div className="w-full">
      <div className="flex items-center justify-between py-2">
        <h3 className="text-lg font-semibold">{selectedPillar ? `Holdings — ${selectedPillar}` : 'All Holdings'}</h3>
        <div className="flex items-center py-2 space-x-4">
          <Input
            placeholder="Filter by symbol..."
            value={(table.getColumn("symbol")?.getFilterValue() as string) ?? ""}
            onChange={(event) =>
              table.getColumn("symbol")?.setFilterValue(event.target.value)
            }
            className="max-w-sm"
          />

          <DropdownMenu>
            <DropdownMenuTrigger>
              <Button variant="outline">
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                View
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => {
                  return (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      className="capitalize"
                      checked={column.getIsVisible()}
                      onCheckedChange={(value: boolean | 'indeterminate') => column.toggleVisibility(!!value)}
                    >
                      {column.id.replace(/_/g, ' ')}
                    </DropdownMenuCheckboxItem>
                  );
                })}
            </DropdownMenuContent>
          </DropdownMenu>

          <Button variant="outline" onClick={() => setShowCustomize(true)}>Customize</Button>
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup: any) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header: any) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row: any) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell: any) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={dynamicColumns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-end space-x-2 py-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          Next
        </Button>
      </div>

      {/* Customize modal */}
      {showCustomize && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-card p-6 rounded-lg w-[min(800px,90%)]">
            <h3 className="text-lg font-semibold mb-4">Customize table fields</h3>
            <p className="text-sm text-muted-foreground mb-4">Pick which attributes from the dataset should be visible in the table.</p>
            <div className="grid grid-cols-2 gap-2 max-h-72 overflow-auto mb-4">
              {availableFields.map((f) => (
                <label key={f} className="flex items-center gap-2">
                  <input type="checkbox" checked={selectedFields.includes(f)} onChange={(e) => {
                    const next = e.target.checked ? [...selectedFields, f] : selectedFields.filter(s => s !== f);
                    setSelectedFields(next);
                  }} />
                  <span className="capitalize">{f}</span>
                </label>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setShowCustomize(false)}>Cancel</Button>
              <Button onClick={() => setShowCustomize(false)}>Save</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
