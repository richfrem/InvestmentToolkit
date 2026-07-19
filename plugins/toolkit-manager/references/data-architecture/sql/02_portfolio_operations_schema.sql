-- Portfolio Operations Schema
-- Bounded context: fully-typed transactional records (trades, cash flows, order
-- executions). Deliberately separate from intelligence_event — ADR-029 §3.
--
-- Status: DESIGNED, NOT YET APPLIED. Source design:
-- docs/architecture/persistence-domain-data-model.md.
-- Owning package (once built, per ADR-028 amendment): py_services/portfolio_ledger/.
-- Same anti-duplication rule as the intelligence ledger: no producer/consumer script
-- opens its own connection to these tables.

CREATE TABLE IF NOT EXISTS trade_log_entry (
    entry_id        TEXT PRIMARY KEY,               -- from source trade-log.json 'id' field
    instrument_id   TEXT NOT NULL REFERENCES instrument(instrument_id),
    action          TEXT NOT NULL,                   -- BUY/SELL/etc.
    shares          REAL NOT NULL,
    price           REAL,
    total_cost      REAL,
    account         TEXT NOT NULL,                   -- e.g. TFSA, RRSP
    order_type      TEXT,
    limit_price     REAL,
    trade_date      TEXT NOT NULL,
    notes           TEXT,
    status          TEXT,
    source          TEXT,
    priority        TEXT,
    logged_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trade_log_instrument ON trade_log_entry(instrument_id);
CREATE INDEX IF NOT EXISTS idx_trade_log_account ON trade_log_entry(account);
CREATE INDEX IF NOT EXISTS idx_trade_log_date ON trade_log_entry(trade_date);

CREATE TABLE IF NOT EXISTS order_execution (
    execution_id      TEXT PRIMARY KEY,              -- generated: hash(timestamp, ticker, side)
    executed_at        TEXT NOT NULL,
    instrument_id       TEXT NOT NULL REFERENCES instrument(instrument_id),
    side                 TEXT NOT NULL,               -- BUY/SELL
    shares               REAL NOT NULL,
    price                REAL,                        -- NULL for market orders (no cost estimate)
    decision             TEXT NOT NULL,               -- BLOCKED / EXECUTED / etc.
    gate_result_json     TEXT                         -- variable-shape audit detail, kept as JSON deliberately
);

CREATE INDEX IF NOT EXISTS idx_order_execution_instrument ON order_execution(instrument_id);
CREATE INDEX IF NOT EXISTS idx_order_execution_executed_at ON order_execution(executed_at);

CREATE TABLE IF NOT EXISTS cash_flow (
    flow_id                             TEXT PRIMARY KEY,   -- generated: hash(date, account, type)
    flow_date                            TEXT NOT NULL,
    flow_type                            TEXT NOT NULL,      -- deposit / withdrawal
    amount_cad                           REAL NOT NULL,
    portfolio_value_before_flow_cad       REAL,
    account                               TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cash_flow_account ON cash_flow(account);
CREATE INDEX IF NOT EXISTS idx_cash_flow_date ON cash_flow(flow_date);

CREATE TABLE IF NOT EXISTS cash_flow_baseline (
    account                TEXT PRIMARY KEY,
    starting_balance_cad   REAL NOT NULL,
    starting_date          TEXT NOT NULL
);
