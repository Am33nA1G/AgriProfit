"""
Core application modules for configuration, security, logging, and monitoring.

This package provides:
- Centralized configuration management
- Rate limiting with configurable tiers
- Structured JSON logging
- Request/response middleware
- Security monitoring

Note: Imports are lazy to avoid circular dependencies during startup.
Import specific modules directly when needed (e.g., `from app.core.config import settings`).
"""

# Only export config at package level to avoid circular imports
# Other modules (rate_limit, logging_config, middleware) should be imported directly
from app.core.config import (
    settings,
    get_settings,
    Settings,
    Environment,
)

__all__ = [
    # Configuration (always available)
    "settings",
    "get_settings",
    "Settings",
    "Environment",
]


def __getattr__(name: str):
    """
    Lazy import for modules that depend on FastAPI.

    This allows `from app.core.config import settings` to work
    without loading rate_limit, logging_config, or middleware.
    """
    # Rate limiting
    if name in (
        "limiter", "critical_limit", "write_limit", "read_limit",
        "analytics_limit", "RATE_LIMIT_CRITICAL", "RATE_LIMIT_WRITE",
        "RATE_LIMIT_READ", "RATE_LIMIT_ANALYTICS",
    ):
        from app.core import rate_limit
        return getattr(rate_limit, name)

    # Logging
    if name in (
        "setup_logging", "get_logger", "get_access_logger",
        "get_security_logger", "log_auth_failure", "log_admin_action",
        "log_security_event",
    ):
        from app.core import logging_config
        return getattr(logging_config, name)

    # Middleware
    if name in (
        "RequestLoggingMiddleware", "SecurityMonitoringMiddleware",
        "ErrorLoggingMiddleware", "log_database_error", "log_external_api_error",
    ):
        from app.core import middleware
        return getattr(middleware, name)

    raise AttributeError(f"module 'app.core' has no attribute '{name}'")
