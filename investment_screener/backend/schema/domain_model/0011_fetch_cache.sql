-- 0011_fetch_cache: short-lived cache of raw market-data fetches (yfinance, EDGAR).
--
-- Replaces per-ticker JSON cache files (data/cache/, scripts/cache/, py_services/cache/) so the
-- repo holds no file-based data store; one row per (data_class, cache_key), overwritten on each
-- fetch. A cache only: nothing reads it as a source of record, and expiry is per data_class
-- (cache.CACHE_TTL_SECONDS).

CREATE TABLE fetch_cache (
    data_class   TEXT NOT NULL,
    cache_key    TEXT NOT NULL,
    fetched_at   REAL NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (data_class, cache_key)
);
