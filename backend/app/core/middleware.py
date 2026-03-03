"""
Middleware for error handling, logging, and request tracking.
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.logging import get_logger, log_error
from app.core.exceptions import BizCloneException
from app.config.settings import settings

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            duration = time.time() - start_time
            log_error(
                logger,
                exc,
                context={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": round(duration, 3),
                }
            )
            raise


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return appropriate responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle exceptions."""
        try:
            return await call_next(request)
        except BizCloneException as exc:
            # Handle custom exceptions
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.message,
                    "details": exc.details,
                    "request_id": getattr(request.state, "request_id", None),
                }
            )
        except ValueError as exc:
            # Handle validation errors
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Validation error",
                    "details": {"message": str(exc)},
                    "request_id": getattr(request.state, "request_id", None),
                }
            )
        except Exception as exc:
            # Handle unexpected exceptions
            log_error(logger, exc, context={"path": request.url.path})
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "details": {"message": str(exc)} if settings.debug else {},
                    "request_id": getattr(request.state, "request_id", None),
                }
            )


def setup_cors(app) -> None:
    """
    Setup CORS middleware.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_middleware(app) -> None:
    """
    Setup all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Add CORS
    setup_cors(app)
    
    # Add custom middleware (order matters - last added is executed first)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    logger.info("middleware_configured", middleware_count=2)

