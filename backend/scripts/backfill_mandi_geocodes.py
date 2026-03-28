"""
Backfill Missing Mandi Geocodes

This script geocodes existing mandis in the database that are missing
latitude/longitude coordinates. It uses the Nominatim/OpenStreetMap
geocoding service with rate limiting (1 req/sec).

Usage:
    python scripts/backfill_mandi_geocodes.py [--limit N] [--dry-run]
"""
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal
from app.models.mandi import Mandi
from app.integrations.geocoding import get_geocoding_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def backfill_geocodes(limit: int = None, dry_run: bool = False):
    """
    Backfill missing geocodes for mandis.
    
    Args:
        limit: Maximum number of mandis to process (None = all)
        dry_run: If True, don't commit changes to database
    """
    db = SessionLocal()
    geocoding_service = get_geocoding_service()
    
    try:
        # Find mandis without geocodes
        query = db.query(Mandi).filter(
            Mandi.latitude.is_(None),
            Mandi.is_active == True
        )
        
        if limit:
            query = query.limit(limit)
        
        mandis_to_geocode = query.all()
        total = len(mandis_to_geocode)
        
        if total == 0:
            logger.info("No mandis found without geocodes. All done!")
            return
        
        logger.info(f"Found {total} mandis without geocodes")
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be saved")
        
        geocoded = 0
        failed = 0
        
        for i, mandi in enumerate(mandis_to_geocode, 1):
            logger.info(
                f"[{i}/{total}] Processing: {mandi.name}, {mandi.district}, {mandi.state}"
            )
            
            try:
                coords = geocoding_service.geocode_mandi(
                    mandi_name=mandi.name,
                    district=mandi.district,
                    state=mandi.state,
                )
                
                if coords:
                    latitude, longitude = coords
                    logger.info(
                        f"  ✓ Geocoded: lat={latitude:.4f}, lon={longitude:.4f}"
                    )
                    
                    if not dry_run:
                        mandi.latitude = latitude
                        mandi.longitude = longitude
                    
                    geocoded += 1
                else:
                    logger.warning(f"  ✗ Failed to geocode")
                    failed += 1
            
            except Exception as e:
                logger.error(f"  ✗ Error geocoding: {e}")
                failed += 1
            
            # Commit every 10 mandis to avoid losing progress
            if not dry_run and (i % 10 == 0 or i == total):
                db.commit()
                logger.info(f"  💾 Progress saved ({geocoded} geocoded, {failed} failed)")
        
        if not dry_run:
            db.commit()
        
        logger.info("\n" + "="*60)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"Total processed: {total}")
        logger.info(f"Successfully geocoded: {geocoded}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success rate: {geocoded/total*100:.1f}%" if total > 0 else "N/A")
        logger.info("="*60)
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Backfill missing geocodes for mandis in the database"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of mandis to process (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without committing changes to database",
    )
    
    args = parser.parse_args()
    
    logger.info("Starting mandi geocode backfill...")
    logger.info(f"Limit: {args.limit if args.limit else 'None (process all)'}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")
    
    backfill_geocodes(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
