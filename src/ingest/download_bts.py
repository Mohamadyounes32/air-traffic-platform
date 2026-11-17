import argparse
import time
import zipfile
from pathlib import Path

import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://transtats.bts.gov/PREZIP"
FILE_TEMPLATE = (
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)
RAW_DIR = Path("data/raw/bts")
MAX_RETRIES = 5  # زدنا المحاولات لـ 5
TIMEOUT_SECONDS = 120 # زدنا وقت الانتظار

# هذا السطر بيخلي السيرفر يظن إننا متصفح كروم
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_year_month(value: str) -> tuple[int, int]:
    year, month = value.split("-")
    return int(year), int(month)

def month_range(start: tuple[int, int], end: tuple[int, int]):
    year, month = start
    while (year, month) <= end:
        yield year, month
        month += 1
        if month > 12:
            year, month = year + 1, 1

def is_valid_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return zf.testzip() is None
    except zipfile.BadZipFile:
        return False

def download_month(year: int, month: int, session: requests.Session) -> str:
    filename = FILE_TEMPLATE.format(year=year, month=month)
    target = RAW_DIR / filename

    if target.exists() and is_valid_zip(target):
        logger.info("SKIP     %d-%02d (already downloaded)", year, month)
        return "skipped"

    url = f"{BASE_URL}/{filename}"
    tmp = target.with_suffix(".part")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            downloaded_bytes = tmp.stat().st_size if tmp.exists() else 0
            
            headers = HEADERS.copy() # نستخدم الهيدرز الجديدة
            if downloaded_bytes > 0:
                headers['Range'] = f'bytes={downloaded_bytes}-'
                logger.info("RESUME   %d-%02d from byte %d (attempt %d/%d)", year, month, downloaded_bytes, attempt, MAX_RETRIES)
            else:
                logger.info("DOWNLOAD %d-%02d (attempt %d/%d)", year, month, attempt, MAX_RETRIES)

            with session.get(url, stream=True, timeout=TIMEOUT_SECONDS, headers=headers) as resp:
                if resp.status_code == 404:
                    logger.warning("NOT FOUND %d-%02d (not published yet?): %s", year, month, url)
                    return "not_found"

                if resp.status_code == 200 and downloaded_bytes > 0:
                    logger.warning("Server ignored Range header. Restarting download from scratch.")
                    downloaded_bytes = 0
                    mode = 'wb'
                elif resp.status_code == 206: # Partial Content
                    mode = 'ab'
                else:
                    mode = 'wb'

                resp.raise_for_status()

                with open(tmp, mode) as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            downloaded_bytes += len(chunk)

            if not is_valid_zip(tmp):
                raise ValueError("downloaded file is not a valid zip")

            tmp.replace(target)
            size_mb = target.stat().st_size / (1024 * 1024)
            logger.info("DONE     %d-%02d (%.1f MB)", year, month, size_mb)
            return "downloaded"

        except (requests.RequestException, ValueError) as exc:
            logger.warning("RETRY    %d-%02d failed: %s", year, month, exc)
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    logger.error("FAILED   %d-%02d after %d attempts", year, month, MAX_RETRIES)
    return "failed"

def main() -> None:
    parser = argparse.ArgumentParser(description="Download BTS on-time performance files")
    parser.add_argument("--start", required=True, help="First month, e.g. 2025-01")
    parser.add_argument("--end", required=True, help="Last month, e.g. 2025-03")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, int] = {}

    with requests.Session() as session:
        # نمرر الهيدرز للجلسة كلها
        session.headers.update(HEADERS)
        
        for year, month in month_range(parse_year_month(args.start), parse_year_month(args.end)):
            status = download_month(year, month, session)
            results[status] = results.get(status, 0) + 1

    logger.info("SUMMARY  %s", results)
    if results.get("failed"):
        raise SystemExit(1)