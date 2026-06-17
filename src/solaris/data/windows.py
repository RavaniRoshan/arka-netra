from __future__ import annotations

import numpy as np
import pandas as pd


def add_forecast_labels(frame: pd.DataFrame, events: pd.DataFrame, horizon_minutes: int) -> pd.DataFrame:
    """Add forward-looking flare labels and upcoming-event metadata."""
    result = frame.sort_values("timestamp").reset_index(drop=True).copy()
    result["flare_label"] = 0
    result["upcoming_event_id"] = ""
    result["upcoming_flare_class"] = ""
    result["time_to_flare_minutes"] = np.nan

    for idx, row in result.iterrows():
        now = row["timestamp"]
        future = events[(events["start_time"] >= now) & (events["start_time"] <= now + pd.Timedelta(minutes=horizon_minutes))]
        if not future.empty:
            event = future.iloc[0]
            result.at[idx, "flare_label"] = 1
            result.at[idx, "upcoming_event_id"] = event["event_id"]
            result.at[idx, "upcoming_flare_class"] = event["flare_class"]
            result.at[idx, "time_to_flare_minutes"] = (event["start_time"] - now).total_seconds() / 60
    return result

