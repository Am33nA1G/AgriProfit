"""
CLI Commands for data.gov.in Integration

Usage:
    python -m app.cli seed-from-api [--limit N]
    python -m app.cli sync-prices
"""
import argparse
import logging
import sys
import os

# Load .env file before importing modules that need env vars
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_seed_from_api(args):
    """Seed database from data.gov.in API."""
    from app.integrations.seeder import seed_from_api
    
    logger.info("Starting database seed from data.gov.in...")
    logger.info(f"Limit: {args.limit or 'All records'}")
    
    seed_from_api(limit=args.limit)
    logger.info("Seed complete!")


def cmd_start_scheduler(args):
    """Start background scheduler process."""
    from app.integrations.scheduler import start_scheduler
    import time
    
    scheduler = start_scheduler()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


def cmd_sync_prices(args):
    """Sync latest prices from API (incremental update)."""
    from app.integrations.seeder import seed_from_api
    
    logger.info("Syncing latest prices from data.gov.in...")
    # Fetch only today's data (API returns current day by default)
    seed_from_api(limit=None)
    logger.info("Sync complete!")


def cmd_geocode_mandis(args):
    """Geocode mandis that don't have lat/lon coordinates."""
    from app.database.session import SessionLocal
    from app.models.mandi import Mandi
    from app.core.geocoding import geocoding_service
    
    logger.info("Starting mandi geocoding...")
    
    db = SessionLocal()
    try:
        # Find mandis without coordinates
        mandis_to_geocode = db.query(Mandi).filter(
            (Mandi.latitude == None) | (Mandi.longitude == None)
        ).all()
        
        total = len(mandis_to_geocode)
        logger.info(f"Found {total} mandis without coordinates")
        
        if total == 0:
            logger.info("All mandis already have coordinates!")
            return
        
        if not args.force and total > 50:
            confirm = input(f"This will geocode {total} mandis. Continue? (y/n): ")
            if confirm.lower() != 'y':
                logger.info("Cancelled by user")
                return
        
        success_count = 0
        failed_count = 0
        
        for i, mandi in enumerate(mandis_to_geocode, 1):
            logger.info(f"[{i}/{total}] Geocoding: {mandi.name}, {mandi.district}, {mandi.state}")
            
            coords = geocoding_service.geocode_mandi(
                name=mandi.name,
                address=mandi.address,
                district=mandi.district,
                state=mandi.state
            )
            
            if coords:
                lat, lon = coords
                mandi.latitude = lat
                mandi.longitude = lon
                db.commit()
                logger.info(f"  ✓ Success: {lat:.6f}, {lon:.6f}")
                success_count += 1
            else:
                logger.warning(f"  ✗ Failed to geocode")
                failed_count += 1
            
            # Progress update every 10 mandis
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{total} ({success_count} success, {failed_count} failed)")
        
        logger.info(f"\nGeocoding complete!")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info(f"  Total: {total}")
        
    except Exception as e:
        logger.error(f"Error during geocoding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def cmd_test_api(args):
    """Test API connection."""
    from app.integrations.data_gov_client import get_data_gov_client
    
    logger.info("Testing data.gov.in API connection...")
    client = get_data_gov_client()
    
    data = client.fetch_prices(limit=5)
    logger.info(f"Connection successful! Total records available: {data.get('total', 0)}")
    
    records = data.get("records", [])
    if records:
        logger.info("Sample records:")
        for r in records[:3]:
            logger.info(
                f"  - {r.get('commodity')} @ {r.get('market')}, {r.get('state')}: "
                f"₹{r.get('modal_price')}/quintal"
            )


def main():
    parser = argparse.ArgumentParser(
        description="AgriProfit CLI - Data Integration Commands"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # seed-from-api command
    seed_parser = subparsers.add_parser(
        "seed-from-api",
        help="Seed database from data.gov.in API"
    )
    seed_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of records (for testing)"
    )
    seed_parser.set_defaults(func=cmd_seed_from_api)
    
    # sync-prices command
    sync_parser = subparsers.add_parser(
        "sync-prices",
        help="Sync latest prices from API"
    )
    sync_parser.set_defaults(func=cmd_sync_prices)
    
    # start-scheduler command
    scheduler_parser = subparsers.add_parser(
        "start-scheduler",
        help="Start background scheduler"
    )
    scheduler_parser.set_defaults(func=cmd_start_scheduler)
    
    # test-api command
    test_parser = subparsers.add_parser(
        "test-api",
        help="Test API connection"
    )
    test_parser.set_defaults(func=cmd_test_api)
    
    # geocode-mandis command
    geocode_parser = subparsers.add_parser(
        "geocode-mandis",
        help="Geocode mandis without coordinates"
    )
    geocode_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    geocode_parser.set_defaults(func=cmd_geocode_mandis)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
