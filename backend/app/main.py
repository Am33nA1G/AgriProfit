"""
AgriProfit API - Agricultural Commodity Price Tracking Platform

A comprehensive REST API for tracking agricultural commodity prices across
Kerala's mandis (markets), providing price forecasts, community features,
and analytics for farmers and agricultural stakeholders.

This module initializes the FastAPI application with all routes, middleware,
and configuration settings.
"""
from dotenv import load_dotenv
load_dotenv()  # MUST be first - before any app imports that read env vars

import sys
from contextlib import asynccontextmanager

from app.database.base import Base
from app.database.session import engine
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Core modules (config, logging, rate limiting, middleware)
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.core.middleware import (
    RequestLoggingMiddleware,
    SecurityMonitoringMiddleware,
    ErrorLoggingMiddleware,
)

# ROUTER IMPORTS
from app.auth.routes import router as auth_router
from app.commodities.routes import router as commodities_router
from app.mandi.routes import router as mandis_router
from app.users.routes import router as users_router
from app.prices.routes import router as prices_router
from app.forecasts.routes import router as forecasts_router
from app.community.routes import router as community_router
from app.notifications.routes import router as notifications_router
from app.admin.routes import router as admin_router
from app.analytics.routes import router as analytics_router
from app.transport.routes import router as transport_router
from app.uploads.routes import router as uploads_router
from app.inventory.routes import router as inventory_router
from app.sales.routes import router as sales_router
from app.seasonal.routes import router as seasonal_router
from app.forecast.routes import router as forecast_ml_router
from app.soil_advisor.routes import router as soil_advisor_router
from app.arbitrage.routes import router as arbitrage_router
from app.harvest_advisor.routes import router as harvest_advisor_router
from app.advisory.routes import router as advisory_router


# =============================================================================
# API METADATA & TAGS
# =============================================================================

API_TITLE = settings.api_title
API_VERSION = settings.api_version
API_DESCRIPTION = """
## Agricultural Commodity Price Tracking & Forecasting Platform

AgriProfit empowers Kerala's farmers with real-time market intelligence,
price forecasts, and community support.

### Key Features

* **Price Tracking** - Real-time prices from 100+ mandis across Kerala
* **Price Forecasts** - ML-powered predictions for informed selling decisions
* **Community** - Connect with fellow farmers, share tips and market insights
* **Notifications** - Price alerts, weather updates, and market announcements
* **Analytics** - Trends, comparisons, and market statistics

### Authentication

Most endpoints require JWT authentication. Obtain a token via OTP-based phone verification:

1. Request OTP: `POST /auth/request-otp`
2. Verify OTP: `POST /auth/verify-otp` (returns JWT token)
3. Include token: `Authorization: Bearer <token>`

### Rate Limits

* OTP requests: 1 per 60 seconds per phone number
* API calls: 100 requests per minute per user

### Support

For issues or feedback, contact the development team.
"""

# Tag metadata for grouping endpoints in docs
TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Health check endpoints for monitoring and load balancers.",
    },
    {
        "name": "Authentication",
        "description": "OTP-based phone authentication. Request OTP, verify, and receive JWT tokens.",
    },
    {
        "name": "Users",
        "description": "User profile management. View and update profiles, admin user management.",
    },
    {
        "name": "Commodities",
        "description": "Agricultural commodities catalog. Rice, wheat, vegetables, spices, and more.",
    },
    {
        "name": "Mandis",
        "description": "Market (mandi) directory. Kerala's agricultural markets with locations and details.",
    },
    {
        "name": "Prices",
        "description": "Historical price data. Daily min/max/modal prices by commodity and mandi.",
    },
    {
        "name": "Forecasts",
        "description": "ML-powered price predictions. Future price forecasts with confidence scores.",
    },
    {
        "name": "Community",
        "description": "Community posts and discussions. Tips, questions, and market insights from farmers.",
    },
    {
        "name": "Notifications",
        "description": "User notifications. Price alerts, announcements, and system messages.",
    },
    {
        "name": "Admin",
        "description": "Administrative actions log. Audit trail for admin operations (admin only).",
    },
    {
        "name": "Analytics",
        "description": "Market analytics and insights. Trends, statistics, comparisons, and dashboards.",
    },
    {
        "name": "Transport",
        "description": "Transport cost calculator. Compare costs and find optimal mandi for selling produce.",
    },
    {
        "name": "Seasonal",
        "description": "Seasonal price calendar. View best and worst months to sell your produce based on 10 years of data.",
    },
    {
        "name": "Forecast",
        "description": "XGBoost price forecasts. 7-day and 14-day predictions with confidence band.",
    },
    {
        "name": "Soil Advisor",
        "description": "ICAR-based soil crop advisor. State → district → block drill-down showing NPK/pH distributions, ranked crop recommendations, and fertiliser advice cards.",
    },
    {
        "name": "Arbitrage",
        "description": "Mandi arbitrage signals. Top-3 destination mandis ranked by net profit per quintal after freight, spoilage, and all mandi fees. Results filtered by configurable margin threshold (default 10%).",
    },
    {
        "name": "Harvest Advisor",
        "description": "AI-powered harvest recommendations. Get top crop recommendations ranked by expected profit per hectare with weather warnings for the season.",
    },
    {
        "name": "Advisory",
        "description": "Conservative 7-day directional price advisories with hard abstention when model confidence or data quality is insufficient.",
    },
]


# =============================================================================
# LIFESPAN EVENT HANDLER
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.

    Startup:
    - Validate configuration
    - Configure logging
    - Initialize rate limiter
    - Start price sync scheduler

    Shutdown:
    - Cleanup resources
    - Stop scheduler
    """
    # Startup
    setup_logging()
    logger = get_logger("app")

    # Validate configuration in production
    if settings.is_production:
        validation_errors = settings.validate_production_settings()
        if validation_errors:
            for error in validation_errors:
                logger.error(f"Configuration error: {error}")
            logger.critical("Startup aborted due to configuration errors")
            sys.exit(1)

    # Log startup with configuration info
    logger.info(
        "AgriProfit API starting up",
        extra={
            "version": API_VERSION,
            "environment": settings.environment.value,
            "debug": settings.debug,
        }
    )

    # Start background scheduler for price syncing
    scheduler = None
    try:
        from app.integrations.scheduler import start_scheduler, trigger_startup_sync
        scheduler = start_scheduler()
        logger.info("Background scheduler started for automatic price syncing")
        
        # Trigger initial sync on startup
        trigger_startup_sync()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        logger.warning("API will continue without automatic price syncing")

    # Attach ML model LRU cache to app.state
    try:
        from app.ml.loader import get_model_cache
        app.state.model_cache = get_model_cache()
        logger.info("ML model LRU cache attached to app.state")
    except Exception as e:
        logger.error(f"Failed to attach model cache: {e}", exc_info=True)

    # Load climatological normals for serving-time exog construction
    try:
        from app.ml.serving_exog import load_climatological_normals
        load_climatological_normals()
        logger.info("Climatological normals loaded for forecast serving")
    except Exception as e:
        logger.error(f"Failed to load climatological normals: {e}", exc_info=True)
        logger.warning("Forecast serving will use constant weather defaults")

    yield

    # Shutdown
    if scheduler:
        try:
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}", exc_info=True)
    
    logger.info("AgriProfit API shutting down")


# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs" if settings.debug else None,  # Disable docs in production if needed
    redoc_url="/redoc" if settings.debug else None,
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "AgriProfit Development Team",
        "email": settings.api_contact_email,
    },
    license_info={
        "name": "Proprietary",
        "identifier": "LicenseRef-AgriProfit",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Local Development"},
        {"url": "https://api.agriprofit.in", "description": "Production"},
        {"url": "https://staging-api.agriprofit.in", "description": "Staging"},
    ],
    lifespan=lifespan,
    debug=settings.debug,
)

# Initialize rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# =============================================================================
# CUSTOM OPENAPI SCHEMA
# =============================================================================

def custom_openapi():
    """Generate custom OpenAPI schema with additional metadata."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
        tags=TAGS_METADATA,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /auth/verify-otp endpoint",
        }
    }

    # Add global security requirement for protected endpoints
    # Individual endpoints can override this
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Add additional info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://agriprofit.in/logo.png",
        "altText": "AgriProfit Logo",
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# =============================================================================
# MIDDLEWARE (order matters - first added = last executed)
# =============================================================================

# Add cache-control headers to prevent browser caching of API responses
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Add cache-control headers to API responses to ensure fresh data."""
    response = await call_next(request)
    # Only add no-cache headers for API endpoints, not static files
    if not request.url.path.startswith("/uploads/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Error logging middleware (catch unhandled exceptions)
app.add_middleware(ErrorLoggingMiddleware)

# Security monitoring middleware (track auth failures, admin actions)
app.add_middleware(SecurityMonitoringMiddleware)

# Request logging middleware (log all requests with timing)
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware must be added LAST so it becomes the outermost user middleware.
# This ensures its `send` wrapper injects Access-Control-Allow-Origin headers into
# ALL responses including 4xx/5xx errors, which is required by the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# =============================================================================
# ROUTERS
# =============================================================================

app.include_router(auth_router, prefix="/api/v1")
app.include_router(commodities_router, prefix="/api/v1")
app.include_router(mandis_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(prices_router, prefix="/api/v1")
app.include_router(forecasts_router, prefix="/api/v1")
app.include_router(community_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(transport_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(sales_router, prefix="/api/v1")
app.include_router(seasonal_router, prefix="/api/v1")
app.include_router(forecast_ml_router, prefix="/api/v1")
app.include_router(soil_advisor_router, prefix="/api/v1")
app.include_router(arbitrage_router, prefix="/api/v1")
app.include_router(harvest_advisor_router, prefix="/api/v1")
app.include_router(advisory_router, prefix="/api/v1")


# =============================================================================
# STATIC FILES (Uploads)
# =============================================================================

# Create uploads directory if it doesn't exist
UPLOADS_DIR = Path("uploads/images")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for serving uploaded images
app.mount("/uploads/images", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and healthy. Used by load balancers and monitoring systems.",
    responses={
        200: {
            "description": "API is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "healthy", "version": "1.0.0"}
                }
            }
        }
    }
)
def health_check():
    """
    Perform a health check on the API.

    Returns a simple status indicating the API is running.
    This endpoint does not require authentication and is used
    by load balancers and monitoring systems.

    Returns:
        dict: Health status with API version
    """
    return {"status": "healthy", "version": API_VERSION}


@app.get(
    "/sync/status",
    tags=["Health"],
    summary="Data Sync Status",
    description="Check the status of the background price data sync service.",
    responses={
        200: {
            "description": "Sync status information",
            "content": {
                "application/json": {
                    "example": {
                        "status": "idle",
                        "total_syncs": 5,
                        "total_failures": 0,
                        "last_success_at": "2026-02-06T06:00:00",
                        "last_sync": {
                            "status": "success",
                            "records_fetched": 6000,
                            "duration_seconds": 12.5,
                        },
                    }
                }
            },
        }
    },
)
def sync_status():
    """
    Get the current status of the price data sync service.

    Returns sync state including last run time, record counts,
    and error information if any.
    """
    from app.integrations.data_sync import get_sync_service
    return get_sync_service().get_status_dict()


@app.get(
    "/",
    tags=["Health"],
    summary="API Root",
    description="Welcome endpoint with API information and documentation links.",
    responses={
        200: {
            "description": "API information",
            "content": {
                "application/json": {
                    "example": {
                        "name": "AgriProfit API",
                        "version": "1.0.0",
                        "docs": "/docs",
                        "redoc": "/redoc"
                    }
                }
            }
        }
    }
)
def root():
    """
    API root endpoint with welcome message and documentation links.

    Returns:
        dict: API name, version, and documentation URLs
    """
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "description": "Agricultural Commodity Price Tracking Platform",
        "docs": "/docs",
        "redoc": "/redoc",
    }
