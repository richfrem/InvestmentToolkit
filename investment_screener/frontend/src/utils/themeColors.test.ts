/**
 * themeColors.test.ts
 *
 * Purpose:
 *     Category colours for pillar / sub-strategy / sector groupings (Portfolio
 *     Summary donut, heatmap group headers). Before 2026-09-28 the maps lacked
 *     newer ids (defense, photonics, robotics, quality_saas and 10 sub-strategies),
 *     so every missing id fell back to the same grey and donut slices collided.
 *
 * Layer: Frontend / Utils (vitest)
 */
import { describe, it, expect } from 'vitest';
import { assignCategoryColors, PILLAR_COLORS, SUB_STRATEGY_COLORS } from './themeColors';

// Current ids in domain_model.sqlite strategy_pillar / sub_strategy (2026-09-28).
const PILLARS = ['compute', 'titans', 'sovfin', 'datainfra', 'power', 'security', 'quality_saas', 'cash',
    'quantum', 'biohealth', 'defense', 'photonics', 'robotics', 'other'];
const SUB_STRATEGIES = ['ai-infrastructure', 'cash', 'cybersecurity', 'defense-ai-space', 'frontier-bets',
    'memory-storage-packaging', 'metabolic-rewriting', 'ontological-os', 'photonics-optical',
    'power-infrastructure', 'preipo-access', 'quality-saas', 'quantum-computing', 'robotics-automation',
    'sa-asi-race', 'sovereign-finance', 'titans-cloud'];

const distinct = (colors: Record<string, string>) => new Set(Object.values(colors)).size === Object.keys(colors).length;

describe('category colours', () => {
    it('every current pillar and sub-strategy has a curated colour', () => {
        expect(PILLARS.filter(id => !PILLAR_COLORS[id])).toEqual([]);
        expect(SUB_STRATEGIES.filter(id => !SUB_STRATEGY_COLORS[id])).toEqual([]);
    });

    it('gives every slice in one chart a distinct colour', () => {
        expect(distinct(assignCategoryColors('pillar', PILLARS))).toBe(true);
        expect(distinct(assignCategoryColors('sub-strategy', SUB_STRATEGIES))).toBe(true);
    });

    it('uses the curated colour when there is one', () => {
        expect(assignCategoryColors('pillar', ['compute']).compute).toBe(PILLAR_COLORS.compute);
    });

    it('never falls back to one shared grey for unknown ids', () => {
        const colors = assignCategoryColors('sector', ['Technology', 'New Sector A', 'New Sector B', 'New Sector C']);
        expect(distinct(colors)).toBe(true);
    });
});
