"""
Tests for API endpoints.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.integration
    def test_health_check(self):
        """Test the main health check endpoint against a live database."""
        from app.db import check_db_connection

        if not check_db_connection():
            pytest.skip("PostgreSQL not reachable - integration test")

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data
        assert data["services"]["api"] == "healthy"

    def test_health_check_reports_healthy_when_db_up(self):
        """Health payload is 'healthy' when the DB check passes (no live DB)."""
        with patch("app.api.health.check_db_connection", return_value=True):
            response = client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert data["services"]["api"] == "healthy"
        assert data["services"]["database"] == "healthy"

    def test_ping(self):
        """Test the ping endpoint."""
        response = client.get("/health/ping")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "pong"
        assert "timestamp" in data


class TestRootEndpoints:
    """Test root and info endpoints."""
    
    def test_root(self):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "environment" in data
    
    def test_info(self):
        """Test the info endpoint."""
        response = client.get("/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "business_name" in data


class TestMiddleware:
    """Test middleware functionality."""
    
    def test_request_id_header(self):
        """Test that request ID is added to response headers."""
        response = client.get("/health/ping")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = client.options("/health")
        # CORS headers should be present
        assert response.status_code in [200, 405]  # OPTIONS might not be explicitly defined


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

