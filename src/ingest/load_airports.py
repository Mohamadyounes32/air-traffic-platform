import io
import time
from pathlib import Path

import pandas as pd
import requests

from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)

URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
REF_DIR = Path("data/raw/reference")
TARGET = REF_DIR / "ourairports_airports.csv"
SQL_FILE = Path("sql/06_enrich_airports.sql")
MAX_RETRIES = 3

COLUMNS = [
    "id", "ident", "type", "name", "latitude_deg", "longitude_deg",
    "elevation_ft", "iso_country", "iso_region", "municipality",
    "scheduled_service", "iata_code", "local_code", "gps_code",
]


def download() -> None:
    """Download the file. If it fails but a local copy exists, keep using the copy."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TARGET.with_suffix(".part")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("DOWNLOAD OurAirports (attempt %d)", attempt)
            resp = requests.get(URL, timeout=60)
            resp.raise_for_status()
            header = resp.text.split("\n", 1)[0]
            if "iata_code" not in header or "latitude_deg" not in header:
                raise ValueError("unexpected file format (header check failed)")
            tmp.write_bytes(resp.content)
            tmp.replace(TARGET)
            logger.info("DONE     %.1f MB", TARGET.stat().st_size / (1024 * 1024))
            return
        except (requests.RequestException, ValueError) as exc:
            logger.warning("RETRY    download failed: %s", exc)
            time.sleep(2 ** attempt)

    tmp.unlink(missing_ok=True)
    if TARGET.exists():
        logger.warning("Download failed; using the existing local copy")
    else:
        raise SystemExit("Download failed and no local copy exists")


def load_raw(conn) -> None:
    df = pd.read_csv(TARGET, usecols=COLUMNS, dtype=str, keep_default_na=False)[COLUMNS]
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    col_defs = ", ".join(f"{c} TEXT" for c in COLUMNS)
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS raw.ourairports_airports (
                {col_defs},
                loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
        cur.execute("TRUNCATE raw.ourairports_airports")
        cur.copy_expert(
            f"COPY raw.ourairports_airports ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT csv)",
            buffer,
        )
        cur.execute("SELECT count(*) FROM raw.ourairports_airports")
        loaded = cur.fetchone()[0]
        if loaded != len(df):
            raise RuntimeError(f"row count mismatch: file {len(df)}, table {loaded}")
    logger.info("LOADED  raw.ourairports_airports (%s rows)", f"{loaded:,}")


def enrich(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SQL_FILE.read_text(encoding="utf-8"))
        updated = cur.rowcount
        cur.execute("SELECT count(*) FROM analytics.dim_airport")
        total = cur.fetchone()[0]
    logger.info("ENRICHED %s of %s airports", updated, total)


def main() -> None:
    download()
    conn = get_connection()
    try:
        load_raw(conn)
        enrich(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()