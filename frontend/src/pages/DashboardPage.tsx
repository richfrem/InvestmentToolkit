import { useState, useCallback } from 'react'
import PillarHistogram from '../components/PillarHistogram';
import PillarTreemap from '../components/PillarTreemap';
import HoldingsDataTable from '@/components/HoldingsDataTable';
import { useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';

export default function DashboardPage() {
  const [selectedPillar, setSelectedPillar] = useState<string | null>(null)
  const [masterData, setMasterData] = useState<any>(null)
  const [selectedPillarLabel, setSelectedPillarLabel] = useState<string | null>(null)

  const handlePillarSelect = useCallback((pillarName: string | null) => {
    // toggle behavior: clicking the same pillar clears selection
    setSelectedPillar(prev => (prev === pillarName ? null : pillarName))
  }, [])

  useEffect(() => {
    fetch('/TargetPortfolio/portfolio_master_data.json')
      .then(r => r.json())
      .then(d => setMasterData(d))
      .catch(() => setMasterData(null))
  }, [])

  useEffect(() => {
    if (!selectedPillar || !masterData) {
      setSelectedPillarLabel(null);
      return;
    }
    const found = masterData.pillars.find((p: any) => p.code === selectedPillar || p.name === selectedPillar);
    setSelectedPillarLabel(found ? found.name : selectedPillar);
  }, [selectedPillar, masterData])

  return (
    <div className="space-y-4">
      {/* Top controls: Clear filter placed top-right when active */}
      <div className="flex items-center justify-end">
        {selectedPillar && (
          <div className="flex items-center space-x-2">
            <div className="text-sm text-muted-foreground">Filtered: <span className="font-medium">{selectedPillarLabel || selectedPillar}</span></div>
            <button className="btn btn-outline text-sm" onClick={() => setSelectedPillar(null)}>Clear filter</button>
          </div>
        )}
      </div>

      {/* SPLIT-VIEW: left column charts, right column data table */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        {/* LEFT: charts stacked (5/12) */}
        <div className="lg:col-span-5 space-y-4">
          <PillarHistogram selectedPillar={selectedPillar} onPillarSelect={handlePillarSelect} />
          <PillarTreemap selectedPillar={selectedPillar} onPillarSelect={handlePillarSelect} />
        </div>

        {/* RIGHT: data table (details) (7/12) */}
        <div className="lg:col-span-7">
          <Card>
            <CardContent className="p-4">
              <HoldingsDataTable selectedPillar={selectedPillar} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
