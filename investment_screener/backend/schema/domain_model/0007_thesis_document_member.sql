-- 0007_thesis_document_member: which stocks each thesis document covers.
--
-- A thesis document (data/theses/sub_strategies/<document_id>.md) is prose. The stocks it covers
-- used to appear only as a frozen markdown table inside it, with stale shares and weights.
-- This table records the membership so the web app can show the live positions table for one
-- thesis. Membership is many-to-many with investment.sub_strategy_id: the ASI Race document
-- spans several sub-strategies, and one sub-strategy can appear in more than one document.

CREATE TABLE thesis_document_member (
    document_id TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    added_at    TEXT NOT NULL,
    PRIMARY KEY (document_id, symbol)
);

CREATE INDEX idx_thesis_document_member_symbol ON thesis_document_member (symbol);
