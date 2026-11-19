from pathlib import Path

from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)
SQL_DIR = Path("sql")

COMMON = """
    COUNT(*)                                                    AS scheduled_flights,
    COUNT(*) FILTER (WHERE f.is_cancelled)                      AS cancelled_flights,
    COUNT(*) FILTER (WHERE f.is_diverted)                       AS diverted_flights,
    COUNT(*) FILTER (WHERE f.cancellation_code = 'A')           AS cancel_carrier,
    COUNT(*) FILTER (WHERE f.cancellation_code = 'B')           AS cancel_weather,
    COUNT(*) FILTER (WHERE f.cancellation_code = 'C')           AS cancel_nas,
    COUNT(*) FILTER (WHERE f.cancellation_code = 'D')           AS cancel_security"""

DEPARTURES = """
    COUNT(*) FILTER (WHERE NOT f.is_cancelled AND f.dep_del15 IS NOT NULL) AS departures_measured,
    COUNT(*) FILTER (WHERE NOT f.is_cancelled AND f.dep_del15)             AS departures_late_15,
    COALESCE(SUM(f.dep_delay_minutes) FILTER (WHERE NOT f.is_cancelled), 0) AS dep_delay_minutes_sum"""

ARRIVALS = """
    COUNT(*) FILTER (WHERE NOT f.is_cancelled AND f.arr_del15 IS NOT NULL) AS arrivals_measured,
    COUNT(*) FILTER (WHERE NOT f.is_cancelled AND f.arr_del15)             AS arrivals_late_15,
    COALESCE(SUM(f.arr_delay_minutes)
             FILTER (WHERE NOT f.is_cancelled AND NOT f.is_diverted), 0)   AS arr_delay_minutes_sum"""

CAUSES = """
    COALESCE(SUM(f.carrier_delay)       FILTER (WHERE f.arr_del15), 0) AS cause_carrier_min,
    COALESCE(SUM(f.weather_delay)       FILTER (WHERE f.arr_del15), 0) AS cause_weather_min,
    COALESCE(SUM(f.nas_delay)           FILTER (WHERE f.arr_del15), 0) AS cause_nas_min,
    COALESCE(SUM(f.security_delay)      FILTER (WHERE f.arr_del15), 0) AS cause_security_min,
    COALESCE(SUM(f.late_aircraft_delay) FILTER (WHERE f.arr_del15), 0) AS cause_late_aircraft_min"""

FROM_JOIN = """FROM analytics.fact_flights f
               JOIN analytics.dim_date d ON d.date_key = f.date_key"""

TABLES = {
    "daily_network": f"SELECT d.full_date, {COMMON}, {DEPARTURES}, {ARRIVALS}, {CAUSES} "
                     f"{FROM_JOIN} GROUP BY d.full_date",
    "daily_airline": f"SELECT d.full_date, f.airline_key, {COMMON}, {DEPARTURES}, {ARRIVALS}, {CAUSES} "
                     f"{FROM_JOIN} GROUP BY d.full_date, f.airline_key",
    "daily_airport": f"SELECT d.full_date, f.origin_airport_key AS airport_key, {COMMON}, {DEPARTURES} "
                     f"{FROM_JOIN} GROUP BY d.full_date, f.origin_airport_key",
    "hour_pattern":  f"SELECT d.year, d.month, d.month_name, d.day_of_week, d.day_name, "
                     f"f.sched_dep_hour, {COMMON}, {DEPARTURES} "
                     f"{FROM_JOIN} GROUP BY d.year, d.month, d.month_name, d.day_of_week, "
                     f"d.day_name, f.sched_dep_hour",
}


def main() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for name, select in TABLES.items():       # one transaction: all or nothing
                cur.execute(f"DROP TABLE IF EXISTS reporting.{name}")
                cur.execute(f"CREATE TABLE reporting.{name} AS {select}")
                cur.execute(f"SELECT count(*) FROM reporting.{name}")
                logger.info("REPORTING %-14s %s rows", name, f"{cur.fetchone()[0]:,}")
            cur.execute((SQL_DIR / "12_reporting_views.sql").read_text(encoding="utf-8"))
        conn.commit()
        logger.info("REPORTING views refreshed")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()