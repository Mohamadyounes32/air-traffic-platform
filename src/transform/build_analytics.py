from pathlib import Path

from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)
SQL_DIR = Path("sql")

PENDING_SQL = """
    SELECT c.source_file, c.file_sha256
    FROM clean.build_log c
    LEFT JOIN analytics.build_log a
           ON a.source_file = c.source_file AND a.file_sha256 = c.file_sha256
    WHERE a.source_file IS NULL
    ORDER BY c.source_file
"""


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def main() -> None:
    conn = get_connection()
    failed = 0
    try:
        # Schema script has no parameters, so it can contain any characters
        with conn.cursor() as cur:
            cur.execute(read_sql("03_analytics_schema.sql"))
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(PENDING_SQL)
            pending = cur.fetchall()
        conn.commit()

        if not pending:
            logger.info("Nothing to build: analytics layer is up to date")
            return

        files = [p[0] for p in pending]

        # Dimensions first, so every foreign key target exists
        with conn.cursor() as cur:
            cur.execute(read_sql("04_load_dimensions.sql"), {"files": files})
        conn.commit()
        logger.info("Dimensions updated from %d file(s)", len(files))

        fact_sql = read_sql("05_load_fact.sql")
        for source_file, file_hash in pending:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM analytics.fact_flights WHERE source_file = %s",
                                (source_file,))
                    cur.execute(fact_sql, {"source_file": source_file})
                    rows = cur.rowcount

                    cur.execute("SELECT rows_clean FROM clean.build_log WHERE source_file = %s",
                                (source_file,))
                    expected = cur.fetchone()[0]
                    if rows != expected:
                        raise RuntimeError(f"row count mismatch: clean {expected}, fact {rows}")

                    cur.execute(
                        """INSERT INTO analytics.build_log (source_file, file_sha256, rows_loaded)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (source_file) DO UPDATE SET
                               file_sha256 = EXCLUDED.file_sha256,
                               rows_loaded = EXCLUDED.rows_loaded,
                               built_at = now()""",
                        (source_file, file_hash, rows))
                conn.commit()
                logger.info("FACT    %s | %s rows", source_file, f"{rows:,}")
            except Exception as exc:
                conn.rollback()
                failed += 1
                logger.error("FAILED  %s: %s", source_file, exc)
    finally:
        conn.close()

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()