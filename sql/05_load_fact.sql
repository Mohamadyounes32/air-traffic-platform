INSERT INTO analytics.fact_flights (
    flight_id, date_key, airline_key, origin_airport_key, dest_airport_key,
    aircraft_key, sched_dep_hour, flight_number,
    crs_dep_time, dep_time, crs_arr_time, arr_time,
    dep_delay, dep_delay_minutes, dep_del15,
    arr_delay, arr_delay_minutes, arr_del15,
    taxi_out, taxi_in, is_cancelled, cancellation_code, is_diverted,
    crs_elapsed_time, actual_elapsed_time, air_time, distance,
    carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay,
    source_file
)
SELECT
    f.flight_id,
    to_char(f.flight_date, 'YYYYMMDD')::int,
    f.dot_id_airline,
    f.origin_airport_id,
    f.dest_airport_id,
    COALESCE(a.aircraft_key, 0),
    EXTRACT(HOUR FROM f.crs_dep_time)::smallint,
    f.flight_number,
    f.crs_dep_time, f.dep_time, f.crs_arr_time, f.arr_time,
    f.dep_delay, f.dep_delay_minutes, f.dep_del15,
    f.arr_delay, f.arr_delay_minutes, f.arr_del15,
    f.taxi_out, f.taxi_in, f.cancelled, f.cancellation_code, f.diverted,
    f.crs_elapsed_time, f.actual_elapsed_time, f.air_time, f.distance,
    f.carrier_delay, f.weather_delay, f.nas_delay, f.security_delay, f.late_aircraft_delay,
    f.source_file
FROM clean.flights f
LEFT JOIN analytics.dim_aircraft a ON a.tail_number = f.tail_number
WHERE f.source_file = %(source_file)s;