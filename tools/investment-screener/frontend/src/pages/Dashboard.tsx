import { useState } from 'react';
import { fetchStockData, type StockData } from '../services/api';
import StockSearch from '../components/StockSearch';
import { useRecentTickers } from '../hooks/useRecentTickers';
import MetricsGrid from '../components/MetricsGrid';
import RuleOf40Chart from '../components/Charts/RuleOf40Chart';
import FundamentalChart from '../components/Charts/FundamentalChart';

export default function Dashboard() {
    // const [currentTicker, setCurrentTicker] = useState<string>(''); // Removed unused state
    const [stockData, setStockData] = useState<StockData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { addTicker } = useRecentTickers();

    const handleSearch = async (ticker: string) => {
        setLoading(true);
        setError(null);
        // setCurrentTicker(ticker);
        setStockData(null);

        try {
            console.log(`Searching for ${ticker}...`);
            const data = await fetchStockData(ticker);
            console.log("Data received:", data);
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
        <div className="space-y-8 max-w-6xl mx-auto">
            <header className="text-center space-y-4 mb-12">
                <h2 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent inline-block">
                    Market Intelligence
                </h2>
                <p className="text-secondary text-lg">
                    Real-time valuation modeling and expert metrics.
                </p>
            </header>

            <StockSearch onSearch={handleSearch} isLoading={loading} />

            {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-center">
                    {error}
                </div>
            )}

            {stockData && (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
                    {/* Header Info */}
                    <div className="bg-surface rounded-xl p-8 border border-slate-800">
                        <div className="flex justify-between items-start">
                            <div>
                                <h3 className="text-4xl font-bold text-text mb-2">{stockData.symbol}</h3>
                                <p className="text-secondary text-lg">{stockData.profile.sector} • {stockData.currency}</p>
                            </div>
                            <div className="text-right">
                                <div className="text-3xl font-bold text-primary">${stockData.price.toFixed(2)}</div>
                                <div className="text-secondary">Current Price</div>
                            </div>
                        </div>
                    </div>

                    {/* Expert Metrics Grid */}
                    <MetricsGrid stockData={stockData} />

                    {/* Charts Row */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <RuleOf40Chart stockData={stockData} />
                        <FundamentalChart stockData={stockData} />
                    </div>
                </div>
            )}

            {!stockData && !loading && !error && (
                <div className="text-center mt-12 opacity-50">
                    <div className="text-6xl mb-4 grayscale">📈</div>
                    <p className="text-slate-600">Enter a ticker above to begin analysis.</p>
                </div>
            )}
        </div>
    );
}
