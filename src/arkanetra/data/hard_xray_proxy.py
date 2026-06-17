from __future__ import annotations

import re
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd

from arkanetra.config import ROOT
from arkanetra.data.download import fetch_binary

RHESSI_BASE_URL = "https://hesperia.gsfc.nasa.gov/hessidata/metadata/catalog/"
FERMI_GBM_BASE_URL = "https://heasarc.gsfc.nasa.gov/FTP/fermi/data/gbm/daily"
SAMPLE_DIR = ROOT / "data" / "raw" / "goes_sample"
SAMPLE_RHESSI_PATH = SAMPLE_DIR / "rhessi_hard_xray_20170905_20170907.csv"
DEFAULT_ENERGY_BAND = "25-100 keV"
FERMI_DEFAULT_CHANNEL = "n5"


def load_rhessi_from_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"timestamp", "hard_xray_flux"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"RHESSI CSV file is missing required columns: {sorted(missing)}")
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    raw["hard_xray_flux"] = pd.to_numeric(raw["hard_xray_flux"], errors="coerce")
    raw = raw.sort_values("timestamp").reset_index(drop=True)
    raw = _add_quality_flags(raw)
    return raw


def load_rhessi_obs_summary(path: str | Path, energy_band: str = DEFAULT_ENERGY_BAND) -> pd.DataFrame:
    from astropy.io import fits

    hdul = fits.open(path)
    table = None
    for hdu in hdul:
        if isinstance(hdu, fits.BinTableHDU) or isinstance(hdu, fits.TableHDU):
            table = hdu
            break

    if table is None:
        hdul.close()
        raise ValueError(f"No binary table found in {path}")

    data = table.data
    if "TIME" not in data.columns.names:
        hdul.close()
        raise ValueError(f"No TIME column in {path}")

    time_vals = data["TIME"]
    ref = pd.Timestamp("1979-01-01T00:00:00", tz="UTC")
    timestamps = pd.to_datetime(ref.value + time_vals.astype(np.float64) * 1e9)

    target_lo, target_hi = _parse_band_range(energy_band)
    hard = np.zeros(len(time_vals), dtype=np.float64)
    found = False
    for col in data.columns:
        col_name = str(col.name).strip()
        band_range = _parse_energy_range(col_name)
        if band_range is None:
            continue
        lo, hi = band_range
        if hi < target_lo or lo > target_hi:
            continue
        vals = data[col.name].astype(np.float64)
        vals = np.nan_to_num(vals, nan=0.0)
        hard += vals
        found = True

    hdul.close()

    if not found:
        import warnings
        warnings.warn(f"No energy bands matched '{energy_band}' in {path}. Using all keV columns.")
        for col in data.columns:
            col_name = str(col.name).strip()
            if "keV" in col_name.lower() or "kev" in col_name.lower():
                vals = data[col.name].astype(np.float64)
                vals = np.nan_to_num(vals, nan=0.0)
                hard += vals

    frame = pd.DataFrame({"timestamp": timestamps, "hard_xray_flux": hard})
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    frame = _add_quality_flags(frame)
    return frame


def _parse_energy_range(name: str) -> tuple[float, float] | None:
    match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*[kK][eE]?[vV]?", name)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None


def _parse_band_range(target: str) -> tuple[float, float]:
    match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*[kK][eE]?[vV]?", target)
    if match:
        return float(match.group(1)), float(match.group(2))
    return 25.0, 100.0


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


def download_rhessi_obs_summary(start: str, end: str, save_dir: str | Path | None = None) -> list[Path] | None:
    if save_dir is None:
        save_dir = SAMPLE_DIR
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)
    paths = []

    for day in pd.date_range(start_dt.date(), end_dt.date(), freq="D"):
        year = day.year
        month = day.month
        day_num = day.day
        for seq in (58, 59, 60):
            url = f"{RHESSI_BASE_URL}hsi_obssumm_{year:04d}{month:02d}{day_num:02d}_{seq:03d}.fits"
            try:
                data = fetch_binary(url, timeout_seconds=30)
                filename = f"hsi_obssumm_{year:04d}{month:02d}{day_num:02d}_{seq:03d}.fits"
                filepath = save_dir / filename
                filepath.write_bytes(data)
                paths.append(filepath)
            except urllib.error.HTTPError:
                continue
            except (urllib.error.URLError, OSError):
                break

    if not paths:
        import warnings
        warnings.warn(f"No RHESSI observing summary files found for {start} to {end}.")
        return None

    return paths


def download_fermi_gbm_data(
    start: str,
    end: str,
    save_dir: str | Path | None = None,
    detector: str = FERMI_DEFAULT_CHANNEL,
) -> list[Path]:
    if save_dir is None:
        save_dir = SAMPLE_DIR
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)
    paths = []

    for day in pd.date_range(start_dt.date(), end_dt.date(), freq="D"):
        year = day.year
        month = day.month
        day_num = day.day
        url = f"{FERMI_GBM_BASE_URL}/{year:04d}/{month:02d}/{day_num:02d}/current/"
        for prefix in ("glg_cspec", "glg_ctime"):
            file_url = f"{url}{prefix}_{detector}_{year:04d}{month:02d}{day_num:02d}_v00.fit"
            try:
                data = fetch_binary(file_url, timeout_seconds=60)
                filename = f"{prefix}_{detector}_{year:04d}{month:02d}{day_num:02d}_v00.fit"
                filepath = save_dir / filename
                filepath.write_bytes(data)
                paths.append(filepath)
            except (urllib.error.HTTPError, urllib.error.URLError, OSError):
                continue

    if not paths:
        import warnings
        warnings.warn(f"No Fermi GBM data found for {start} to {end}.")

    return paths


def build_hard_xray_data(
    data_cfg: dict,
    time_start: pd.Timestamp,
    time_end: pd.Timestamp,
) -> pd.DataFrame | None:
    hard_source = data_cfg.get("hard_source", "auto")
    cadence_minutes = int(data_cfg.get("cadence_minutes", 5))
    energy_band = data_cfg.get("rhessi_energy_band", DEFAULT_ENERGY_BAND)

    if hard_source == "none":
        return None

    raw: pd.DataFrame | None = None
    source_label = "NONE"

    if hard_source in ("auto", "rhessi", "fermi"):
        if SAMPLE_RHESSI_PATH.exists():
            raw = load_rhessi_from_csv(SAMPLE_RHESSI_PATH)
            source_label = "RHESSI_SAMPLE"

    if raw is None and hard_source in ("auto", "fermi"):
        try:
            gbm_files = download_fermi_gbm_data(
                time_start.isoformat(), time_end.isoformat(),
            )
            if gbm_files:
                from astropy.io import fits
                for gf in gbm_files:
                    try:
                        with fits.open(gf) as hdul:
                            raw = _parse_fermi_fits(hdul)
                            source_label = "FERMI_GBM_LIVE"
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    if raw is None or raw.empty:
        import warnings
        warnings.warn("No hard X-ray data file found; hard X-ray will be zero-filled.")
        return None

    # Preserve provenance if available
    if "hard_instrument" in raw.columns:
        source_label = str(raw["hard_instrument"].dropna().iloc[0])
    elif "hard_energy_band" in raw.columns:
        source_label = str(raw["hard_energy_band"].dropna().iloc[0])

    raw = raw[(raw["timestamp"] >= time_start) & (raw["timestamp"] <= time_end)].copy()
    if raw.empty:
        return None

    resampled = _resample_to_cadence(raw, cadence_minutes)
    resampled["hard_source"] = source_label
    return resampled[["timestamp", "hard_xray_flux", "hard_source"]].copy()


def _parse_fermi_fits(hdul, energy_lo: float = 25.0, energy_hi: float = 300.0) -> pd.DataFrame:
    from astropy.io import fits
    table = None
    for hdu in hdul:
        if isinstance(hdu, fits.BinTableHDU):
            table = hdu
            break
    if table is None:
        raise ValueError("No BinTableHDU found in Fermi FITS file")

    data = table.data
    colnames = [str(c).strip() for c in data.columns.names]

    time_col = next((c for c in colnames if c.upper() in ("TIME", "SCLK")), None)
    if time_col is None:
        raise ValueError("No TIME column in Fermi FITS file")

    time_vals = data[time_col].astype(np.float64)
    ref = pd.Timestamp("2001-01-01T00:00:00", tz="UTC")
    timestamps = pd.to_datetime(ref.value + time_vals * 1e9)

    try:
        ebounds = hdul["EBOUNDS"].data
        chan_lo = ebounds["E_MIN"].astype(np.float64)
        chan_hi = ebounds["E_MAX"].astype(np.float64)
    except (KeyError, IndexError):
        try:
            ch_indices = [i for i, c in enumerate(colnames) if c.upper().startswith("CH")]
            if not ch_indices:
                rate_col = next((c for c in colnames if c.upper().startswith("RATE")), None)
                if rate_col:
                    rates = data[rate_col].astype(np.float64)
                    return pd.DataFrame({
                        "timestamp": timestamps,
                        "hard_xray_flux": np.nanmean(rates, axis=1) if rates.ndim == 2 else rates,
                    })
            return pd.DataFrame({
                "timestamp": timestamps,
                "hard_xray_flux": np.zeros(len(timestamps), dtype=np.float64),
            })
        except Exception:
            return pd.DataFrame({
                "timestamp": timestamps,
                "hard_xray_flux": np.zeros(len(timestamps), dtype=np.float64),
            })

    rate_col_candidates = [c for c in colnames if c.upper().startswith("RATE") or c.upper().startswith("COUNTS")]
    if not rate_col_candidates:
        return pd.DataFrame({
            "timestamp": timestamps,
            "hard_xray_flux": np.zeros(len(timestamps), dtype=np.float64),
        })

    rates = data[rate_col_candidates[0]].astype(np.float64)
    nchannels = rates.shape[1] if rates.ndim == 2 else len(chan_lo)
    chan_mask = (chan_lo[:nchannels] >= energy_lo) & (chan_hi[:nchannels] <= energy_hi)
    if not chan_mask.any():
        chan_mask = np.ones(nchannels, dtype=bool)

    if rates.ndim == 2:
        hard_flux = rates[:, chan_mask].sum(axis=1)
    else:
        hard_flux = rates

    frame = pd.DataFrame({"timestamp": timestamps, "hard_xray_flux": hard_flux})
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    return frame


def load_fermi_gbm_from_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"timestamp", "hard_xray_flux"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"Fermi GBM CSV is missing required columns: {sorted(missing)}")
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True)
    raw["hard_xray_flux"] = pd.to_numeric(raw["hard_xray_flux"], errors="coerce")
    raw = raw.sort_values("timestamp").reset_index(drop=True)
    raw = _add_quality_flags(raw)
    return raw