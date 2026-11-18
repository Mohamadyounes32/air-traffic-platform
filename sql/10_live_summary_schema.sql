CREATE TABLE IF NOT EXISTS analytics.live_national (
    poll_id          BIGINT      PRIMARY KEY,
    api_time         TIMESTAMPTZ NOT NULL,
    states_total     INTEGER,
    states_kept      INTEGER,
    fresh_airborne   INTEGER     NOT NULL,
    fresh_on_ground  INTEGER     NOT NULL,
    fresh_share_pct  NUMERIC(5,2)
);
CREATE INDEX IF NOT EXISTS ix_live_national_time ON analytics.live_national (api_time);

CREATE TABLE IF NOT EXISTS analytics.live_grid_hourly (
    hour_utc       TIMESTAMPTZ  NOT NULL,
    cell_lat       SMALLINT     NOT NULL,   -- south edge of a 2-degree cell
    cell_lon       SMALLINT     NOT NULL,   -- west edge of a 2-degree cell
    avg_airborne   NUMERIC(8,2) NOT NULL,
    max_airborne   INTEGER      NOT NULL,
    polls_in_hour  INTEGER      NOT NULL,
    PRIMARY KEY (hour_utc, cell_lat, cell_lon)
);