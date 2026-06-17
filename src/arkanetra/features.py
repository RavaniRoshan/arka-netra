from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    y = np.asarray(values, dtype=float)
    x = x - x.mean()
    denom = float((x * x).sum())
    if denom == 0:
        return 0.0
    return float((x * (y - y.mean())).sum() / denom)


def add_features(frame: pd.DataFrame, events: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Add physics-inspired, past-only time-series features."""
    cfg = config["features"]
    window = int(cfg["rolling_window"])
    smooth = int(cfg["smoothing_window"])
    eps = float(cfg["hardness_epsilon"])

    result = frame.sort_values("timestamp").reset_index(drop=True).copy()
    cadence_minutes = result["timestamp"].diff().dt.total_seconds().div(60).median()
    if not np.isfinite(cadence_minutes) or cadence_minutes <= 0:
        cadence_minutes = float(config["data"]["cadence_minutes"])

    result["soft_xray_smoothed"] = result["soft_xray_flux"].rolling(smooth, min_periods=1).mean()
    result["hard_xray_smoothed"] = result["hard_xray_flux"].rolling(smooth, min_periods=1).mean()
    result["hardness_ratio"] = result["hard_xray_smoothed"] / np.maximum(result["soft_xray_smoothed"], eps)
    result["soft_xray_derivative"] = result["soft_xray_smoothed"].diff().fillna(0.0) / cadence_minutes
    result["integrated_hard_xray_energy"] = (
        result["hard_xray_flux"].rolling(window, min_periods=1).sum() * cadence_minutes
    )

    result["rolling_mean"] = result["soft_xray_flux"].rolling(window, min_periods=1).mean()
    result["rolling_variance"] = result["soft_xray_flux"].rolling(window, min_periods=2).var().fillna(0.0)
    result["rolling_slope"] = (
        result["soft_xray_flux"].rolling(window, min_periods=2).apply(_rolling_slope, raw=True).fillna(0.0)
    )
    result["rolling_volatility"] = result["soft_xray_flux"].rolling(window, min_periods=2).std().fillna(0.0)
    result["hard_rolling_mean"] = result["hard_xray_flux"].rolling(window, min_periods=1).mean()
    result["hard_rolling_slope"] = (
        result["hard_xray_flux"].rolling(window, min_periods=2).apply(_rolling_slope, raw=True).fillna(0.0)
    )

    starts = list(pd.to_datetime(events["start_time"], utc=True).sort_values())
    waiting = []
    last = None
    for timestamp in result["timestamp"]:
        for event_start in starts:
            if event_start <= timestamp:
                last = event_start
            else:
                break
        waiting.append(9999.0 if last is None else (timestamp - last).total_seconds() / 60)
    result["waiting_time_since_previous_flare"] = waiting
    return result


FEATURE_COLUMNS = [
    "soft_xray_flux",
    "hard_xray_flux",
    "hardness_ratio",
    "soft_xray_derivative",
    "integrated_hard_xray_energy",
    "waiting_time_since_previous_flare",
    "rolling_mean",
    "rolling_variance",
    "rolling_slope",
    "rolling_volatility",
    "hard_rolling_mean",
    "hard_rolling_slope",
]

