import PillarHistogram from '../components/PillarHistogram';
import PillarTreemap from '../components/PillarTreemap';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import HoldingsDataTable from '@/components/HoldingsDataTable';


export default function ChartsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold tracking-tight">Charts Dashboard</h2>

      <Tabs defaultValue="bar_chart" className="w-full">
        <TabsList>
          <TabsTrigger value="bar_chart">Pillar Bar Chart</TabsTrigger>
          <TabsTrigger value="treemap">Pillar Treemap</TabsTrigger>
          <TabsTrigger value="holdings_table">Holdings Table</TabsTrigger>
        </TabsList>

        <TabsContent value="bar_chart">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <PillarHistogram />
            </div>
            <div className="lg:col-span-1">
              <PillarTreemap />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="treemap">
          <PillarTreemap />
        </TabsContent>

        <TabsContent value="holdings_table">
          {/* Use the new TanStack-powered table */}
          <HoldingsDataTable />
        </TabsContent>
      </Tabs>
    </div>
  );
}
