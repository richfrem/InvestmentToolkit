/**
 * StockSearch.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Simple search input for looking up stocks by ticker symbol.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <StockSearch onSearch={(ticker) => console.log(ticker)} isLoading={false} />
 *
 * Key Functions:
 *     - handleSubmit() - Prevents default form submission and triggers the search callback with a sanitized uppercase ticker
 */
import { Search } from 'lucide-react';
import { useState } from 'react';

interface StockSearchProps {
    onSearch: (ticker: string) => void;
    isLoading: boolean;
}

export default function StockSearch({ onSearch, isLoading }: StockSearchProps) {
    const [ticker, setTicker] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (ticker.trim()) {
            onSearch(ticker.trim().toUpperCase());
        }
    };

    return (
        <form onSubmit={handleSubmit} className="relative w-full">
            <div className="relative flex items-center">
                <Search className="absolute left-4 text-slate-500" size={20} />
                <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    placeholder="Enter stock ticker (e.g. AAPL)..."
                    disabled={isLoading}
                    className="w-full bg-surface border border-slate-700 text-text pl-12 pr-4 py-4 rounded-xl focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all shadow-lg placeholder:text-slate-600"
                />
                <button
                    type="submit"
                    disabled={isLoading || !ticker.trim()}
                    className="absolute right-2 bg-primary/10 text-primary hover:bg-primary/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isLoading ? 'Loading...' : 'Analyze'}
                </button>
            </div>
        </form>
    );
}
