import { useState, useEffect, useRef } from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { getPillarColor } from '@/lib/colors';

interface PillarTreemapProps {
  isActive?: boolean;
  selectedPillar?: string | null;
  onPillarSelect?: (pillarName: string | null) => void;
}

export default function PillarTreemap({ isActive = true, selectedPillar = null, onPillarSelect }: PillarTreemapProps) {
  const [masterData, setMasterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [useTargetAllocation, setUseTargetAllocation] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [showChart, setShowChart] = useState(false);
  const [drilledPillar, setDrilledPillar] = useState<string | null>(null);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient || !isActive) return;
    const el = containerRef.current;
    if (!el) return;
    if (el.clientWidth > 0 && el.clientHeight > 0) {
      setShowChart(true);
      return;
    }

    const ResizeObs = (window as any).ResizeObserver;
    if (!ResizeObs) return;
    const ro = new ResizeObs((entries: ResizeObserverEntry[]) => {
      for (const entry of entries) {
        const cr = (entry as any).contentRect;
        if (cr.width > 0 && cr.height > 0) {
          setShowChart(true);
          ro.disconnect();
          break;
        }
      }
    });
    ro.observe(el);
    return () => { ro.disconnect(); };
  }, [isClient, masterData?.symbolAllocations?.length, masterData?.pillars?.length, useTargetAllocation, isActive]);

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

  useEffect(() => {
    if (!isClient || !isActive) return;
    const id = setTimeout(() => window.dispatchEvent(new Event('resize')), 60);
    return () => clearTimeout(id);
  }, [isClient, useTargetAllocation, masterData?.symbolAllocations?.length, masterData?.pillars?.length, isActive]);

  // Reset showChart when tab becomes inactive so we re-evaluate measurement when re-activated
  useEffect(() => {
    if (!isActive) setShowChart(false);
  }, [isActive]);

  if (loading) {
    return (
      <>
        <CardHeader>
          <CardTitle>Portfolio Allocation Treemap</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-96">
            <p>Loading treemap data...</p>
          </div>
        </CardContent>
      </>
    );
  }

  if (!masterData) {
    return (
      <>
        <CardHeader>
          <CardTitle>Portfolio Allocation Treemap</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-96">
            <p>Unable to load portfolio data</p>
          </div>
        </CardContent>
      </>
    );
  }

  // If the tab is inactive, don't attempt to build or render the chart.
  if (!isActive) {
    return (
      <>
        <CardHeader>
          <CardTitle>Portfolio Allocation Treemap</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[400px] min-w-[1px] min-h-[1px]">
            <p className="text-muted-foreground">Treemap hidden (inactive tab)</p>
          </div>
        </CardContent>
      </>
    );
  }

  // Group symbols by pillar and create treemap data
  const treemapData = masterData.symbolAllocations.reduce((acc: any, symbol: any) => {
    const pillarCode = String(symbol.pillarCode || 'OTHER');
    const pillarName = masterData.pillars.find((p: any) => p.code === pillarCode)?.name || pillarCode;
    const allocationValue = Number(useTargetAllocation ? symbol.targetAllocation : symbol.currentAllocation) || 0;

    let pillar = acc.find((p: any) => p.name === pillarName);
    if (!pillar) {
      pillar = { name: String(pillarName), pillarCode, children: [] };
      acc.push(pillar);
    }

    if (allocationValue > 0) {
      pillar.children.push({
        name: String(symbol.symbol),
        size: allocationValue,
        pillarCode
      });
    }

    return acc;
  }, []);

  const totalAllocation = treemapData.reduce(
    (sum: number, pillar: any) =>
      sum + pillar.children.reduce((pillarSum: number, symbol: any) => pillarSum + Number(symbol.size || 0), 0),
    0
  );

  // Only pass top-level pillar nodes to the Treemap so we get a clean overview
  const flattenedData = treemapData.map((pillar: any) => ({
    name: String(pillar.name),
    pillarCode: String(pillar.pillarCode),
    // Do not include children here — we want a high-level pillar-only treemap
    size: pillar.children.reduce((sum: number, symbol: any) => sum + Number(symbol.size || 0), 0)
  }));

  // If a pillar is drilled, show its children (symbols). selectedPillar is a visual filter/highlight only
  const effectiveRoot = drilledPillar;
  const displayData = effectiveRoot
    ? (treemapData.find((p: any) => p.name === effectiveRoot || p.pillarCode === effectiveRoot)?.children || []).map((s: any) => ({
        name: String(s.name),
        size: Number(s.size || 0),
        pillarCode: effectiveRoot
      }))
    : flattenedData;

  console.log('Treemap data:', flattenedData);

  const treemapKey = `${isClient}-${useTargetAllocation}-${Math.round(totalAllocation * 100)}-${drilledPillar || 'root'}`;

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const value = Number(payload[0].value) || 0;
      return (
        <div className="bg-background p-3 border rounded-lg shadow-lg">
          <p className="font-bold text-card-foreground">{data.name}</p>
          <p className="text-sm text-muted-foreground">
            Allocation: <span className="font-medium text-card-foreground">{value.toFixed(2)}%</span>
          </p>
          {drilledPillar ? (
            <p className="text-xs text-muted-foreground mt-1">Pillar: {drilledPillar}</p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">Level: Pillar</p>
          )}
        </div>
      );
    }
    return null;
  };

  // Simplified renderer: only render pillar-level rectangles (no nested symbols)
  const CustomContent = (props: any) => {
    const { x, y, width, height, index, name } = props;
    const item = displayData[index];
    const pillarColor = getPillarColor(item?.pillarCode || 'OTHER');

    // helper to compute fill opacity and stroke for stronger highlight

    // Only show text when the block is reasonably large
    const canShowText = width > 50 && height > 25;

    const isSelected = selectedPillar && (item?.pillarCode === selectedPillar || item?.name === selectedPillar);
    const isFiltered = Boolean(selectedPillar);
    const fillOpacity = !isFiltered ? 0.95 : isSelected ? 0.95 : 0.28;
    const strokeColor = isSelected ? '#0f172a' : '#ffffff';
    const strokeWidth = isSelected ? 3 : 2;
    return (
      <g style={{ cursor: !drilledPillar ? 'pointer' : 'default' }}>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          onClick={() => {
            // call parent with pillar code or name
            const codeOrName = item?.pillarCode || item?.name || null;
            if (!drilledPillar) {
              setDrilledPillar(codeOrName);
            }
            if (onPillarSelect) onPillarSelect(codeOrName);
          }}
          style={{
            fill: pillarColor,
            fillOpacity,
            stroke: strokeColor,
            strokeWidth: strokeWidth
          }}
        />
        {canShowText && (
          <text
            x={x + width / 2}
            y={y + height / 2}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-white text-xs font-bold pointer-events-none"
            style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.7)' }}
          >
            {String(name)}
          </text>
        )}
      </g>
    );
  };

  return (
    <>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {drilledPillar ? (
              <Button variant="ghost" size="sm" onClick={() => setDrilledPillar(null)}>
                ← Back
              </Button>
            ) : null}
            <CardTitle>{drilledPillar ? `Symbols in ${drilledPillar}` : 'Portfolio Allocation Treemap'}</CardTitle>
          </div>
          <div>
            <div className="flex items-center space-x-1 rounded-md bg-muted p-1">
              <Button
                variant={!useTargetAllocation ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3"
                onClick={() => setUseTargetAllocation(false)}
              >
                Current
              </Button>
              <Button
                variant={useTargetAllocation ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-3"
                onClick={() => setUseTargetAllocation(true)}
              >
                Target
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="w-full h-64" ref={containerRef}>
          {isClient && showChart ? (
            <ResponsiveContainer key={treemapKey} width="100%" height="100%">
        <Treemap
          data={displayData}
                dataKey="size"
                aspectRatio={4 / 3}
                isAnimationActive={false}
                content={<CustomContent />}
              >
                <Tooltip content={<CustomTooltip />} />
              </Treemap>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-muted-foreground">Initializing Chart...</p>
            </div>
          )}
        </div>
      </CardContent>
    </>
  );
}

// getPillarColor is imported from frontend/src/lib/colors.ts
