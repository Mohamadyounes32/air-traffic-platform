import argparse
import subprocess
import sys
import time

from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_step(name: str, args: list[str]) -> None:
    logger.info("=== STEP %s ===", name)
    start = time.perf_counter()
    result = subprocess.run([sys.executable, *args])
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        logger.error("STEP %s FAILED (exit code %s) after %.0fs", name, result.returncode, elapsed)
        raise SystemExit(result.returncode)
    logger.info("STEP %s OK (%.0fs)", name, elapsed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full US air traffic pipeline")
    parser.add_argument("--start", default="2024-01", help="First month, e.g. 2024-01")
    parser.add_argument("--end", default="2025-12", help="Last month, e.g. 2025-12")
    args = parser.parse_args()

    steps = [
        ("download",        ["-m", "src.ingest.download_bts", "--start", args.start, "--end", args.end]),
        ("load_raw",        ["-m", "src.ingest.load_raw"]),
        ("build_clean",     ["-m", "src.transform.build_clean"]),
        ("build_analytics", ["-m", "src.transform.build_analytics"]),
        ("enrich_airports", ["-m", "src.ingest.load_airports"]),
        ("quality_checks",  ["-m", "src.quality.run_checks"]),
    ]

    total_start = time.perf_counter()
    for name, step_args in steps:
        run_step(name, step_args)
    logger.info("PIPELINE COMPLETE in %.0fs", time.perf_counter() - total_start)


if __name__ == "__main__":
    main()