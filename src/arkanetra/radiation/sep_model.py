from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd


@dataclass
class SEPRiskResult:
    sep_risk_index: float
    sep_category: str
    confidence: str
    contributing_factors: list[str]
    is_experimental: bool = True
    particle_data_available: bool = False
    timestamp: str | None = None

    def to_dict(self) -> dict:
        return {
            "sep_risk_index": float(self.sep_risk_index),
            "sep_category": self.sep_category,
            "confidence": self.confidence,
            "contributing_factors": self.contributing_factors,
            "is_experimental": self.is_experimental,
            "particle_data_available": self.particle_data_available,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
        }


class SEPRiskModel:
    def __init__(
        self,
        particle_data: "ParticleData | None" = None,
        enable_particle_integration: bool = False,
    ):
        self.particle_data = particle_data
        self.enable_particle_integration = enable_particle_integration

    def assess(
        self,
        upcoming_flare_class: str | None = None,
        hard_xray_behavior: dict | None = None,
        uncertainty_variance: float = 0.0,
        flare_probability: float = 0.0,
        current_proton_flux: float | None = None,
        current_electron_flux: float | None = None,
    ) -> SEPRiskResult:
        factors: list[str] = []
        risk_score = 0.0

        if upcoming_flare_class:
            klass = upcoming_flare_class[:1].upper()
            if klass == "X":
                risk_score += 40.0
                factors.append("X-class flare is SEP-capable")
            elif klass == "M":
                risk_score += 20.0
                factors.append("M-class flare possible SEP event")

        if hard_xray_behavior:
            peak = hard_xray_behavior.get("peak_flux", 0.0)
            rise_rate = hard_xray_behavior.get("rise_rate", 0.0)
            if peak > 100:
                risk_score += 20.0
                factors.append("Very high hard X-ray peak indicates strong acceleration")
            elif peak > 10:
                risk_score += 10.0
                factors.append("Elevated hard X-ray flux")

            if rise_rate > 5.0:
                risk_score += 10.0
                factors.append("Rapid hard X-ray rise suggests efficient particle acceleration")

        if uncertainty_variance > 0.15:
            confidence = "low"
            risk_score += 10.0
            factors.append("High uncertainty increases SEP prediction uncertainty")
        elif uncertainty_variance > 0.05:
            confidence = "moderate"
        else:
            confidence = "high"

        if flare_probability >= 0.55:
            risk_score += 15.0
            factors.append("High flare probability correlates with SEP likelihood")

        if self.particle_data_available and current_proton_flux is not None:
            if current_proton_flux > 10:
                risk_score += 25.0
                factors.append("Elevated proton flux already observed")
            elif current_proton_flux > 1:
                risk_score += 10.0
                factors.append("Slight proton enhancement detected")

        if self.particle_data_available and current_electron_flux is not None:
            if current_electron_flux > 1000:
                risk_score += 10.0
                factors.append("Elevated electron flux indicates shock acceleration")

        risk_score = min(risk_score, 100.0)

        if risk_score >= 75:
            category = "HIGH"
        elif risk_score >= 50:
            category = "MODERATE"
        elif risk_score >= 25:
            category = "LOW"
        else:
            category = "MINIMAL"

        return SEPRiskResult(
            sep_risk_index=risk_score,
            sep_category=category,
            confidence=confidence,
            contributing_factors=factors,
            is_experimental=True,
            particle_data_available=self.particle_data_available,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @property
    def particle_data_available(self) -> bool:
        return self.particle_data is not None and self.enable_particle_integration


def compute_sep_risk_index(
    predictions: pd.DataFrame,
    particle_data: "ParticleData | None" = None,
    enable_particle_integration: bool = False,
) -> pd.DataFrame:
    model = SEPRiskModel(particle_data=particle_data, enable_particle_integration=enable_particle_integration)
    results = []
    for _, row in predictions.iterrows():
        hard_behavior = {
            "peak_flux": float(row.get("hard_xray_flux", 0.0)),
            "rise_rate": float(row.get("hard_rolling_slope", 0.0)),
        }
        result = model.assess(
            upcoming_flare_class=str(row.get("upcoming_flare_class", "")) if pd.notna(row.get("upcoming_flare_class")) else None,
            hard_xray_behavior=hard_behavior,
            uncertainty_variance=float(row.get("uncertainty_variance", 0.0)),
            flare_probability=float(row.get("flare_probability", 0.0)),
        )
        results.append(result.to_dict())
    sep_df = pd.DataFrame(results)
    merged = predictions.copy()
    for col in ["sep_risk_index", "sep_category", "confidence", "contributing_factors", "is_experimental", "particle_data_available", "timestamp"]:
        if col in sep_df.columns:
            merged[col] = sep_df[col].values
    return merged