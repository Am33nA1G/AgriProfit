"""
Check Mandi Geocoding Progress

Quick script to check how many mandis have been geocoded.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal
from app.models.mandi import Mandi


def check_progress():
    """Check and display geocoding progress."""
    db = SessionLocal()
    
    try:
        # Count total active mandis
        total = db.query(Mandi).filter(Mandi.is_active == True).count()
        
        # Count mandis with coordinates
        with_coords = db.query(Mandi).filter(
            Mandi.is_active == True,
            Mandi.latitude.isnot(None)
        ).count()
        
        # Count mandis without coordinates
        without_coords = total - with_coords
        
        # Calculate percentage
        percentage = (with_coords / total * 100) if total > 0 else 0
        
        # Display results
        print("\n" + "="*60)
        print("MANDI GEOCODING PROGRESS")
        print("="*60)
        print(f"Total active mandis:        {total:,}")
        print(f"With coordinates:           {with_coords:,}")
        print(f"Without coordinates:        {without_coords:,}")
        print(f"Coverage:                   {percentage:.1f}%")
        print("="*60 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    check_progress()
