from __future__ import annotations

import json
import warnings
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from solaris.config import ROOT

SAMPLE_SOLEXS_DIR = ROOT / "data" / "raw" / "aditya_l1_sample"
DEFAULT_CADENCE_MINUTES = 5

ISRO_ARCHIVE_BASE = "https://isro.gov.in/aditya-l1/solexs/data"
ISRO_ARCHIVE_URLS = {
    "l1": f"{ISRO_ARCHIVE_BASE}/solexs_l1_flux.json",
    "archive": f"{ISRO_ARCHIVE_BASE}/solexs_archive.json",
}


def load_solexs_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"timestamp", "soft_xray_flux"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"SoLEXS file is missing required columns: {sorted(missing)}")
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    raw["soft_xray_flux"] = pd.to_numeric(raw["soft_xray_flux"], errors="coerce")
    raw = raw.sort_values("timestamp").reset_index(drop=True)
    raw = _add_quality_flags(raw)
    return raw


def download_solexs_data(
    start: datetime | str | None = None,
    end: datetime | str | None = None,
    source: str = "archive",
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
        warnings.warn(f"Could not fetch SoLEXS data from {url}: {e}. Returning empty DataFrame.")
        return pd.DataFrame(columns=["timestamp", "soft_xray_flux", "data_quality"])

    records = []
    for item in data.get("data", data if isinstance(data, list) else []):
        try:
            ts = datetime.fromisoformat(item["time_tag"].replace("Z", "+00:00"))
            flux = float(item.get("soft_xray_flux", item.get("flux", float("nan"))))
            records.append({"timestamp": ts, "soft_xray_flux": flux})
        except (KeyError, ValueError):
            continue

    if not records:
        return pd.DataFrame(columns=["timestamp", "soft_xray_flux", "data_quality"])

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    if start is not None:
        df = df[df["timestamp"] >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        df = df[df["timestamp"] <= pd.Timestamp(end, tz="UTC")]

    df = _add_quality_flags(df)
    return df


def _add_quality_flags(frame: pd.DataFrame) -> pd.DataFrame:
    flags = []
    for _, row in frame.iterrows():
        flux = row["soft_xray_flux"]
        if pd.isna(flux) or flux <= 0:
            flags.append("invalid")
        elif flux < 1e-10:
            flags.append("stale")
        elif flux > 1e-2:
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


def build_solexs_replay(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_cfg = config.get("data", {})
    aditya_cfg = data_cfg.get("aditya_l1", {})
    cadence_minutes = int(data_cfg.get("cadence_minutes", DEFAULT_CADENCE_MINUTES))
    soft_source = str(aditya_cfg.get("soft_source", "auto"))

    solexs_path: Path | None = None

    if soft_source.lower() == "auto" or soft_source.lower() == "solexs_sample":
        sample_path = SAMPLE_SOLEXS_DIR / "solexs_sample_20260101_20260102.csv"
        if sample_path.exists():
            solexs_path = sample_path
    else:
        candidate = Path(soft_source)
        if candidate.exists():
            solexs_path = candidate

    if solexs_path is None or not solexs_path.exists():
        import warnings
        warnings.warn("No SoLEXS data file found; soft X-ray will be zero-filled.")
        empty_frame = pd.DataFrame(columns=["timestamp", "soft_xray_flux", "data_quality"])
        empty_frame["timestamp"] = pd.to_datetime(empty_frame["timestamp"], utc=True)
        return empty_frame, pd.DataFrame(columns=["event_id", "start_time", "peak_time", "flare_class", "severity", "scenario"])

    raw = load_solexs_csv(solexs_path)
    resampled = _resample_to_cadence(raw, cadence_minutes)

    window_start = resampled["timestamp"].min()
    window_end = resampled["timestamp"].max()

    events = _build_solexs_events(window_start, window_end)

    hard_frame = _load_hel1os(data_cfg, window_start, window_end)

    if hard_frame is not None and not hard_frame.empty:
        resampled = _merge_soft_hard(resampled, hard_frame)
        hard_source_str = str(hard_frame["hard_instrument"].iloc[0]) if "hard_instrument" in hard_frame.columns else "HEL1OS"
    else:
        resampled["hard_xray_flux"] = np.zeros(len(resampled), dtype=np.float64)
        hard_source_str = "HEL1OS_NONE"

    frame = pd.DataFrame({
        "timestamp": resampled["timestamp"],
        "soft_xray_flux": resampled["soft_xray_flux"].values,
        "hard_xray_flux": resampled["hard_xray_flux"].values,
        "data_quality": resampled["data_quality"].values,
        "soft_source": "SOLEXS",
        "hard_source": hard_source_str,
    })

    return frame, events


def _build_solexs_events(window_start: pd.Timestamp, window_end: pd.Timestamp) -> pd.DataFrame:
    solexs_catalog_path = SAMPLE_SOLEXS_DIR / "noaa_flare_catalog_solexs.csv"
    if solexs_catalog_path.exists():
        events = pd.read_csv(solexs_catalog_path, parse_dates=["start_time", "peak_time"])
        for col in ["start_time", "peak_time"]:
            events[col] = pd.to_datetime(events[col], utc=True)
    else:
        events = pd.DataFrame(columns=["event_id", "start_time", "peak_time", "flare_class", "severity", "scenario"])

    if "end_time" in events.columns and "scenario" not in events.columns:
        events["scenario"] = events["flare_class"].apply(_scenario_for_class)
    if "severity" not in events.columns:
        events["severity"] = events["flare_class"].apply(_flare_class_to_severity)

    events = events[
        (events["peak_time"] >= window_start) & (events["peak_time"] <= window_end)
    ].copy().reset_index(drop=True)

    return events


def _load_hel1os(data_cfg: dict, window_start: pd.Timestamp, window_end: pd.Timestamp) -> pd.DataFrame | None:
    hard_source = data_cfg.get("aditya_l1", {}).get("hard_source", "auto")
    if hard_source == "none":
        return None
    try:
        from solaris.data.hel1os import build_hel1os_replay
        return build_hel1os_replay(data_cfg, window_start, window_end)
    except Exception:
        import warnings
        warnings.warn("Could not load HEL1OS data. Hard X-ray will be zero-filled.")
        return None


def _merge_soft_hard(soft: pd.DataFrame, hard: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge_asof(
        soft[["timestamp", "soft_xray_flux", "data_quality"]].sort_values("timestamp"),
        hard[["timestamp", "hard_xray_flux"]].sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("5min"),
    )
    merged["hard_xray_flux"] = merged["hard_xray_flux"].fillna(0.0)
    return merged


def _flare_class_to_severity(flare_class: str) -> int:
    letter = str(flare_class).upper()[:1]
    return {"A": 1, "B": 2, "C": 3, "M": 4, "X": 5}.get(letter, 0)


def _scenario_for_class(flare_class: str) -> str:
    letter = str(flare_class).upper()[:1]
    if letter == "X":
        return "X-class critical replay"
    if letter == "M":
        return "M-class warning replay"
    if letter == "C":
        return "C-class watch replay"
    return "Background archive"