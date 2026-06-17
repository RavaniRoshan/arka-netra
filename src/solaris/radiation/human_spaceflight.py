from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import numpy as np


class MissionPhase(Enum):
    NOMINAL = "nominal"
    SOLAR_MAXIMUM = "solar_maximum"
    SOLAR_MINIMUM = "solar_minimum"
    SEP_EVENT = "sep_event"
    EVA = "eva"


class ShieldingLevel(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    ENHANCED = "enhanced"


@dataclass
class AstronautDoseEstimate:
    estimated_dose_msv: float
    career_dose_msv: float
    career_limit_msv: float
    mission_phase: MissionPhase
    shielding: ShieldingLevel
    risk_assessment: str
    dose_rate_msv_per_hour: float
    mission_duration_hours: float
    is_experimental: bool = True
    disclaimer: str = (
        "Human spaceflight radiation dose estimates are simplified models. "
        "Not validated against ISS or deep-space dosimetry. "
        "For informational purposes only."
    )
    contributing_factors: list[str] = field(default_factory=list)
    timestamp: str | None = None

    def to_dict(self) -> dict:
        return {
            "estimated_dose_msv": round(self.estimated_dose_msv, 4),
            "career_dose_msv": round(self.career_dose_msv, 4),
            "career_limit_msv": round(self.career_limit_msv, 2),
            "mission_phase": self.mission_phase.value,
            "shielding": self.shielding.value,
            "risk_assessment": self.risk_assessment,
            "dose_rate_msv_per_hour": round(self.dose_rate_msv_per_hour, 6),
            "mission_duration_hours": round(self.mission_duration_hours, 2),
            "is_experimental": self.is_experimental,
            "disclaimer": self.disclaimer,
            "contributing_factors": self.contributing_factors,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
        }


_SHIELDING_FACTORS = {
    ShieldingLevel.MINIMAL: 1.0,
    ShieldingLevel.STANDARD: 0.3,
    ShieldingLevel.ENHANCED: 0.1,
}

_ORBIT_BASE_DOSE_RATE_MSV_PER_HOUR = {
    "geostationary": 0.012,
    "l1": 0.055,
    "leo": 0.008,
    "meo": 0.015,
    "deep_space": 0.18,
    "lunar": 0.12,
    "mars": 0.22,
}

_PHASE_MULTIPLIERS = {
    MissionPhase.NOMINAL: 1.0,
    MissionPhase.SOLAR_MAXIMUM: 1.5,
    MissionPhase.SOLAR_MINIMUM: 0.7,
    MissionPhase.SEP_EVENT: 5.0,
    MissionPhase.EVA: 3.0,
}

CAREER_DOSE_LIMITS_MSV = {
    "age_30": 600,
    "age_40": 700,
    "age_50": 800,
}

DEFAULT_CAREER_LIMIT_MSV = 600.0


def estimate_dose_rate(
    orbit: str,
    sep_risk_index: float = 0.0,
    shielding: ShieldingLevel = ShieldingLevel.STANDARD,
    mission_phase: MissionPhase = MissionPhase.NOMINAL,
) -> float:
    base_rate = _ORBIT_BASE_DOSE_RATE_MSV_PER_HOUR.get(orbit, 0.012)
    sep_multiplier = 1.0 + sep_risk_index / 50.0
    shielding_factor = _SHIELDING_FACTORS[shielding]
    phase_multiplier = _PHASE_MULTIPLIERS[mission_phase]
    return base_rate * sep_multiplier * shielding_factor * phase_multiplier


def estimate_mission_dose(
    orbit: str,
    mission_duration_hours: float,
    sep_risk_index: float = 0.0,
    shielding: ShieldingLevel = ShieldingLevel.STANDARD,
    mission_phase: MissionPhase = MissionPhase.NOMINAL,
    previous_dose_msv: float = 0.0,
    career_limit_msv: float = DEFAULT_CAREER_LIMIT_MSV,
) -> AstronautDoseEstimate:
    dose_rate = estimate_dose_rate(
        orbit=orbit,
        sep_risk_index=sep_risk_index,
        shielding=shielding,
        mission_phase=mission_phase,
    )
    estimated_dose = dose_rate * mission_duration_hours
    career_dose = previous_dose_msv + estimated_dose

    factors: list[str] = []
    factors.append(f"Orbit: {orbit}")
    factors.append(f"Shielding: {shielding.value}")
    factors.append(f"Mission phase: {mission_phase.value}")
    factors.append(f"SEP risk index: {sep_risk_index:.1f}")

    if sep_risk_index >= 75:
        factors.append("HIGH SEP risk: significant radiation enhancement expected")
    elif sep_risk_index >= 50:
        factors.append("MODERATE SEP risk: enhanced monitoring recommended")
    elif sep_risk_index >= 25:
        factors.append("LOW SEP risk: nominal operations with monitoring")

    if mission_phase == MissionPhase.EVA:
        factors.append("EVA operations: reduced shielding, elevated dose rate")
    elif mission_phase == MissionPhase.SEP_EVENT:
        factors.append("Active SEP event: major radiation enhancement in progress")

    if career_dose > career_limit_msv:
        risk = "CRITICAL: Career dose limit exceeded"
    elif career_dose > career_limit_msv * 0.9:
        risk = "HIGH: Approaching career dose limit (>90%)"
    elif career_dose > career_limit_msv * 0.75:
        risk = "MODERATE: Significant career dose accumulated (>75%)"
    elif estimated_dose > 50.0:
        risk = "MODERATE: High single-mission dose (>50 mSv)"
    elif estimated_dose > 20.0:
        risk = "LOW: Elevated mission dose (>20 mSv)"
    else:
        risk = "MINIMAL: Acceptable dose for mission duration"

    return AstronautDoseEstimate(
        estimated_dose_msv=estimated_dose,
        career_dose_msv=career_dose,
        career_limit_msv=career_limit_msv,
        mission_phase=mission_phase,
        shielding=shielding,
        risk_assessment=risk,
        dose_rate_msv_per_hour=dose_rate,
        mission_duration_hours=mission_duration_hours,
        is_experimental=True,
        contributing_factors=factors,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def estimate_eva_dose(
    orbit: str,
    eva_duration_minutes: float,
    sep_risk_index: float = 0.0,
    shielding: ShieldingLevel = ShieldingLevel.MINIMAL,
    previous_dose_msv: float = 0.0,
    career_limit_msv: float = DEFAULT_CAREER_LIMIT_MSV,
) -> AstronautDoseEstimate:
    return estimate_mission_dose(
        orbit=orbit,
        mission_duration_hours=eva_duration_minutes / 60.0,
        sep_risk_index=sep_risk_index,
        shielding=shielding,
        mission_phase=MissionPhase.EVA,
        previous_dose_msv=previous_dose_msv,
        career_limit_msv=career_limit_msv,
    )


def compute_human_dose_for_predictions(
    predictions_df,
    orbit: str = "leo",
    shielding: str = "standard",
    career_dose_msv: float = 0.0,
    career_limit_msv: float = DEFAULT_CAREER_LIMIT_MSV,
    mission_duration_hours: float = 6.0,
) -> None:
    shielding_level = ShieldingLevel(shielding.lower())
    sep_indices = (
        predictions_df["sep_risk_index"].values
        if "sep_risk_index" in predictions_df.columns
        else np.zeros(len(predictions_df))
    )

    for i in range(len(predictions_df)):
        sep_val = float(sep_indices[i]) if i < len(sep_indices) else 0.0
        result = estimate_mission_dose(
            orbit=orbit,
            mission_duration_hours=mission_duration_hours,
            sep_risk_index=sep_val,
            shielding=shielding_level,
            previous_dose_msv=career_dose_msv,
            career_limit_msv=career_limit_msv,
        )
        d = result.to_dict()
        for key in [
            "estimated_dose_msv",
            "career_dose_msv",
            "career_limit_msv",
            "risk_assessment",
            "dose_rate_msv_per_hour",
            "is_experimental",
        ]:
            col_name = f"hsr_{key}"
            if col_name not in predictions_df.columns:
                predictions_df[col_name] = None
            predictions_df.at[predictions_df.index[i], col_name] = d[key]
