import { useState } from 'react';
import { fetchStockData, type StockData } from '../services/api';
import StockSearch from '../components/StockSearch';
import { useRecentTickers } from '../hooks/useRecentTickers';

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
        <div className="space-y-8 max-w-4xl mx-auto">
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
                <div className="bg-surface rounded-xl p-8 border border-slate-800 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h3 className="text-3xl font-bold text-text">{stockData.symbol}</h3>
                            <p className="text-secondary">{stockData.currency} • Market Cap: ${(stockData.metrics.market_cap / 1e9).toFixed(2)}B</p>
                        </div>
                        <div className="text-right">
                            <div className="text-2xl font-bold text-primary">${stockData.price.toFixed(2)}</div>
                            <div className="text-sm text-secondary">Current Price</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-slate-950/50 p-6 rounded-lg border border-slate-800">
                            <h4 className="text-sm font-medium text-secondary mb-4 uppercase tracking-wider">Expert Metrics</h4>
                            <div className="space-y-4">
                                <div className="flex justify-between">
                                    <span>Rule of 40</span>
                                    <span className={`font-mono font-bold ${stockData.expert_metrics.rule_of_40.score >= 40 ? 'text-green-400' : 'text-red-400'}`}>
                                        {stockData.expert_metrics.rule_of_40.score.toFixed(2)}%
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Piotroski F-Score</span>
                                    <span className="font-mono font-bold text-primary">
                                        {stockData.expert_metrics.piotroski_f_score.score} / 9
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="bg-slate-950/50 p-6 rounded-lg border border-slate-800">
                            <h4 className="text-sm font-medium text-secondary mb-4 uppercase tracking-wider">Raw Data (Debug)</h4>
                            <pre className="text-xs text-slate-500 overflow-x-auto">
                                {JSON.stringify(stockData.metrics, null, 2)}
                            </pre>
                        </div>
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
