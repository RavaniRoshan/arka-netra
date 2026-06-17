from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestCrossCalibration:
    def _make_solexs_df(self, n=50, noise=0.1):
        rng = np.random.default_rng(42)
        timestamps = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
        flux = 1e-6 + rng.normal(0, noise * 1e-6, n)
        flux = np.abs(flux)
        return pd.DataFrame({"timestamp": timestamps, "soft_xray_flux": flux})

    def _make_goes_df(self, n=50, noise=0.1):
        rng = np.random.default_rng(42)
        timestamps = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
        flux = 1e-5 + rng.normal(0, noise * 1e-5, n)
        flux = np.abs(flux)
        return pd.DataFrame({"timestamp": timestamps, "long_wavelength_flux": flux})

    def _make_hel1os_df(self, n=50, noise=0.1):
        rng = np.random.default_rng(42)
        timestamps = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
        flux = 1e-8 + rng.normal(0, noise * 1e-8, n)
        flux = np.abs(flux)
        return pd.DataFrame({"timestamp": timestamps, "hard_xray_flux": flux})

    def _make_rhessi_df(self, n=50, noise=0.1):
        rng = np.random.default_rng(42)
        timestamps = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
        flux = 1e-7 + rng.normal(0, noise * 1e-7, n)
        flux = np.abs(flux)
        return pd.DataFrame({"timestamp": timestamps, "hard_xray_flux": flux})

    def test_solexs_vs_goes_returns_result(self):
        from solaris.data.cross_calibration import cross_calibrate_solexs_vs_goes
        solexs = self._make_solexs_df()
        goes = self._make_goes_df()
        result = cross_calibrate_solexs_vs_goes(solexs, goes)
        assert result.instrument_a == "SoLEXS"
        assert result.instrument_b == "GOES XRS"
        assert result.is_experimental is True

    def test_solexs_vs_goes_has_correlation(self):
        from solaris.data.cross_calibration import cross_calibrate_solexs_vs_goes
        solexs = self._make_solexs_df()
        goes = self._make_goes_df()
        result = cross_calibrate_solexs_vs_goes(solexs, goes)
        assert -1 <= result.correlation_coefficient <= 1

    def test_solexs_vs_goes_insufficient_data(self):
        from solaris.data.cross_calibration import cross_calibrate_solexs_vs_goes
        solexs = pd.DataFrame({"timestamp": pd.to_datetime([], utc=True), "soft_xray_flux": []})
        goes = pd.DataFrame({"timestamp": pd.to_datetime([], utc=True), "long_wavelength_flux": []})
        result = cross_calibrate_solexs_vs_goes(solexs, goes)
        assert result.n_overlapping_points == 0
        assert len(result.notes) > 0

    def test_hel1os_vs_rhessi_returns_result(self):
        from solaris.data.cross_calibration import cross_calibrate_hel1os_vs_reference
        hel1os = self._make_hel1os_df()
        rhessi = self._make_rhessi_df()
        result = cross_calibrate_hel1os_vs_reference(hel1os, rhessi, reference_instrument="RHESSI")
        assert result.instrument_a == "HEL1OS"
        assert result.instrument_b == "RHESSI"
        assert result.is_experimental is True

    def test_hel1os_vs_rhessi_has_gain_factor(self):
        from solaris.data.cross_calibration import cross_calibrate_hel1os_vs_reference
        hel1os = self._make_hel1os_df()
        rhessi = self._make_rhessi_df()
        result = cross_calibrate_hel1os_vs_reference(hel1os, rhessi)
        assert result.gain_factor > 0

    def test_hel1os_vs_rhessi_insufficient_data(self):
        from solaris.data.cross_calibration import cross_calibrate_hel1os_vs_reference
        hel1os = pd.DataFrame({"timestamp": pd.to_datetime([], utc=True), "hard_xray_flux": []})
        ref = pd.DataFrame({"timestamp": pd.to_datetime([], utc=True), "hard_xray_flux": []})
        result = cross_calibrate_hel1os_vs_reference(hel1os, ref)
        assert result.n_overlapping_points == 0

    def test_to_dict(self):
        from solaris.data.cross_calibration import cross_calibrate_solexs_vs_goes
        solexs = self._make_solexs_df()
        goes = self._make_goes_df()
        result = cross_calibrate_solexs_vs_goes(solexs, goes)
        d = result.to_dict()
        assert "correlation_coefficient" in d
        assert d["is_experimental"] is True
        assert "disclaimer" in d
        assert "notes" in d

    def test_generate_calibration_report(self):
        from solaris.data.cross_calibration import (
            cross_calibrate_solexs_vs_goes,
            cross_calibrate_hel1os_vs_reference,
            generate_calibration_report,
        )
        solexs = self._make_solexs_df()
        goes = self._make_goes_df()
        hel1os = self._make_hel1os_df()
        rhessi = self._make_rhessi_df()
        cal1 = cross_calibrate_solexs_vs_goes(solexs, goes)
        cal2 = cross_calibrate_hel1os_vs_reference(hel1os, rhessi)
        report = generate_calibration_report(cal1, cal2)
        assert "Cross-Calibration Report" in report
        assert "SoLEXS" in report
        assert "HEL1OS" in report
        assert "Disclaimer" in report


class TestAdityaL1Download:
    def test_download_solexs_returns_dataframe(self):
        from solaris.data.solexs import download_solexs_data
        df = download_solexs_data()
        assert isinstance(df, pd.DataFrame)

    def test_download_hel1os_returns_dataframe(self):
        from solaris.data.hel1os import download_hel1os_data
        df = download_hel1os_data()
        assert isinstance(df, pd.DataFrame)

    def test_download_solexs_has_expected_columns(self):
        from solaris.data.solexs import download_solexs_data
        df = download_solexs_data()
        assert "timestamp" in df.columns
        assert "soft_xray_flux" in df.columns
        assert "data_quality" in df.columns

    def test_download_hel1os_has_expected_columns(self):
        from solaris.data.hel1os import download_hel1os_data
        df = download_hel1os_data()
        assert "timestamp" in df.columns
        assert "hard_xray_flux" in df.columns
        assert "data_quality" in df.columns

    def test_download_solexs_graceful_failure(self):
        from solaris.data.solexs import download_solexs_data
        df = download_solexs_data(source="nonexistent_source")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_download_hel1os_graceful_failure(self):
        from solaris.data.hel1os import download_hel1os_data
        df = download_hel1os_data(source="nonexistent_source")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
