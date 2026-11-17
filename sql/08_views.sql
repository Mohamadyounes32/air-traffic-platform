CREATE OR REPLACE VIEW analytics.v_flights AS
SELECT
    f.flight_id,
    d.full_date, d.year, d.quarter, d.month, d.month_name,
    d.day_of_week, d.day_name, d.is_weekend, d.season,
    d.is_federal_holiday, d.holiday_name,
    al.carrier_code, al.carrier_name,
    o.airport_code AS origin, o.city AS origin_city, o.state AS origin_state,
    o.latitude AS origin_lat, o.longitude AS origin_lon,
    de.airport_code AS dest, de.city AS dest_city, de.state AS dest_state,
    f.sched_dep_hour, h.day_part,
    ac.tail_number, f.flight_number,
    f.crs_dep_time, f.dep_time, f.crs_arr_time, f.arr_time,
    f.dep_delay, f.dep_delay_minutes, f.dep_del15,
    f.arr_delay, f.arr_delay_minutes, f.arr_del15,
    f.taxi_out, f.taxi_in,
    f.is_cancelled, f.cancellation_code, f.is_diverted,
    f.distance, f.air_time,
    f.carrier_delay, f.weather_delay, f.nas_delay,
    f.security_delay, f.late_aircraft_delay
FROM analytics.fact_flights f
JOIN analytics.dim_date     d  ON d.date_key     = f.date_key
JOIN analytics.dim_airline  al ON al.airline_key = f.airline_key
JOIN analytics.dim_airport  o  ON o.airport_key  = f.origin_airport_key
JOIN analytics.dim_airport  de ON de.airport_key = f.dest_airport_key
JOIN analytics.dim_aircraft ac ON ac.aircraft_key = f.aircraft_key
LEFT JOIN analytics.dim_hour h ON h.hour_key = f.sched_dep_hour;