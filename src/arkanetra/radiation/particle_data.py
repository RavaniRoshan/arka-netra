from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class ParticleData:
    timestamp: pd.DatetimeIndex
    proton_flux: pd.Series
    electron_flux: pd.Series
    quality_flag: str = "nominal"
    source: str = "unknown"
    metadata: dict = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame({"proton_flux": self.proton_flux, "electron_flux": self.electron_flux})
        df["quality_flag"] = self.quality_flag
        df["source"] = self.source
        return df

    @property
    def is_available(self) -> bool:
        return len(self.timestamp) > 0

    def is_recent(self, max_age_minutes: int = 60) -> bool:
        if not self.is_available:
            return False
        age = datetime.now(timezone.utc) - self.timestamp[-1].to_pydatetime()
        return age.total_seconds() < max_age_minutes * 60


def fetch_goes_particle_data(
    start: datetime | str | None = None,
    end: datetime | str | None = None,
    source: str = "swpc",
    sample_file: Path | None = None,
) -> ParticleData:
    if isinstance(start, str):
        start = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if isinstance(end, str):
        end = datetime.fromisoformat(end.replace("Z", "+00:00"))

    if start is None:
        start = datetime.now(timezone.utc) - timedelta(hours=6)
    if end is None:
        end = datetime.now(timezone.utc)

    if sample_file is None:
        sample_file = Path(__file__).parent.parent.parent.parent / "data" / "goes_particle_sample.csv"

    if sample_file and sample_file.exists():
        try:
            return _load_particle_csv(sample_file, start, end)
        except Exception as e:
            warnings.warn(f"Could not load particle sample file: {e}. Returning empty ParticleData.")

    return _fetch_from_swpc(start, end, source)


def _load_particle_csv(path: Path, start: datetime, end: datetime) -> ParticleData:
    try:
        df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
        df = df[(df.index >= start) & (df.index <= end)]
        if df.empty:
            return ParticleData(
                timestamp=pd.DatetimeIndex([]),
                proton_flux=pd.Series([], dtype=float),
                electron_flux=pd.Series([], dtype=float),
                quality_flag="no_data",
                source="sample_file",
            )
        return ParticleData(
            timestamp=df.index,
            proton_flux=df["proton_flux"] if "proton_flux" in df.columns else pd.Series(np.nan, index=df.index),
            electron_flux=df["electron_flux"] if "electron_flux" in df.columns else pd.Series(np.nan, index=df.index),
            quality_flag=str(df.get("quality_flag", ["nominal"] * len(df)).iloc[0]),
            source="sample_file",
            metadata={"file": str(path), "rows": len(df)},
        )
    except Exception as e:
        warnings.warn(f"Error loading particle CSV: {e}")
        return ParticleData(
            timestamp=pd.DatetimeIndex([]),
            proton_flux=pd.Series([], dtype=float),
            electron_flux=pd.Series([], dtype=float),
            quality_flag="load_error",
        )


def _fetch_from_swpc(start: datetime, end: datetime, source: str) -> ParticleData:
    import urllib.request

    base_url = "https://services.swpc.noaa.gov/json/goes particle"
    urls = {
        "primary": f"{base_url}/primary proton 5-minute.json",
        "secondary": f"{base_url}/secondary proton 5-minute.json",
    }

    for label, url in urls.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            if data:
                break
        except Exception as e:
            warnings.warn(f"Could not fetch GOES particle data from {url}: {e}")
            continue

    if not data:
        return ParticleData(
            timestamp=pd.DatetimeIndex([]),
            proton_flux=pd.Series([], dtype=float),
            electron_flux=pd.Series([], dtype=float),
            quality_flag="fetch_failed",
            source="swpc",
        )

    records = []
    for item in data:
        try:
            ts = datetime.fromisoformat(item["time_tag"].replace("Z", "+00:00"))
            records.append({"timestamp": ts, "proton_flux": item.get("proton_flux", np.nan), "electron_flux": np.nan})
        except (KeyError, ValueError):
            continue

    if not records:
        return ParticleData(
            timestamp=pd.DatetimeIndex([]),
            proton_flux=pd.Series([], dtype=float),
            electron_flux=pd.Series([], dtype=float),
            quality_flag="parse_error",
            source="swpc",
        )

    df = pd.DataFrame(records).set_index("timestamp")
    df = df[(df.index >= start) & (df.index <= end)]
    return ParticleData(
        timestamp=df.index,
        proton_flux=df["proton_flux"],
        electron_flux=df["electron_flux"],
        quality_flag="nominal",
        source=f"swpc_{label}" if "label" in dir() else "swpc",
    )


def get_latest_particle_reading(particle_data: ParticleData) -> dict | None:
    if not particle_data.is_available:
        return None
    latest = particle_data.timestamp[-1]
    return {
        "timestamp": latest.isoformat(),
        "proton_flux": float(particle_data.proton_flux.iloc[-1]) if not particle_data.proton_flux.empty else None,
        "electron_flux": float(particle_data.electron_flux.iloc[-1]) if not particle_data.electron_flux.empty else None,
        "quality_flag": particle_data.quality_flag,
        "is_recent": particle_data.is_recent(),
    }