from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    name: str
    layer: str
    severity: str                  # "ERROR" stops the pipeline, "WARN" is only logged
    description: str
    sql: str                       # must return exactly one number
    min_value: float | None = 0    # default rule: the number must be exactly zero
    max_value: float | None = 0


CHECKS = [
    # ---------- reconciliation between layers ----------
    Check("raw_matches_load_log", "raw", "ERROR",
          "Rows in the raw table equal the rows recorded in the load log",
          """SELECT (SELECT count(*) FROM raw.bts_ontime)
                  - (SELECT COALESCE(sum(rows_loaded), 0) FROM raw.load_log)"""),

    Check("clean_reconciles_with_raw", "clean", "ERROR",
          "Clean rows plus removed duplicates equal raw rows (every row accounted for)",
          """SELECT (SELECT count(*) FROM clean.flights)
                  + (SELECT COALESCE(sum(duplicates_removed), 0) FROM clean.build_log)
                  - (SELECT count(*) FROM raw.bts_ontime)"""),

       Check("no_duplicate_flights", "analytics", "ERROR",
          "No flight appears twice on its natural key",
          """SELECT count(*) FROM (
                 SELECT 1 FROM analytics.fact_flights
                 GROUP BY date_key, airline_key, flight_number,
                          origin_airport_key, dest_airport_key, crs_dep_time
                 HAVING count(*) > 1) d"""),
    
    # ---------- integrity ----------

    Check("no_missing_days", "analytics", "ERROR",
          "Every calendar day between the first and last flight has flights",
          """SELECT count(*) FROM analytics.dim_date d
             WHERE d.date_key BETWEEN (SELECT min(date_key) FROM analytics.fact_flights)
                                  AND (SELECT max(date_key) FROM analytics.fact_flights)
               AND NOT EXISTS (SELECT 1 FROM analytics.fact_flights f
                               WHERE f.date_key = d.date_key)"""),

    Check("scheduled_departure_present", "analytics", "ERROR",
          "Every flight has a scheduled departure time",
          "SELECT count(*) FROM analytics.fact_flights WHERE crs_dep_time IS NULL"),

    Check("cancelled_have_no_arrival_time", "analytics", "ERROR",
          "Cancelled flights never have an arrival time (verified rule)",
          """SELECT count(*) FROM analytics.fact_flights
             WHERE is_cancelled AND arr_time IS NOT NULL"""),

    # ---------- known data quirks (warnings) ----------
    Check("operated_flights_have_aircraft", "analytics", "WARN",
          "Flights that operated have a recognised tail number (all unknowns were cancelled)",
          """SELECT count(*) FROM analytics.fact_flights
             WHERE aircraft_key = 0 AND NOT is_cancelled"""),

    Check("delay_causes_add_up", "analytics", "WARN",
          "Cause minutes match arrival delay (baseline measured: 16 flights with no cause recorded)",
          """SELECT count(*) FROM analytics.fact_flights
             WHERE arr_del15
               AND COALESCE(carrier_delay,0) + COALESCE(weather_delay,0)
                 + COALESCE(nas_delay,0) + COALESCE(security_delay,0)
                 + COALESCE(late_aircraft_delay,0) <> arr_delay""",
          min_value=0, max_value=100),

    Check("no_absurd_delays", "analytics", "WARN",
          "No delay above 10,000 minutes (about 7 days)",
          """SELECT count(*) FROM analytics.fact_flights
             WHERE dep_delay > 10000 OR arr_delay > 10000"""),

    Check("airports_have_coordinates", "analytics", "WARN",
          "No departures from airports without coordinates",
          """SELECT count(*) FROM analytics.fact_flights f
             JOIN analytics.dim_airport ap ON ap.airport_key = f.origin_airport_key
             WHERE ap.latitude IS NULL"""),

    Check("coordinates_in_plausible_range", "analytics", "WARN",
          "Airport coordinates fall inside US and territory bounds",
          """SELECT count(*) FROM analytics.dim_airport
             WHERE latitude IS NOT NULL
               AND NOT (latitude BETWEEN -15 AND 72
                        AND (longitude BETWEEN -180 AND -64
                             OR longitude BETWEEN 140 AND 180))"""),

    # ---------- wide statistical guardrails ----------
    Check("late_arrival_rate_plausible", "analytics", "WARN",
          "Share of arrivals 15+ minutes late is between 10 and 35 percent",
          "SELECT round(100.0 * avg(arr_del15::int), 2) FROM analytics.fact_flights",
          min_value=10, max_value=35),

    Check("cancellation_rate_plausible", "analytics", "WARN",
          "Cancellation rate is between 0.2 and 5 percent",
          "SELECT round(100.0 * avg(is_cancelled::int), 2) FROM analytics.fact_flights",
          min_value=0.2, max_value=5),
]