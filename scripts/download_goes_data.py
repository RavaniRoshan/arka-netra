#!/usr/bin/env python3
"""Download GOES XRS data from NOAA SWPC for a specified date range.

Usage:
    python scripts/download_goes_data.py --start 2017-09-05 --end 2017-09-07
    python scripts/download_goes_data.py --save-dir data/raw/goes_sample

By default saves to data/raw/goes_sample/ and uses the last 7 days.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from arkanetra.data.goes import download_goes_xrs


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GOES XRS data from NOAA SWPC")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD or ISO format). Default: 7 days ago")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD or ISO format). Default: today")
    parser.add_argument("--save-dir", default=None, help="Directory to save the CSV file")
    args = parser.parse_args()

    today = datetime.now(timezone.utc)
    start = args.start or (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = args.end or today.strftime("%Y-%m-%d")

    save_dir = Path(args.save_dir) if args.save_dir else None
    path = download_goes_xrs(start, end, save_dir)

    if path:
        print(f"GOES XRS data saved to: {path}")
        print(f"Date range: {start} to {end}")
    else:
        print("Download failed. The bundled sample CSV remains available.")
        print(f"  Sample: data/raw/goes_sample/goes_xrs_20170905_20170907.csv")


if __name__ == "__main__":
    main()
