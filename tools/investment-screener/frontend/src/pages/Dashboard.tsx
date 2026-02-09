import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { fetchStockData, type StockData } from '../services/api';
import { useRecentTickers } from '../hooks/useRecentTickers';
import MetricsGrid from '../components/MetricsGrid';
import FinancialChart from '../components/analysis/FinancialChart';
import AnalysisChartToggle, { type ChartMode } from '../components/analysis/AnalysisChartToggle';
import ValuationModeler from '../components/ValuationModeler';
import { LayoutDashboard, BarChart3, Calculator } from 'lucide-react';
import PerformanceMetrics from '../components/PerformanceMetrics';

type Tab = 'overview' | 'analysis' | 'valuation';

export default function Dashboard() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [activeTab, setActiveTab] = useState<Tab>('overview');
    const [chartMode, setChartMode] = useState<ChartMode>('revenue');
    const [stockData, setStockData] = useState<StockData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { addTicker } = useRecentTickers();

    const handleSearch = async (ticker: string) => {
        setLoading(true);
        setError(null);
        setStockData(null);
        setSearchParams({ ticker }); // Update URL

        try {
            const data = await fetchStockData(ticker);
            setStockData(data);
            addTicker(ticker);
        } catch (err: any) {
            console.error("Search failed:", err);
            setError(err.message || "Failed to fetch stock data");
        } finally {
            setLoading(false);
        }
    };

    // Auto-load from URL
    useEffect(() => {
        const tickerParam = searchParams.get('ticker');
        if (tickerParam && (!stockData || stockData.symbol !== tickerParam)) {
            handleSearch(tickerParam);
        }
    }, [searchParams]);

    // If no stock selected, show welcome message with search
    if (!stockData && !loading && !error) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center max-w-md">
                    <div className="text-6xl mb-4">📊</div>
                    <h2 className="text-2xl font-bold text-white mb-2">Stock Analysis</h2>
                    <p className="text-slate-400 mb-6">
                        Enter a stock symbol below or click on a stock in the Heatmap.
                    </p>
                    <div className="mb-4">
                        <input
                            type="text"
                            placeholder="Enter ticker (e.g. NVDA)"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    const val = e.currentTarget.value.trim().toUpperCase();
                                    if (val) handleSearch(val);
                                }
                            }}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white text-center focus:border-primary focus:outline-none placeholder:text-slate-500"
                            autoFocus
                        />
                    </div>
                    <div className="text-xs text-slate-500">
                        Examples: NVDA, AAPL, MSFT, GOOG, AMD
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full overflow-hidden">
            {loading && (
                <div className="flex-1 flex items-center justify-center">
                    <div className="flex flex-col items-center gap-4">
                        <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary border-t-transparent"></div>
                        <span className="text-slate-400">Loading stock data...</span>
                    </div>
                </div>
            )}

            {error && (
                <div className="flex-1 flex items-center justify-center">
                    <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-6 rounded-xl text-center max-w-md">
                        <div className="text-2xl mb-2">⚠️</div>
                        <div className="font-semibold mb-2">Failed to load stock data</div>
                        <div className="text-sm">{error}</div>
                    </div>
                </div>
            )}

            {stockData && (
                <div className="flex flex-col h-full overflow-hidden">
                    {/* Header Bar */}
                    <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800 flex-shrink-0">
                        <div className="flex items-center gap-6">
                            {/* Ticker Info */}
                            <div className="flex items-center gap-4">
                                <div>
                                    <h2 className="text-2xl font-bold text-white">{stockData.symbol}</h2>
                                </div>
                            </div>

                            {/* Price */}
                            <div className="h-8 w-px bg-slate-800" />
                            <div>
                                <span className="text-2xl font-bold text-primary">${stockData.price?.toFixed(2)}</span>
                                <span className="text-sm text-slate-500 ml-2">Current Price</span>
                            </div>

                            {/* Performance Strip */}
                            {stockData.performance && (
                                <>
                                    <div className="h-8 w-px bg-slate-800" />
                                    <div>
                                        <PerformanceMetrics performance={stockData.performance} />
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Navigation Tabs - No more Heatmap tab */}
                        <div className="flex bg-slate-900/50 p-1 rounded-lg border border-slate-800">
                            <button
                                onClick={() => setActiveTab('overview')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'overview' ? 'bg-primary/10 text-primary shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
                            >
                                <LayoutDashboard size={16} />
                                Overview
                            </button>
                            <button
                                onClick={() => setActiveTab('analysis')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'analysis' ? 'bg-primary/10 text-primary shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
                            >
                                <BarChart3 size={16} />
                                Analysis
                            </button>
                            <button
                                onClick={() => setActiveTab('valuation')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'valuation' ? 'bg-primary/10 text-primary shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
                            >
                                <Calculator size={16} />
                                Valuation
                            </button>
                        </div>
                    </div>

                    {/* Tab Content */}
                    <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">

                        {activeTab === 'overview' && (
                            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
                                <MetricsGrid stockData={stockData} />
                            </div>
                        )}

                        {activeTab === 'analysis' && (
                            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300 h-full flex flex-col space-y-4">
                                <div className="flex justify-between items-center">
                                    <h3 className="text-lg font-bold text-text">Historical Performance</h3>
                                    <AnalysisChartToggle activeMode={chartMode} onModeChange={setChartMode} />
                                </div>
                                <div className="flex-1 min-h-[500px] bg-slate-900/30 rounded-xl border border-slate-800 p-4">
                                    <FinancialChart stockData={stockData} mode={chartMode} />
                                </div>
                            </div>
                        )}

                        {activeTab === 'valuation' && (
                            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300 w-full">
                                <ValuationModeler stockData={stockData} />
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
