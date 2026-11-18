import argparse
from pathlib import Path

from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)
SQL_DIR = Path("sql")


def split_statements(text: str) -> dict[str, str]:
    """Split the file on '-- @@ name' marker lines."""
    statements: dict[str, str] = {}
    name, lines = None, []
    for line in text.splitlines():
        if line.startswith("-- @@"):
            if name:
                statements[name] = "\n".join(lines)
            name, lines = line.removeprefix("-- @@").strip(), []
        else:
            lines.append(line)
    if name:
        statements[name] = "\n".join(lines)
    return statements


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize live positions and apply retention")
    parser.add_argument("--keep-days", type=int, default=7, help="Days of raw states to keep")
    args = parser.parse_args()

    statements = split_statements((SQL_DIR / "11_live_summaries.sql").read_text(encoding="utf-8"))
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute((SQL_DIR / "10_live_summary_schema.sql").read_text(encoding="utf-8"))
        conn.commit()

        for name in ("national", "grid", "retention"):
            with conn.cursor() as cur:
                cur.execute(statements[name], {"keep_days": args.keep_days})
                logger.info("LIVE %-9s %s rows", name, f"{cur.rowcount:,}")
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()