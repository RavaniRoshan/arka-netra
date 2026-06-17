from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_noaa_flare_catalog(path: str | Path) -> pd.DataFrame:
    """Load a NOAA-like flare catalog CSV."""
    frame = pd.read_csv(path, parse_dates=["start_time", "peak_time"])
    required = {"event_id", "start_time", "peak_time", "flare_class"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"NOAA catalog is missing required columns: {sorted(missing)}")
    for column in ["start_time", "peak_time"]:
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame.sort_values("start_time").reset_index(drop=True)


def flare_class_rank(flare_class: str) -> int:
    """Map A/B/C/M/X flare letters into ordered severity ranks."""
    letter = str(flare_class).upper()[:1]
    return {"A": 1, "B": 2, "C": 3, "M": 4, "X": 5}.get(letter, 0)

