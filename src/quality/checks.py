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

    Check("fact_matches_clean", "analytics", "ERROR",
          "Fact rows equal clean rows",
          """SELECT (SELECT count(*) FROM analytics.fact_flights)
                  - (SELECT count(*) FROM clean.flights)"""),

    # ---------- integrity ----------
    Check("no_duplicate_flights", "analytics", "ERROR",
          "No flight appears twice on its natural key",
          """SELECT count(*) FROM (
                 SELECT 1 FROM analytics.fact_flights
                 GROUP BY date_key, airline_key, flight_number,
                          origin_airport_key, dest_airport_key, crs_dep_time
                 HAVING count(*) > 1) d"""),

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

    # ---------- live layer (Step 9b) ----------
    Check("live_last_success_age_minutes", "raw", "WARN",
          "A successful poll happened in the last 15 minutes (collector running)",
          """SELECT COALESCE(EXTRACT(EPOCH FROM (now() - max(requested_at))) / 60, 99999)
             FROM raw.opensky_poll WHERE http_status = 200""",
          min_value=0, max_value=15),

    Check("live_error_rate_24h_pct", "raw", "WARN",
          "At most 5 percent of polls in the last 24 hours failed",
          """SELECT COALESCE(ROUND(100.0 * COUNT(*) FILTER (WHERE http_status <> 200)
                                  / NULLIF(COUNT(*), 0), 2), 0)
             FROM raw.opensky_poll WHERE requested_at > now() - INTERVAL '24 hours'""",
          min_value=0, max_value=5),

    Check("live_max_gap_minutes_24h", "raw", "WARN",
          "No gap longer than 15 minutes between successful polls in the last 24 hours",
          """SELECT COALESCE(MAX(gap), 0) FROM (
                 SELECT EXTRACT(EPOCH FROM (requested_at - LAG(requested_at) OVER (ORDER BY requested_at))) / 60 AS gap
                 FROM raw.opensky_poll
                 WHERE http_status = 200 AND requested_at > now() - INTERVAL '24 hours') g""",
          min_value=0, max_value=15),

    Check("live_credits_above_reserve_24h", "raw", "WARN",
          "Remaining API credits never fell below the 300-credit reserve",
          """SELECT COALESCE(MIN(credits_remaining), 99999) FROM raw.opensky_poll
             WHERE requested_at > now() - INTERVAL '24 hours' AND credits_remaining IS NOT NULL""",
          min_value=300, max_value=None),

    Check("live_every_poll_summarized", "analytics", "ERROR",
          "Every successful poll older than one hour appears in the national summary",
          """SELECT COUNT(*) FROM raw.opensky_poll p
             WHERE p.http_status = 200 AND p.api_time IS NOT NULL
               AND p.api_time < now() - INTERVAL '1 hour'
               AND NOT EXISTS (SELECT 1 FROM analytics.live_national n WHERE n.poll_id = p.poll_id)"""),

        Check("reporting_network_matches_fact", "reporting", "ERROR",
          "Daily network table accounts for every fact row",
          """SELECT (SELECT COALESCE(SUM(scheduled_flights), 0) FROM reporting.daily_network)
                  - (SELECT COUNT(*) FROM analytics.fact_flights)"""),

    Check("reporting_airline_matches_fact", "reporting", "ERROR",
          "Daily airline table accounts for every fact row",
          """SELECT (SELECT COALESCE(SUM(scheduled_flights), 0) FROM reporting.daily_airline)
                  - (SELECT COUNT(*) FROM analytics.fact_flights)"""),

    Check("reporting_airport_matches_fact", "reporting", "ERROR",
          "Daily airport table accounts for every fact row",
          """SELECT (SELECT COALESCE(SUM(scheduled_flights), 0) FROM reporting.daily_airport)
                  - (SELECT COUNT(*) FROM analytics.fact_flights)"""),

]