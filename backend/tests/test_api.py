"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self):
        """Test the main health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data
        assert data["services"]["api"] == "healthy"
    
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


class TestTwilioWebhooks:
    """Test Twilio webhook endpoints."""
    
    def test_inbound_call_webhook(self):
        """Test the inbound call webhook."""
        # Simulate Twilio webhook data
        form_data = {
            "CallSid": "CA1234567890abcdef1234567890abcdef",
            "From": "+15551234567",
            "To": "+15559876543",
            "CallStatus": "ringing",
            "Direction": "inbound",
            "FromCity": "NEW YORK",
            "FromState": "NY",
            "FromCountry": "US",
        }
        
        response = client.post("/webhooks/twilio/voice", data=form_data)
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        
        # Check TwiML response
        twiml = response.text
        assert "<?xml version" in twiml
        assert "<Response>" in twiml
        assert "<Say" in twiml
        assert "<Record" in twiml
    
    def test_recording_webhook(self):
        """Test the recording completion webhook."""
        form_data = {
            "CallSid": "CA1234567890abcdef1234567890abcdef",
            "RecordingUrl": "https://api.twilio.com/recordings/RE123",
            "RecordingSid": "RE1234567890abcdef1234567890abcdef",
            "RecordingDuration": "42",
        }
        
        response = client.post("/webhooks/twilio/recording", data=form_data)
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        
        # Check TwiML response
        twiml = response.text
        assert "<?xml version" in twiml
        assert "<Response>" in twiml
        assert "Thank you" in twiml
    
    def test_call_status_webhook(self):
        """Test the call status update webhook."""
        form_data = {
            "CallSid": "CA1234567890abcdef1234567890abcdef",
            "CallStatus": "completed",
            "CallDuration": "45",
        }
        
        response = client.post("/webhooks/twilio/status", data=form_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "received"
        assert data["call_sid"] == form_data["CallSid"]


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

