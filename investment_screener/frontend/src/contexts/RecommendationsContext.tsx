/**
 * Purpose: share one server recommendation snapshot across every current-action display.
 * Layer: Frontend / Context. Usage: RecommendationsProvider + useRecommendations().
 * Key Functions: RecommendationsProvider, refresh.
 * Key input dependencies: GET /api/screener/recommendations; recommendation-data-changed event.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { fetchRecommendations } from '../services/api';
import type { RecommendationRecord } from '../services/api';
import { RecommendationsContext } from './useRecommendations';



export function RecommendationsProvider({ children }: { children: ReactNode }) {
    const [records, setRecords] = useState<Record<string, RecommendationRecord>>({});
    const version = useRef(0);
    const refresh = useCallback(async () => {
        const request = ++version.current;
        try {
            const data = await fetchRecommendations();
            if (request === version.current) setRecords(data);
        } catch {
            if (request === version.current) setRecords({});
        }
    }, []);
    useEffect(() => {
        const reload = () => { void refresh(); };
        const initial = window.setTimeout(reload, 0);
        const timer = window.setInterval(reload, 60_000);
        window.addEventListener('focus', reload);
        window.addEventListener('recommendation-data-changed', reload);
        return () => {
            window.clearInterval(timer);
            window.clearTimeout(initial);
            window.removeEventListener('focus', reload);
            window.removeEventListener('recommendation-data-changed', reload);
        };
    }, [refresh]);
    return <RecommendationsContext.Provider value={records}>{children}</RecommendationsContext.Provider>;
}
