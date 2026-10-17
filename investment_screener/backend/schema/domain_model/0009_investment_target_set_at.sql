-- 0009_investment_target_set_at: when each investment's target weight was last set.
--
-- Target weights went stale because nothing changed them when the owner traded: a sold position
-- kept its target and a position the owner kept buying stayed at an old target. The daily loop
-- now re-baselines a target to the post-trade weight when a fill is newer than this timestamp
-- (target_rebaseline.py), and flags targets that are old or older than the latest valuation.
-- update_investment_fields() stamps it whenever target_weight changes value. NULL means the
-- target predates this column.

ALTER TABLE investment ADD COLUMN target_set_at TEXT;
