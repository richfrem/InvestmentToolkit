-- 0004_event_logs: store the evolution event log and the thesis breaker override log.
--
-- Evolution events (earnings catalysts, breaker overrides, rebalance executions, large price
-- moves, dividends, forced exits) were one JSON record per line in evolution_events.jsonl.
-- One row per record. The same (ticker, event_type, event_date) may appear more than once
-- when its event_details changed, so there is no uniqueness constraint on the key; rows are
-- ordered by event_seq. record_json holds the whole event (context, event_details, outcome).

CREATE TABLE evolution_event (
    event_seq   INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    event_date  TEXT NOT NULL,
    record_json TEXT NOT NULL
);

CREATE INDEX idx_evolution_event_key ON evolution_event (ticker, event_type, event_date);

-- Thesis breaker overrides: one row each time the owner decided to hold through a TRIGGERED
-- breaker (the accountability trail). Append-only; override_json holds the whole record.

CREATE TABLE thesis_breaker_override (
    override_seq  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT NOT NULL,
    breaker_id    TEXT NOT NULL,
    override_date TEXT NOT NULL,
    override_json TEXT NOT NULL
);

CREATE INDEX idx_thesis_breaker_override_ticker ON thesis_breaker_override (ticker, breaker_id);
