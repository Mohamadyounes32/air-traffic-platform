import pandas as pd

from src.utils.db import get_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)
REQUIRED = ["event_name", "event_type", "start_date", "end_date", "source_url", "notes"]


def main() -> None:
    df = pd.read_csv("reference/events.csv", dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"events.csv is missing columns: {missing}")

    for col in ("start_date", "end_date"):
        parsed = pd.to_datetime(df[col].replace("", None), errors="raise")
        df[col] = parsed.dt.date
    if (df["start_date"] > df["end_date"].fillna(df["start_date"])).any():
        raise SystemExit("an event ends before it starts")

    df["source_url"] = df["source_url"].replace("", None)
    df.to_sql("events", get_engine(), schema="reporting", if_exists="replace", index=False)
    logger.info("EVENTS loaded %d rows into reporting.events", len(df))


if __name__ == "__main__":
    main()