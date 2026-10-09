-- 0002_thesis_breakers: add thesis_breaker (definitions) and thesis_breaker_state (evaluated state).
--
-- Thesis breakers were a `thesisBreakers` list on each holding plus a machine-written
-- thesis_breaker_state.json; neither had a SQLite home (investment.thesis_breaker_status was
-- empty for every row). One row per breaker definition, one row per evaluated state.
-- Auto breakers carry metric/operator/threshold/horizon; manual breakers carry a hand-set
-- status, the date it was set and a review cadence. investment.thesis_breaker_status stays a
-- derived scalar (worst current status), written only by replace_breaker_state().

CREATE TABLE thesis_breaker (
    breaker_id          TEXT NOT NULL,
    investment_id       TEXT NOT NULL REFERENCES investment(investment_id),
    breaker_type        TEXT NOT NULL CHECK (breaker_type IN ('auto', 'manual')),
    metric              TEXT,
    operator            TEXT NOT NULL CHECK (operator IN ('<', '<=', '>', '>=', '==', 'in')),
    threshold_json      TEXT,
    horizon_json        TEXT,
    note                TEXT,
    status              TEXT CHECK (status IN ('OK', 'WATCHING', 'TRIGGERED')),
    status_set_at       TEXT,
    review_cadence_days INTEGER,
    created_at          TEXT NOT NULL,
    PRIMARY KEY (investment_id, breaker_id)
);

CREATE TABLE thesis_breaker_state (
    investment_id       TEXT NOT NULL,
    breaker_id          TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('OK', 'WATCHING', 'TRIGGERED')),
    current_value_json  TEXT,
    condition_met       INTEGER,
    current_streak      INTEGER,
    streak_start_date   TEXT,
    last_evaluated_at   TEXT NOT NULL,
    days_since_review   INTEGER,
    is_stale            INTEGER,
    PRIMARY KEY (investment_id, breaker_id),
    FOREIGN KEY (investment_id, breaker_id) REFERENCES thesis_breaker(investment_id, breaker_id)
);
