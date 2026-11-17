import sys
import time
import uuid
from pathlib import Path

from src.quality.checks import CHECKS, Check
from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)
SCHEMA_SQL = Path("sql/07_dq_schema.sql")


def evaluate(check: Check, value: float) -> str:
    within = (check.min_value is None or value >= check.min_value) and \
             (check.max_value is None or value <= check.max_value)
    if within:
        return "PASS"
    return "FAIL" if check.severity == "ERROR" else "WARN"


def run_check(conn, check: Check, run_id: str) -> str:
    start = time.perf_counter()
    value, error, status = None, None, "EXEC_ERROR"
    try:
        with conn.cursor() as cur:
            cur.execute(check.sql)
            row = cur.fetchone()
        if row is None or row[0] is None:
            raise ValueError("check query returned no value")
        value = float(row[0])
        status = evaluate(check, value)
    except Exception as exc:
        conn.rollback()
        error = str(exc).strip()

    duration = time.perf_counter() - start

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO dq.check_results
                   (run_id, check_name, layer, severity, status, observed_value,
                    min_allowed, max_allowed, duration_seconds, error_message)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (run_id, check.name, check.layer, check.severity, status, value,
             check.min_value, check.max_value, round(duration, 2), error),
        )
    conn.commit()

    shown = "n/a" if value is None else f"{value:g}"
    message = f"{status:<10} {check.layer:<9} {check.name} = {shown} " \
              f"(allowed {check.min_value}..{check.max_value}, {duration:.1f}s)"
    if status == "PASS":
        logger.info(message)
    elif status == "WARN":
        logger.warning("%s | %s", message, check.description)
    else:
        logger.error("%s | %s%s", message, check.description,
                     f" | {error}" if error else "")
    return status


def main() -> None:
    run_id = uuid.uuid4().hex[:12]
    conn = get_connection()
    counts: dict[str, int] = {}
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        conn.commit()

        logger.info("Running %d data quality checks (run %s)", len(CHECKS), run_id)
        for check in CHECKS:
            status = run_check(conn, check, run_id)
            counts[status] = counts.get(status, 0) + 1
    finally:
        conn.close()

    logger.info("DQ SUMMARY %s", counts)
    if counts.get("FAIL") or counts.get("EXEC_ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()