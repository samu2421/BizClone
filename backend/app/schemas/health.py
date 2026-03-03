"""
Pydantic schemas for health check endpoints.
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class HealthCheck(BaseModel):
    """Health check response schema."""
    
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Current timestamp")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    services: Dict[str, str] = Field(default_factory=dict, description="Status of individual services")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-20T10:30:00Z",
                "version": "1.0.0",
                "environment": "development",
                "services": {
                    "database": "healthy",
                    "redis": "healthy",
                    "api": "healthy"
                }
            }
        }


class ServiceStatus(BaseModel):
    """Individual service status."""
    
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status (healthy/unhealthy/degraded)")
    message: Optional[str] = Field(None, description="Additional status message")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")

