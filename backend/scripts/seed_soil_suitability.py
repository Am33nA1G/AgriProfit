"""Seed soil_profiles and soil_crop_suitability tables from CSV files and ICAR data.

Usage:
    cd backend
    python scripts/seed_soil_suitability.py

This script is idempotent — re-running produces the same result via ON CONFLICT upsert.
Expects the soil health CSV files at data/soil-health/nutrients/*.csv relative to repo root.
"""
import sys
import os
import glob
import logging
from pathlib import Path

# Windows compatibility
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ICAR crop suitability data (hardcoded — authoritative source)
# ---------------------------------------------------------------------------

# Nutrient key -> fertiliser advice text
_FERTILISER_ADVICE_MAP = {
    "Nitrogen": "Urea (46% N) at 120-150 kg/ha for cereals; 50-80 kg/ha for legumes",
    "Phosphorus": "DAP (18% N, 46% P2O5) at 100-125 kg/ha or SSP at 250-375 kg/ha",
    "Potassium": "MOP (60% K2O) at 50-100 kg/ha based on crop requirement",
    "Organic Carbon": "FYM (farmyard manure) at 10-15 t/ha or compost at 5-7 t/ha",
    "Potential Of Hydrogen": (
        "Test soil pH; apply lime to raise pH for acidic soils (pH < 6.0) "
        "or sulfur to lower pH for alkaline soils (pH > 8.5)"
    ),
}

# Each crop: nutrient rows (N, P, K, OC) + pH row
# Format: (crop_name, nutrient, min_tolerance, ph_min, ph_max)
_ICAR_ROWS = [
    # Rice
    ("Rice", "Nitrogen", "medium", None, None),
    ("Rice", "Phosphorus", "low", None, None),
    ("Rice", "Potassium", "medium", None, None),
    ("Rice", "Organic Carbon", "medium", None, None),
    ("Rice", "Potential Of Hydrogen", "medium", 5.5, 7.0),
    # Wheat
    ("Wheat", "Nitrogen", "high", None, None),
    ("Wheat", "Phosphorus", "medium", None, None),
    ("Wheat", "Potassium", "medium", None, None),
    ("Wheat", "Organic Carbon", "medium", None, None),
    ("Wheat", "Potential Of Hydrogen", "medium", 6.0, 7.5),
    # Maize
    ("Maize", "Nitrogen", "high", None, None),
    ("Maize", "Phosphorus", "medium", None, None),
    ("Maize", "Potassium", "medium", None, None),
    ("Maize", "Organic Carbon", "medium", None, None),
    ("Maize", "Potential Of Hydrogen", "medium", 5.5, 7.0),
    # Soybean (N-fixer)
    ("Soybean", "Nitrogen", "low", None, None),
    ("Soybean", "Phosphorus", "medium", None, None),
    ("Soybean", "Potassium", "medium", None, None),
    ("Soybean", "Organic Carbon", "medium", None, None),
    ("Soybean", "Potential Of Hydrogen", "medium", 6.0, 7.0),
    # Groundnut
    ("Groundnut", "Nitrogen", "low", None, None),
    ("Groundnut", "Phosphorus", "medium", None, None),
    ("Groundnut", "Potassium", "medium", None, None),
    ("Groundnut", "Organic Carbon", "medium", None, None),
    ("Groundnut", "Potential Of Hydrogen", "medium", 5.5, 7.0),
    # Cotton
    ("Cotton", "Nitrogen", "high", None, None),
    ("Cotton", "Phosphorus", "medium", None, None),
    ("Cotton", "Potassium", "high", None, None),
    ("Cotton", "Organic Carbon", "medium", None, None),
    ("Cotton", "Potential Of Hydrogen", "medium", 6.0, 7.5),
    # Sugarcane
    ("Sugarcane", "Nitrogen", "high", None, None),
    ("Sugarcane", "Phosphorus", "medium", None, None),
    ("Sugarcane", "Potassium", "high", None, None),
    ("Sugarcane", "Organic Carbon", "medium", None, None),
    ("Sugarcane", "Potential Of Hydrogen", "medium", 6.0, 7.5),
    # Potato
    ("Potato", "Nitrogen", "medium", None, None),
    ("Potato", "Phosphorus", "medium", None, None),
    ("Potato", "Potassium", "high", None, None),
    ("Potato", "Organic Carbon", "medium", None, None),
    ("Potato", "Potential Of Hydrogen", "medium", 5.0, 6.5),
    # Tomato
    ("Tomato", "Nitrogen", "medium", None, None),
    ("Tomato", "Phosphorus", "medium", None, None),
    ("Tomato", "Potassium", "high", None, None),
    ("Tomato", "Organic Carbon", "medium", None, None),
    ("Tomato", "Potential Of Hydrogen", "medium", 5.5, 7.0),
    # Onion
    ("Onion", "Nitrogen", "medium", None, None),
    ("Onion", "Phosphorus", "high", None, None),
    ("Onion", "Potassium", "high", None, None),
    ("Onion", "Organic Carbon", "medium", None, None),
    ("Onion", "Potential Of Hydrogen", "medium", 6.0, 7.5),
    # Chickpea (N-fixer)
    ("Chickpea", "Nitrogen", "low", None, None),
    ("Chickpea", "Phosphorus", "medium", None, None),
    ("Chickpea", "Potassium", "medium", None, None),
    ("Chickpea", "Organic Carbon", "medium", None, None),
    ("Chickpea", "Potential Of Hydrogen", "medium", 6.0, 7.5),
    # Mustard
    ("Mustard", "Nitrogen", "medium", None, None),
    ("Mustard", "Phosphorus", "medium", None, None),
    ("Mustard", "Potassium", "medium", None, None),
    ("Mustard", "Organic Carbon", "medium", None, None),
    ("Mustard", "Potential Of Hydrogen", "medium", 5.5, 7.0),
    # Bajra
    ("Bajra", "Nitrogen", "medium", None, None),
    ("Bajra", "Phosphorus", "low", None, None),
    ("Bajra", "Potassium", "low", None, None),
    ("Bajra", "Organic Carbon", "medium", None, None),
    ("Bajra", "Potential Of Hydrogen", "medium", 6.0, 7.5),
    # Jowar
    ("Jowar", "Nitrogen", "medium", None, None),
    ("Jowar", "Phosphorus", "low", None, None),
    ("Jowar", "Potassium", "low", None, None),
    ("Jowar", "Organic Carbon", "medium", None, None),
    ("Jowar", "Potential Of Hydrogen", "medium", 6.0, 8.0),
    # Lentil (N-fixer)
    ("Lentil", "Nitrogen", "low", None, None),
    ("Lentil", "Phosphorus", "medium", None, None),
    ("Lentil", "Potassium", "medium", None, None),
    ("Lentil", "Organic Carbon", "medium", None, None),
    ("Lentil", "Potential Of Hydrogen", "medium", 6.0, 7.5),
]


def _parse_pct(value: str) -> int:
    """Strip % sign and convert to int. Raises ValueError on bad input."""
    return int(str(value).strip().rstrip("%"))


def seed_soil_profiles(data_dir: str, session) -> int:
    """Seed soil_profiles table from CSV files in data_dir.

    Args:
        data_dir: Path to directory containing *.csv soil health files.
        session: SQLAlchemy Session.

    Returns:
        Total number of rows inserted/upserted.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("pandas is required for seeding: pip install pandas") from exc

    from sqlalchemy import text

    pattern = str(Path(data_dir) / "*.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        logger.warning("No CSV files found in %s", data_dir)
        return 0

    logger.info("Found %d CSV files in %s", len(files), data_dir)

    upsert_sql = text(
        """
        INSERT INTO soil_profiles
            (state, district, block, cycle, nutrient, high_pct, medium_pct, low_pct)
        VALUES
            (:state, :district, :block, :cycle, :nutrient, :high_pct, :medium_pct, :low_pct)
        ON CONFLICT ON CONSTRAINT uq_soil_profile
        DO UPDATE SET
            high_pct = EXCLUDED.high_pct,
            medium_pct = EXCLUDED.medium_pct,
            low_pct = EXCLUDED.low_pct,
            seeded_at = now()
        """
    )

    chunk_size = 500
    batch = []
    total_rows = 0
    error_files = 0

    for fpath in files:
        try:
            df = pd.read_csv(fpath)
            # Expected columns: cycle, state, district, block, nutrient, high, medium, low
            required = {"cycle", "state", "district", "block", "nutrient", "high", "medium", "low"}
            missing = required - set(df.columns.str.strip().str.lower())
            if missing:
                logger.warning("Skipping %s — missing columns: %s", fpath, missing)
                error_files += 1
                continue

            # Normalize column names
            df.columns = df.columns.str.strip().str.lower()

            for _, row in df.iterrows():
                try:
                    batch.append(
                        {
                            "state": str(row["state"]).strip().upper(),
                            "district": str(row["district"]).strip().upper(),
                            "block": str(row["block"]).strip(),
                            "cycle": str(row["cycle"]).strip(),
                            "nutrient": str(row["nutrient"]).strip(),
                            "high_pct": _parse_pct(row["high"]),
                            "medium_pct": _parse_pct(row["medium"]),
                            "low_pct": _parse_pct(row["low"]),
                        }
                    )
                except (ValueError, KeyError) as exc:
                    logger.warning("Skipping malformed row in %s: %s", fpath, exc)
                    continue

                if len(batch) >= chunk_size:
                    session.execute(upsert_sql, batch)
                    session.commit()
                    total_rows += len(batch)
                    logger.debug("Committed chunk of %d rows (total so far: %d)", len(batch), total_rows)
                    batch = []

        except Exception as exc:
            logger.warning("Error reading file %s: %s", fpath, exc)
            error_files += 1
            continue

    # Flush remaining rows
    if batch:
        session.execute(upsert_sql, batch)
        session.commit()
        total_rows += len(batch)

    if error_files > 0:
        logger.warning("Skipped %d files due to errors", error_files)

    logger.info("Seeded %d soil profile rows from %d files", total_rows, len(files))
    return total_rows


def seed_soil_crop_suitability(session) -> int:
    """Seed soil_crop_suitability table from hardcoded ICAR data.

    Args:
        session: SQLAlchemy Session.

    Returns:
        Number of rows inserted/upserted.
    """
    from sqlalchemy import text

    upsert_sql = text(
        """
        INSERT INTO soil_crop_suitability
            (crop_name, nutrient, min_tolerance, ph_min, ph_max, fertiliser_advice)
        VALUES
            (:crop_name, :nutrient, :min_tolerance, :ph_min, :ph_max, :fertiliser_advice)
        ON CONFLICT ON CONSTRAINT uq_crop_nutrient
        DO UPDATE SET
            min_tolerance = EXCLUDED.min_tolerance,
            ph_min = EXCLUDED.ph_min,
            ph_max = EXCLUDED.ph_max,
            fertiliser_advice = EXCLUDED.fertiliser_advice
        """
    )

    rows = [
        {
            "crop_name": crop_name,
            "nutrient": nutrient,
            "min_tolerance": min_tolerance,
            "ph_min": ph_min,
            "ph_max": ph_max,
            "fertiliser_advice": _FERTILISER_ADVICE_MAP.get(nutrient, ""),
        }
        for (crop_name, nutrient, min_tolerance, ph_min, ph_max) in _ICAR_ROWS
    ]

    session.execute(upsert_sql, rows)
    session.commit()

    logger.info("Seeded %d crop suitability rows", len(rows))
    return len(rows)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Resolve repo root: this script lives at backend/scripts/; data/ is at repo root
    _script_dir = Path(__file__).resolve().parent
    _repo_root = _script_dir.parent.parent
    _data_dir = str(_repo_root / "data" / "soil-health" / "nutrients")

    # Add backend to sys.path so app imports work
    _backend_dir = str(_script_dir.parent)
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)

    from app.database.session import SessionLocal

    with SessionLocal() as session:
        n_profiles = seed_soil_profiles(_data_dir, session)
        n_crops = seed_soil_crop_suitability(session)
        print(f"Seeded {n_profiles} soil profile rows, {n_crops} crop suitability rows")
