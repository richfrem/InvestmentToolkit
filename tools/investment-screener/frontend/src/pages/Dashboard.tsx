import { useState } from 'react';
import { fetchStockData, type StockData } from '../services/api';
import StockSearch from '../components/StockSearch';
import { useRecentTickers } from '../hooks/useRecentTickers';
import MetricsGrid from '../components/MetricsGrid';
import RuleOf40Chart from '../components/Charts/RuleOf40Chart';
import FundamentalChart from '../components/Charts/FundamentalChart';
import ValuationModeler from '../components/ValuationModeler';
import { LayoutDashboard, BarChart3, Calculator } from 'lucide-react';

type Tab = 'overview' | 'analysis' | 'valuation';

export default function Dashboard() {
    const [activeTab, setActiveTab] = useState<Tab>('overview');
    const [stockData, setStockData] = useState<StockData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { addTicker } = useRecentTickers();

    const handleSearch = async (ticker: string) => {
        setLoading(true);
        setError(null);
        setStockData(null);

        try {
            const data = await fetchStockData(ticker);
            setStockData(data);
            addTicker(ticker); // T011 integration
        } catch (err: any) {
            console.error("Search failed:", err);
            setError(err.message || "Failed to fetch stock data");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-[calc(100vh-2rem)] flex flex-col space-y-4 max-w-7xl mx-auto overflow-hidden">
            {/* Header Section - Always Visible */}
            <div className="flex-none space-y-4">
                <header className="flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent inline-block">
                            Market Intelligence
                        </h2>
                        {!stockData && <p className="text-secondary text-sm">Real-time valuation modeling and expert metrics.</p>}
                    </div>
                </header>

                <StockSearch onSearch={handleSearch} isLoading={loading} />

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
                            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300 grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
                                <div className="h-full min-h-[400px]">
                                    <RuleOf40Chart stockData={stockData} />
                                </div>
                                <div className="h-full min-h-[400px]">
                                    <FundamentalChart stockData={stockData} />
                                </div>
                            </div>
                        )}

                        {activeTab === 'valuation' && (
                            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300 max-w-4xl mx-auto">
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
