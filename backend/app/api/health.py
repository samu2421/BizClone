"""
Health check endpoints.
"""
from fastapi import APIRouter, status
from datetime import datetime, timezone

from app.schemas.health import HealthCheck
from app.config.settings import settings
from app.core.logging import get_logger
from app.db import check_db_connection

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthCheck,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health status of the application and its services"
)
async def health_check() -> HealthCheck:
    """
    Perform a health check on the application.
    
    Returns:
        HealthCheck: Current health status of the application
    """
    logger.debug("health_check_requested")

    # Check database connection
    db_healthy = check_db_connection()

    services = {
        "api": "healthy",
        "database": "healthy" if db_healthy else "unhealthy",
        # Will add Redis check in later steps
    }

    # Overall status is healthy only if all services are healthy
    overall_status = "healthy" if all(
        status == "healthy" for status in services.values()
    ) else "unhealthy"
    
    health_status = HealthCheck(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version=settings.app_version,
        environment=settings.environment,
        services=services
    )
    
    logger.info("health_check_completed", status=health_status.status)
    
    return health_status


@router.get(
    "/ping",
    status_code=status.HTTP_200_OK,
    summary="Ping",
    description="Simple ping endpoint to check if the service is running"
)
async def ping() -> dict:
    """
    Simple ping endpoint.
    
    Returns:
        dict: Pong response with timestamp
    """
    return {
        "message": "pong",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

