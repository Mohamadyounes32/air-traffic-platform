import argparse
import csv
import io
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.utils.db import get_connection
from src.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

TOKEN_URL = ("https://auth.opensky-network.org/auth/realms/"
             "opensky-network/protocol/openid-connect/token")
API_URL = "https://opensky-network.org/api/states/all"
BBOX = {"lamin": 24.0, "lomin": -125.0, "lamax": 50.0, "lomax": -66.0}  # contiguous US
BBOX_TEXT = f"{BBOX['lamin']},{BBOX['lomin']},{BBOX['lamax']},{BBOX['lomax']}"
CREDITS_PER_CALL = 4            # box over 400 sq. degrees
MAX_DAILY_CREDITS = 3_600       # leaves a margin under the 4,000 quota
CREDIT_RESERVE = 300            # stop polling below this balance
SCHEMA_SQL = Path("sql/09_live_schema.sql")
AIRLINE_CALLSIGN = re.compile(r"^[A-Z]{3}[0-9]{1,4}[A-Z]?$")

STATE_COLUMNS = ("poll_id, icao24, callsign, origin_country, time_position, last_contact, "
                 "longitude, latitude, baro_altitude, geo_altitude, on_ground, velocity, "
                 "true_track, vertical_rate, squawk, position_source, category")


class TokenManager:
    """One token, reused until shortly before it expires (tokens last 30 minutes)."""

    def __init__(self) -> None:
        self.client_id = os.getenv("OPENSKY_CLIENT_ID")
        self.client_secret = os.getenv("OPENSKY_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise SystemExit("Set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in .env")
        self.token: str | None = None
        self.expires_at = 0.0

    def get(self, force: bool = False) -> str:
        if force or self.token is None or time.time() >= self.expires_at:
            resp = requests.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials",
                      "client_id": self.client_id,
                      "client_secret": self.client_secret},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self.token = data["access_token"]
            self.expires_at = time.time() + data.get("expires_in", 1800) - 60
        return self.token


def to_ts(epoch):
    return None if epoch is None else datetime.fromtimestamp(epoch, tz=timezone.utc)


def fetch_states(session: requests.Session, tokens: TokenManager) -> requests.Response:
    """One API call. If the token is rejected (401), refresh it and retry once."""
    resp = None
    for attempt in (1, 2):
        headers = {"Authorization": f"Bearer {tokens.get(force=(attempt == 2))}"}
        resp = session.get(API_URL, params={**BBOX, "extended": 1},
                           headers=headers, timeout=60)
        if resp.status_code == 401 and attempt == 1:
            logger.warning("Token rejected (401): refreshing and retrying once")
            continue
        break
    return resp


def parse_states(payload: dict) -> list[tuple]:
    rows = []
    for s in payload.get("states") or []:
        category = s[17] if len(s) > 17 else None
        callsign = (s[1] or "").strip() or None
        rows.append((
            s[0], callsign, s[2], to_ts(s[3]), to_ts(s[4]),
            s[5], s[6], s[7], s[13], s[8], s[9], s[10], s[11],
            s[14], s[16], category,
        ))
    return rows


def is_airline_like(row: tuple) -> bool:
    callsign, category = row[1], row[15]
    return category in (3, 4, 5, 6) or bool(callsign and AIRLINE_CALLSIGN.match(callsign))


def poll_once(conn, session, tokens) -> dict:
    requested_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    status, error, payload, remaining, retry_after = 0, None, None, None, None

    try:
        resp = fetch_states(session, tokens)
        status = resp.status_code
        if "X-Rate-Limit-Remaining" in resp.headers:
            remaining = int(float(resp.headers["X-Rate-Limit-Remaining"]))
        if status == 200:
            payload = resp.json()
        elif status == 429:
            retry_after = int(float(resp.headers.get("X-Rate-Limit-Retry-After-Seconds", 0)))
            error = f"rate limited; retry after {retry_after}s"
        else:
            error = f"HTTP {status}"
    except (requests.RequestException, ValueError, KeyError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    duration = round(time.perf_counter() - started, 2)
    total = kept_count = 0
    api_time = None
    kept: list[tuple] = []

    if payload is not None:
        api_time = to_ts(payload.get("time"))
        rows = parse_states(payload)
        kept = [r for r in rows if is_airline_like(r)]
        total, kept_count = len(rows), len(kept)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO raw.opensky_poll
                       (requested_at, api_time, bbox, http_status, states_total, states_kept,
                        credits_remaining, duration_seconds, error_message)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (bbox, api_time) DO NOTHING
                   RETURNING poll_id""",
                (requested_at, api_time, BBOX_TEXT, status,
                 total if payload is not None else None,
                 kept_count if payload is not None else None,
                 remaining, duration, error),
            )
            row = cur.fetchone()

            if payload is not None and row is None:
                logger.info("Snapshot %s already stored; skipping", api_time)
            elif row is not None and kept:
                poll_id = row[0]
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                for r in kept:
                    writer.writerow((poll_id, *r))
                buffer.seek(0)
                cur.copy_expert(
                    f"COPY raw.opensky_states ({STATE_COLUMNS}) FROM STDIN WITH (FORMAT csv)",
                    buffer,
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    if error:
        logger.warning("POLL FAILED status=%s %s", status, error)
    else:
        logger.info("POLL OK  snapshot=%s states=%d kept=%d credits_left=%s (%.1fs)",
                    api_time, total, kept_count, remaining, duration)
    return {"retry_after": retry_after, "remaining": remaining, "status": status}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect live US aircraft positions from OpenSky")
    parser.add_argument("--interval", type=int, default=120, help="Seconds between polls")
    parser.add_argument("--once", action="store_true", help="Run a single poll and exit")
    parser.add_argument("--max-polls", type=int, default=0, help="Stop after this many polls (0 = no limit)")
    args = parser.parse_args()

    daily_credits = 86_400 / args.interval * CREDITS_PER_CALL
    if not args.once and daily_credits > MAX_DAILY_CREDITS:
        parser.error(f"--interval {args.interval}s would use about {daily_credits:,.0f} credits/day "
                     f"(safe limit {MAX_DAILY_CREDITS:,}). Use an interval of "
                     f"{int(86_400 * CREDITS_PER_CALL / MAX_DAILY_CREDITS) + 1}s or more.")

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    conn.commit()

    tokens = TokenManager()
    polls = 0
    next_run = time.monotonic()
    logger.info("Collector started (interval %ss, about %.0f credits/day)",
                args.interval, daily_credits)

    try:
        with requests.Session() as session:
            while True:
                result = poll_once(conn, session, tokens)
                polls += 1

                if args.once or (args.max_polls and polls >= args.max_polls):
                    break
                if result["retry_after"]:
                    if result["retry_after"] > 900:
                        logger.error("Rate limited for %ss; stopping", result["retry_after"])
                        sys.exit(2)
                    time.sleep(result["retry_after"] + 5)
                elif result["remaining"] is not None and result["remaining"] < CREDIT_RESERVE:
                    logger.error("Credits down to %s (reserve %s); stopping to protect the quota",
                                 result["remaining"], CREDIT_RESERVE)
                    sys.exit(2)

                next_run += args.interval
                time.sleep(max(0.0, next_run - time.monotonic()))
    except KeyboardInterrupt:
        logger.info("Stopped by user after %d polls", polls)
    finally:
        conn.close()


if __name__ == "__main__":
    main()