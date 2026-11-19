CREATE OR REPLACE VIEW reporting.dim_date AS
SELECT date_key, full_date, year, quarter, month, month_name, day_of_month,
       iso_week, day_of_week, day_name, is_weekend, season,
       is_federal_holiday, holiday_name
FROM analytics.dim_date
WHERE date_key BETWEEN (SELECT MIN(date_key) FROM analytics.fact_flights)
                   AND (SELECT MAX(date_key) FROM analytics.fact_flights);

CREATE OR REPLACE VIEW reporting.dim_airport AS
SELECT airport_key, airport_code, airport_name, city, state, latitude, longitude,
       airport_code || ' - ' || COALESCE(city, '') AS airport_label
FROM analytics.dim_airport;

CREATE OR REPLACE VIEW reporting.dim_airline AS
SELECT airline_key, carrier_code, carrier_name
FROM analytics.dim_airline;

CREATE OR REPLACE VIEW reporting.live_national AS
SELECT api_time, fresh_airborne, fresh_on_ground, fresh_share_pct, states_total, states_kept
FROM analytics.live_national
WHERE api_time >= now() - INTERVAL '14 days';

CREATE OR REPLACE VIEW reporting.live_grid_hourly AS
SELECT hour_utc, cell_lat, cell_lon,
       cell_lat + 1 AS center_lat, cell_lon + 1 AS center_lon,   -- cells are 2 degrees wide
       avg_airborne, max_airborne, polls_in_hour
FROM analytics.live_grid_hourly
WHERE hour_utc >= now() - INTERVAL '14 days';

CREATE OR REPLACE VIEW reporting.dq_latest AS
SELECT check_name, layer, severity, status, observed_value,
       min_allowed, max_allowed, checked_at
FROM dq.check_results
WHERE run_id = (SELECT run_id FROM dq.check_results ORDER BY checked_at DESC LIMIT 1);

CREATE OR REPLACE VIEW reporting.pipeline_status AS
SELECT source_file, rows_loaded, loaded_at FROM raw.load_log;