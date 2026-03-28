"""
Request logging and monitoring middleware.

This module provides:
- Request ID injection for tracing
- Request/response logging
- Performance monitoring (slow request warnings)
- Error logging
"""
import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.logging_config import get_access_logger, get_security_logger


# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths to exclude from logging (health checks, static files)
EXCLUDED_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}

# Threshold for slow request warning (in seconds)
SLOW_REQUEST_THRESHOLD = 1.0

# Headers to exclude from logging (sensitive)
EXCLUDED_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
}


# =============================================================================
# REQUEST LOGGING MIDDLEWARE
# =============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Features:
    - Adds unique request ID to each request
    - Logs request details (method, path, status, duration)
    - Warns on slow requests (>1 second)
    - Excludes sensitive data from logs
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.access_logger = get_access_logger()
        self.app_logger = logging.getLogger("app")

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Skip logging for excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Store request ID in state for access in routes
        request.state.request_id = request_id

        # Record start time
        start_time = time.perf_counter()

        # Get client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")

        # Process request
        response = None
        error = None

        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            raise
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time
            duration_ms = round(duration * 1000, 2)

            # Get user ID if available
            user_id = self._get_user_id(request)

            # Build log data
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params) if request.query_params else None,
                "status_code": response.status_code if response else 500,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "user_agent": user_agent[:100] if user_agent else None,  # Truncate long UAs
                "user_id": str(user_id) if user_id else None,
            }

            # Log the request
            if error:
                self.access_logger.error(
                    f"{request.method} {request.url.path} - Error",
                    extra={**log_data, "error": str(error)},
                )
            elif duration > SLOW_REQUEST_THRESHOLD:
                self.access_logger.warning(
                    f"{request.method} {request.url.path} - Slow request ({duration_ms}ms)",
                    extra=log_data,
                )
            else:
                self.access_logger.info(
                    f"{request.method} {request.url.path} - {response.status_code if response else 'N/A'}",
                    extra=log_data,
                )

        # Add request ID to response headers
        if response:
            response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Get the real client IP address.

        Checks X-Forwarded-For header for proxied requests.
        """
        # Check for forwarded header (when behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_id(self, request: Request) -> str | None:
        """Get user ID from request state if available."""
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return str(user.id)
        return None


# =============================================================================
# SECURITY MONITORING MIDDLEWARE
# =============================================================================

class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security monitoring.

    Features:
    - Tracks failed authentication attempts
    - Monitors admin endpoints
    - Logs suspicious activity
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.security_logger = get_security_logger()
        self._auth_failures: dict[str, int] = {}  # IP -> failure count

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        # Track authentication failures
        if self._is_auth_endpoint(request.url.path):
            if response.status_code in (400, 401, 403):
                self._track_auth_failure(request)

        # Log admin actions
        if self._is_admin_endpoint(request.url.path):
            if request.method in ("POST", "PUT", "DELETE"):
                self._log_admin_endpoint_access(request, response)

        return response

    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if path is an authentication endpoint."""
        return path.startswith("/auth/")

    def _is_admin_endpoint(self, path: str) -> bool:
        """Check if path is an admin endpoint."""
        return "/admin" in path or path.endswith("/admin-override")

    def _track_auth_failure(self, request: Request) -> None:
        """Track and log authentication failures."""
        client_ip = self._get_client_ip(request)

        # Increment failure count
        self._auth_failures[client_ip] = self._auth_failures.get(client_ip, 0) + 1
        failure_count = self._auth_failures[client_ip]

        # Log warning for repeated failures
        if failure_count >= 3:
            self.security_logger.warning(
                "Multiple auth failures from IP",
                extra={
                    "event": "auth_failure_threshold",
                    "client_ip": client_ip,
                    "failure_count": failure_count,
                    "path": request.url.path,
                }
            )

        # Reset counter after some time (in production, use Redis with TTL)
        if failure_count > 10:
            self._auth_failures[client_ip] = 0

    def _log_admin_endpoint_access(self, request: Request, response: Response) -> None:
        """Log access to admin endpoints."""
        user_id = None
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            user_id = str(user.id)

        self.security_logger.info(
            f"Admin endpoint accessed: {request.method} {request.url.path}",
            extra={
                "event": "admin_endpoint_access",
                "method": request.method,
                "path": request.url.path,
                "user_id": user_id,
                "client_ip": self._get_client_ip(request),
                "status_code": response.status_code,
            }
        )

    def _get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"


# =============================================================================
# ERROR LOGGING MIDDLEWARE
# =============================================================================

class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging unhandled errors.

    Captures exceptions and logs them with full context.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("app.errors")

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # Get request context
            request_id = getattr(request.state, "request_id", "unknown")

            self.logger.exception(
                f"Unhandled exception in {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )

            # Return a proper JSON 500 response instead of re-raising.
            # Re-raising would propagate the exception past CORSMiddleware's `send`
            # wrapper, causing CORS headers to be absent on error responses.
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )


# =============================================================================
# DATABASE ERROR LOGGING
# =============================================================================

def log_database_error(error: Exception, operation: str, **kwargs) -> None:
    """
    Log database errors with context.

    Args:
        error: The exception that occurred
        operation: Description of the database operation
        **kwargs: Additional context (table, query, etc.)
    """
    logger = logging.getLogger("app.database")

    logger.error(
        f"Database error during {operation}",
        extra={
            "event": "database_error",
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            **kwargs,
        }
    )


# =============================================================================
# EXTERNAL API LOGGING
# =============================================================================

def log_external_api_error(
    service_name: str,
    endpoint: str,
    status_code: int | None,
    error: Exception | None,
    duration_ms: float,
) -> None:
    """
    Log external API call failures.

    Args:
        service_name: Name of the external service
        endpoint: The API endpoint called
        status_code: HTTP status code (if available)
        error: Exception (if any)
        duration_ms: Request duration in milliseconds
    """
    logger = logging.getLogger("app.external")

    logger.error(
        f"External API error: {service_name}",
        extra={
            "event": "external_api_error",
            "service": service_name,
            "endpoint": endpoint,
            "status_code": status_code,
            "error_type": type(error).__name__ if error else None,
            "error_message": str(error) if error else None,
            "duration_ms": duration_ms,
        }
    )
