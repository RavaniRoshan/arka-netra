from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd

from arkanetra.config import ROOT

SWPC_XRAY_7DAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json"
SWPC_XRAY_1DAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"
SWPC_FLARES_7DAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"
SAMPLE_GOES_DIR = ROOT / "data" / "raw" / "goes_sample"
SAMPLE_GOES_PATH = SAMPLE_GOES_DIR / "goes_xrs_20170905_20170907.csv"
SAMPLE_NOAA_CATALOG = SAMPLE_GOES_DIR / "noaa_flare_catalog_20170906.csv"
DEFAULT_CADENCE_MINUTES = 5
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0


def load_goes_xrs(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"timestamp", "soft_xray_flux"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"GOES file is missing required columns: {sorted(missing)}")
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    raw["soft_xray_flux"] = pd.to_numeric(raw["soft_xray_flux"], errors="coerce")
    raw = raw.sort_values("timestamp").reset_index(drop=True)
    raw = _add_quality_flags(raw)
    return raw


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


def _fetch_swpc_json(url: str, timeout_seconds: int = 30) -> list[dict]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ArkaNetra/1.0.0"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 404:
                break
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            last_error = exc
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise last_error if last_error else RuntimeError("Unknown fetch error")


def download_goes_xrs(start: str, end: str, save_dir: str | Path | None = None) -> Path | None:
    if save_dir is None:
        save_dir = SAMPLE_GOES_DIR
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    fetch_error = None

    for url in (SWPC_XRAY_7DAY_URL, SWPC_XRAY_1DAY_URL):
        try:
            records = _fetch_swpc_json(url)
            break
        except Exception as exc:
            fetch_error = exc
            continue

    if not records:
        import warnings
        warnings.warn(f"Could not fetch GOES data from SWPC: {fetch_error}. Falling back to sample file.")
        return None

    rows = []
    for rec in records:
        energy = str(rec.get("energy", "")).strip()
        if energy and _is_short_channel(energy):
            continue
        time_tag = rec.get("time_tag")
        flux = rec.get("flux")
        if time_tag is None or flux is None:
            continue
        rows.append({
            "timestamp": time_tag,
            "soft_xray_flux": float(flux),
        })

    if not rows:
        import warnings
        warnings.warn("SWPC returned no GOES XRS long-channel data after parsing.")
        return None

    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    frame = frame[(frame["timestamp"] >= pd.Timestamp(start)) & (frame["timestamp"] <= pd.Timestamp(end))].copy()

    if frame.empty:
        import warnings
        warnings.warn(f"SWPC data had no rows in window [{start}, {end}].")
        return None

    save_path = save_dir / f"goes_xrs_{start[:10]}_{end[:10]}.csv"
    frame.to_csv(save_path, index=False)
    return save_path


def _is_short_channel(energy: str) -> bool:
    energy_lower = energy.lower().replace(" ", "")
    return energy_lower in ("0.5-4.0a", "0.5-4a", "0.05-0.4nm", "short")


def _resample_to_cadence(frame: pd.DataFrame, cadence_minutes: int) -> pd.DataFrame:
    numeric = frame.select_dtypes(include=["number"])
    meta = frame.select_dtypes(exclude=["number"]).iloc[:0]
    numeric = numeric.set_index(frame["timestamp"])
    resampled_num = numeric.resample(f"{cadence_minutes}min").asfreq().interpolate(method="time").reset_index()
    resampled_num = resampled_num.rename(columns={"index": "timestamp"})
    resampled_num = _add_quality_flags(resampled_num)
    return resampled_num


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


def build_goes_replay(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_cfg = config["data"]
    cadence_minutes = int(data_cfg.get("cadence_minutes", DEFAULT_CADENCE_MINUTES))
    source = str(data_cfg.get("goes_source", "auto"))
    window_hours = int(data_cfg.get("goes_event_window_hours", 48))

    goes_path: Path | None = None

    if source.lower() in ("auto", "live"):
        if SAMPLE_GOES_PATH.exists():
            goes_path = SAMPLE_GOES_PATH
        downloaded = download_goes_xrs(
            (pd.Timestamp.now("UTC") - pd.Timedelta(hours=window_hours)).isoformat(),
            pd.Timestamp.now("UTC").isoformat(),
        )
        if downloaded is not None and downloaded.exists():
            goes_path = downloaded
    elif source.lower() == "sample":
        goes_path = SAMPLE_GOES_PATH
    else:
        candidate = Path(source)
        if candidate.exists():
            goes_path = candidate

    soft_source_label = "GOES_XRS_LIVE"
    if source.lower() == "sample":
        soft_source_label = "GOES_XRS_SAMPLE"
    elif goes_path is None or not goes_path.exists():
        import warnings
        warnings.warn("No GOES data file found; falling back to built-in sample.")
        goes_path = SAMPLE_GOES_PATH
        soft_source_label = "GOES_XRS_SAMPLE"

    raw = load_goes_xrs(goes_path)
    resampled = _resample_to_cadence(raw, cadence_minutes)

    catalog_path = source.replace(".csv", "_catalog.csv") if source.lower() not in ("auto", "live", "sample") else SAMPLE_NOAA_CATALOG
    if not Path(catalog_path).exists():
        catalog_path = SAMPLE_NOAA_CATALOG

    if catalog_path.exists():
        events = pd.read_csv(catalog_path, parse_dates=["start_time", "peak_time"])
        for col in ["start_time", "peak_time"]:
            events[col] = pd.to_datetime(events[col], utc=True)
    else:
        events = pd.DataFrame(columns=["event_id", "start_time", "peak_time", "flare_class", "severity", "scenario"])

    if "end_time" in events.columns and "scenario" not in events.columns:
        events["scenario"] = events["flare_class"].apply(_scenario_for_class)
    if "severity" not in events.columns:
        events["severity"] = events["flare_class"].apply(_flare_class_to_severity)

    window_start = resampled["timestamp"].min()
    window_end = resampled["timestamp"].max()
    events = events[
        (events["peak_time"] >= window_start) & (events["peak_time"] <= window_end)
    ].copy().reset_index(drop=True)

    hard_frame = _load_hard_xray(data_cfg, window_start, window_end)

    if hard_frame is not None and not hard_frame.empty:
        resampled = _merge_soft_hard(resampled, hard_frame)
        hard_source_str = str(hard_frame.get("hard_instrument", hard_frame.get("hard_energy_band", "RHESSI_REAL")).iloc[0]) if "hard_instrument" in hard_frame.columns else "RHESSI_REAL"
    else:
        resampled["hard_xray_flux"] = np.zeros(len(resampled), dtype=np.float64)
        hard_source_str = "NONE_PHASE2_FALLBACK"

    frame = pd.DataFrame({
        "timestamp": resampled["timestamp"],
        "soft_xray_flux": resampled["soft_xray_flux"].values,
        "hard_xray_flux": resampled["hard_xray_flux"].values,
        "data_quality": resampled["data_quality"].values,
        "soft_source": soft_source_label,
        "hard_source": hard_source_str,
    })

    return frame, events


def _load_hard_xray(data_cfg: dict, window_start: pd.Timestamp, window_end: pd.Timestamp) -> pd.DataFrame | None:
    hard_source = data_cfg.get("hard_source", "auto")
    if hard_source == "none":
        return None
    try:
        from arkanetra.data.hard_xray_proxy import build_hard_xray_data
        return build_hard_xray_data(data_cfg, window_start, window_end)
    except Exception as exc:
        import warnings
        warnings.warn(f"Could not load hard X-ray data: {exc}. Hard X-ray will be zero-filled.")
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
