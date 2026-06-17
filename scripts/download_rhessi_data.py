#!/usr/bin/env python3
"""Download RHESSI observing summary data for a specified date range.

Tries to fetch FITS files from the RHESSI archive at
https://hesperia.gsfc.nasa.gov/hessidata/metadata/catalog/

If FITS access fails, falls back to the bundled sample CSV.


Usage:
    python scripts/download_rhessi_data.py --start 2017-09-05 --end 2017-09-07
    python scripts/download_rhessi_data.py --energy-band 25-50 keV --save-dir data/raw/goes_sample

By default saves to data/raw/goes_sample/.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from solaris.data.hard_xray_proxy import download_rhessi_obs_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Download RHESSI hard X-ray data")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--energy-band", default="25-100 keV", help="Target energy band")
    parser.add_argument("--save-dir", default=None, help="Directory to save files")
    args = parser.parse_args()

    today = datetime.now(timezone.utc)
    start = args.start or (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = args.end or today.strftime("%Y-%m-%d")

    save_dir = Path(args.save_dir) if args.save_dir else None
    paths = download_rhessi_obs_summary(start, end, save_dir)

    if paths:
        print(f"Downloaded {len(paths)} RHESSI file(s) for {start} to {end}:")
        for p in paths:
            print(f"  {p}")
    else:
        print("Download failed. The bundled sample CSV remains available.")
        print(f"  Sample: data/raw/goes_sample/rhessi_hard_xray_20170905_20170907.csv")


if __name__ == "__main__":
    main()
