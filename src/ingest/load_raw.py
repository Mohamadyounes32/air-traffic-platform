import argparse
import csv
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

from psycopg2 import sql

from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)

RAW_DIR = Path("data/raw/bts")
SCHEMA = "raw"
TABLE = "bts_ontime"
LOG_TABLE = "load_log"
METADATA_COLUMNS = {"source_file", "ingested_at"}


class SchemaDriftError(Exception):
    """The file's columns do not match the existing raw table."""


# ---------- helpers ----------

def sanitize(name: str) -> str:
    """'Reporting_Airline' -> 'reporting_airline'. Safe, lowercase column names."""
    clean = re.sub(r"[^0-9a-zA-Z_]", "_", name.strip()).lower()
    return f"c_{clean}" if clean[:1].isdigit() else clean


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def month_key(path: Path) -> tuple[int, int]:
    """Sort key so files load in calendar order: ..._2025_2.zip before ..._2025_10.zip."""
    match = re.search(r"_(\d{4})_(\d{1,2})\.zip$", path.name)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


class LineCleaner:
    """File-like wrapper feeding COPY. Optionally strips a trailing comma from each line."""

    def __init__(self, text_stream, strip_trailing_comma: bool):
        self.src = text_stream
        self.strip = strip_trailing_comma

    def read(self, size: int = 1024 * 1024) -> str:
        parts, total = [], 0
        while total < size:
            line = self.src.readline()
            if not line:
                break
            if self.strip:
                line = line.rstrip("\r\n")
                if line.endswith(","):
                    line = line[:-1]
                line += "\n"
            parts.append(line)
            total += len(line)
        return "".join(parts)


def find_csv_member(zf: zipfile.ZipFile) -> str:
    members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if len(members) != 1:
        raise ValueError(f"expected exactly 1 CSV in the zip, found {members}")
    return members[0]


def read_header(text_stream) -> tuple[list[str], bool]:
    """Read the header line. Returns (column names, header_has_trailing_comma)."""
    raw_names = next(csv.reader([text_stream.readline()]))
    trailing = bool(raw_names) and raw_names[-1].strip() == ""
    if trailing:
        raw_names = raw_names[:-1]
    names = [sanitize(n) for n in raw_names]
    if len(set(names)) != len(names):
        raise ValueError("duplicate column names after sanitizing")
    return names, trailing


# ---------- database setup ----------

def ensure_log_table(cur) -> None:
    cur.execute(sql.SQL("""
        CREATE TABLE IF NOT EXISTS {}.{} (
            load_id     BIGSERIAL PRIMARY KEY,
            source_file TEXT        NOT NULL,
            file_sha256 TEXT        NOT NULL,
            rows_loaded BIGINT      NOT NULL,
            loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """).format(sql.Identifier(SCHEMA), sql.Identifier(LOG_TABLE)))


def ensure_raw_table(cur, columns: list[str]) -> None:
    """Create the raw table on first use; afterwards verify the columns still match."""
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (SCHEMA, TABLE),
    )
    existing = [r[0] for r in cur.fetchall() if r[0] not in METADATA_COLUMNS]

    if existing:
        if set(existing) != set(columns):
            missing = sorted(set(existing) - set(columns))
            extra = sorted(set(columns) - set(existing))
            raise SchemaDriftError(f"missing in file: {missing} | new in file: {extra}")
        return

    col_defs = sql.SQL(", ").join(
        sql.SQL("{} TEXT").format(sql.Identifier(c)) for c in columns
    )
    cur.execute(sql.SQL("""
        CREATE TABLE {}.{} (
            {},
            source_file TEXT        NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """).format(sql.Identifier(SCHEMA), sql.Identifier(TABLE), col_defs))
    cur.execute(sql.SQL("CREATE INDEX ON {}.{} (source_file)").format(
        sql.Identifier(SCHEMA), sql.Identifier(TABLE)))
    logger.info("Created table %s.%s with %d columns", SCHEMA, TABLE, len(columns))


# ---------- main load logic ----------

def load_file(conn, path: Path) -> str:
    """Load one zip. Returns 'loaded' or 'skipped'."""
    source_file = path.name
    file_hash = sha256_of(path)

    with conn.cursor() as cur:
        ensure_log_table(cur)
        cur.execute(
            sql.SQL("SELECT 1 FROM {}.{} WHERE source_file = %s AND file_sha256 = %s").format(
                sql.Identifier(SCHEMA), sql.Identifier(LOG_TABLE)),
            (source_file, file_hash),
        )
        already_loaded = cur.fetchone() is not None
    conn.commit()

    if already_loaded:
        logger.info("SKIP    %s (identical file already loaded)", source_file)
        return "skipped"

    with zipfile.ZipFile(path) as zf:
        member = find_csv_member(zf)
        text_stream = io.TextIOWrapper(zf.open(member), encoding="utf-8-sig", newline="")
        columns, trailing_comma = read_header(text_stream)
        col_list = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
        target = sql.SQL("{}.{}").format(sql.Identifier(SCHEMA), sql.Identifier(TABLE))

        try:
            with conn.cursor() as cur:
                ensure_raw_table(cur, columns)

                cur.execute(sql.SQL("CREATE TEMP TABLE stg_bts ({}) ON COMMIT DROP").format(
                    sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(c)) for c in columns)))

                copy_sql = sql.SQL("COPY stg_bts ({}) FROM STDIN WITH (FORMAT csv)").format(
                    col_list).as_string(conn)
                cur.copy_expert(copy_sql, LineCleaner(text_stream, trailing_comma))

                cur.execute("SELECT count(*) FROM stg_bts")
                staged_rows = cur.fetchone()[0]

                # Re-loading a changed file replaces its old rows instead of duplicating them
                cur.execute(sql.SQL("DELETE FROM {} WHERE source_file = %s").format(target),
                            (source_file,))
                cur.execute(sql.SQL("INSERT INTO {} ({}, source_file) SELECT {}, %s FROM stg_bts").format(
                    target, col_list, col_list), (source_file,))

                # Verification: what is in the table must equal what we copied
                cur.execute(sql.SQL("SELECT count(*) FROM {} WHERE source_file = %s").format(target),
                            (source_file,))
                table_rows = cur.fetchone()[0]
                if table_rows != staged_rows:
                    raise RuntimeError(f"row count mismatch: staged {staged_rows}, table {table_rows}")

                cur.execute(
                    sql.SQL("DELETE FROM {}.{} WHERE source_file = %s").format(
                        sql.Identifier(SCHEMA), sql.Identifier(LOG_TABLE)),
                    (source_file,))
                cur.execute(
                    sql.SQL("INSERT INTO {}.{} (source_file, file_sha256, rows_loaded) VALUES (%s, %s, %s)").format(
                        sql.Identifier(SCHEMA), sql.Identifier(LOG_TABLE)),
                    (source_file, file_hash, staged_rows))
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    logger.info("LOADED  %s (%s rows)", source_file, f"{staged_rows:,}")
    return "loaded"


def main() -> None:
    parser = argparse.ArgumentParser(description="Load downloaded BTS files into the raw layer")
    parser.add_argument("--file", help="Load one specific zip instead of the whole folder")
    args = parser.parse_args()

    files = [Path(args.file)] if args.file else sorted(RAW_DIR.glob("*.zip"), key=month_key)
    if not files:
        logger.error("No zip files found in %s", RAW_DIR)
        sys.exit(1)

    results: dict[str, int] = {}
    conn = get_connection()
    try:
        for path in files:
            try:
                status = load_file(conn, path)
            except SchemaDriftError as exc:
                logger.error("SCHEMA DRIFT in %s: %s", path.name, exc)
                status = "failed"
            except Exception as exc:
                logger.error("FAILED  %s: %s", path.name, exc)
                status = "failed"
            results[status] = results.get(status, 0) + 1
    finally:
        conn.close()

    logger.info("SUMMARY %s", results)
    if results.get("failed"):
        sys.exit(1)


if __name__ == "__main__":
    main()