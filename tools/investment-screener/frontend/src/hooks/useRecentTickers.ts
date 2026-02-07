import { useState, useEffect } from 'react';

export function useRecentTickers() {
    const [recentTickers, setRecentTickers] = useState<string[]>([]);

    useEffect(() => {
        const saved = localStorage.getItem('recent_tickers');
        if (saved) {
            setRecentTickers(JSON.parse(saved));
        }
    }, []);

    const addTicker = (ticker: string) => {
        const updated = [ticker, ...recentTickers.filter(t => t !== ticker)].slice(0, 10);
        setRecentTickers(updated);
        localStorage.setItem('recent_tickers', JSON.stringify(updated));
    };

    return { recentTickers, addTicker };
}
