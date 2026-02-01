"""Tests for the health check endpoint."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test suite for GET /health endpoint."""

    def test_health_returns_ok(self, client_no_mock: TestClient) -> None:
        """Test that health endpoint returns status ok."""
        response = client_no_mock.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_response_content_type(self, client_no_mock: TestClient) -> None:
        """Test that health endpoint returns JSON content type."""
        response = client_no_mock.get("/health")

        assert response.headers["content-type"] == "application/json"

    def test_health_includes_request_id(self, client_no_mock: TestClient) -> None:
        """Test that response includes X-Request-ID header."""
        response = client_no_mock.get("/health")

        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    def test_health_uses_provided_request_id(self, client_no_mock: TestClient) -> None:
        """Test that provided X-Request-ID is echoed back."""
        request_id = "test-request-123"
        response = client_no_mock.get(
            "/health",
            headers={"X-Request-ID": request_id},
        )

        assert response.headers["x-request-id"] == request_id
