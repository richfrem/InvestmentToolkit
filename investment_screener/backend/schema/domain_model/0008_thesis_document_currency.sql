-- 0008_thesis_document_currency: the current developments note for each thesis document.
--
-- A thesis document (data/theses/sub_strategies/<document_id>.md) is prose that goes stale: the
-- news, results and analyst moves of the stocks it covers keep arriving. The daily, weekly and
-- review skills write a short "current developments" note per document here, replacing the
-- previous one. There is deliberately one row per document and no history: the note is meant to
-- be right today, and the events behind it stay in the intelligence ledger.

CREATE TABLE thesis_document_currency (
    document_id TEXT PRIMARY KEY,
    as_of       TEXT NOT NULL,
    markdown    TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    updated_by  TEXT
);
