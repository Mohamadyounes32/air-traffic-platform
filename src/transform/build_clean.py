from pathlib import Path

from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)
SQL_DIR = Path("sql")

PENDING_SQL = """
    SELECT l.source_file, l.file_sha256, l.rows_loaded
    FROM raw.load_log l
    LEFT JOIN clean.build_log b
           ON b.source_file = l.source_file AND b.file_sha256 = l.file_sha256
    WHERE b.source_file IS NULL
    ORDER BY l.source_file
"""


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def main() -> None:
    conn = get_connection()
    failed = 0
    try:
        with conn.cursor() as cur:
            cur.execute(read_sql("01_clean_schema.sql"))
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(PENDING_SQL)
            pending = cur.fetchall()
        conn.commit()

        if not pending:
            logger.info("Nothing to build: clean layer is up to date")
            return

        insert_sql = read_sql("02_clean_flights_insert.sql")

        for source_file, file_hash, rows_raw in pending:
            try:
                with conn.cursor() as cur:
                    # Replace this file's previous rows (if any), then rebuild them
                    cur.execute("DELETE FROM clean.flights WHERE source_file = %s", (source_file,))
                    cur.execute(insert_sql, {"source_file": source_file})
                    rows_clean = cur.rowcount
                    duplicates = rows_raw - rows_clean

                    cur.execute(
                        """INSERT INTO clean.build_log
                               (source_file, file_sha256, rows_raw, rows_clean, duplicates_removed)
                           VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (source_file) DO UPDATE SET
                               file_sha256 = EXCLUDED.file_sha256,
                               rows_raw = EXCLUDED.rows_raw,
                               rows_clean = EXCLUDED.rows_clean,
                               duplicates_removed = EXCLUDED.duplicates_removed,
                               built_at = now()""",
                        (source_file, file_hash, rows_raw, rows_clean, duplicates),
                    )
                conn.commit()
                logger.info("CLEANED %s | raw %s -> clean %s | duplicates removed %s",
                            source_file, f"{rows_raw:,}", f"{rows_clean:,}", duplicates)
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