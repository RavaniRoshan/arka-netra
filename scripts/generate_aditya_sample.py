"""Generate Aditya-L1 sample data for Phase 3."""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "data" / "raw" / "aditya_l1_sample"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

BASE_TIME = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
N_POINTS = 576
CADENCE_MINUTES = 5

timestamps = [BASE_TIME + pd.Timedelta(minutes=i*CADENCE_MINUTES) for i in range(N_POINTS)]

def make_goes_like_soft(timestamps, base_flux=1e-7, flare_peak=1e-4, flare_center_pct=0.5, flare_width_pct=0.05):
    flux = np.full(len(timestamps), base_flux)
    center = int(len(timestamps) * flare_center_pct)
    width = int(len(timestamps) * flare_width_pct)
    for i in range(center - width, center + width):
        if 0 <= i < len(flux):
            t = (i - (center - width)) / (2 * width)
            envelope = np.sin(t * np.pi) ** 2
            flux[i] = base_flux + (flare_peak - base_flux) * envelope
    noise = np.random.randn(len(flux)) * base_flux * 0.1
    return np.maximum(flux + noise, 1e-12)

def make_rhessi_like_hard(timestamps, base_flux=1e-9, flare_peak=5e-6, flare_center_pct=0.5, flare_width_pct=0.03):
    flux = np.full(len(timestamps), base_flux)
    center = int(len(timestamps) * flare_center_pct)
    width = int(len(timestamps) * flare_width_pct)
    for i in range(center - width, center + width):
        if 0 <= i < len(flux):
            t = (i - (center - width)) / (2 * width)
            envelope = np.sin(t * np.pi) ** 2
            flux[i] = base_flux + (flare_peak - base_flux) * envelope
    noise = np.random.randn(len(flux)) * base_flux * 0.15
    return np.maximum(flux + noise, 1e-14)

np.random.seed(42)
solexs_flux = make_goes_like_soft(timestamps, base_flux=1e-7, flare_peak=2e-4, flare_center_pct=0.5, flare_width_pct=0.04)
np.random.seed(43)
hel1os_flux = make_rhessi_like_hard(timestamps, base_flux=1e-9, flare_peak=8e-6, flare_center_pct=0.5, flare_width_pct=0.03)

solexs_df = pd.DataFrame({
    "timestamp": timestamps,
    "soft_xray_flux": solexs_flux,
    "energy_band": "1-8 keV",
    "solexs_channel": "SXS",
    "exposure_time": 1.0,
    "background_flag": False,
    "payload_version": "1.0.0",
})
solexs_df.to_csv(SAMPLE_DIR / "solexs_sample_20260101_20260102.csv", index=False)
print(f"Created SoLEXS sample: {len(solexs_df)} rows")

hel1os_df = pd.DataFrame({
    "timestamp": timestamps,
    "hard_xray_flux": hel1os_flux,
    "energy_band": "25-100 keV",
    "hel1os_channel": "HXR-3",
    "background_subtracted": True,
    "background_level": 1e-9,
    "exposure_time": 1.0,
    "payload_version": "1.0.0",
})
hel1os_df.to_csv(SAMPLE_DIR / "hel1os_sample_20260101_20260102.csv", index=False)
print(f"Created HEL1OS sample: {len(hel1os_df)} rows")

flare_catalog = pd.DataFrame({
    "event_id": ["SOL-X-001", "SOL-M-002", "SOL-C-003"],
    "start_time": [
        BASE_TIME + pd.Timedelta(hours=23),
        BASE_TIME + pd.Timedelta(hours=24),
        BASE_TIME + pd.Timedelta(hours=25),
    ],
    "peak_time": [
        BASE_TIME + pd.Timedelta(hours=24),
        BASE_TIME + pd.Timedelta(hours=24) + pd.Timedelta(minutes=15),
        BASE_TIME + pd.Timedelta(hours=25) + pd.Timedelta(minutes=30),
    ],
    "end_time": [
        BASE_TIME + pd.Timedelta(hours=25),
        BASE_TIME + pd.Timedelta(hours=25),
        BASE_TIME + pd.Timedelta(hours=26),
    ],
    "flare_class": ["X1.2", "M5.4", "C2.8"],
    "severity": [5, 4, 3],
    "scenario": ["X-class critical replay", "M-class warning replay", "C-class watch replay"],
})
flare_catalog.to_csv(SAMPLE_DIR / "noaa_flare_catalog_solexs.csv", index=False)
print(f"Created flare catalog: {len(flare_catalog)} events")
print("Done generating Aditya-L1 sample data.")