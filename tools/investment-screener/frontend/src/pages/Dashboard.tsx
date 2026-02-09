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

    return (
        <div className="h-[calc(100vh-2rem)] flex flex-col space-y-4 max-w-7xl mx-auto overflow-hidden">
            {/* Header Section - Always Visible */}
            <div className="flex-none pt-4 space-y-4">
                {/* Search moved to Sidebar */}
                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-center text-sm">
                        {error}
                    </div>
                )}
            </div>

            {/* Main Content Area */}
            {stockData ? (
                <div className="flex-1 flex flex-col min-h-0 bg-surface/50 rounded-xl border border-slate-800/50 backdrop-blur-sm overflow-hidden">

                    {/* Ticker Header & Tabs */}
                    <div className="flex-none p-4 border-b border-slate-800 flex justify-between items-center bg-surface">
                        <div className="flex items-center gap-6">
                            <div className="flex items-center gap-4">
                                <div>
                                    <h3 className="text-2xl font-bold text-text">{stockData.symbol}</h3>
                                    <span className="text-secondary text-sm">{stockData.profile.sector}</span>
                                </div>
                                <div className="h-8 w-px bg-slate-800" />
                                <div>
                                    <div className="text-xl font-bold text-primary">${stockData.price.toFixed(2)}</div>
                                    <div className="text-xs text-secondary">Current Price</div>
                                </div>
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

                        {/* Navigation Tabs */}
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

                    {/* Tab Content - Scrollable if needed, but contained */}
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
            ) : (
                !loading && (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-600 opacity-50">
                        <div className="text-6xl mb-4 grayscale">📈</div>
                        <p>Enter a ticker above to begin analysis.</p>
                    </div>
                )
            )}
        </div>
    );
}
