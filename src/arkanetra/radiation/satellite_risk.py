from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import numpy as np


class SatelliteOrbit(Enum):
    GEO = "geostationary"
    L1 = "l1"
    LEO = "leo"
    MEO = "meo"


@dataclass
class SatelliteRiskContext:
    orbit: SatelliteOrbit
    cumulative_dose_rate: float
    radiation_context: str
    risk_level: str
    advisory: str
    is_experimental: bool = True
    disclaimer: str = "Satellite radiation context is informational only. Not validated against operational radiation models."
    timestamp: str | None = None

    def to_dict(self) -> dict:
        return {
            "orbit": self.orbit.value,
            "cumulative_dose_rate": float(self.cumulative_dose_rate),
            "radiation_context": self.radiation_context,
            "risk_level": self.risk_level,
            "advisory": self.advisory,
            "is_experimental": self.is_experimental,
            "disclaimer": self.disclaimer,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
        }


def estimate_dose_rate(sep_risk_index: float, orbit: SatelliteOrbit) -> float:
    base_rate = {
        SatelliteOrbit.GEO: 0.01,
        SatelliteOrbit.L1: 0.05,
        SatelliteOrbit.LEO: 0.002,
        SatelliteOrbit.MEO: 0.008,
    }[orbit]
    multiplier = 1.0 + sep_risk_index / 50.0
    return base_rate * multiplier


def assess_satellite_risk(
    sep_risk_index: float,
    orbit: SatelliteOrbit = SatelliteOrbit.GEO,
    exposure_minutes: int = 60,
    proton_enhancement: float | None = None,
    electron_enhancement: float | None = None,
) -> SatelliteRiskContext:
    dose_rate = estimate_dose_rate(sep_risk_index, orbit)
    cumulative_dose = dose_rate * exposure_minutes / 60.0

    if orbit == SatelliteOrbit.L1:
        dose_rate *= 3.0
    elif orbit == SatelliteOrbit.GEO:
        dose_rate *= 1.5

    cumulative_dose = dose_rate * exposure_minutes / 60.0

    if sep_risk_index >= 75 or (proton_enhancement and proton_enhancement > 10):
        risk_level = "HIGH"
        context = "Elevated proton flux expected; single-event effects possible for unshielded electronics."
        advisory = "Consider placing satellites in safe hold mode. Monitor housekeeping data for single-event upsets."
    elif sep_risk_index >= 50 or (electron_enhancement and electron_enhancement > 1000):
        risk_level = "MODERATE"
        context = "Increased radiation environment; cumulative dose accumulating faster than nominal."
        advisory = "Monitor spacecraft charging and deep-dielectric charging indicators. Review high-voltage operations."
    elif sep_risk_index >= 25:
        risk_level = "LOW"
        context = "Slightly elevated radiation; nominal operations with enhanced monitoring recommended."
        advisory = "No action required; standard spacecraft monitoring applies."
    else:
        risk_level = "MINIMAL"
        context = "Background radiation conditions; no operational concerns."
        advisory = "Nominal operations."

    return SatelliteRiskContext(
        orbit=orbit,
        cumulative_dose_rate=round(cumulative_dose, 6),
        radiation_context=context,
        risk_level=risk_level,
        advisory=advisory,
        is_experimental=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def add_satellite_risk_to_predictions(predictions_df, orbit_str: str = "geostationary") -> None:
    orbit_map = {
        "geostationary": SatelliteOrbit.GEO,
        "l1": SatelliteOrbit.L1,
        "leo": SatelliteOrbit.LEO,
        "meo": SatelliteOrbit.MEO,
    }
    orbit = orbit_map.get(orbit_str.lower(), SatelliteOrbit.GEO)
    sep_indices = predictions_df["sep_risk_index"].values if "sep_risk_index" in predictions_df.columns else np.zeros(len(predictions_df))
    proton_vals = predictions_df["proton_flux"].values if "proton_flux" in predictions_df.columns else None
    electron_vals = predictions_df["electron_flux"].values if "electron_flux" in predictions_df.columns else None

    for i in range(len(predictions_df)):
        sep_val = float(sep_indices[i]) if i < len(sep_indices) else 0.0
        proton = float(proton_vals[i]) if proton_vals is not None and i < len(proton_vals) and not np.isnan(proton_vals[i]) else None
        electron = float(electron_vals[i]) if electron_vals is not None and i < len(electron_vals) and not np.isnan(electron_vals[i]) else None
        result = assess_satellite_risk(sep_val, orbit=orbit, proton_enhancement=proton, electron_enhancement=electron)
        for k, v in result.to_dict().items():
            col_name = f"sat_{k}"
            if col_name not in predictions_df.columns:
                predictions_df[col_name] = None
            predictions_df.at[predictions_df.index[i], col_name] = v