CREATE TABLE IF NOT EXISTS raw.opensky_poll (
    poll_id            BIGSERIAL PRIMARY KEY,
    requested_at       TIMESTAMPTZ NOT NULL,       -- our clock, UTC
    api_time           TIMESTAMPTZ,                -- snapshot time reported by OpenSky
    bbox               TEXT        NOT NULL,
    http_status        INTEGER     NOT NULL,
    states_total       INTEGER,
    states_kept        INTEGER,
    credits_remaining  INTEGER,
    duration_seconds   DOUBLE PRECISION,
    error_message      TEXT,
    UNIQUE (bbox, api_time)
);

CREATE TABLE IF NOT EXISTS raw.opensky_states (
    poll_id          BIGINT   NOT NULL REFERENCES raw.opensky_poll (poll_id) ON DELETE CASCADE,
    icao24           TEXT     NOT NULL,
    callsign         TEXT,
    origin_country   TEXT,
    time_position    TIMESTAMPTZ,
    last_contact     TIMESTAMPTZ,
    longitude        REAL,
    latitude         REAL,
    baro_altitude    REAL,
    geo_altitude     REAL,
    on_ground        BOOLEAN,
    velocity         REAL,
    true_track       REAL,
    vertical_rate    REAL,
    squawk           TEXT,
    position_source  SMALLINT,
    category         SMALLINT
);

CREATE INDEX IF NOT EXISTS ix_opensky_states_poll ON raw.opensky_states (poll_id);