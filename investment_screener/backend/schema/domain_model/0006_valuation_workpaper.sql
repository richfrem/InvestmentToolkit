-- 0006_valuation_workpaper: keep the working files of a stock valuation in the database.
--
-- A valuation run passes data between steps as JSON files in temp/evaluations (raw fundamentals,
-- scenarios, DCF result, WACC build, reverse DCF, technicals, intake, the projection payload,
-- ...). Only the final result reached projection_version. One row per (symbol, stage, content):
-- the stage is the step name, as_of the day it was produced, payload_json the whole document.
-- Identical content for the same symbol and stage is stored once.

CREATE TABLE valuation_workpaper (
    workpaper_id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    stage        TEXT NOT NULL,
    as_of        TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source       TEXT,
    saved_at     TEXT NOT NULL,
    UNIQUE (symbol, stage, content_hash)
);

CREATE INDEX idx_valuation_workpaper_lookup ON valuation_workpaper (symbol, stage, as_of DESC, workpaper_id DESC);
