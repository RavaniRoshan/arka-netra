from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestSEPRiskModel:
    def test_minimal_risk_no_factors(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess()
        assert result.sep_risk_index == 0.0
        assert result.sep_category == "MINIMAL"
        assert result.is_experimental is True
        assert len(result.contributing_factors) == 0

    def test_x_class_flare_increases_risk(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(upcoming_flare_class="X")
        assert result.sep_risk_index >= 40.0
        assert any("X-class" in f for f in result.contributing_factors)

    def test_m_class_flare_increases_risk(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(upcoming_flare_class="M")
        assert result.sep_risk_index >= 20.0
        assert any("M-class" in f for f in result.contributing_factors)

    def test_hard_xray_peak_high(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(hard_xray_behavior={"peak_flux": 150.0, "rise_rate": 1.0})
        assert result.sep_risk_index >= 20.0

    def test_rapid_rise_increases_risk(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(hard_xray_behavior={"peak_flux": 5.0, "rise_rate": 6.0})
        assert result.sep_risk_index >= 10.0

    def test_high_flare_probability_increases_risk(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(flare_probability=0.6)
        assert result.sep_risk_index >= 15.0

    def test_high_uncertainty_increases_risk(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(uncertainty_variance=0.2)
        assert result.sep_risk_index >= 10.0
        assert result.confidence == "low"

    def test_risk_capped_at_100(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(
            upcoming_flare_class="X",
            hard_xray_behavior={"peak_flux": 200, "rise_rate": 10},
            uncertainty_variance=0.2,
            flare_probability=0.9,
        )
        assert result.sep_risk_index <= 100.0

    def test_category_high(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(
            upcoming_flare_class="X",
            hard_xray_behavior={"peak_flux": 200, "rise_rate": 10},
            flare_probability=0.9,
        )
        assert result.sep_category == "HIGH"

    def test_category_low(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess(
            upcoming_flare_class="M",
            hard_xray_behavior={"peak_flux": 5.0, "rise_rate": 1.0},
            flare_probability=0.55,
        )
        assert result.sep_category == "LOW"

    def test_to_dict(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        model = SEPRiskModel()
        result = model.assess()
        d = result.to_dict()
        assert "sep_risk_index" in d
        assert "is_experimental" in d
        assert d["is_experimental"] is True
        assert "timestamp" in d

    def test_compute_sep_risk_index_dataframe(self):
        from arkanetra.radiation.sep_model import compute_sep_risk_index
        df = pd.DataFrame({
            "hard_xray_flux": [100.0, 5.0, 0.0],
            "hard_rolling_slope": [2.0, 0.5, 0.0],
            "flare_probability": [0.6, 0.3, 0.1],
            "upcoming_flare_class": ["X", "M", "C"],
            "uncertainty_variance": [0.01, 0.05, 0.1],
        })
        result = compute_sep_risk_index(df)
        assert "sep_risk_index" in result.columns
        assert "sep_category" in result.columns
        assert "is_experimental" in result.columns
        assert len(result) == 3
        assert result.iloc[0]["sep_risk_index"] > result.iloc[2]["sep_risk_index"]


class TestSatelliteRisk:
    def test_assess_satellite_risk_geo(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        result = assess_satellite_risk(50.0, orbit=SatelliteOrbit.GEO)
        assert result.orbit == SatelliteOrbit.GEO
        assert result.is_experimental is True
        assert result.risk_level in ("MINIMAL", "LOW", "MODERATE", "HIGH")

    def test_assess_satellite_risk_all_orbits(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        for orbit in SatelliteOrbit:
            result = assess_satellite_risk(30.0, orbit=orbit)
            assert result.orbit == orbit
            assert result.is_experimental is True
            assert result.cumulative_dose_rate >= 0

    def test_high_risk_high_sep(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        result = assess_satellite_risk(80.0, orbit=SatelliteOrbit.GEO)
        assert result.risk_level == "HIGH"

    def test_minimal_risk_low_sep(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        result = assess_satellite_risk(0.0, orbit=SatelliteOrbit.GEO)
        assert result.risk_level == "MINIMAL"

    def test_dose_rate_increases_with_sep(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        low = assess_satellite_risk(0.0, orbit=SatelliteOrbit.LEO)
        high = assess_satellite_risk(80.0, orbit=SatelliteOrbit.LEO)
        assert high.cumulative_dose_rate > low.cumulative_dose_rate

    def test_proton_enhancement_triggers_high(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        result = assess_satellite_risk(10.0, orbit=SatelliteOrbit.GEO, proton_enhancement=15.0)
        assert result.risk_level == "HIGH"

    def test_to_dict(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        result = assess_satellite_risk(30.0, orbit=SatelliteOrbit.L1)
        d = result.to_dict()
        assert "orbit" in d
        assert d["is_experimental"] is True
        assert "disclaimer" in d
        assert "satellite radiation" in d["disclaimer"].lower()

    def test_add_satellite_risk_to_predictions(self):
        from arkanetra.radiation.satellite_risk import add_satellite_risk_to_predictions
        df = pd.DataFrame({"sep_risk_index": [50.0, 20.0, 80.0]})
        add_satellite_risk_to_predictions(df, orbit_str="leo")
        assert "sat_risk_level" in df.columns
        assert "sat_cumulative_dose_rate" in df.columns
        assert len(df) == 3

    def test_all_orbit_types_covered(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        tested = set()
        for orbit in SatelliteOrbit:
            result = assess_satellite_risk(40.0, orbit=orbit)
            tested.add(orbit.value)
        assert tested == {"geostationary", "l1", "leo", "meo"}


class TestHumanSpaceflight:
    def test_estimate_dose_rate_leo(self):
        from arkanetra.radiation.human_spaceflight import estimate_dose_rate
        rate = estimate_dose_rate("leo")
        assert rate > 0

    def test_estimate_dose_rate_deep_space_highest(self):
        from arkanetra.radiation.human_spaceflight import estimate_dose_rate
        leo = estimate_dose_rate("leo")
        deep = estimate_dose_rate("deep_space")
        assert deep > leo

    def test_shielding_reduces_dose(self):
        from arkanetra.radiation.human_spaceflight import estimate_dose_rate, ShieldingLevel
        minimal = estimate_dose_rate("leo", shielding=ShieldingLevel.MINIMAL)
        standard = estimate_dose_rate("leo", shielding=ShieldingLevel.STANDARD)
        enhanced = estimate_dose_rate("leo", shielding=ShieldingLevel.ENHANCED)
        assert minimal > standard > enhanced

    def test_sep_increases_dose(self):
        from arkanetra.radiation.human_spaceflight import estimate_dose_rate
        nominal = estimate_dose_rate("leo", sep_risk_index=0.0)
        high_sep = estimate_dose_rate("leo", sep_risk_index=80.0)
        assert high_sep > nominal

    def test_eva_phase_increases_dose(self):
        from arkanetra.radiation.human_spaceflight import estimate_dose_rate, MissionPhase
        nominal = estimate_dose_rate("leo", mission_phase=MissionPhase.NOMINAL)
        eva = estimate_dose_rate("leo", mission_phase=MissionPhase.EVA)
        assert eva > nominal

    def test_mission_dose_calculation(self):
        from arkanetra.radiation.human_spaceflight import estimate_mission_dose
        result = estimate_mission_dose(orbit="leo", mission_duration_hours=24.0)
        assert result.estimated_dose_msv > 0
        assert result.is_experimental is True
        assert result.mission_phase.value == "nominal"

    def test_mission_dose_with_previous_dose(self):
        from arkanetra.radiation.human_spaceflight import estimate_mission_dose
        result = estimate_mission_dose(orbit="leo", mission_duration_hours=24.0, previous_dose_msv=500.0)
        assert result.career_dose_msv > 500.0

    def test_career_limit_exceeded(self):
        from arkanetra.radiation.human_spaceflight import estimate_mission_dose
        result = estimate_mission_dose(
            orbit="leo",
            mission_duration_hours=10000.0,
            previous_dose_msv=580.0,
            career_limit_msv=600.0,
        )
        assert "CRITICAL" in result.risk_assessment

    def test_eva_dose_estimation(self):
        from arkanetra.radiation.human_spaceflight import estimate_eva_dose
        result = estimate_eva_dose(orbit="leo", eva_duration_minutes=60.0)
        assert result.estimated_dose_msv > 0
        assert result.mission_phase.value == "eva"
        assert result.is_experimental is True

    def test_all_orbits_covered(self):
        from arkanetra.radiation.human_spaceflight import estimate_mission_dose
        orbits = ["geostationary", "l1", "leo", "meo", "deep_space", "lunar", "mars"]
        for orbit in orbits:
            result = estimate_mission_dose(orbit=orbit, mission_duration_hours=1.0)
            assert result.estimated_dose_msv > 0

    def test_to_dict(self):
        from arkanetra.radiation.human_spaceflight import estimate_mission_dose
        result = estimate_mission_dose(orbit="leo", mission_duration_hours=6.0)
        d = result.to_dict()
        assert "estimated_dose_msv" in d
        assert d["is_experimental"] is True
        assert "disclaimer" in d
        assert "contributing_factors" in d
        assert isinstance(d["contributing_factors"], list)

    def test_compute_human_dose_for_predictions(self):
        from arkanetra.radiation.human_spaceflight import compute_human_dose_for_predictions
        df = pd.DataFrame({"sep_risk_index": [0.0, 50.0, 80.0]})
        compute_human_dose_for_predictions(df, orbit="leo", mission_duration_hours=6.0)
        assert "hsr_estimated_dose_msv" in df.columns
        assert "hsr_risk_assessment" in df.columns
        assert "hsr_is_experimental" in df.columns
        assert all(df["hsr_is_experimental"] == True)


class TestExperimentalDisclaimers:
    def test_sep_result_is_experimental(self):
        from arkanetra.radiation.sep_model import SEPRiskModel
        result = SEPRiskModel().assess()
        assert result.is_experimental is True

    def test_satellite_risk_is_experimental(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        result = assess_satellite_risk(30.0, orbit=SatelliteOrbit.GEO)
        assert result.is_experimental is True

    def test_human_dose_is_experimental(self):
        from arkanetra.radiation.human_spaceflight import estimate_mission_dose
        result = estimate_mission_dose(orbit="leo", mission_duration_hours=6.0)
        assert result.is_experimental is True

    def test_satellite_risk_has_disclaimer(self):
        from arkanetra.radiation.satellite_risk import assess_satellite_risk, SatelliteOrbit
        result = assess_satellite_risk(30.0, orbit=SatelliteOrbit.GEO)
        assert "informational only" in result.disclaimer.lower()

    def test_human_dose_has_disclaimer(self):
        from arkanetra.radiation.human_spaceflight import estimate_mission_dose
        result = estimate_mission_dose(orbit="leo", mission_duration_hours=6.0)
        assert "not validated" in result.disclaimer.lower()
