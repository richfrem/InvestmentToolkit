-- 0003_computed_snapshot: store computed outputs that were written to files.
--
-- The risk engine, rebalancer, risk officer and market regime classifier each wrote their
-- result to a JSON file that a later step read back (the order-risk gate, the prediction
-- harvester, the risk officer). One row per computed result; the latest row per name is the
-- current one, older rows are history (the repository keeps the last 30 per name).

CREATE TABLE computed_snapshot (
    snapshot_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_name TEXT NOT NULL CHECK (snapshot_name IN (
        'risk_snapshot', 'rebalance_plan', 'market_regime',
        'risk_officer_review', 'risk_officer_override'
    )),
    computed_at   TEXT NOT NULL,
    payload_json  TEXT NOT NULL
);

CREATE INDEX idx_computed_snapshot_name_time ON computed_snapshot (snapshot_name, computed_at DESC, snapshot_id DESC);
