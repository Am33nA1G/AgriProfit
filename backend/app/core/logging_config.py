"""
Structured logging configuration for the application.

This module provides:
- JSON-formatted structured logging
- Log rotation (daily, keep 30 days)
- Separate log files for different purposes
- Environment-specific log levels
"""
import logging
import platform
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from pathlib import Path
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import settings, Environment

# Detect if running on Windows
IS_WINDOWS = platform.system() == "Windows"


# =============================================================================
# CONFIGURATION (from centralized settings)
# =============================================================================

# Environment
ENVIRONMENT = settings.environment.value

# Log levels by environment
LOG_LEVELS = {
    "development": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.WARNING,
}

# Get log level from settings or environment default
_log_level_name = settings.log_level.upper()
LOG_LEVEL = getattr(logging, _log_level_name, LOG_LEVELS.get(ENVIRONMENT, logging.INFO))

# Log directory
LOG_DIR = settings.log_dir

# Log retention (days)
LOG_RETENTION_DAYS = settings.log_retention_days

# Sensitive fields to mask in logs
SENSITIVE_FIELDS = {
    "password", "token", "access_token", "refresh_token", "otp",
    "authorization", "secret", "api_key", "credit_card", "ssn",
}


# =============================================================================
# CUSTOM JSON FORMATTER
# =============================================================================

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields.

    Adds timestamp, environment, and sanitizes sensitive data.
    """

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Add environment
        log_record["environment"] = ENVIRONMENT

        # Add log level as string
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add source location
        log_record["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Sanitize sensitive fields
        self._sanitize_record(log_record)

    def _sanitize_record(self, record: dict) -> None:
        """Mask sensitive fields in the log record."""
        for key, value in list(record.items()):
            if isinstance(value, dict):
                self._sanitize_record(value)
            elif isinstance(key, str) and key.lower() in SENSITIVE_FIELDS:
                record[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 100:
                # Truncate very long strings
                record[key] = value[:100] + "...[truncated]"


# =============================================================================
# LOGGER SETUP
# =============================================================================

def setup_logging() -> None:
    """
    Configure logging for the application.

    Creates log handlers for:
    - Console (stdout)
    - General application logs (app.log)
    - Access logs (access.log)
    - Error logs (error.log)
    - Security logs (security.log)
    """
    # Create log directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Create formatters
    json_formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s"
    )

    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ===================
    # ROOT LOGGER
    # ===================
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler (always enabled in dev, warnings+ in prod)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if ENVIRONMENT == "development" else logging.WARNING)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # ===================
    # APPLICATION LOG
    # ===================
    # Use RotatingFileHandler on Windows to avoid file locking issues
    if IS_WINDOWS:
        app_handler = RotatingFileHandler(
            LOG_DIR / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    else:
        app_handler = TimedRotatingFileHandler(
            LOG_DIR / "app.log",
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    app_handler.setLevel(LOG_LEVEL)
    app_handler.setFormatter(json_formatter)
    root_logger.addHandler(app_handler)

    # ===================
    # ACCESS LOG
    # ===================
    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False  # Don't propagate to root

    # Use RotatingFileHandler on Windows to avoid file locking issues
    if IS_WINDOWS:
        access_handler = RotatingFileHandler(
            LOG_DIR / "access.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    else:
        access_handler = TimedRotatingFileHandler(
            LOG_DIR / "access.log",
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    access_handler.setFormatter(json_formatter)
    access_logger.addHandler(access_handler)

    # ===================
    # ERROR LOG
    # ===================
    # Use RotatingFileHandler on Windows to avoid file locking issues
    if IS_WINDOWS:
        error_handler = RotatingFileHandler(
            LOG_DIR / "error.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    else:
        error_handler = TimedRotatingFileHandler(
            LOG_DIR / "error.log",
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    root_logger.addHandler(error_handler)

    # ===================
    # SECURITY LOG
    # ===================
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False

    # Use RotatingFileHandler on Windows to avoid file locking issues
    if IS_WINDOWS:
        security_handler = RotatingFileHandler(
            LOG_DIR / "security.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    else:
        security_handler = TimedRotatingFileHandler(
            LOG_DIR / "security.log",
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
    security_handler.setFormatter(json_formatter)
    security_logger.addHandler(security_handler)

    # ===================
    # SILENCE NOISY LOGGERS
    # ===================
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log startup message
    root_logger.info(
        f"Logging configured",
        extra={
            "environment": ENVIRONMENT,
            "log_level": logging.getLevelName(LOG_LEVEL),
            "log_dir": str(LOG_DIR),
        }
    )


# =============================================================================
# LOGGER GETTERS
# =============================================================================

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def get_access_logger() -> logging.Logger:
    """Get the access log logger."""
    return logging.getLogger("access")


def get_security_logger() -> logging.Logger:
    """Get the security log logger."""
    return logging.getLogger("security")


# =============================================================================
# SECURITY LOGGING HELPERS
# =============================================================================

def log_auth_failure(
    phone_number: str,
    ip_address: str,
    reason: str,
    attempt_count: int = 1,
) -> None:
    """
    Log authentication failure for security monitoring.

    Logs as WARNING for single failures, ERROR for repeated failures.
    """
    logger = get_security_logger()

    # Mask phone number partially
    masked_phone = phone_number[:3] + "****" + phone_number[-3:] if len(phone_number) >= 6 else "***"

    log_data = {
        "event": "auth_failure",
        "phone_masked": masked_phone,
        "ip_address": ip_address,
        "reason": reason,
        "attempt_count": attempt_count,
    }

    if attempt_count >= 3:
        logger.error("Repeated authentication failures detected", extra=log_data)
    else:
        logger.warning("Authentication failure", extra=log_data)


def log_admin_action(
    admin_id: str,
    action_type: str,
    target_id: str | None,
    description: str,
    ip_address: str,
) -> None:
    """Log admin action for audit trail."""
    logger = get_security_logger()

    logger.info(
        f"Admin action: {action_type}",
        extra={
            "event": "admin_action",
            "admin_id": admin_id,
            "action_type": action_type,
            "target_id": target_id,
            "description": description,
            "ip_address": ip_address,
        }
    )


def log_security_event(
    event_type: str,
    message: str,
    **kwargs: Any,
) -> None:
    """Log a general security event."""
    logger = get_security_logger()

    logger.info(
        message,
        extra={
            "event": event_type,
            **kwargs,
        }
    )
