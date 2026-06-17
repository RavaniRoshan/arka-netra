from __future__ import annotations

import json
import warnings
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from arkanetra.config import ROOT

SAMPLE_HEL1OS_DIR = ROOT / "data" / "raw" / "aditya_l1_sample"
DEFAULT_ENERGY_BAND = "25-100 keV"

ISRO_ARCHIVE_BASE = "https://isro.gov.in/aditya-l1/hel1os/data"
ISRO_ARCHIVE_URLS = {
    "l1": f"{ISRO_ARCHIVE_BASE}/hel1os_l1_flux.json",
    "archive": f"{ISRO_ARCHIVE_BASE}/hel1os_archive.json",
}


def load_hel1os_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"timestamp", "hard_xray_flux"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"HEL1OS file is missing required columns: {sorted(missing)}")
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    raw["hard_xray_flux"] = pd.to_numeric(raw["hard_xray_flux"], errors="coerce")
    raw = raw.sort_values("timestamp").reset_index(drop=True)
    raw = _add_quality_flags(raw)
    return raw


def download_hel1os_data(
    start: datetime | str | None = None,
    end: datetime | str | None = None,
    source: str = "archive",
    energy_band: str = DEFAULT_ENERGY_BAND,
) -> pd.DataFrame:
    if isinstance(start, str):
        start = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if isinstance(end, str):
        end = datetime.fromisoformat(end.replace("Z", "+00:00"))

    url = ISRO_ARCHIVE_URLS.get(source, ISRO_ARCHIVE_URLS["archive"])

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        warnings.warn(f"Could not fetch HEL1OS data from {url}: {e}. Returning empty DataFrame.")
        return pd.DataFrame(columns=["timestamp", "hard_xray_flux", "data_quality"])

    records = []
    for item in data.get("data", data if isinstance(data, list) else []):
        try:
            ts = datetime.fromisoformat(item["time_tag"].replace("Z", "+00:00"))
            flux = float(item.get("hard_xray_flux", item.get("flux", float("nan"))))
            records.append({"timestamp": ts, "hard_xray_flux": flux})
        except (KeyError, ValueError):
            continue

    if not records:
        return pd.DataFrame(columns=["timestamp", "hard_xray_flux", "data_quality"])

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    if start is not None:
        df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

    df = _add_quality_flags(df)
    df["hard_instrument"] = "HEL1OS"
    df["hard_energy_band"] = energy_band
    return df


def _add_quality_flags(frame: pd.DataFrame) -> pd.DataFrame:
    flags = []
    for _, row in frame.iterrows():
        flux = row["hard_xray_flux"]
        if pd.isna(flux) or flux < 0:
            flags.append("invalid")
        elif flux < 1e-12:
            flags.append("stale")
        elif flux > 1e-1:
            flags.append("suspect_high")
        else:
            flags.append("ok")
    frame["data_quality"] = flags
    return frame


def _resample_to_cadence(frame: pd.DataFrame, cadence_minutes: int) -> pd.DataFrame:
    numeric = frame.select_dtypes(include=["number"])
    numeric = numeric.set_index(frame["timestamp"])
    resampled = numeric.resample(f"{cadence_minutes}min").asfreq().interpolate(method="time").reset_index()
    resampled = resampled.rename(columns={"index": "timestamp"})
    resampled = _add_quality_flags(resampled)
    return resampled


def build_hel1os_replay(
    data_cfg: dict,
    time_start: pd.Timestamp,
    time_end: pd.Timestamp,
) -> pd.DataFrame | None:
    aditya_cfg = data_cfg.get("aditya_l1", {})
    hard_source = str(aditya_cfg.get("hard_source", "auto"))
    cadence_minutes = int(data_cfg.get("cadence_minutes", 5))
    energy_band = aditya_cfg.get("hel1os_energy_band", DEFAULT_ENERGY_BAND)

    hel1os_path: Path | None = None

    if hard_source.lower() in ("auto", "hel1os_sample", "hel1os"):
        sample_path = SAMPLE_HEL1OS_DIR / "hel1os_sample_20260101_20260102.csv"
        if sample_path.exists():
            hel1os_path = sample_path
    else:
        candidate = Path(hard_source)
        if candidate.exists():
            hel1os_path = candidate

    if hel1os_path is None or not hel1os_path.exists():
        import warnings
        warnings.warn("No HEL1OS data file found; hard X-ray will be zero-filled.")
        return None

    raw = load_hel1os_csv(hel1os_path)

    raw = raw[(raw["timestamp"] >= time_start) & (raw["timestamp"] <= time_end)].copy()
    if raw.empty:
        return None

    resampled = _resample_to_cadence(raw, cadence_minutes)
    resampled["hard_instrument"] = "HEL1OS"
    resampled["hard_energy_band"] = energy_band
    return resampled[["timestamp", "hard_xray_flux", "hard_instrument", "hard_energy_band"]].copy()