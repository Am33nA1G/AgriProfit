#!/usr/bin/env python3
"""
Configuration validation script for AgriProfit API.

This script validates the application configuration and reports any issues.
Run this before deployment to ensure all required settings are configured.

Usage:
    python scripts/check_config.py [--env ENV]

Options:
    --env ENV    Override the environment (development, staging, production)

Exit codes:
    0 - All configuration valid
    1 - Configuration errors found
"""
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(
        description="Validate AgriProfit API configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        help="Override the environment for validation",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output errors",
    )
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Override environment if specified
    if args.env:
        os.environ["ENVIRONMENT"] = args.env

    # Import settings directly from config module (avoid __init__.py cascade)
    # This allows the script to run without all dependencies installed
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "config",
        Path(__file__).parent.parent / "app" / "core" / "config.py"
    )
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    settings = config_module.settings
    Environment = config_module.Environment

    errors = []
    warnings = []

    def info(msg: str):
        if not args.quiet:
            print(f"\033[94m[INFO]\033[0m {msg}")

    def warn(msg: str):
        warnings.append(msg)
        if not args.quiet:
            print(f"\033[93m[WARN]\033[0m {msg}")

    def error(msg: str):
        errors.append(msg)
        print(f"\033[91m[ERROR]\033[0m {msg}")

    def success(msg: str):
        if not args.quiet:
            print(f"\033[92m[OK]\033[0m {msg}")

    # Header
    if not args.quiet:
        print("=" * 60)
        print("AgriProfit API Configuration Validation")
        print("=" * 60)
        print()

    # Environment
    info(f"Environment: {settings.environment.value}")
    info(f"Debug mode: {settings.debug}")
    print()

    # ==========================================================================
    # DATABASE
    # ==========================================================================
    if not args.quiet:
        print("Database Configuration")
        print("-" * 40)

    if "CHANGEME" in settings.database_url:
        error("DATABASE_URL contains placeholder 'CHANGEME'")
    elif "localhost" in settings.database_url and settings.is_production:
        warn("DATABASE_URL points to localhost in production")
    else:
        success(f"Database URL configured")

    info(f"Pool size: {settings.database_pool_size}")
    info(f"Max overflow: {settings.database_max_overflow}")
    print()

    # ==========================================================================
    # JWT AUTHENTICATION
    # ==========================================================================
    if not args.quiet:
        print("JWT Authentication")
        print("-" * 40)

    if settings.jwt_secret_key == "your-secret-key-change-in-production":
        if settings.is_production:
            error("JWT_SECRET_KEY is using default value in production")
        else:
            warn("JWT_SECRET_KEY is using default value")
    elif "CHANGEME" in settings.jwt_secret_key:
        error("JWT_SECRET_KEY contains placeholder 'CHANGEME'")
    elif len(settings.jwt_secret_key) < 32:
        warn(f"JWT_SECRET_KEY is short ({len(settings.jwt_secret_key)} chars), recommend 32+")
    else:
        success("JWT secret key configured")

    info(f"Algorithm: {settings.jwt_algorithm}")
    info(f"Token expiry: {settings.access_token_expire_minutes} minutes")
    print()

    # ==========================================================================
    # OTP CONFIGURATION
    # ==========================================================================
    if not args.quiet:
        print("OTP Configuration")
        print("-" * 40)

    success(f"OTP length: {settings.otp_length}")
    success(f"OTP expiry: {settings.otp_expire_minutes} minutes")
    success(f"OTP cooldown: {settings.otp_cooldown_seconds} seconds")
    print()

    # ==========================================================================
    # SMS PROVIDER
    # ==========================================================================
    if not args.quiet:
        print("SMS Provider")
        print("-" * 40)

    if settings.sms_provider:
        info(f"SMS provider: {settings.sms_provider}")

        if settings.sms_provider == "fast2sms":
            if not settings.fast2sms_api_key:
                error("SMS_PROVIDER is fast2sms but FAST2SMS_API_KEY is not set")
            elif "CHANGEME" in settings.fast2sms_api_key:
                error("FAST2SMS_API_KEY contains placeholder 'CHANGEME'")
            else:
                success("Fast2SMS API key configured")

        elif settings.sms_provider == "twilio":
            if not settings.twilio_account_sid:
                error("SMS_PROVIDER is twilio but TWILIO_ACCOUNT_SID is not set")
            elif "CHANGEME" in settings.twilio_account_sid:
                error("TWILIO_ACCOUNT_SID contains placeholder 'CHANGEME'")

            if not settings.twilio_auth_token:
                error("SMS_PROVIDER is twilio but TWILIO_AUTH_TOKEN is not set")
            elif "CHANGEME" in settings.twilio_auth_token:
                error("TWILIO_AUTH_TOKEN contains placeholder 'CHANGEME'")

            if not settings.twilio_phone_number:
                error("SMS_PROVIDER is twilio but TWILIO_PHONE_NUMBER is not set")

            if settings.twilio_account_sid and settings.twilio_auth_token:
                success("Twilio credentials configured")
    else:
        if settings.is_production:
            error("SMS_PROVIDER is not set in production")
        else:
            info("SMS provider not configured (OTPs will be logged)")
    print()

    # ==========================================================================
    # CORS
    # ==========================================================================
    if not args.quiet:
        print("CORS Configuration")
        print("-" * 40)

    if "*" in settings.cors_origins:
        if settings.is_production:
            error("CORS_ORIGINS is '*' in production (security risk)")
        else:
            info("CORS allows all origins (development mode)")
    else:
        success(f"CORS origins: {', '.join(settings.cors_origins)}")
    print()

    # ==========================================================================
    # RATE LIMITING
    # ==========================================================================
    if not args.quiet:
        print("Rate Limiting")
        print("-" * 40)

    if settings.redis_url:
        if "CHANGEME" in settings.redis_url:
            error("REDIS_URL contains placeholder 'CHANGEME'")
        else:
            success(f"Redis URL configured")
    else:
        if settings.is_production:
            warn("REDIS_URL not set in production (using in-memory storage)")
        else:
            info("Using in-memory rate limit storage")

    info(f"Critical: {settings.rate_limit_critical}")
    info(f"Write: {settings.rate_limit_write}")
    info(f"Read: {settings.rate_limit_read}")
    info(f"Analytics: {settings.rate_limit_analytics}")
    print()

    # ==========================================================================
    # LOGGING
    # ==========================================================================
    if not args.quiet:
        print("Logging Configuration")
        print("-" * 40)

    log_dir = Path(settings.log_dir)
    if log_dir.exists():
        success(f"Log directory exists: {log_dir}")
    else:
        info(f"Log directory will be created: {log_dir}")

    info(f"Log level: {settings.log_level}")
    info(f"Retention: {settings.log_retention_days} days")
    print()

    # ==========================================================================
    # SECURITY
    # ==========================================================================
    if not args.quiet:
        print("Security Settings")
        print("-" * 40)

    if "*" in settings.allowed_hosts and settings.is_production:
        warn("ALLOWED_HOSTS is '*' in production")
    else:
        success(f"Allowed hosts: {', '.join(settings.allowed_hosts)}")

    if settings.https_redirect:
        success("HTTPS redirect enabled")
    elif settings.is_production:
        warn("HTTPS redirect is disabled in production")
    else:
        info("HTTPS redirect disabled")
    print()

    # ==========================================================================
    # MONITORING
    # ==========================================================================
    if not args.quiet:
        print("Monitoring")
        print("-" * 40)

    if settings.sentry_dsn:
        if "CHANGEME" in settings.sentry_dsn:
            error("SENTRY_DSN contains placeholder 'CHANGEME'")
        else:
            success("Sentry DSN configured")
    else:
        if settings.is_production:
            warn("SENTRY_DSN not set in production")
        else:
            info("Sentry not configured")
    print()

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("=" * 60)
    print("Validation Summary")
    print("=" * 60)

    if errors:
        print(f"\033[91m{len(errors)} error(s) found\033[0m")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print(f"\033[93m{len(warnings)} warning(s) found\033[0m")
        if not args.quiet:
            for w in warnings:
                print(f"  - {w}")

    if not errors and not warnings:
        print("\033[92mAll configuration valid!\033[0m")
    elif not errors:
        print("\033[92mConfiguration valid with warnings.\033[0m")

    print()

    # Exit with appropriate code
    if errors or (args.strict and warnings):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
