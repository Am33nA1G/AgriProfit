"""
Background Job Scheduler

Handles periodic tasks like:
- Syncing mandi prices from data.gov.in
- Refreshing forecast cache nightly (03:00)
- Cleaning up old OTPs (future)
- Generating daily reports (future)
"""
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.integrations.data_sync import get_sync_service

logger = logging.getLogger(__name__)


def sync_prices_job() -> None:
    """Job to sync prices from data.gov.in API."""
    logger.info("Starting scheduled price sync...")
    service = get_sync_service()
    result = service.sync()
    logger.info(
        f"Scheduled sync finished: status={result.status.value} "
        f"records={result.records_fetched} "
        f"duration={result.duration_seconds:.1f}s"
    )


def refresh_forecast_cache_job() -> None:
    """Nightly job: regenerate stale forecast_cache entries.

    Runs at 03:00 daily (2 hours after the price sync at 01:00).
    Only regenerates entries where expires_at < now().
    Incorporates new price data since last refresh.
    """
    logger.info("Starting nightly forecast cache refresh...")
    try:
        from app.database.session import SessionLocal
        from app.forecast.service import ForecastService
        from app.models.forecast_cache import ForecastCache
        from sqlalchemy import select
        from datetime import datetime, timezone

        db = SessionLocal()
        try:
            stale = db.execute(
                select(
                    ForecastCache.commodity_name,
                    ForecastCache.district_name,
                ).where(
                    ForecastCache.expires_at < datetime.now(timezone.utc)
                ).distinct()
            ).all()

            service = ForecastService(db)
            refreshed = 0
            for row in stale:
                try:
                    service.get_forecast(row.commodity_name, row.district_name, 14)
                    refreshed += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to refresh {row.commodity_name}/{row.district_name}: {e}"
                    )

            logger.info(f"Forecast cache refresh complete: {refreshed} entries refreshed")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Forecast cache refresh job failed: {e}", exc_info=True)


def trigger_startup_sync() -> None:
    """
    Trigger an initial price sync on application startup.
    
    Runs in a background thread so it doesn't block the startup process.
    """
    if not settings.price_sync_enabled:
        logger.info("Startup sync skipped (PRICE_SYNC_ENABLED=false)")
        return
    
    def run_sync():
        logger.info("Triggering startup price sync...")
        service = get_sync_service()
        result = service.sync()
        logger.info(
            f"Startup sync finished: status={result.status.value} "
            f"records={result.records_fetched} "
            f"duration={result.duration_seconds:.1f}s"
        )
    
    # Run in background thread so startup isn't blocked
    thread = threading.Thread(target=run_sync, daemon=True, name="StartupSync")
    thread.start()
    logger.info("Startup sync initiated in background thread")


def start_scheduler() -> BackgroundScheduler:
    """
    Start the background scheduler.

    Reads interval from settings.price_sync_interval_hours.
    Skips starting if settings.price_sync_enabled is False.

    Returns:
        The started BackgroundScheduler instance.
    """
    if not settings.price_sync_enabled:
        logger.info("Price sync scheduler is disabled (PRICE_SYNC_ENABLED=false)")
        return None

    interval_hours = settings.price_sync_interval_hours
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        sync_prices_job,
        trigger=IntervalTrigger(hours=interval_hours),
        id="sync_prices",
        name="Sync Mandi Prices",
        replace_existing=True,
    )

    scheduler.add_job(
        refresh_forecast_cache_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="refresh_forecast_cache",
        name="Nightly Forecast Cache Refresh",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started. Price sync every {interval_hours} hours. "
        f"Forecast cache refresh at 03:00 daily."
    )

    return scheduler
