/**
 * Purpose: expose the single server recommendation snapshot to every consumer.
 * Layer: Frontend / Context. Key Functions: useRecommendations.
 * Key input dependencies: RecommendationsProvider; RecommendationRecord API contract.
 */
import { createContext, useContext } from 'react';
import type { RecommendationRecord } from '../services/api';

export const RecommendationsContext = createContext<Record<string, RecommendationRecord>>({});

export function useRecommendations(): Record<string, RecommendationRecord> {
    return useContext(RecommendationsContext);
}
