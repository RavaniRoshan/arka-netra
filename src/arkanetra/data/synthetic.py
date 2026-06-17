from __future__ import annotations

import numpy as np
import pandas as pd


def build_synthetic_proxy_data(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create deterministic GOES/RHESSI-like replay data for an immediately runnable MVP."""
    data_cfg = config["data"]
    rng = np.random.default_rng(int(data_cfg["random_seed"]))
    timestamps = pd.date_range(
        data_cfg["start"],
        periods=int(data_cfg["periods"]),
        freq=f"{int(data_cfg['cadence_minutes'])}min",
        tz="UTC",
    )
    minutes = np.arange(len(timestamps)) * int(data_cfg["cadence_minutes"])

    soft = 1.2e-7 + rng.normal(0, 3.0e-9, len(timestamps))
    hard = 2.8e-8 + rng.normal(0, 2.5e-9, len(timestamps))
    n = len(timestamps)

    def at_fraction(fraction: float) -> pd.Timestamp:
        index = min(max(int(n * fraction), 1), n - 2)
        return timestamps[index]

    def peak_after(start: pd.Timestamp, steps: int) -> pd.Timestamp:
        index = timestamps.get_indexer([start])[0]
        return timestamps[min(index + steps, n - 1)]

    events = pd.DataFrame(
        [
            {
                "event_id": "SOL-C-001",
                "start_time": at_fraction(0.21),
                "peak_time": peak_after(at_fraction(0.21), 16),
                "flare_class": "C6.1",
                "severity": 3,
                "scenario": "C-class watch replay",
            },
            {
                "event_id": "SOL-M-002",
                "start_time": at_fraction(0.49),
                "peak_time": peak_after(at_fraction(0.49), 18),
                "flare_class": "M2.8",
                "severity": 4,
                "scenario": "M-class warning replay",
            },
            {
                "event_id": "SOL-X-003",
                "start_time": at_fraction(0.75),
                "peak_time": peak_after(at_fraction(0.75), 18),
                "flare_class": "X1.3",
                "severity": 5,
                "scenario": "X-class critical replay",
            },
        ]
    )

    for _, event in events.iterrows():
        peak_minute = (event["peak_time"] - timestamps[0]).total_seconds() / 60
        start_minute = (event["start_time"] - timestamps[0]).total_seconds() / 60
        severity = float(event["severity"])
        hard_impulse = np.exp(-0.5 * ((minutes - (start_minute + 12)) / 18) ** 2)
        soft_thermal = np.exp(-0.5 * ((minutes - peak_minute) / 52) ** 2)
        precursor = np.exp(-0.5 * ((minutes - (start_minute - 70)) / 44) ** 2)
        hard += (severity * 2.1e-8 * hard_impulse) + (severity * 5.5e-9 * precursor)
        soft += (severity * 7.5e-8 * soft_thermal) + (severity * 8.0e-9 * precursor)

    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "soft_xray_flux": np.clip(soft, 1e-10, None),
            "hard_xray_flux": np.clip(hard, 1e-10, None),
            "soft_source": "GOES_XRS_SYNTHETIC",
            "hard_source": "RHESSI_PROXY_SYNTHETIC",
        }
    )
    return frame, events
