import pandas as pd
import numpy as np

start_time = "2017-09-05T00:00:00Z"
end_time = "2017-09-07T00:00:00Z"
periods = 48
cadence_minutes = 5

timestamps = pd.date_range(start_time, end_time, periods=periods, freq=f"{cadence_minutes}min", tz="UTC")

base_flux = 1.2e-7
noise = np.random.normal(0, 3.0e-9, periods)
flux = base_flux + noise

peak_idx = 26
severity = 5.0

for i in range(max(0, peak_idx - 20), min(periods, peak_idx + 30)):
    minutes_from_peak = (i - peak_idx) * cadence_minutes
    soft_thermal = np.exp(-0.5 * ((minutes_from_peak) / 52) ** 2)
    precursor = np.exp(-0.5 * ((minutes_from_peak + 70) / 44) ** 2)
    flux[i] += (severity * 7.5e-8 * soft_thermal) + (severity * 8.0e-9 * precursor)

df = pd.DataFrame({
    "timestamp": timestamps,
    "soft_xray_flux": np.clip(flux, 1e-10, None),
    "hard_xray_flux": 0.0,
    "soft_source": "GOES_XRS_SAMPLE",
    "hard_source": "NONE_PHASE1",
    "missing": False,
    "zero_flux": False,
    "stale": False,
    "invalid": False,
})

output_path = "data/raw/goes_sample/goes_xrs_20170905_20170907.csv"
df.to_csv(output_path, index=False)
print(f"Created sample GOES data with {len(df)} rows")
print(f"Timestamp range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Flux range: {df['soft_xray_flux'].min():.2e} to {df['soft_xray_flux'].max():.2e}")
print(f"Saved to: {output_path}")
