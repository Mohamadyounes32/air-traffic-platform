CREATE TABLE IF NOT EXISTS clean.flights (
    flight_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flight_date         DATE        NOT NULL,
    reporting_airline   TEXT,
    dot_id_airline      INTEGER,
    flight_number       INTEGER,
    tail_number         TEXT,
    origin_airport_id   INTEGER,
    origin              TEXT,
    origin_city         TEXT,
    origin_state        TEXT,
    dest_airport_id     INTEGER,
    dest                TEXT,
    dest_city           TEXT,
    dest_state          TEXT,
    crs_dep_time        TIME,       -- scheduled, local time
    dep_time            TIME,       -- actual, local time
    dep_delay           INTEGER,    -- minutes, negative = early
    dep_delay_minutes   INTEGER,    -- early counted as 0
    dep_del15           BOOLEAN,
    taxi_out            INTEGER,
    taxi_in             INTEGER,
    crs_arr_time        TIME,
    arr_time            TIME,
    arr_delay           INTEGER,
    arr_delay_minutes   INTEGER,
    arr_del15           BOOLEAN,
    cancelled           BOOLEAN     NOT NULL,
    cancellation_code   TEXT,
    diverted            BOOLEAN     NOT NULL,
    crs_elapsed_time    INTEGER,
    actual_elapsed_time INTEGER,
    air_time            INTEGER,
    distance            INTEGER,
    carrier_delay       INTEGER,
    weather_delay       INTEGER,
    nas_delay           INTEGER,
    security_delay      INTEGER,
    late_aircraft_delay INTEGER,
    source_file         TEXT        NOT NULL,
    cleaned_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_flights_source_file ON clean.flights (source_file);
CREATE INDEX IF NOT EXISTS ix_flights_date        ON clean.flights (flight_date);
CREATE INDEX IF NOT EXISTS ix_flights_tail_date   ON clean.flights (tail_number, flight_date);

CREATE TABLE IF NOT EXISTS clean.build_log (
    source_file        TEXT PRIMARY KEY,
    file_sha256        TEXT        NOT NULL,
    rows_raw           BIGINT      NOT NULL,
    rows_clean         BIGINT      NOT NULL,
    duplicates_removed BIGINT      NOT NULL,
    built_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- '1.00' or '-4.00' or '12' or '' -> integer or NULL
CREATE OR REPLACE FUNCTION clean.to_int(t TEXT) RETURNS INTEGER
LANGUAGE sql IMMUTABLE AS $fn$
    SELECT NULLIF(btrim(t), '')::numeric::integer
$fn$;

-- '1.00' / '0.00' -> TRUE / FALSE, '' -> NULL
CREATE OR REPLACE FUNCTION clean.to_bool(t TEXT) RETURNS BOOLEAN
LANGUAGE sql IMMUTABLE AS $fn$
    SELECT NULLIF(btrim(t), '')::numeric = 1
$fn$;

-- '905' / '0905' / '905.00' -> 09:05; '2400' -> 00:00; invalid -> NULL
CREATE OR REPLACE FUNCTION clean.hhmm_to_time(t TEXT) RETURNS TIME
LANGUAGE sql IMMUTABLE AS $fn$
    SELECT CASE
        WHEN s IS NULL                  THEN NULL
        WHEN s !~ '^[0-9]{4}$'          THEN NULL
        WHEN s = '2400'                 THEN TIME '00:00'
        WHEN left(s, 2)::int > 23
          OR right(s, 2)::int > 59      THEN NULL
        ELSE make_time(left(s, 2)::int, right(s, 2)::int, 0)
    END
    FROM (SELECT lpad(split_part(NULLIF(btrim(t), ''), '.', 1), 4, '0') AS s) x
$fn$;