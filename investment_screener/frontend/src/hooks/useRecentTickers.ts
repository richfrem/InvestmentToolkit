/**
 * useRecentTickers.ts (React Hook)
 * =====================================
 *
 * Purpose:
 *     Custom hook for managing and persisting a list of recently searched stock tickers in localStorage.
 *
 * Layer: Frontend / Hooks
 *
 * Usage Examples:
 *     const { recentTickers, addTicker } = useRecentTickers();
 *
 * Key Functions:
 *     - addTicker() - Adds a new ticker to the front of the list, ensuring uniqueness and limiting to the last 10 entries
 *     - useRecentTickers() - Maintains the stateful list of tickers and handles initial hydration from localStorage
 */
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
