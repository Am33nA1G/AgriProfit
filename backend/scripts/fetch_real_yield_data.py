"""
Download real crop production data for India and convert it into the
yield_data_raw.csv format expected by the pipeline.

DATA SOURCES (tried in order):
  1. Kaggle  — "sureshsuresh1995/crop-production-statistics-india"
              Requires: pip install kaggle  +  ~/.kaggle/kaggle.json
  2. data.gov.in OGPL API
              Requires: DATA_GOV_IN_API_KEY env-var or --api-key flag
  3. Bundled GitHub mirrors (several known CSVs; tried in sequence)
  4. Manual  — prints download instructions and exits

OUTPUT:
  data/crop_yields/yield_data_raw.csv   (same schema as synthetic version)
  Columns: state, district, crop_name, season, year,
           area_ha, production_tonnes, yield_kg_ha, data_source

Usage:
    cd backend
    # Method 1 – Kaggle (recommended)
    pip install kaggle
    # place kaggle.json in C:\\Users\\<you>\\.kaggle\\
    python -m scripts.fetch_real_yield_data

    # Method 2 – data.gov.in
    python -m scripts.fetch_real_yield_data --api-key YOUR_KEY

    # Dry-run (show what would be downloaded)
    python -m scripts.fetch_real_yield_data --dry-run
"""
import argparse
import io
import logging
import os
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "crop_yields" / "yield_data_raw.csv"

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ---------------------------------------------------------------------------
# Known target columns in source datasets
# ---------------------------------------------------------------------------
# data.gov.in / Kaggle dataset: "Crop Production Statistics of India"
# Typical columns: State_Name, District_Name, Crop_Year, Season, Crop,
#                  Area (hectares), Production (tonnes)
SOURCE_COL_MAP: dict[str, str] = {
    "state_name":        "state",
    "state":             "state",
    "district_name":     "district",
    "district":          "district",
    "crop_year":         "year",
    "year":              "year",
    "season":            "season",
    "crop":              "crop_name",
    "crop_name":         "crop_name",
    "area":              "area_ha",
    "area_":             "area_ha",   # data.gov.in API returns trailing underscore
    "area_ha":           "area_ha",
    "production":        "production_tonnes",
    "production_":       "production_tonnes",  # data.gov.in API returns trailing underscore
    "production_tonnes": "production_tonnes",
}

# Keep ALL crops from the source — no whitelist filter.
TARGET_CROPS: set[str] = set()  # empty = keep everything

CROP_NORMALISE: dict[str, str] = {
    "arhar/tur":              "arhar",
    "tur":                    "arhar",
    "moong(green gram)":      "moong",
    "green gram":             "moong",
    "rapeseed &mustard":      "mustard",
    "rapeseed":               "mustard",
    "rape seed":              "mustard",
    "soya beans":             "soybean",
    "gram":                   "chana",
    "cotton(lint)":           "cotton",
    "dry chillies":           "chili",
    "ragi":                   "finger_millet",
    "bajra":                  "pearl_millet",
    "jowar":                  "sorghum",
    "pome granet":            "pomegranate",
    "cowpea(lobia)":          "cowpea",
    "peas  (vegetable)":      "peas",
    "beans & mutter(vegetable)": "beans",
    "other fresh fruits":     "other_fruits",
    "other vegetables":       "other_vegetables",
    "other  rabi pulses":     "other_pulses",
    "other kharif pulses":    "other_pulses",
    "other misc. pulses":     "other_pulses",
    "other oilseeds":         "other_oilseeds",
    "other fibres":           "other_fibres",
    "small millets":          "small_millets",
    "niger seed":             "niger_seed",
    "black pepper":           "black_pepper",
    "dry ginger":             "ginger",
    "sweet potato":           "sweet_potato",
    "citrus fruit":           "citrus",
    "pome fruit":             "pome_fruit",
}

DATA_GOV_RESOURCE_ID = "35be999b-0208-4354-b557-f6ca9a5355de"
DATA_GOV_BASE = "https://api.data.gov.in/resource/{rid}"

# Public CSVs archived on GitHub (tried in order)
GITHUB_MIRRORS = [
    # Various community re-uploads of the Kaggle dataset
    "https://raw.githubusercontent.com/rishi2628/crop-yield-india/main/crop_production.csv",
    "https://raw.githubusercontent.com/SwathiMurali/Crop-Production-Analysis/master/crop_production.csv",
    "https://raw.githubusercontent.com/SubhamPaul21/Crop-Production-in-India-Analysis/main/crop_production.csv",
    "https://raw.githubusercontent.com/niteshkumarjha59/crop_production/main/crop_production.csv",
    "https://raw.githubusercontent.com/Deepthi2020/Crop-Production-Prediction/master/crop_production.csv",
    "https://raw.githubusercontent.com/AditiAgarwal21/Crop-Production-in-India/main/data/crop_production.csv",
]

KAGGLE_DATASET = "sureshsuresh1995/crop-production-statistics-india"
KAGGLE_FILENAME = "crop_production.csv"


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename source columns to pipeline schema."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={k: v for k, v in SOURCE_COL_MAP.items() if k in df.columns})
    return df


def _normalise_content(df: pd.DataFrame) -> pd.DataFrame:
    """Clean values and compute yield_kg_ha."""
    # Normalise crop names
    df["crop_name"] = (
        df["crop_name"].str.strip().str.lower()
        .replace(CROP_NORMALISE)
    )

    # Filter to target crops (empty set = keep all)
    if TARGET_CROPS:
        df = df[df["crop_name"].isin(TARGET_CROPS)].copy()

    # Normalise season
    df["season"] = df["season"].str.strip().str.lower() if "season" in df.columns else "unknown"

    # Coerce numeric columns
    for col in ("year", "area_ha", "production_tonnes"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows missing critical fields
    df = df.dropna(subset=["state", "district", "crop_name", "year",
                            "area_ha", "production_tonnes"])
    df = df[(df["area_ha"] > 0) & (df["production_tonnes"] >= 0)]
    df["year"] = df["year"].astype(int)

    # Compute yield
    df["yield_kg_ha"] = (df["production_tonnes"] * 1000.0 / df["area_ha"]).round(1)

    # Clamp unrealistic values (same range as clean_yield_data.py)
    df = df[(df["yield_kg_ha"] >= 10) & (df["yield_kg_ha"] <= 50_000)]

    df["data_source"] = "data.gov.in"

    out_cols = [
        "state", "district", "crop_name", "season", "year",
        "area_ha", "production_tonnes", "yield_kg_ha", "data_source",
    ]
    return df[[c for c in out_cols if c in df.columns]].reset_index(drop=True)


def _print_summary(df: pd.DataFrame) -> None:
    print(f"\nTotal rows:  {len(df):,}")
    print(f"States:      {df['state'].nunique()}")
    print(f"Districts:   {df['district'].nunique()}")
    print(f"Crops:       {df['crop_name'].nunique()}  {sorted(df['crop_name'].unique())}")
    print(f"Year range:  {df['year'].min()} – {df['year'].max()}")


# ---------------------------------------------------------------------------
# Download methods
# ---------------------------------------------------------------------------

def _try_kaggle(dry_run: bool = False) -> pd.DataFrame | None:
    """Download via Kaggle API (requires kaggle package + credentials)."""
    try:
        import kaggle  # noqa: F401 – just check importability
    except ImportError:
        logger.info("kaggle package not installed — skipping Kaggle method")
        return None

    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        logger.info("~/.kaggle/kaggle.json not found — skipping Kaggle method")
        return None

    if dry_run:
        logger.info("[DRY-RUN] Would download Kaggle dataset: %s", KAGGLE_DATASET)
        return pd.DataFrame()

    import tempfile
    logger.info("Downloading via Kaggle API: %s …", KAGGLE_DATASET)
    try:
        from kaggle.api.kaggle_api_extended import KaggleApiExtended
        api = KaggleApiExtended()
        api.authenticate()
        with tempfile.TemporaryDirectory() as tmpdir:
            api.dataset_download_files(KAGGLE_DATASET, path=tmpdir, unzip=True)
            csv_path = Path(tmpdir) / KAGGLE_FILENAME
            if not csv_path.exists():
                # Try any CSV in the directory
                csvs = list(Path(tmpdir).glob("*.csv"))
                if not csvs:
                    logger.warning("No CSV found in Kaggle download")
                    return None
                csv_path = csvs[0]
            df = pd.read_csv(csv_path, low_memory=False)
        logger.info("  Kaggle download OK: %d rows", len(df))
        return df
    except Exception as e:
        logger.warning("Kaggle download failed: %s", e)
        return None


def _try_data_gov_in(api_key: str, dry_run: bool = False) -> pd.DataFrame | None:
    """Download via data.gov.in OGPL API (paginated)."""
    if not api_key:
        return None

    if dry_run:
        logger.info("[DRY-RUN] Would download from data.gov.in (resource %s)", DATA_GOV_RESOURCE_ID)
        return pd.DataFrame()

    url = DATA_GOV_BASE.format(rid=DATA_GOV_RESOURCE_ID)
    all_records = []
    offset = 0
    page_size = 1000
    max_retries = 5

    logger.info("Downloading from data.gov.in (resource %s) …", DATA_GOV_RESOURCE_ID)
    while True:
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": page_size,
            "offset": offset,
        }
        # Retry with exponential backoff on timeout
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning("data.gov.in request failed at offset %d (attempt %d/%d): %s — retrying in %ds",
                                   offset, attempt + 1, max_retries, e, wait)
                    import time; time.sleep(wait)
                else:
                    logger.warning("data.gov.in request failed at offset %d after %d attempts: %s — stopping",
                                   offset, max_retries, e)
                    data = None

        if data is None:
            break

        records = data.get("records", [])
        if not records:
            break
        all_records.extend(records)
        offset += page_size
        total = data.get("total", 0)
        logger.info("  Fetched %d / %d rows …", len(all_records), total)
        if offset >= total:
            break

    if not all_records:
        return None

    df = pd.DataFrame(all_records)
    logger.info("  data.gov.in download OK: %d rows", len(df))
    return df


def _try_github_mirrors(dry_run: bool = False) -> pd.DataFrame | None:
    """Try downloading from each GitHub mirror URL in turn."""
    for url in GITHUB_MIRRORS:
        if dry_run:
            logger.info("[DRY-RUN] Would try: %s", url)
            continue
        logger.info("Trying GitHub mirror: %s", url)
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            content = resp.content

            # Handle zip files
            if url.endswith(".zip") or resp.headers.get("Content-Type", "").startswith("application/zip"):
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    csvs = [n for n in zf.namelist() if n.endswith(".csv")]
                    if not csvs:
                        continue
                    with zf.open(csvs[0]) as f:
                        df = pd.read_csv(f, low_memory=False)
            else:
                df = pd.read_csv(io.StringIO(content.decode("utf-8", errors="replace")), low_memory=False)

            if len(df) < 100:
                logger.warning("  Too few rows (%d) — skipping", len(df))
                continue

            logger.info("  OK: %d rows from %s", len(df), url)
            return df
        except Exception as e:
            logger.info("  Failed: %s", e)
            continue

    return None


def _print_manual_instructions() -> None:
    print("""
=============================================================
 MANUAL DOWNLOAD INSTRUCTIONS
=============================================================
None of the automatic methods succeeded.

Option A — Kaggle (easiest):
  1. Create a free account at https://www.kaggle.com/
  2. Go to Account → API → Create New Token → downloads kaggle.json
  3. Copy kaggle.json to C:\\Users\\<you>\\.kaggle\\kaggle.json
  4. Run:  pip install kaggle
  5. Re-run: python -m scripts.fetch_real_yield_data

Option B — Manual Kaggle download:
  1. Visit https://www.kaggle.com/datasets/sureshsuresh1995/crop-production-statistics-india
  2. Download the ZIP and extract crop_production.csv
  3. Place it at:
       data/crop_yields/crop_production_raw.csv
  4. Run:  python -m scripts.fetch_real_yield_data --local data/crop_yields/crop_production_raw.csv

Option C — data.gov.in API:
  1. Register at https://data.gov.in/ and get an API key
  2. Run:  python -m scripts.fetch_real_yield_data --api-key YOUR_KEY

Original resource IDs on data.gov.in:
  35be999b-0208-4354-b557-f6ca9a5355de  (crop production district-wise)
=============================================================
""")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download real Indian crop yield data.")
    p.add_argument("--api-key", default=os.getenv("DATA_GOV_IN_API_KEY", ""),
                   help="data.gov.in API key")
    p.add_argument("--local", default=None,
                   help="Path to a manually downloaded CSV to normalise instead of downloading")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would be downloaded without doing it")
    p.add_argument("--output", default=None,
                   help=f"Override output path (default: {OUTPUT_PATH})")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    output = Path(args.output) if args.output else OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)

    raw_df: pd.DataFrame | None = None

    # --- 0. Local file provided manually ---
    if args.local:
        local = Path(args.local)
        if not local.exists():
            logger.error("Local file not found: %s", local)
            sys.exit(1)
        logger.info("Loading local file: %s", local)
        raw_df = pd.read_csv(local, low_memory=False)

    # --- 1. Kaggle ---
    if raw_df is None:
        raw_df = _try_kaggle(dry_run=args.dry_run)

    # --- 2. data.gov.in ---
    if raw_df is None:
        raw_df = _try_data_gov_in(args.api_key, dry_run=args.dry_run)

    # --- 3. GitHub mirrors ---
    if raw_df is None:
        raw_df = _try_github_mirrors(dry_run=args.dry_run)

    if raw_df is None or (args.dry_run and raw_df.empty):
        if args.dry_run:
            logger.info("[DRY-RUN] complete — no files written")
        else:
            logger.error("All download methods failed.")
            _print_manual_instructions()
            sys.exit(1)
        return

    # --- Normalise ---
    logger.info("Normalising %d raw rows …", len(raw_df))
    df = _normalise_columns(raw_df)
    df = _normalise_content(df)

    if df.empty:
        logger.error("No usable rows after normalisation. Check source column names.")
        logger.error("Columns found: %s", list(raw_df.columns))
        sys.exit(1)

    # --- Save ---
    df.to_csv(output, index=False)
    logger.info("Saved %d rows → %s", len(df), output)
    print(f"\nSaved {len(df):,} real yield records → {output}")
    _print_summary(df)


if __name__ == "__main__":
    main()
