INSERT INTO analytics.dim_airline (airline_key, carrier_code, carrier_name)
SELECT DISTINCT ON (dot_id_airline)
       dot_id_airline, reporting_airline, reporting_airline
FROM clean.flights
WHERE source_file = ANY(%(files)s) AND dot_id_airline IS NOT NULL
ORDER BY dot_id_airline, flight_date DESC
ON CONFLICT (airline_key) DO UPDATE SET carrier_code = EXCLUDED.carrier_code;

INSERT INTO analytics.dim_airport (airport_key, airport_code, city, state)
SELECT DISTINCT ON (airport_id) airport_id, code, city, state
FROM (
    SELECT origin_airport_id AS airport_id, origin AS code,
           origin_city AS city, origin_state AS state, flight_date
    FROM clean.flights WHERE source_file = ANY(%(files)s)
    UNION ALL
    SELECT dest_airport_id, dest, dest_city, dest_state, flight_date
    FROM clean.flights WHERE source_file = ANY(%(files)s)
) x
WHERE airport_id IS NOT NULL
ORDER BY airport_id, flight_date DESC
ON CONFLICT (airport_key) DO UPDATE
    SET airport_code = EXCLUDED.airport_code,
        city         = EXCLUDED.city,
        state        = EXCLUDED.state;

INSERT INTO analytics.dim_aircraft (tail_number)
SELECT DISTINCT analytics.normalize_tail(tail_number)
FROM clean.flights
WHERE source_file = ANY(%(files)s)
  AND analytics.normalize_tail(tail_number) IS NOT NULL
ON CONFLICT (tail_number) DO NOTHING;