from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd


@dataclass
class CrossCalibrationResult:
    instrument_a: str
    instrument_b: str
    correlation_coefficient: float
    gain_factor: float
    offset: float
    rms_residual: float
    n_overlapping_points: int
    time_range_start: str
    time_range_end: str
    is_experimental: bool = True
    disclaimer: str = (
        "Cross-calibration results are derived from limited overlapping data. "
        "Not validated against official calibration standards."
    )
    notes: list[str] = field(default_factory=list)
    timestamp: str | None = None

    def to_dict(self) -> dict:
        return {
            "instrument_a": self.instrument_a,
            "instrument_b": self.instrument_b,
            "correlation_coefficient": round(self.correlation_coefficient, 4),
            "gain_factor": round(self.gain_factor, 6),
            "offset": round(self.offset, 6),
            "rms_residual": round(self.rms_residual, 6),
            "n_overlapping_points": self.n_overlapping_points,
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
            "is_experimental": self.is_experimental,
            "disclaimer": self.disclaimer,
            "notes": self.notes,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
        }


def cross_calibrate_solexs_vs_goes(
    solexs_df: pd.DataFrame,
    goes_df: pd.DataFrame,
    tolerance_minutes: int = 5,
) -> CrossCalibrationResult:
    solexs = solexs_df[["timestamp", "soft_xray_flux"]].copy()
    solexs = solexs.rename(columns={"soft_xray_flux": "solexs_flux"})
    solexs["timestamp"] = pd.to_datetime(solexs["timestamp"], utc=True)

    goes_col = "long_wavelength_flux" if "long_wavelength_flux" in goes_df.columns else "flux"
    goes = goes_df[["timestamp", goes_col]].copy()
    goes = goes.rename(columns={goes_col: "goes_flux"})
    goes["timestamp"] = pd.to_datetime(goes["timestamp"], utc=True)

    merged = pd.merge_asof(
        solexs.sort_values("timestamp"),
        goes.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(f"{tolerance_minutes}min"),
    )
    merged = merged.dropna(subset=["solexs_flux", "goes_flux"])

    notes: list[str] = []

    if len(merged) < 3:
        notes.append(f"Insufficient overlapping data: {len(merged)} points")
        return CrossCalibrationResult(
            instrument_a="SoLEXS",
            instrument_b="GOES XRS",
            correlation_coefficient=0.0,
            gain_factor=1.0,
            offset=0.0,
            rms_residual=0.0,
            n_overlapping_points=len(merged),
            time_range_start=str(solexs["timestamp"].min()) if len(solexs) > 0 else "",
            time_range_end=str(solexs["timestamp"].max()) if len(solexs) > 0 else "",
            notes=notes,
        )

    x = merged["goes_flux"].values.astype(float)
    y = merged["solexs_flux"].values.astype(float)

    valid = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x, y = x[valid], y[valid]

    if len(x) < 3:
        notes.append("All values non-positive or non-finite after filtering")
        return CrossCalibrationResult(
            instrument_a="SoLEXS",
            instrument_b="GOES XRS",
            correlation_coefficient=0.0,
            gain_factor=1.0,
            offset=0.0,
            rms_residual=0.0,
            n_overlapping_points=0,
            time_range_start="",
            time_range_end="",
            notes=notes,
        )

    corr = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 else 0.0

    log_x = np.log10(x)
    log_y = np.log10(y)
    coeffs = np.polyfit(log_x, log_y, 1)
    gain_factor = float(10 ** coeffs[0])
    offset = float(coeffs[1])

    predicted = gain_factor * x + offset
    rms = float(np.sqrt(np.mean((y - predicted) ** 2)))

    notes.append(f"Log-space linear fit: log10(y) = {coeffs[0]:.4f} * log10(x) + {coeffs[1]:.4f}")
    notes.append(f"Gain factor: {gain_factor:.6f} (SoLEXS/GOES ratio)")

    return CrossCalibrationResult(
        instrument_a="SoLEXS",
        instrument_b="GOES XRS",
        correlation_coefficient=corr,
        gain_factor=gain_factor,
        offset=offset,
        rms_residual=rms,
        n_overlapping_points=len(x),
        time_range_start=str(merged["timestamp"].min()),
        time_range_end=str(merged["timestamp"].max()),
        notes=notes,
    )


def cross_calibrate_hel1os_vs_reference(
    hel1os_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    reference_instrument: str = "RHESSI",
    tolerance_minutes: int = 5,
) -> CrossCalibrationResult:
    hel1os = hel1os_df[["timestamp", "hard_xray_flux"]].copy()
    hel1os = hel1os.rename(columns={"hard_xray_flux": "hel1os_flux"})
    hel1os["timestamp"] = pd.to_datetime(hel1os["timestamp"], utc=True)

    ref_col = "hard_xray_flux" if "hard_xray_flux" in reference_df.columns else "flux"
    ref = reference_df[["timestamp", ref_col]].copy()
    ref = ref.rename(columns={ref_col: "ref_flux"})
    ref["timestamp"] = pd.to_datetime(ref["timestamp"], utc=True)

    merged = pd.merge_asof(
        hel1os.sort_values("timestamp"),
        ref.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(f"{tolerance_minutes}min"),
    )
    merged = merged.dropna(subset=["hel1os_flux", "ref_flux"])

    notes: list[str] = []

    if len(merged) < 3:
        notes.append(f"Insufficient overlapping data: {len(merged)} points")
        return CrossCalibrationResult(
            instrument_a="HEL1OS",
            instrument_b=reference_instrument,
            correlation_coefficient=0.0,
            gain_factor=1.0,
            offset=0.0,
            rms_residual=0.0,
            n_overlapping_points=len(merged),
            time_range_start=str(hel1os["timestamp"].min()) if len(hel1os) > 0 else "",
            time_range_end=str(hel1os["timestamp"].max()) if len(hel1os) > 0 else "",
            notes=notes,
        )

    x = merged["ref_flux"].values.astype(float)
    y = merged["hel1os_flux"].values.astype(float)

    valid = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x, y = x[valid], y[valid]

    if len(x) < 3:
        notes.append("All values non-positive or non-finite after filtering")
        return CrossCalibrationResult(
            instrument_a="HEL1OS",
            instrument_b=reference_instrument,
            correlation_coefficient=0.0,
            gain_factor=1.0,
            offset=0.0,
            rms_residual=0.0,
            n_overlapping_points=0,
            time_range_start="",
            time_range_end="",
            notes=notes,
        )

    corr = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 else 0.0

    log_x = np.log10(x)
    log_y = np.log10(y)
    coeffs = np.polyfit(log_x, log_y, 1)
    gain_factor = float(10 ** coeffs[0])
    offset = float(coeffs[1])

    predicted = gain_factor * x + offset
    rms = float(np.sqrt(np.mean((y - predicted) ** 2)))

    notes.append(f"Log-space linear fit: log10(y) = {coeffs[0]:.4f} * log10(x) + {coeffs[1]:.4f}")
    notes.append(f"Gain factor: {gain_factor:.6f} (HEL1OS/{reference_instrument} ratio)")

    return CrossCalibrationResult(
        instrument_a="HEL1OS",
        instrument_b=reference_instrument,
        correlation_coefficient=corr,
        gain_factor=gain_factor,
        offset=offset,
        rms_residual=rms,
        n_overlapping_points=len(x),
        time_range_start=str(merged["timestamp"].min()),
        time_range_end=str(merged["timestamp"].max()),
        notes=notes,
    )


def generate_calibration_report(
    solexs_vs_goes: CrossCalibrationResult,
    hel1os_vs_ref: CrossCalibrationResult,
) -> str:
    lines = [
        "# Aditya-L1 Cross-Calibration Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "---",
        "",
        "## SoLEXS vs GOES XRS",
        "",
        f"- **Correlation**: {solexs_vs_goes.correlation_coefficient:.4f}",
        f"- **Gain factor**: {solexs_vs_goes.gain_factor:.6f}",
        f"- **RMS residual**: {solexs_vs_goes.rms_residual:.6e}",
        f"- **Overlapping points**: {solexs_vs_goes.n_overlapping_points}",
        f"- **Time range**: {solexs_vs_goes.time_range_start} to {solexs_vs_goes.time_range_end}",
        "",
    ]
    for note in solexs_vs_goes.notes:
        lines.append(f"  - {note}")

    lines.extend([
        "",
        "## HEL1OS vs " + hel1os_vs_ref.instrument_b,
        "",
        f"- **Correlation**: {hel1os_vs_ref.correlation_coefficient:.4f}",
        f"- **Gain factor**: {hel1os_vs_ref.gain_factor:.6f}",
        f"- **RMS residual**: {hel1os_vs_ref.rms_residual:.6e}",
        f"- **Overlapping points**: {hel1os_vs_ref.n_overlapping_points}",
        f"- **Time range**: {hel1os_vs_ref.time_range_start} to {hel1os_vs_ref.time_range_end}",
        "",
    ])
    for note in hel1os_vs_ref.notes:
        lines.append(f"  - {note}")

    lines.extend([
        "",
        "---",
        "",
        "## Disclaimer",
        "",
        solexs_vs_goes.disclaimer,
        "",
        "Cross-calibration uses log-space linear regression. Gain factors are instrument-ratio ",
        "coefficients, not absolute calibration values. Results depend on overlapping data availability ",
        "and should be validated against official calibration standards before operational use.",
    ])

    return "\n".join(lines)
