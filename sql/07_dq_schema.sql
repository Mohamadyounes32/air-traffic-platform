CREATE TABLE IF NOT EXISTS dq.check_results (
    result_id         BIGSERIAL PRIMARY KEY,
    run_id            TEXT        NOT NULL,
    checked_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    check_name        TEXT        NOT NULL,
    layer             TEXT        NOT NULL,
    severity          TEXT        NOT NULL,
    status            TEXT        NOT NULL,
    observed_value    DOUBLE PRECISION,
    min_allowed       DOUBLE PRECISION,
    max_allowed       DOUBLE PRECISION,
    duration_seconds  DOUBLE PRECISION,
    error_message     TEXT
);

CREATE INDEX IF NOT EXISTS ix_dq_results_run ON dq.check_results (run_id);