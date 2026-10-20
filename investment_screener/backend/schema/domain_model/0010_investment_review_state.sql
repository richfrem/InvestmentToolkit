-- 0010_investment_review_state: every followed investment must be reviewed each cycle.
--
-- A recommendation must reflect current analysis. review_state starts at NEEDS_ANALYSIS (also
-- the default for a newly onboarded ticker); each daily/weekly cycle resets holdings and the
-- watchlist to it, a deterministic triage clears names with nothing new, and the cycle's final
-- check fails while any name is still NEEDS_ANALYSIS (review_cycle.py). While NEEDS_ANALYSIS,
-- recommendation.py gives no buy/trim call for the name.

ALTER TABLE investment ADD COLUMN review_state TEXT NOT NULL DEFAULT 'NEEDS_ANALYSIS';
ALTER TABLE investment ADD COLUMN reviewed_at TEXT;
ALTER TABLE investment ADD COLUMN review_price REAL;
ALTER TABLE investment ADD COLUMN review_reason TEXT;
ALTER TABLE investment ADD COLUMN last_earnings_at TEXT;
