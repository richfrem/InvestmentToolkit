"use client"
import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { ArrowUpDown } from "lucide-react"

// Define the shape of our data
export type HoldingData = {
  symbol: string
  pillar: string
  openQuantity: number
  currentPrice: number
  avgEntry: number
  gainPct: number
  marketValue: number
  actualPct: number
  targetPct: number
  gapPct: number
}

export const columns: ColumnDef<HoldingData>[] = [
  {
    accessorKey: "symbol",
    header: ({ column }: any) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Symbol <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "pillar",
    header: "Pillar",
  },
  {
    accessorKey: "openQuantity",
    header: () => <div className="text-right">Qty</div>,
    cell: ({ row }: any) => <div className="text-right">{row.getValue("openQuantity")}</div>,
  },
  {
    accessorKey: "marketValue",
    header: ({ column }: any) => (
      <div className="text-right">
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Mkt Value <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      </div>
    ),
    cell: ({ row }: any) => {
      const amount = parseFloat(String(row.getValue("marketValue"))) || 0
      const formatted = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
      }).format(amount)
      return <div className="text-right font-medium">{formatted}</div>
    },
  },
  {
    accessorKey: "actualPct",
    header: ({ column }: any) => (
      <div className="text-right">
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Actual % <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      </div>
    ),
    cell: ({ row }: any) => <div className="text-right">{`${Number(row.getValue("actualPct")).toFixed(2)}%`}</div>,
  },
  {
    accessorKey: "targetPct",
    header: () => <div className="text-right">Target %</div>,
    cell: ({ row }: any) => <div className="text-right">{`${Number(row.getValue("targetPct")).toFixed(2)}%`}</div>,
  },
  {
    accessorKey: "gapPct",
    header: ({ column }: any) => (
      <div className="text-right">
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Gap % <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      </div>
    ),
    cell: ({ row }: any) => {
      const gap = Number(row.getValue("gapPct")) || 0;
      const color = gap > 0.1 ? "text-green-600" : gap < -0.1 ? "text-red-600" : "text-muted-foreground";
      return <div className={`text-right font-medium ${color}`}>{`${gap.toFixed(2)}%`}</div>
    }
  },
]
