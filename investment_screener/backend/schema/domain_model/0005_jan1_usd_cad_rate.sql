-- 0005_jan1_usd_cad_rate: keep the January 1 USD/CAD rate with the YTD baseline.
--
-- The year-to-date summary needs two personal numbers: the portfolio's starting balance
-- (already in cash_flow_baseline) and the USD/CAD rate on January 1. The rate used to be read
-- from a gitignored portfolio-config.json file. It lives on the baseline row now; NULL means
-- not recorded yet.

ALTER TABLE cash_flow_baseline ADD COLUMN jan1_usd_cad_rate REAL;
