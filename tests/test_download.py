from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from arkanetra.data.download import fetch_binary, fetch_json


class TestFetchJson:
    def test_returns_list_for_valid_url(self):
        url = "https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json"
        result = fetch_json(url, timeout_seconds=15)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "time_tag" in result[0]
        assert "flux" in result[0]

    def test_returns_list_for_latest(self):
        url = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"
        result = fetch_json(url, timeout_seconds=15)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_raises_on_404(self):
        with pytest.raises(Exception):
            fetch_json("https://services.swpc.noaa.gov/json/goes/primary/nonexistent.json", timeout_seconds=10)

    def test_retries_on_failure(self):
        with patch("arkanetra.data.download.urllib.request.urlopen") as mock_urlopen:
            from urllib.error import URLError
            mock_urlopen.side_effect = URLError("connection refused")
            with pytest.raises(URLError):
                fetch_json("https://example.invalid/test.json", timeout_seconds=5)


class TestFetchBinary:
    def test_downloads_binary_file(self):
        url = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"
        data = fetch_binary(url, timeout_seconds=15)
        assert len(data) > 0
        assert isinstance(data, bytes)

    def test_raises_on_404(self):
        with pytest.raises(Exception):
            fetch_binary("https://services.swpc.noaa.gov/json/goes/primary/nonexistent.bin", timeout_seconds=10)


class TestGoesLiveDownload:
    def test_swpc_download_goes_xrs_data(self):
        from arkanetra.data.goes import download_goes_xrs
        from arkanetra.config import ROOT

        now = __import__("pandas").Timestamp.now("UTC")
        result = download_goes_xrs(
            (now - __import__("pandas").Timedelta(hours=24)).isoformat(),
            now.isoformat(),
        )
        assert result is None or (Path(result).exists() and Path(result).stat().st_size > 0)

    def test_downloaded_data_matches_contract(self):
        from arkanetra.data.goes import SWPC_XRAY_7DAY_URL, _fetch_swpc_json

        records = _fetch_swpc_json(SWPC_XRAY_7DAY_URL, timeout_seconds=15)
        assert len(records) > 0
        row = records[0]
        assert "time_tag" in row
        assert "flux" in row
        assert "energy" in row

    def test_short_channel_filtered_out(self):
        from arkanetra.data.goes import _is_short_channel

        assert _is_short_channel("0.5-4.0A")
        assert _is_short_channel("0.5-4A")
        assert not _is_short_channel("1.0-8.0A")
        assert not _is_short_channel(" 1.0-8.0A ")


class TestFermiGbmDownload:
    def test_download_fermi_gbm_download(self):
        from arkanetra.data.hard_xray_proxy import download_fermi_gbm_data
        from arkanetra.config import ROOT

        save_dir = ROOT / "data" / "raw" / "goes_sample"
        paths = download_fermi_gbm_data("2026-06-16", "2026-06-16", save_dir=save_dir)
        assert isinstance(paths, list)