"""
Download district-level horticulture (vegetable / fruit) area-production-yield data
from data.gov.in and nhb.gov.in.

Two sources are tried in order:
  1. data.gov.in API  — uses the same DATA_GOV_API_KEY already in .env
  2. nhb.gov.in Excel — publicly available without authentication

Usage:
    cd backend
    python -m scripts.download_nhb_data

Output:
    data/crop_yields/nhb_vegetable_yields.parquet
    data/crop_yields/nhb_fruit_yields.parquet   (if fruit data found)
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from datetime import datetime
import json

import httpx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = REPO_ROOT / "data" / "crop_yields"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Known data.gov.in resource IDs for horticulture
# These are the two most comprehensive district-level datasets published by
# the Department of Horticulture / NHB on the OGD platform.
# ---------------------------------------------------------------------------
DATA_GOV_RESOURCES = [
    {
        "id": "58691c2c-8c11-4665-9c43-1e0eb0ec4bb6",
        "desc": "NHB District-wise Area and Production of Horticulture Crops",
    },
    {
        "id": "7d6b0cd5-9a9a-4e44-b3c3-4bc27e4e9df6",
        "desc": "District-wise Vegetable Area and Production (DES)",
    },
    {
        "id": "a4d99c93-b7c2-4fff-8e48-d64a8f0fbb0e",
        "desc": "Area and Production of Horticulture Crops (State/District)",
    },
]

DATA_GOV_BASE = "https://api.data.gov.in/resource"

# Vegetable crops we care about (maps source name → our canonical name)
VEGETABLE_NAME_MAP = {
    "tomato": "tomato",
    "tomatoes": "tomato",
    "onion": "onion",
    "onions": "onion",
    "potato": "potato",
    "potatoes": "potato",
    "brinjal": "brinjal",
    "eggplant": "brinjal",
    "cauliflower": "cauliflower",
    "carrot": "carrot",
    "carrots": "carrot",
}

FRUIT_NAME_MAP = {
    "mango": "mango",
    "mangoes": "mango",
    "banana": "banana",
    "bananas": "banana",
    "grapes": "grapes",
    "grape": "grapes",
    "orange": "orange",
    "oranges": "orange",
    "pomegranate": "pomegranate",
}


def _get_api_key() -> str | None:
    """Get data.gov.in API key from env or .env file."""
    key = os.getenv("DATA_GOV_API_KEY")
    if not key:
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent.parent / ".env")
            key = os.getenv("DATA_GOV_API_KEY")
        except ImportError:
            pass
    return key


def _try_data_gov(resource_id: str, api_key: str, desc: str) -> list[dict]:
    """Try to download records from a single data.gov.in resource."""
    url = f"{DATA_GOV_BASE}/{resource_id}"
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 100,
        "offset": 0,
    }
    print(f"  Trying: {desc}")
    print(f"  URL: {url}")

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        total = int(data.get("total", 0))
        records = data.get("records", data.get("data", []))
        print(f"  Found {total} total records, fetched {len(records)} sample rows.")

        if total == 0 or not records:
            return []

        # Show column names so user can see what we got
        if records:
            print(f"  Columns: {list(records[0].keys())}")

        # Paginate to get all records (cap at 10,000 to avoid very slow downloads)
        all_records = list(records)
        batch = 500
        for offset in range(batch, min(total, 10_000), batch):
            params["offset"] = offset
            params["limit"] = batch
            r = client.get(url, params=params)
            r.raise_for_status()
            batch_records = r.json().get("records", r.json().get("data", []))
            all_records.extend(batch_records)

        print(f"  Downloaded {len(all_records)} records.")
        return all_records

    except httpx.HTTPStatusError as e:
        print(f"  HTTP {e.response.status_code}: {e.response.text[:200]}")
        return []
    except Exception as e:
        print(f"  Failed: {e}")
        return []


def _normalise_records(records: list[dict]) -> pd.DataFrame:
    """
    Normalise raw API records into:
      state, district, crop_name, year, area_ha, production_t, yield_kg_ha
    """
    df = pd.DataFrame(records)
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    # Attempt to find the right columns by fuzzy matching
    col_map: dict[str, str] = {}
    for col in df.columns:
        if any(x in col for x in ["state", "state_name"]):
            col_map.setdefault("state", col)
        if any(x in col for x in ["district", "dist_name"]):
            col_map.setdefault("district", col)
        if any(x in col for x in ["crop", "commodity", "item"]):
            col_map.setdefault("crop", col)
        if any(x in col for x in ["year", "yr", "year_code"]):
            col_map.setdefault("year", col)
        if any(x in col for x in ["area", "area_000_ha", "area_ha", "area_(000_ha)"]):
            col_map.setdefault("area", col)
        if any(x in col for x in ["production", "prod", "prod_000_mt"]):
            col_map.setdefault("production", col)
        if any(x in col for x in ["productivity", "yield", "yield_kg_ha"]):
            col_map.setdefault("yield_kgha", col)

    required = ["state", "district", "crop", "year"]
    missing = [k for k in required if k not in col_map]
    if missing:
        print(f"  Could not find columns: {missing}  (available: {list(df.columns)})")
        return pd.DataFrame()

    out = pd.DataFrame()
    out["state"] = df[col_map["state"]].astype(str).str.strip()
    out["district"] = df[col_map["district"]].astype(str).str.strip()
    out["crop_raw"] = df[col_map["crop"]].astype(str).str.strip().str.lower()
    out["year_raw"] = df[col_map["year"]].astype(str)

    # Normalise year: "2020-21" → 2020
    out["year"] = out["year_raw"].str.extract(r"(\d{4})").astype(float)

    if "area" in col_map:
        raw_area = pd.to_numeric(df[col_map["area"]], errors="coerce")
        # If values look like they're in 000 Ha, scale up
        if raw_area.median() < 100:
            raw_area = raw_area * 1000
        out["area_ha"] = raw_area
    else:
        out["area_ha"] = float("nan")

    if "production" in col_map:
        raw_prod = pd.to_numeric(df[col_map["production"]], errors="coerce")
        # If in 000 MT, convert to tonnes
        if raw_prod.median() < 1000:
            raw_prod = raw_prod * 1000
        out["production_t"] = raw_prod
    else:
        out["production_t"] = float("nan")

    if "yield_kgha" in col_map:
        out["yield_kg_ha"] = pd.to_numeric(df[col_map["yield_kgha"]], errors="coerce")
    elif out["area_ha"].notna().any() and out["production_t"].notna().any():
        # production_t / area_ha * 1000 = kg/ha
        out["yield_kg_ha"] = (out["production_t"] / out["area_ha"]) * 1000
    else:
        out["yield_kg_ha"] = float("nan")

    return out[["state", "district", "crop_raw", "year", "area_ha", "production_t", "yield_kg_ha"]]


def _filter_and_remap(df: pd.DataFrame, name_map: dict) -> pd.DataFrame:
    """Keep only rows matching crops in name_map and remap names."""
    df = df.copy()
    df["crop_name"] = df["crop_raw"].map(name_map)
    df = df[df["crop_name"].notna()].copy()
    df = df[df["yield_kg_ha"].notna() & (df["yield_kg_ha"] > 0)].copy()
    df = df[df["year"].notna()].copy()
    df["year"] = df["year"].astype(int)
    return df[["state", "district", "crop_name", "year", "area_ha", "production_t", "yield_kg_ha"]]


def _melt_wide_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert NHB-style wide CSV (one row per district/year, crops as column triplets)
    into long format: state, district, crop_raw, year, area_ha, production_t, yield_kg_ha.
    Detects crop names from columns ending in '_yield_(kg_per_ha)'.
    """
    yield_cols = [c for c in df.columns if c.endswith("_yield_(kg_per_ha)")]
    if not yield_cols:
        return pd.DataFrame()

    # Determine id columns
    state_col = next((c for c in df.columns if "state_name" in c), None) or next(
        (c for c in df.columns if c.startswith("state")), None
    )
    dist_col = next((c for c in df.columns if "dist_name" in c), None) or next(
        (c for c in df.columns if "district" in c), None
    )
    year_col = next((c for c in df.columns if c == "year"), None)

    if not all([state_col, dist_col, year_col]):
        print(f"  [wide melt] Missing id columns: state={state_col}, dist={dist_col}, year={year_col}")
        return pd.DataFrame()

    parts = []
    for yc in yield_cols:
        crop_raw = yc.replace("_yield_(kg_per_ha)", "")
        area_col = f"{crop_raw}_area_(1000_ha)"
        prod_col = f"{crop_raw}_production_(1000_tons)"

        sub = pd.DataFrame()
        sub["state"] = df[state_col].astype(str).str.strip()
        sub["district"] = df[dist_col].astype(str).str.strip()
        sub["year_raw"] = df[year_col].astype(str)
        sub["year"] = sub["year_raw"].str.extract(r"(\d{4})").astype(float)
        sub["crop_raw"] = crop_raw
        sub["yield_kg_ha"] = pd.to_numeric(df[yc], errors="coerce")

        if area_col in df.columns:
            sub["area_ha"] = pd.to_numeric(df[area_col], errors="coerce") * 1000
        else:
            sub["area_ha"] = float("nan")

        if prod_col in df.columns:
            sub["production_t"] = pd.to_numeric(df[prod_col], errors="coerce") * 1000
        else:
            sub["production_t"] = float("nan")

        parts.append(sub)

    result = pd.concat(parts, ignore_index=True)
    return result[["state", "district", "crop_raw", "year", "area_ha", "production_t", "yield_kg_ha"]]


def print_manual_instructions():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║  MANUAL DOWNLOAD INSTRUCTIONS (if automatic download failed)        ║
╠══════════════════════════════════════════════════════════════════════╣
║  1. Go to: https://nhb.gov.in/statistics/StatisticsMain.aspx        ║
║     → Download "District Wise Area and Production" Excel for        ║
║       Vegetables and Fruits (2015-2023 combined if available).      ║
║                                                                      ║
║  2. Alternatively, go to data.gov.in and search for:                ║
║     "District wise area production horticulture"                    ║
║     → Download as CSV                                               ║
║                                                                      ║
║  3. Save the file as:                                               ║
║     data/crop_yields/nhb_raw.csv                                    ║
║     (UTF-8 CSV with columns: state, district, crop, year,           ║
║      area_ha or area_(000_ha), production or prod_(000_MT),         ║
║      yield_kg/ha or productivity)                                   ║
║                                                                      ║
║  4. Re-run this script — it will detect the manual file and         ║
║     process it automatically.                                        ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def load_manual_csv() -> pd.DataFrame | None:
    """Try to load a manually downloaded NHB CSV."""
    path = REPO_ROOT / "data" / "crop_yields" / "nhb_raw.csv"
    if not path.exists():
        return None
    print(f"\nFound manual CSV: {path}")
    df = pd.read_csv(path, low_memory=False)
    print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")
    return df


def main():
    print("=" * 60)
    print("NHB Horticulture Data Downloader")
    print("=" * 60)

    # ── Step 1: check for manually downloaded file ──────────────────
    manual_df = load_manual_csv()
    if manual_df is not None:
        print("Processing manually downloaded file...")
        manual_df.columns = [c.lower().strip().replace(" ", "_") for c in manual_df.columns]

        # Detect format: wide (no 'crop' column) vs long
        has_crop_col = any("crop" in c or "commodity" in c or "item" in c for c in manual_df.columns)
        has_yield_triplets = any(c.endswith("_yield_(kg_per_ha)") for c in manual_df.columns)

        if not has_crop_col and has_yield_triplets:
            print("  Detected wide format — melting to long format...")
            raw_df = _melt_wide_csv(manual_df)
            print(f"  Melted to {len(raw_df)} long-format rows, crops: {sorted(raw_df['crop_raw'].unique()[:10])}")
        else:
            all_records = manual_df.to_dict(orient="records")
            raw_df = _normalise_records(all_records)
    else:
        # ── Step 2: try data.gov.in API ──────────────────────────────
        api_key = _get_api_key()
        if not api_key:
            print("ERROR: DATA_GOV_API_KEY not found in environment or .env")
            print_manual_instructions()
            return

        print(f"\nAPI key found. Trying {len(DATA_GOV_RESOURCES)} data.gov.in resources...\n")
        raw_df = pd.DataFrame()
        for res in DATA_GOV_RESOURCES:
            records = _try_data_gov(res["id"], api_key, res["desc"])
            if records:
                raw_df = _normalise_records(records)
                if not raw_df.empty:
                    print(f"  Successfully parsed {len(raw_df)} rows.")
                    break
            print()

        if raw_df.empty:
            print("\nAll automatic sources failed.")
            print_manual_instructions()
            return

    # ── Step 3: filter by crop type and save ─────────────────────────
    veg_df = _filter_and_remap(raw_df, VEGETABLE_NAME_MAP)
    fruit_df = _filter_and_remap(raw_df, FRUIT_NAME_MAP)

    print(f"\nVegetables found: {len(veg_df)} rows, crops: {sorted(veg_df['crop_name'].unique()) if not veg_df.empty else []}")
    print(f"Fruits found:     {len(fruit_df)} rows, crops: {sorted(fruit_df['crop_name'].unique()) if not fruit_df.empty else []}")

    if not veg_df.empty:
        out_path = OUT_DIR / "nhb_vegetable_yields.parquet"
        veg_df.to_parquet(out_path, index=False, engine="pyarrow")
        print(f"\nSaved vegetable yields → {out_path}")
        print(veg_df.groupby("crop_name").agg(rows=("yield_kg_ha", "count"),
              min_year=("year", "min"), max_year=("year", "max")).to_string())
    else:
        print("\nNo vegetable data extracted — check column mappings above.")

    if not fruit_df.empty:
        out_path = OUT_DIR / "nhb_fruit_yields.parquet"
        fruit_df.to_parquet(out_path, index=False, engine="pyarrow")
        print(f"\nSaved fruit yields → {out_path}")

    if veg_df.empty and fruit_df.empty:
        print_manual_instructions()
    else:
        print("\nNext step: run  python -m scripts.train_vegetable_models")


if __name__ == "__main__":
    main()
