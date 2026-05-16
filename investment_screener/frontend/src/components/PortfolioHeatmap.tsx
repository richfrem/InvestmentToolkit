/**
 * PortfolioHeatmap.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Interactive treemap visualization of the investment portfolio, supporting
 *     grouping by Sector, Thesis Pillar, and Strategy.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <PortfolioHeatmap />
 *
 * Key Functions:
 *     - refreshPrices() - Triggers backend price update and re-fetches data
 *     - fetchHeatmapData() - Pulls current portfolio and generates heatmap metrics
 *     - getTextColor() - Utility for WCAG-compliant text contrast
 *     - getColorForChange() - Returns Finviz-style green/red shades for price action
 *     - formatValue() - Formats dollar amounts (K/M suffixes)
 *     - formatChange() - Formats percentages with +/- signs
 *     - renderTreemap() - Core D3 logic for building the hierarchy and SVG nodes
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import * as d3 from 'd3';
import { PriceSourceBadge } from './PriceSourceBadge';
import { PILLAR_COLORS, SECTOR_COLORS, SUB_STRATEGY_COLORS } from '../utils/themeColors';

interface StockHeatmapData {
    symbol: string;
    name: string;
    sector: string;
    industry: string;
    price: number;
    shares: number;
    position_value: number;
    change_pct: number;
}

interface SectorData {
    name: string;
    sector_value: number;
    stocks: StockHeatmapData[];
}

interface HeatmapResponse {
    sectors: Record<string, SectorData>;
    stocks: StockHeatmapData[];
    total_value: number;
    price_source?: string;
    refreshed_at?: string;
    exchange_rate?: number;
}

interface TreemapNode {
    name: string;
    id?: string; // Add id to identify pillar/strategy for coloring
    value?: number;
    change_pct?: number;
    symbol?: string;
    shares?: number;
    price?: number;
    children?: TreemapNode[];
}

export default function PortfolioHeatmap() {
    const navigate = useNavigate();
    const [data, setData] = useState<HeatmapResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [groupBy, setGroupBy] = useState<'sector' | 'strategy' | 'pillar'>('sector');
    const [strategyMap, setStrategyMap] = useState<Record<string, string>>({});
    const [pillarMap, setPillarMap] = useState<Record<string, string>>({});
    const [pillarNames, setPillarNames] = useState<Record<string, string>>({});
    const [priceSource, setPriceSource] = useState<string | null>(null);
    const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchHeatmapData();
        // Fetch strategy and pillar assignments
        Promise.all([
            fetch('/api/screener/all-holdings').then(r => r.ok ? r.json() : []),
            fetch('/api/theses/pillars').then(r => r.ok ? r.json() : [])
        ]).then(([holdings, pillars]) => {
            const sMap: Record<string, string> = {};
            const pMap: Record<string, string> = {};
            const pNames: Record<string, string> = {};

            for (const h of holdings) {
                sMap[h.ticker] = h.subStrategyId ?? 'Other';
                pMap[h.ticker] = h.pillarId ?? 'other';
            }
            for (const p of pillars) {
                pNames[p.id] = p.name;
            }
            pNames['other'] = 'Other';
            pNames['cash'] = 'Cash';

            setStrategyMap(sMap);
            setPillarMap(pMap);
            setPillarNames(pNames);
        }).catch(() => {});
    }, []);

    useEffect(() => {
        if (data && svgRef.current && containerRef.current) {
            renderTreemap();
        }
    }, [data, groupBy, strategyMap, pillarMap, pillarNames]);

    useEffect(() => {
        const handleResize = () => {
            if (data && svgRef.current && containerRef.current) {
                renderTreemap();
            }
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [data]);

    useEffect(() => {
        const handler = () => fetchHeatmapData();
        window.addEventListener('portfolio-synced', handler);
        return () => window.removeEventListener('portfolio-synced', handler);
    }, []);

    const refreshPrices = async () => {
        setRefreshing(true);
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/portfolio/refresh-prices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) throw new Error('Failed to refresh prices');

            const result = await response.json();
            setData(result.heatmap);
            if (result.heatmap?.price_source) setPriceSource(result.heatmap.price_source);
            if (result.heatmap?.refreshed_at) setLastRefreshedAt(new Date(result.heatmap.refreshed_at));
        } catch (err: any) {
            // Prevent double-hitting the API on failure
            // await fetchHeatmapData();
            setError(err.message || 'Failed to refresh prices');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const fetchHeatmapData = async () => {
        // Validation: If we already have data and aren't forcing a reload, maybe skip? 
        // For now, let's just ensure we don't double-fetch if loading is true from a previous call (though checking loading state here can be tricky with async).

        try {
            // We are NOT setting loading=true here if we want a silent background update, 
            // but for initial load, loading is initialized to true.

            // We need to get the portfolio items to send to the backend, 
            // OR the backend could just read its own file. 
            // The current backend implementation of /api/portfolio-heatmap expects { items: [...] }.
            // The /api/portfolio endpoint returns { items: [...] }.

            // Let's first GET the portfolio from the backend to ensure we have the source of truth
            const portfolioRes = await fetch('/api/portfolio');
            if (!portfolioRes.ok) throw new Error('Failed to fetch portfolio config');
            const portfolioConfig = await portfolioRes.json();

            const items = portfolioConfig.items || [];

            const response = await fetch('/api/portfolio-heatmap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items })
            });

            if (!response.ok) throw new Error('Failed to fetch heatmap data');

            const result = await response.json();
            setData(result);
            if (result.price_source) setPriceSource(result.price_source);
            if (result.refreshed_at) setLastRefreshedAt(new Date(result.refreshed_at));
        } catch (err: any) {
            console.error(err);
            setError(err.message || 'Failed to load portfolio data');
        } finally {
            setLoading(false);
        }
    };

    // Returns black or white depending on background luminance (WCAG split at L=0.179)
    const getTextColor = (hexColor: string): string => {
        const r = parseInt(hexColor.slice(1, 3), 16) / 255;
        const g = parseInt(hexColor.slice(3, 5), 16) / 255;
        const b = parseInt(hexColor.slice(5, 7), 16) / 255;
        const toLinear = (c: number) => c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        const L = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
        return L > 0.179 ? '#000000' : '#ffffff';
    };

    // Finviz-style colors: bigger gains = darker green, bigger losses = darker red
    const getColorForChange = (change: number): string => {
        if (change >= 8) return '#004d00';    // Deepest green
        if (change >= 5) return '#006600';    // Very dark green
        if (change >= 3) return '#008000';    // Dark green
        if (change >= 2) return '#00a000';    // Medium-dark green
        if (change >= 1) return '#00c000';    // Medium green
        if (change >= 0.5) return '#00e000';  // Light green
        if (change >= 0) return '#40ff40';    // Very light green
        if (change >= -0.5) return '#ff6060'; // Very light red
        if (change >= -1) return '#e00000';   // Light red
        if (change >= -2) return '#c00000';   // Medium red
        if (change >= -3) return '#a00000';   // Medium-dark red
        if (change >= -5) return '#800000';   // Dark red
        if (change >= -8) return '#600000';   // Very dark red
        return '#400000';                      // Deepest red
    };

    const formatValue = (value: number): string => {
        if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
        if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
        return `$${value.toFixed(0)}`;
    };

    const formatChange = (change: number): string => {
        const sign = change >= 0 ? '+' : '';
        return `${sign}${change.toFixed(2)}%`;
    };

    const renderTreemap = () => {
        if (!data || !svgRef.current || !containerRef.current) return;

        const container = containerRef.current;
        const width = container.clientWidth;
        const height = Math.max(520, container.clientHeight);

        d3.select(svgRef.current).selectAll('*').remove();

        const hierarchyData: TreemapNode = {
            name: 'Portfolio',
            children: groupBy === 'sector'
                ? Object.values(data.sectors).map(sector => ({
                    name: sector.name,
                    id: sector.name,
                    children: sector.stocks.map(stock => ({
                        name: stock.symbol,
                        symbol: stock.symbol,
                        value: stock.position_value,
                        change_pct: stock.change_pct,
                        shares: stock.shares,
                        price: stock.price
                    }))
                }))
                : (() => {
                    const mapToUse = groupBy === 'strategy' ? strategyMap : pillarMap;
                    const nameMap = groupBy === 'strategy' ? null : pillarNames;
                    
                    const groups: Record<string, StockHeatmapData[]> = {};
                    for (const stock of data.stocks) {
                        const grpId = mapToUse[stock.symbol] ?? (groupBy === 'strategy' ? 'Other' : 'other');
                        if (!groups[grpId]) groups[grpId] = [];
                        groups[grpId].push(stock);
                    }
                    return Object.entries(groups).map(([grpId, stocks]) => ({
                        name: nameMap ? (nameMap[grpId] ?? grpId) : grpId,
                        id: grpId,
                        children: stocks.map(stock => ({
                            name: stock.symbol,
                            symbol: stock.symbol,
                            value: stock.position_value,
                            change_pct: stock.change_pct,
                            shares: stock.shares,
                            price: stock.price,
                        }))
                    }));
                })()
        };

        const root = d3.hierarchy(hierarchyData)
            .sum(d => d.value || 0)
            .sort((a, b) => (b.value || 0) - (a.value || 0));

        const treemap = d3.treemap<TreemapNode>()
            .size([width, height])
            .paddingOuter(2)
            .paddingTop(18)  // Space for sector label
            .paddingInner(1) // Minimal gap between cells
            .round(true);

        treemap(root);

        const svg = d3.select(svgRef.current)
            .attr('width', width)
            .attr('height', height);

        // Sector groups - minimal styling
        const sectors = svg.selectAll('g.sector')
            .data(root.children || [])
            .join('g')
            .attr('class', 'sector');

        // Sector header background for better visibility
        sectors.append('rect')
            .attr('x', d => (d as any).x0)
            .attr('y', d => (d as any).y0)
            .attr('width', d => (d as any).x1 - (d as any).x0)
            .attr('height', 18)
            .attr('fill', d => {
                const id = d.data.id || d.data.name;
                if (groupBy === 'pillar') return PILLAR_COLORS[id] || 'rgba(255,255,255,0.05)';
                if (groupBy === 'sector') return SECTOR_COLORS[id] || 'rgba(255,255,255,0.05)';
                if (groupBy === 'strategy') return SUB_STRATEGY_COLORS[id] || 'rgba(255,255,255,0.05)';
                return 'rgba(255,255,255,0.05)';
            })
            .attr('opacity', 0.15);

        // Sector label - Finviz style with arrow
        sectors.append('text')
            .attr('x', d => (d as any).x0 + 4)
            .attr('y', d => (d as any).y0 + 12)
            .text(d => {
                const name = d.data.name;
                // Simple truncate if too long for the header
                const width = (d as any).x1 - (d as any).x0;
                if (width < 60) return '';
                if (name.length * 6 > width) return name.substring(0, Math.floor(width / 7)) + '...';
                return `${name} ›`;
            })
            .attr('fill', d => {
                const id = d.data.id || d.data.name;
                if (groupBy === 'pillar') return PILLAR_COLORS[id] || 'rgba(255,255,255,0.6)';
                if (groupBy === 'sector') return SECTOR_COLORS[id] || 'rgba(255,255,255,0.6)';
                if (groupBy === 'strategy') return SUB_STRATEGY_COLORS[id] || 'rgba(255,255,255,0.6)';
                return 'rgba(255,255,255,0.6)';
            })
            .attr('font-size', '10px')
            .attr('font-weight', '600');

        // Stock cells - clean Finviz style
        const leaves = svg.selectAll('g.leaf')
            .data(root.leaves())
            .join('g')
            .attr('class', 'leaf')
            .attr('transform', d => `translate(${(d as any).x0},${(d as any).y0})`)
            .style('cursor', 'pointer');

        // Cell background - no border, just color
        leaves.append('rect')
            .attr('class', 'stock-cell')
            .attr('width', d => Math.max(0, (d as any).x1 - (d as any).x0))
            .attr('height', d => Math.max(0, (d as any).y1 - (d as any).y0))
            .attr('fill', d => getColorForChange(d.data.change_pct || 0))
            .attr('stroke', '#0a0a0a')
            .attr('stroke-width', 0.5)
            .style('transition', 'filter 0.15s ease');

        // Hover and click effects
        leaves.on('mouseover', function () {
            d3.select(this).select('.stock-cell')
                .style('filter', 'brightness(1.25)');
            d3.select(this).raise();
        }).on('mouseout', function () {
            d3.select(this).select('.stock-cell')
                .style('filter', 'none');
        }).on('click', function (_, d) {
            const symbol = d.data.symbol;
            if (symbol) {
                navigate(`/analysis?ticker=${symbol}`);
            }
        });

        // Symbol - larger, bold
        leaves.append('text')
            .attr('x', d => ((d as any).x1 - (d as any).x0) / 2)
            .attr('y', d => ((d as any).y1 - (d as any).y0) / 2 - 9)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .attr('fill', d => getTextColor(getColorForChange(d.data.change_pct || 0)))
            .attr('font-size', d => {
                const w = (d as any).x1 - (d as any).x0;
                if (w > 150) return '26px';
                if (w > 100) return '22px';
                if (w > 70)  return '18px';
                if (w > 50)  return '15px';
                if (w > 35)  return '12px';
                return '10px';
            })
            .attr('font-weight', '800')
            .style('text-shadow', d => {
                const tc = getTextColor(getColorForChange(d.data.change_pct || 0));
                return tc === '#000000' ? 'none' : '0 1px 3px rgba(0,0,0,0.8)';
            })
            .text(d => ((d as any).x1 - (d as any).x0) > 28 ? d.data.symbol || '' : '');

        // Change percentage
        leaves.append('text')
            .attr('x', d => ((d as any).x1 - (d as any).x0) / 2)
            .attr('y', d => ((d as any).y1 - (d as any).y0) / 2 + 13)
            .attr('text-anchor', 'middle')
            .attr('fill', d => {
                const tc = getTextColor(getColorForChange(d.data.change_pct || 0));
                return tc === '#000000' ? 'rgba(0,0,0,0.75)' : 'rgba(255,255,255,0.95)';
            })
            .attr('font-size', d => {
                const w = (d as any).x1 - (d as any).x0;
                if (w > 150) return '18px';
                if (w > 100) return '16px';
                if (w > 70)  return '14px';
                if (w > 50)  return '12px';
                return '10px';
            })
            .attr('font-weight', '600')
            .style('text-shadow', d => {
                const tc = getTextColor(getColorForChange(d.data.change_pct || 0));
                return tc === '#000000' ? 'none' : '0 1px 2px rgba(0,0,0,0.6)';
            })
            .text(d => {
                const w = (d as any).x1 - (d as any).x0;
                if (w < 38) return '';
                return formatChange(d.data.change_pct || 0);
            });

        // Value for larger cells
        leaves.append('text')
            .attr('x', d => ((d as any).x1 - (d as any).x0) / 2)
            .attr('y', d => ((d as any).y1 - (d as any).y0) / 2 + 32)
            .attr('text-anchor', 'middle')
            .attr('fill', d => {
                const tc = getTextColor(getColorForChange(d.data.change_pct || 0));
                return tc === '#000000' ? 'rgba(0,0,0,0.55)' : 'rgba(255,255,255,0.5)';
            })
            .attr('font-size', d => {
                const w = (d as any).x1 - (d as any).x0;
                if (w > 150) return '16px';
                if (w > 100) return '14px';
                if (w > 70)  return '13px';
                return '12px';
            })
            .attr('font-weight', '600')
            .text(d => {
                const w = (d as any).x1 - (d as any).x0;
                const h = (d as any).y1 - (d as any).y0;
                if (w < 60 || h < 60) return '';
                return formatValue(d.value || 0);
            });

        // Tooltips
        leaves.append('title')
            .text(d => `${d.data.symbol}\n${d.data.shares} shares @ $${(d.data.price || 0).toFixed(2)}\nValue: ${formatValue(d.value || 0)}\nChange: ${formatChange(d.data.change_pct || 0)}`);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[520px] bg-black rounded-lg">
                <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-2 border-green-500 border-t-transparent"></div>
                    <span className="text-gray-400 text-sm">
                        {refreshing ? 'Refreshing prices...' : 'Loading...'}
                    </span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-900/30 text-red-400 p-4 rounded-lg text-center">
                <div className="font-medium mb-2">Failed to load</div>
                <button onClick={refreshPrices} className="px-3 py-1 bg-red-800/50 rounded text-sm">
                    Retry
                </button>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div className="h-full flex flex-col bg-black rounded-lg overflow-hidden">
            {/* Minimal Header - Finviz style */}
            <div className="flex justify-between items-center px-3 py-2 bg-zinc-900 border-b border-zinc-800">
                <div className="flex items-center gap-4">
                    <span className="text-white font-semibold text-sm">Stock Heatmap</span>
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <span className="text-red-400">-5%</span>
                        <div className="flex gap-px">
                            <div className="w-3 h-2 bg-red-800"></div>
                            <div className="w-3 h-2 bg-red-600"></div>
                            <div className="w-3 h-2 bg-red-400"></div>
                            <div className="w-3 h-2 bg-green-400"></div>
                            <div className="w-3 h-2 bg-green-600"></div>
                            <div className="w-3 h-2 bg-green-800"></div>
                        </div>
                        <span className="text-green-400">+5%</span>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {/* Group by toggle */}
                    <div className="flex items-center bg-zinc-800 rounded text-xs overflow-hidden">
                        <button
                            onClick={() => setGroupBy('sector')}
                            className={`px-2.5 py-1 transition-colors ${groupBy === 'sector' ? 'bg-zinc-600 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}
                        >Sector</button>
                        <button
                            onClick={() => setGroupBy('pillar')}
                            className={`px-2.5 py-1 transition-colors ${groupBy === 'pillar' ? 'bg-zinc-600 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}
                        >Pillar</button>
                        <button
                            onClick={() => setGroupBy('strategy')}
                            className={`px-2.5 py-1 transition-colors ${groupBy === 'strategy' ? 'bg-zinc-600 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}
                        >Strategy</button>
                    </div>
                    <button
                        onClick={refreshPrices}
                        disabled={refreshing}
                        className="px-3 py-1 bg-zinc-800 text-zinc-300 rounded text-xs hover:bg-zinc-700 disabled:opacity-50 transition-colors"
                    >
                        {refreshing ? '↻ Syncing...' : '↻ Refresh'}
                    </button>
                    <PriceSourceBadge priceSource={priceSource} lastRefreshedAt={lastRefreshedAt} />
                    <div className="text-xs text-zinc-400">
                        {data.stocks.length} stocks
                    </div>
                    <div className="text-right">
                        <div className="text-sm font-bold text-white leading-tight">
                            {formatValue(data.total_value)} <span className="text-zinc-500 font-normal text-xs">USD</span>
                        </div>
                        {data.exchange_rate && (
                            <div className="text-xs text-zinc-400 leading-tight">
                                {formatValue(data.total_value * data.exchange_rate)} <span className="text-zinc-500">CAD</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Treemap Container */}
            <div ref={containerRef} className="flex-1 min-h-[520px] bg-black">
                <svg ref={svgRef} className="w-full h-full"></svg>
            </div>
        </div>
    );
}
