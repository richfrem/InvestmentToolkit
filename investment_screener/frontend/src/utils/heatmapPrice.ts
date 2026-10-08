/**
 * Purpose: read the live price from a portfolio-heatmap stock row in one place.
 * Layer: Frontend / Utils. Usage: heatmapPrice(heatmapStock).
 * Key Functions: heatmapPrice — the endpoint's `price` field, never a renamed guess.
 * Key Input Dependencies: POST /api/portfolio-heatmap stock rows (`price`).
 */

/** The heatmap endpoint returns `price`; a missing or non-positive value is unknown, not zero. */
export function heatmapPrice(stock?: { price?: unknown } | null): number | null {
    const price = stock?.price;
    return typeof price === 'number' && Number.isFinite(price) && price > 0 ? price : null;
}
