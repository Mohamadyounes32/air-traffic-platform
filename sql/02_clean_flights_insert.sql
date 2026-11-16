INSERT INTO clean.flights (
    flight_date, reporting_airline, dot_id_airline, flight_number, tail_number,
    origin_airport_id, origin, origin_city, origin_state,
    dest_airport_id, dest, dest_city, dest_state,
    crs_dep_time, dep_time, dep_delay, dep_delay_minutes, dep_del15, taxi_out,
    taxi_in, crs_arr_time, arr_time, arr_delay, arr_delay_minutes, arr_del15,
    cancelled, cancellation_code, diverted,
    crs_elapsed_time, actual_elapsed_time, air_time, distance,
    carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay,
    source_file
)
SELECT
    flightdate::date,
    NULLIF(btrim(reporting_airline), ''),
    clean.to_int(dot_id_reporting_airline),
    clean.to_int(flight_number_reporting_airline),
    NULLIF(btrim(tail_number), ''),
    clean.to_int(originairportid), NULLIF(btrim(origin), ''),
    NULLIF(btrim(origincityname), ''), NULLIF(btrim(originstate), ''),
    clean.to_int(destairportid), NULLIF(btrim(dest), ''),
    NULLIF(btrim(destcityname), ''), NULLIF(btrim(deststate), ''),
    clean.hhmm_to_time(crsdeptime), clean.hhmm_to_time(deptime),
    clean.to_int(depdelay), clean.to_int(depdelayminutes), clean.to_bool(depdel15),
    clean.to_int(taxiout),
    clean.to_int(taxiin),
    clean.hhmm_to_time(crsarrtime), clean.hhmm_to_time(arrtime),
    clean.to_int(arrdelay), clean.to_int(arrdelayminutes), clean.to_bool(arrdel15),
    COALESCE(clean.to_bool(cancelled), FALSE),
    NULLIF(btrim(cancellationcode), ''),
    COALESCE(clean.to_bool(diverted), FALSE),
    clean.to_int(crselapsedtime), clean.to_int(actualelapsedtime),
    clean.to_int(airtime), clean.to_int(distance),
    clean.to_int(carrierdelay), clean.to_int(weatherdelay), clean.to_int(nasdelay),
    clean.to_int(securitydelay), clean.to_int(lateaircraftdelay),
    source_file
FROM (
    SELECT r.*,
           ROW_NUMBER() OVER (
               PARTITION BY flightdate, dot_id_reporting_airline,
                            flight_number_reporting_airline, originairportid,
                            destairportid, crsdeptime
               ORDER BY ctid
           ) AS rn
    FROM raw.bts_ontime r
    WHERE source_file = %(source_file)s
) deduped
WHERE rn = 1;