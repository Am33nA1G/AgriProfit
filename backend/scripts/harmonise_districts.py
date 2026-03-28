"""District Harmonisation Script — Phase 1 Plan 01-01.

Reads price, rainfall, weather, and soil datasets, then uses state-scoped
RapidFuzz fuzzy matching to map each source dataset's district names to the
canonical district names in the price dataset. Results are upserted into the
district_name_map PostgreSQL table.

Usage:
    python backend/scripts/harmonise_districts.py

The script is idempotent: re-running produces the same rows via ON CONFLICT upsert.
"""
import sys
import os
import glob
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from rapidfuzz import process, fuzz, utils as rapidfuzz_utils

# Windows UTF-8 console fix (project standard from MEMORY.md)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend/ to path for imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
_REPO_ROOT = _BACKEND_DIR.parent

sys.path.insert(0, str(_BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State name normalisation
# ---------------------------------------------------------------------------

# Explicit variant → canonical mappings (derived from actual state names across
# all four datasets: price, rainfall, weather, soil).
_STATE_NAME_OVERRIDES: dict[str, str] = {
    # Jammu & Kashmir variants
    # Note: base normalisation converts & → AND with spaces, so "J&K" → "J AND K"
    "J AND K": "JAMMU AND KASHMIR",
    "JAMMU AND KASHMIR": "JAMMU AND KASHMIR",
    # Andaman & Nicobar variants (rainfall: 'Andaman & Nicobar Island' without 's')
    "ANDAMAN AND NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
    "ANDAMAN AND NICOBAR ISLAND": "ANDAMAN AND NICOBAR ISLANDS",
    "ANDAMAN AND NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
    # Arunachal Pradesh (rainfall typo: 'Arunanchal' with double n)
    "ARUNANCHAL PRADESH": "ARUNACHAL PRADESH",
    # Dadra & Nagar Haveli variants
    # Rainfall uses 'Dadara & Nagar Havelli' (spelling errors)
    "DADRA AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADARA AND NAGAR HAVELLI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    # Daman & Diu variants
    "DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    # Delhi / NCT
    "NCT OF DELHI": "DELHI",
    "NATIONAL CAPITAL TERRITORY OF DELHI": "DELHI",
    # Telangana (split from AP in 2014 — some older datasets may not have it)
    "TELANGANA": "TELANGANA",
    # Odisha (older Orissa spelling)
    "ORISSA": "ODISHA",
    # Uttarakhand (older Uttaranchal spelling)
    "UTTARANCHAL": "UTTARAKHAND",
    # Sikkim — not in price dataset (no mandis) — map to itself, will produce unmatched rows
    "SIKKIM": "SIKKIM",
    # Ladakh — new UT (2019), not in price dataset
    "LADAKH": "LADAKH",
}


def normalise_state_name(name: str) -> str:
    """Normalise a state name to canonical form.

    Steps:
    1. Strip whitespace, uppercase, replace & with AND
    2. Check override table for known variants
    3. Return normalised form

    Args:
        name: State name in any format from any dataset.

    Returns:
        Canonical uppercase state name string.
    """
    if not name or not isinstance(name, str):
        return ""
    # Base normalisation: strip, uppercase, then replace & with AND
    # Add spaces around & first to avoid "J&K" → "JANDAK" (should be "J AND K")
    normalised = name.strip().upper()
    normalised = normalised.replace("&", " AND ")
    # Collapse multiple spaces created by the replacement
    while "  " in normalised:
        normalised = normalised.replace("  ", " ")
    normalised = normalised.strip()
    # Override table lookup
    return _STATE_NAME_OVERRIDES.get(normalised, normalised)


# ---------------------------------------------------------------------------
# Legacy state redirect table
# ---------------------------------------------------------------------------

# Some source datasets were created before Indian state reorganisations.
# A district listed under state X in a source dataset may actually be in state Y
# in the price data (which reflects the current administrative structure).
# This dict maps source state → list of additional canonical states to try.
# Matching first checks the source state; if score < 90, also checks these fallback states.
_STATE_FALLBACKS: dict[str, list[str]] = {
    # Andhra Pradesh → Telangana split (2014)
    # Pre-split rainfall data has Telangana districts listed under "Andhra Pradesh"
    "ANDHRA PRADESH": ["TELANGANA"],
    # Telangana → Andhra Pradesh (for completeness, unlikely needed)
    "TELANGANA": ["ANDHRA PRADESH"],
    # Jammu & Kashmir → Ladakh UT split (2019)
    "JAMMU AND KASHMIR": ["LADAKH"],
}


# ---------------------------------------------------------------------------
# Core matching logic (pure function — no DB access)
# ---------------------------------------------------------------------------

def match_within_state(
    source_df: pd.DataFrame,
    canonical_df: pd.DataFrame,
) -> pd.DataFrame:
    """Match source districts to canonical price districts using state-scoped RapidFuzz.

    State boundary is enforced: a source district in state X is matched against
    canonical districts in state X. If no good match (score >= 90) is found in the
    primary state, fallback states in _STATE_FALLBACKS are also checked (to handle
    historical state splits like Andhra Pradesh → Telangana in 2014).

    Args:
        source_df: DataFrame with columns [state, district_name].
            State names must already be normalised.
        canonical_df: DataFrame with columns [state, district_name].
            These are the price dataset canonical district names, normalised.

    Returns:
        DataFrame with columns:
            state             — normalised state name (from source_df)
            source_district   — original district name from source dataset
            canonical_district — matched price district name, or None if unmatched
            score             — RapidFuzz WRatio score 0-100 (0.0 if unmatched)
            match_type        — one of: 'exact', 'fuzzy_accepted', 'fuzzy_review', 'unmatched'
    """
    if source_df.empty:
        return pd.DataFrame(
            columns=["state", "source_district", "canonical_district", "score", "match_type"]
        )

    # Build a per-state lookup of canonical district names
    canonical_by_state: dict[str, list[str]] = {}
    for state in canonical_df["state"].unique():
        canonical_by_state[state] = (
            canonical_df[canonical_df["state"] == state]["district_name"]
            .drop_duplicates()
            .tolist()
        )

    results: list[tuple] = []

    for state in source_df["state"].unique():
        source_names = (
            source_df[source_df["state"] == state]["district_name"]
            .drop_duplicates()
            .tolist()
        )
        canonical_names = canonical_by_state.get(state, [])
        fallback_states = _STATE_FALLBACKS.get(state, [])
        # Build combined canonical list = primary + fallback states
        fallback_names: list[str] = []
        for fb_state in fallback_states:
            fallback_names.extend(canonical_by_state.get(fb_state, []))

        if not canonical_names and not fallback_names:
            # State not present in price canonical list — all unmatched
            for name in source_names:
                results.append((state, name, None, 0.0, "unmatched"))
            continue

        # Build combined candidate list: primary state + fallback states
        all_candidates = canonical_names + fallback_names

        # Vectorised similarity matrix: shape (len(source_names), len(all_candidates))
        # Use default_process processor for case-insensitive + punctuation-normalised comparison
        matrix = process.cdist(
            source_names,
            all_candidates,
            scorer=fuzz.WRatio,
            processor=rapidfuzz_utils.default_process,
            workers=-1,
        )

        for i, source_name in enumerate(source_names):
            row_scores = matrix[i]
            best_idx = int(row_scores.argmax())
            best_score = float(row_scores[best_idx])
            best_canonical = all_candidates[best_idx]

            # Check for exact match first (after basic normalisation: strip + uppercase)
            normalised_source = source_name.strip().upper()
            normalised_canonical = best_canonical.strip().upper()
            if normalised_source == normalised_canonical:
                results.append((state, source_name, best_canonical, best_score, "exact"))
            elif best_score >= 90:
                results.append((state, source_name, best_canonical, best_score, "fuzzy_accepted"))
            elif best_score >= 75:
                results.append((state, source_name, best_canonical, best_score, "fuzzy_review"))
            else:
                results.append((state, source_name, None, best_score, "unmatched"))

    return pd.DataFrame(
        results,
        columns=["state", "source_district", "canonical_district", "score", "match_type"],
    )


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_price_districts(parquet_path: Path) -> pd.DataFrame:
    """Load unique (state, district) pairs from price parquet.

    Returns:
        DataFrame with columns [state, district_name] — normalised state names.
    """
    logger.info("Loading price districts from %s", parquet_path)
    df = pd.read_parquet(parquet_path, columns=["state", "district"], engine="pyarrow")
    unique = df.drop_duplicates()
    unique = unique.rename(columns={"district": "district_name"})
    unique["state"] = unique["state"].apply(normalise_state_name)
    return unique.dropna(subset=["state", "district_name"])


def load_rainfall_districts(rainfall_path: Path) -> pd.DataFrame:
    """Load unique (state, district) pairs from rainfall district monthly parquet.

    The file at rainfall_path has columns: STATE, DISTRICT, year, month, rainfall
    (result of spatial join from IMD gridded data).

    Returns:
        DataFrame with columns [state, district_name] — normalised state names.
    """
    logger.info("Loading rainfall districts from %s", rainfall_path)
    df = pd.read_parquet(rainfall_path, columns=["STATE", "DISTRICT"], engine="pyarrow")
    df = df.rename(columns={"STATE": "state", "DISTRICT": "district_name"})
    df = df.drop_duplicates()
    df["state"] = df["state"].apply(normalise_state_name)
    return df.dropna(subset=["state", "district_name"])


def load_weather_districts(weather_csv: Path) -> pd.DataFrame:
    """Load unique district names from weather CSV.

    The weather CSV has columns: date, district, max_temp_c, min_temp_c,
    avg_temp_c, avg_humidity, max_wind_kph — notably NO state column.

    Since state info is absent from weather data, we return districts with a
    placeholder state of '_UNKNOWN_' and perform cross-state matching in
    match_weather_districts_global().

    Fails fast if the expected 'district' column is not present.

    Returns:
        DataFrame with columns [district_name] — no state column.
    """
    logger.info("Loading weather districts from %s", weather_csv)
    df = pd.read_csv(weather_csv, usecols=lambda c: c in {"district", "state"}, nrows=None)

    # Fail fast if district column missing
    if "district" not in df.columns:
        available = list(df.columns)
        raise ValueError(
            f"Weather CSV at {weather_csv} does not have a 'district' column. "
            f"Available columns: {available}. "
            f"Update load_weather_districts() with the correct column name."
        )

    unique_districts = df["district"].drop_duplicates().dropna().tolist()
    logger.info("Weather data: %d unique districts (no state column)", len(unique_districts))
    return pd.DataFrame({"district_name": unique_districts})


def load_soil_districts(nutrients_dir: Path) -> pd.DataFrame:
    """Load unique (state, district) pairs from soil nutrient CSVs.

    Reads all *.csv files in nutrients_dir. Each file has columns:
    cycle, state, district, block, nutrient, high, medium, low.

    Returns:
        DataFrame with columns [state, district_name] — normalised state names.
    """
    logger.info("Loading soil districts from %s", nutrients_dir)
    files = list(nutrients_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {nutrients_dir}")

    logger.info("  Reading %d soil CSV files...", len(files))
    required_cols = {"state", "district"}
    chunks = []
    for f in files:
        try:
            df = pd.read_csv(f, usecols=lambda c: c in required_cols)
            if required_cols.issubset(df.columns):
                chunks.append(df[["state", "district"]].drop_duplicates())
        except Exception as exc:
            logger.warning("Skipping %s: %s", f.name, exc)

    if not chunks:
        raise ValueError(f"No valid soil CSV files found in {nutrients_dir}")

    combined = pd.concat(chunks, ignore_index=True).drop_duplicates()
    combined = combined.rename(columns={"district": "district_name"})
    combined["state"] = combined["state"].apply(normalise_state_name)
    return combined.dropna(subset=["state", "district_name"])


# ---------------------------------------------------------------------------
# Weather-specific cross-state matching (no state column available)
# ---------------------------------------------------------------------------

def match_weather_districts_global(
    weather_districts: pd.DataFrame,
    canonical_df: pd.DataFrame,
) -> pd.DataFrame:
    """Match weather districts to canonical price districts without state scoping.

    Weather data has no state column, so we perform global matching and assign
    the matched canonical district's state. This is documented as a known
    limitation — coverage may be lower than state-scoped matching.

    Three-tier thresholds same as match_within_state:
        >= 90 → fuzzy_accepted (or exact if normalised names match)
        75-89 → fuzzy_review
        < 75  → unmatched

    Args:
        weather_districts: DataFrame with column [district_name].
        canonical_df: DataFrame with columns [state, district_name].

    Returns:
        DataFrame with columns:
            state             — matched canonical state (or '_UNKNOWN_' if unmatched)
            source_district   — weather district name
            canonical_district — matched price district name, or None
            score             — RapidFuzz WRatio score
            match_type        — 'exact', 'fuzzy_accepted', 'fuzzy_review', 'unmatched'
    """
    if weather_districts.empty:
        return pd.DataFrame(
            columns=["state", "source_district", "canonical_district", "score", "match_type"]
        )

    all_canonical = canonical_df["district_name"].drop_duplicates().tolist()
    # Build a district → state reverse lookup for the canonical dataset
    district_to_state = (
        canonical_df.drop_duplicates(subset=["district_name"])
        .set_index("district_name")["state"]
        .to_dict()
    )

    source_names = weather_districts["district_name"].drop_duplicates().tolist()

    matrix = process.cdist(
        source_names,
        all_canonical,
        scorer=fuzz.WRatio,
        processor=rapidfuzz_utils.default_process,
        workers=-1,
    )

    results: list[tuple] = []
    for i, source_name in enumerate(source_names):
        row_scores = matrix[i]
        best_idx = int(row_scores.argmax())
        best_score = float(row_scores[best_idx])
        best_canonical = all_canonical[best_idx]
        matched_state = district_to_state.get(best_canonical, "_UNKNOWN_")

        normalised_source = source_name.strip().upper()
        normalised_canonical = best_canonical.strip().upper()

        if normalised_source == normalised_canonical:
            results.append((matched_state, source_name, best_canonical, best_score, "exact"))
        elif best_score >= 90:
            results.append((matched_state, source_name, best_canonical, best_score, "fuzzy_accepted"))
        elif best_score >= 75:
            results.append((matched_state, source_name, best_canonical, best_score, "fuzzy_review"))
        else:
            results.append(("_UNKNOWN_", source_name, None, best_score, "unmatched"))

    return pd.DataFrame(
        results,
        columns=["state", "source_district", "canonical_district", "score", "match_type"],
    )


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------

def upsert_district_map(records: list[dict], source_dataset: str) -> None:
    """Upsert harmonisation results into district_name_map table.

    Uses ON CONFLICT DO UPDATE so re-running is idempotent.

    Args:
        records: List of dicts with keys:
            state_name, source_district, canonical_district, match_score, match_type
        source_dataset: One of 'rainfall', 'weather', 'soil'.
    """
    from app.database.session import SessionLocal
    from sqlalchemy import text

    if not records:
        logger.info("No records to upsert for dataset '%s'", source_dataset)
        return

    db = SessionLocal()
    try:
        batch_size = 500
        for start in range(0, len(records), batch_size):
            batch = records[start:start + batch_size]
            for rec in batch:
                db.execute(
                    text(
                        """
                        INSERT INTO district_name_map
                            (source_dataset, state_name, source_district,
                             canonical_district, match_score, match_type)
                        VALUES
                            (:source_dataset, :state_name, :source_district,
                             :canonical_district, :match_score, :match_type)
                        ON CONFLICT (source_dataset, state_name, source_district)
                        DO UPDATE SET
                            canonical_district = EXCLUDED.canonical_district,
                            match_score        = EXCLUDED.match_score,
                            match_type         = EXCLUDED.match_type
                        """
                    ),
                    {
                        "source_dataset": source_dataset,
                        "state_name": rec["state_name"],
                        "source_district": rec["source_district"],
                        "canonical_district": rec.get("canonical_district"),
                        "match_score": rec.get("match_score"),
                        "match_type": rec["match_type"],
                    },
                )
            db.commit()
            logger.info(
                "  Upserted batch %d-%d for '%s'",
                start, min(start + batch_size, len(records)), source_dataset,
            )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Coverage summary
# ---------------------------------------------------------------------------

def print_coverage_summary(match_df: pd.DataFrame, dataset_name: str) -> None:
    """Print match statistics for a dataset to stdout.

    Args:
        match_df: DataFrame returned by match_within_state or match_weather_districts_global.
        dataset_name: Human-readable label (e.g. 'rainfall', 'weather', 'soil').
    """
    total = len(match_df)
    if total == 0:
        print(f"\n[{dataset_name}] No records to summarise.")
        return

    exact = (match_df["match_type"] == "exact").sum()
    fuzzy_accepted = (match_df["match_type"] == "fuzzy_accepted").sum()
    fuzzy_review = (match_df["match_type"] == "fuzzy_review").sum()
    unmatched = (match_df["match_type"] == "unmatched").sum()
    matched = exact + fuzzy_accepted
    coverage_pct = matched / total * 100

    print(f"\n{'=' * 60}")
    print(f"  Coverage summary: {dataset_name}")
    print(f"{'=' * 60}")
    print(f"  Total source districts : {total}")
    print(f"  Exact matches          : {exact}")
    print(f"  Fuzzy accepted (>=90)  : {fuzzy_accepted}")
    print(f"  Fuzzy review (75-89)   : {fuzzy_review}")
    print(f"  Unmatched (<75)        : {unmatched}")
    print(f"  Coverage (exact+fuzzy) : {matched}/{total} = {coverage_pct:.1f}%")

    if dataset_name == "rainfall" and coverage_pct < 95.0:
        print(f"  WARNING: rainfall coverage {coverage_pct:.1f}% is below 95% target!")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point: load all datasets, match districts, upsert to DB."""
    # Resolve data paths relative to repo root
    price_parquet = _REPO_ROOT / "agmarknet_daily_10yr.parquet"
    rainfall_parquet = _REPO_ROOT / "data" / "ranifall_data" / "combined" / "rainfall_district_monthly.parquet"
    weather_csv = _REPO_ROOT / "data" / "weather data" / "india_weather_daily_10years.csv"
    soil_nutrients_dir = _REPO_ROOT / "data" / "soil-health" / "nutrients"

    # Validate paths
    for path in [price_parquet, rainfall_parquet, weather_csv]:
        if not path.exists():
            raise FileNotFoundError(f"Required data file not found: {path}")
    if not soil_nutrients_dir.is_dir():
        raise FileNotFoundError(f"Soil nutrients directory not found: {soil_nutrients_dir}")

    # 1. Load canonical price districts
    logger.info("Step 1: Loading canonical price districts...")
    canonical_df = load_price_districts(price_parquet)
    logger.info("  Price dataset: %d unique (state, district) pairs across %d states",
                len(canonical_df), canonical_df["state"].nunique())

    # 2. Rainfall matching
    logger.info("\nStep 2: Matching rainfall districts...")
    rainfall_df = load_rainfall_districts(rainfall_parquet)
    logger.info("  Rainfall: %d unique districts", len(rainfall_df))
    rainfall_match = match_within_state(rainfall_df, canonical_df)
    print_coverage_summary(rainfall_match, "rainfall")

    rainfall_records = [
        {
            "state_name": row["state"],
            "source_district": row["source_district"],
            "canonical_district": row["canonical_district"],
            "match_score": row["score"],
            "match_type": row["match_type"],
        }
        for _, row in rainfall_match.iterrows()
    ]
    upsert_district_map(rainfall_records, "rainfall")

    # 3. Weather matching (no state column — global matching)
    logger.info("\nStep 3: Matching weather districts (no state column — global matching)...")
    weather_df = load_weather_districts(weather_csv)
    weather_match = match_weather_districts_global(weather_df, canonical_df)
    print_coverage_summary(weather_match, "weather")

    weather_records = [
        {
            "state_name": row["state"],
            "source_district": row["source_district"],
            "canonical_district": row["canonical_district"],
            "match_score": row["score"],
            "match_type": row["match_type"],
        }
        for _, row in weather_match.iterrows()
    ]
    upsert_district_map(weather_records, "weather")

    # 4. Soil matching
    logger.info("\nStep 4: Matching soil districts...")
    soil_df = load_soil_districts(soil_nutrients_dir)
    logger.info("  Soil: %d unique (state, district) pairs across %d states",
                len(soil_df), soil_df["state"].nunique())
    soil_match = match_within_state(soil_df, canonical_df)
    print_coverage_summary(soil_match, "soil")

    soil_records = [
        {
            "state_name": row["state"],
            "source_district": row["source_district"],
            "canonical_district": row["canonical_district"],
            "match_score": row["score"],
            "match_type": row["match_type"],
        }
        for _, row in soil_match.iterrows()
    ]
    upsert_district_map(soil_records, "soil")

    # 5. Final summary
    logger.info("\nDistrict harmonisation complete.")
    soil_states_matched = soil_match[
        soil_match["match_type"].isin(["exact", "fuzzy_accepted"])
    ]["state"].nunique()
    logger.info("  Soil states with at least one matched district: %d", soil_states_matched)
    if soil_states_matched < 31:
        logger.warning(
            "  WARNING: Only %d of 31 expected soil states have matched districts!", soil_states_matched
        )


if __name__ == "__main__":
    main()
