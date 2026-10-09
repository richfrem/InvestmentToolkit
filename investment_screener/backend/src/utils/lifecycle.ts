/**
 * lifecycle.ts - The one lifecycle (role) vocabulary for `investment.lifecycle_status`.
 *
 * Purpose:
 *   TypeScript counterpart of `LIFECYCLE_STATUSES` / `INACTIVE_STATUSES` in
 *   `py_services/portfolio_io.py`. A test (`tests/utils/lifecycle.spec.ts`) fails if the two
 *   lists differ.
 *
 * Key Functions (Index):
 *   - LIFECYCLE_STATUSES: statuses writers produce
 *   - INACTIVE_STATUSES: statuses meaning "no longer an active position"
 *   - ACCEPTED_LIFECYCLE_STATUSES: every value a reader or API accepts
 *   - DEFAULT_LIFECYCLE_STATUS: value for a holding with no stored status
 */
export const LIFECYCLE_STATUSES = ['accumulate', 'trim', 'exit', 'initiate', 'watchlist'] as const;
export const INACTIVE_STATUSES = ['exit', 'exited', 'avoid'] as const;
export const ACCEPTED_LIFECYCLE_STATUSES = [
    'accumulate', 'trim', 'exit', 'initiate', 'watchlist', 'exited', 'avoid',
] as const;
export const DEFAULT_LIFECYCLE_STATUS = 'watchlist';

export type LifecycleStatus = (typeof ACCEPTED_LIFECYCLE_STATUSES)[number];
