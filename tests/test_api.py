from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from solaris.api.prediction_api import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_required_fields(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert data["status"] == "healthy"

    def test_health_bypasses_auth(self, client):
        response = client.get("/health")
        assert response.status_code == 200


class TestRateLimiter:
    def test_allows_requests_under_limit(self):
        from solaris.api.prediction_api import RateLimiter
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed("test_client") is True

    def test_blocks_requests_over_limit(self):
        from solaris.api.prediction_api import RateLimiter
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("test_client")
        assert limiter.is_allowed("test_client") is False

    def test_remaining_decreases(self):
        from solaris.api.prediction_api import RateLimiter
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.remaining("test_client") == 10
        limiter.is_allowed("test_client")
        assert limiter.remaining("test_client") == 9

    def test_separate_clients_independent(self):
        from solaris.api.prediction_api import RateLimiter
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("client_a")
        limiter.is_allowed("client_a")
        assert limiter.is_allowed("client_a") is False
        assert limiter.is_allowed("client_b") is True


class TestAuthentication:
    def test_no_api_key_allows_all(self, client):
        with patch("solaris.api.prediction_api.API_KEY", ""):
            response = client.get("/predictions")
            assert response.status_code == 200

    def test_valid_api_key_bearer(self, client):
        with patch("solaris.api.prediction_api.API_KEY", "test-secret-key"):
            response = client.get(
                "/predictions",
                headers={"Authorization": "Bearer test-secret-key"},
            )
            assert response.status_code == 200

    def test_valid_api_key_header(self, client):
        with patch("solaris.api.prediction_api.API_KEY", "test-secret-key"):
            response = client.get(
                "/predictions",
                headers={"X-API-Key": "test-secret-key"},
            )
            assert response.status_code == 200

    def test_invalid_api_key_returns_401(self, client):
        with patch("solaris.api.prediction_api.API_KEY", "test-secret-key"):
            response = client.get(
                "/predictions",
                headers={"Authorization": "Bearer wrong-key"},
            )
            assert response.status_code == 401

    def test_missing_api_key_returns_401(self, client):
        with patch("solaris.api.prediction_api.API_KEY", "test-secret-key"):
            response = client.get("/predictions")
            assert response.status_code == 401

    def test_health_bypasses_auth_even_with_key(self, client):
        with patch("solaris.api.prediction_api.API_KEY", "test-secret-key"):
            response = client.get("/health")
            assert response.status_code == 200


class TestInputValidation:
    def test_invalid_scenario_returns_400(self, client):
        response = client.get("/predictions?scenario=nonexistent")
        assert response.status_code == 400

    def test_valid_scenario_accepted(self, client):
        response = client.get("/predictions?scenario=baseline")
        assert response.status_code == 200

    def test_invalid_alert_state_returns_400(self, client):
        response = client.get("/alerts?state=INVALID")
        assert response.status_code == 400

    def test_valid_alert_state_accepted(self, client):
        response = client.get("/alerts?state=NORMAL")
        assert response.status_code == 200


class TestEndpointCoverage:
    def test_predictions_endpoint(self, client):
        response = client.get("/predictions")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "total" in data

    def test_alerts_endpoint(self, client):
        response = client.get("/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total" in data

    def test_manifest_endpoint(self, client):
        response = client.get("/manifest")
        assert response.status_code == 200

    def test_audit_endpoint(self, client):
        response = client.get("/audit")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data

    def test_scenarios_endpoint(self, client):
        response = client.get("/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data

    def test_limit_parameter(self, client):
        response = client.get("/predictions?limit=5")
        assert response.status_code == 200

    def test_limit_validation(self, client):
        response = client.get("/predictions?limit=0")
        assert response.status_code == 422
