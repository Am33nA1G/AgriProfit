"""
Centralized configuration management using pydantic-settings.

This module provides:
- Environment-based configuration (development, staging, production)
- Type-safe settings with validation
- Default values with environment overrides
- Singleton pattern for consistent access
"""
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# ENVIRONMENT ENUM
# =============================================================================

class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# =============================================================================
# SETTINGS CLASS
# =============================================================================

class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden via environment variables.
    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # ENVIRONMENT
    # =========================================================================
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment (development, staging, production)",
    )

    debug: bool = Field(
        default=False,
        description="Enable debug mode (auto-enabled in development)",
    )

    # =========================================================================
    # DATABASE
    # =========================================================================
    database_url: str = Field(
        ...,  # Required - no default, must be set via environment variable
        description="Database connection URL (required)",
    )

    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Database connection pool size",
    )

    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Max overflow connections beyond pool size",
    )

    database_echo: bool = Field(
        default=False,
        description="Echo SQL statements (for debugging)",
    )

    # =========================================================================
    # JWT AUTHENTICATION
    # =========================================================================
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        min_length=8,  # Relaxed for dev; validated stricter in production
        description="Secret key for JWT token signing",
    )

    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )

    access_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        ge=1,
        le=43200,  # Max 30 days
        description="JWT access token expiration in minutes",
    )

    # =========================================================================
    # OTP CONFIGURATION
    # =========================================================================
    otp_length: int = Field(
        default=6,
        ge=4,
        le=8,
        description="OTP code length",
    )

    otp_expire_minutes: int = Field(
        default=5,
        ge=1,
        le=30,
        description="OTP expiration in minutes",
    )

    otp_cooldown_seconds: int = Field(
        default=60,
        ge=2,
        le=300,
        description="Cooldown between OTP requests",
    )

    otp_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max OTP verification attempts",
    )

    # Test OTP for development mode (bypasses actual OTP generation)
    # SECURITY: Only set via env var, never hardcode
    test_otp: Optional[str] = Field(
        default="123456",
        description="Fixed OTP for testing - MUST only be set in development",
    )

    enable_test_otp: bool = Field(
        default=True,
        description="Explicitly enable test OTP (development only)",
    )

    # =========================================================================
    # SMS PROVIDER
    # =========================================================================
    sms_provider: Optional[str] = Field(
        default=None,
        description="SMS provider (fast2sms, twilio, or None for dev)",
    )

    fast2sms_api_key: Optional[str] = Field(
        default=None,
        description="Fast2SMS API key",
    )

    twilio_account_sid: Optional[str] = Field(
        default=None,
        description="Twilio account SID",
    )

    twilio_auth_token: Optional[str] = Field(
        default=None,
        description="Twilio auth token",
    )

    twilio_phone_number: Optional[str] = Field(
        default=None,
        description="Twilio sender phone number",
    )

    # =========================================================================
    # CORS
    # =========================================================================
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins (never use * in production)",
    )

    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests",
    )

    cors_allow_methods: List[str] = Field(
        default=["*"],
        description="Allowed HTTP methods for CORS",
    )

    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed headers for CORS",
    )

    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis URL for distributed rate limiting",
    )

    rate_limit_critical: str = Field(
        default="5/minute",
        description="Rate limit for critical endpoints (auth)",
    )

    rate_limit_write: str = Field(
        default="30/minute",
        description="Rate limit for write operations",
    )

    rate_limit_read: str = Field(
        default="100/minute",
        description="Rate limit for read operations",
    )

    rate_limit_analytics: str = Field(
        default="50/minute",
        description="Rate limit for analytics endpoints",
    )

    # =========================================================================
    # LOGGING
    # =========================================================================
    log_dir: Path = Field(
        default=Path("logs"),
        description="Directory for log files",
    )

    log_level: str = Field(
        default="INFO",
        description="Default log level",
    )

    log_retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Log file retention in days",
    )

    log_json_format: bool = Field(
        default=True,
        description="Use JSON format for logs",
    )

    # =========================================================================
    # SECURITY
    # =========================================================================
    allowed_hosts: List[str] = Field(
        default=["*"],
        description="Allowed host headers",
    )

    https_redirect: bool = Field(
        default=False,
        description="Redirect HTTP to HTTPS (production)",
    )

    # =========================================================================
    # API METADATA
    # =========================================================================
    api_title: str = Field(
        default="AgriProfit API",
        description="API title for documentation",
    )

    api_version: str = Field(
        default="1.0.0",
        description="API version",
    )

    api_contact_email: str = Field(
        default="support@agriprofit.in",
        description="API contact email",
    )

    # =========================================================================
    # DATA SYNC (data.gov.in)
    # =========================================================================
    data_gov_api_key: Optional[str] = Field(
        default=None,
        description="data.gov.in API key for fetching mandi prices",
    )

    data_gov_resource_id: str = Field(
        default="9ef84268-d588-465a-a308-a864a43d0070",
        description="data.gov.in resource ID for mandi price dataset",
    )

    price_sync_interval_hours: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Interval in hours between automatic price syncs",
    )

    price_sync_enabled: bool = Field(
        default=True,
        description="Enable automatic price sync scheduler",
    )

    # =========================================================================
    # ROUTING
    # =========================================================================
    osrm_base_url: str = Field(
        default="http://router.project-osrm.org/route/v1/driving",
        description="OSRM routing API base URL. Override to use self-hosted instance.",
    )
    routing_provider: str = Field(
        default="osrm",
        description="Routing provider identifier (osrm, osrm_self_hosted). For metrics/logging.",
    )

    # =========================================================================
    # TRANSPORT ECONOMICS
    # =========================================================================
    diesel_price_per_liter: float = Field(
        default=98.0,
        ge=50.0,
        le=200.0,
        description="Current diesel price in ₹/L. Affects freight rate via sensitivity coefficient.",
    )
    diesel_baseline_price: float = Field(
        default=98.0,
        ge=50.0,
        le=200.0,
        description="Baseline diesel price used for sensitivity calculation (₹/L).",
    )
    transport_weather_risk_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weather risk placeholder (0–1). Used in composite risk score calculation.",
    )
    transport_max_mandis_evaluated: int = Field(
        default=25,
        ge=5,
        le=50,
        description="Hard cap on mandis evaluated per /compare request (performance bound).",
    )

    # =========================================================================
    # ARBITRAGE
    # =========================================================================
    arbitrage_margin_threshold_pct: float = Field(
        default=10.0,
        ge=0.0,
        le=50.0,
        description="Minimum net margin (%) to display arbitrage signal. "
                    "Computed as (net_profit / gross_revenue) * 100 >= threshold. Default: 10%.",
    )

    # =========================================================================
    # MONITORING
    # =========================================================================
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking",
    )

    # =========================================================================
    # VALIDATORS
    # =========================================================================

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from comma-separated string."""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from comma-separated string."""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [method.strip() for method in v.split(",") if method.strip()]
        return v

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from comma-separated string."""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [header.strip() for header in v.split(",") if header.strip()]
        return v

    @model_validator(mode="after")
    def set_environment_defaults(self):
        """Set environment-specific defaults."""
        # Auto-enable debug in development
        if self.environment == Environment.DEVELOPMENT:
            self.debug = True

        # Enable HTTPS redirect in production
        if self.environment == Environment.PRODUCTION:
            self.https_redirect = True

        return self

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def rate_limit_storage_uri(self) -> str:
        """Get rate limit storage URI (Redis or memory)."""
        return self.redis_url if self.redis_url else "memory://"

    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================

    def validate_production_settings(self) -> List[str]:
        """
        Validate that production-required settings are configured.

        Returns a list of validation errors (empty if valid).
        """
        errors = []

        if self.jwt_secret_key == "your-secret-key-change-in-production":
            errors.append("JWT_SECRET_KEY must be changed from default in production")

        if len(self.jwt_secret_key) < 32:
            errors.append(f"JWT_SECRET_KEY should be at least 32 characters (currently {len(self.jwt_secret_key)})")

        if self.environment == Environment.PRODUCTION:
            if "*" in self.cors_origins:
                errors.append("CORS_ORIGINS should not be '*' in production")

            if not self.redis_url:
                errors.append("REDIS_URL should be set for distributed rate limiting in production")

            if not self.sentry_dsn:
                errors.append("SENTRY_DSN should be set for error tracking in production")

        return errors


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to ensure single instance throughout application.
    """
    return Settings()


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

# Global settings instance for direct import
settings = get_settings()
