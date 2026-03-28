import json
import pandas as pd
from pathlib import Path

# ================= CONFIG =================

CSV_DIR = Path("daily_prices_csv")
OUTPUT_PARQUET = "agmarknet_daily_10yr.parquet"
MIN_ROWS_PER_ENTITY = 100  # drop very sparse markets

# ========================================

print("Loading metadata...")

with open("metadata/commodities_1.json") as f:
    commodities = json.load(f)["data"]

# commodity_id -> category_id (name not needed)
commodity_to_category = {
    c.get("commodity_id") or c.get("id"): c.get("category_id")
    for c in commodities
}

# ================= INGEST =================

all_frames = []
bad_files = 0
used_files = 0

csv_files = list(CSV_DIR.glob("*.csv"))
print(f"Found {len(csv_files)} CSV files")

for csv_file in csv_files:
    try:
        df = pd.read_csv(
            csv_file,
            parse_dates=["date"],
            dtype={
                "commodity_id": "int32",
                "state_id": "int16",
                "district_id": "int32",
                "price_min": "float32",
                "price_max": "float32",
                "price_modal": "float32",
            }
        )

        required_cols = {
            "date",
            "commodity_id",
            "state_id",
            "district_id",
            "price_modal",
        }
        if not required_cols.issubset(df.columns):
            bad_files += 1
            continue

        if len(df) < MIN_ROWS_PER_ENTITY:
            continue

        # attach category_id (may be NaN for rare commodities)
        df["category_id"] = df["commodity_id"].map(commodity_to_category)

        df = df.dropna(subset=[
            "date",
            "commodity_id",
            "state_id",
            "district_id",
            "price_modal",
        ])

        df = (
            df.sort_values("date")
              .drop_duplicates(subset=[
                  "date",
                  "commodity_id",
                  "state_id",
                  "district_id",
              ])
        )

        # stable entity id
        df["entity_id"] = (
            df["commodity_id"].astype(str) + "_" +
            df["state_id"].astype(str) + "_" +
            df["district_id"].astype(str)
        )

        all_frames.append(df)
        used_files += 1

    except Exception:
        bad_files += 1
        continue

print(f"Used files: {used_files}")
print(f"Bad / skipped files: {bad_files}")

# ================= MERGE =================

print("Concatenating dataframes...")
final_df = pd.concat(all_frames, ignore_index=True)

final_df = final_df.dropna(subset=["price_modal"])
final_df = final_df.sort_values(["entity_id", "date"])

# memory tightening
final_df["commodity_id"] = final_df["commodity_id"].astype("int16")
final_df["state_id"] = final_df["state_id"].astype("int16")
final_df["district_id"] = final_df["district_id"].astype("int32")
final_df["category_id"] = final_df["category_id"].astype("Int16")

# ================= SAVE =================

print("Writing Parquet...")
final_df.to_parquet(
    OUTPUT_PARQUET,
    engine="pyarrow",
    compression="snappy",
    index=False
)

print("\nDATASET READY")
print(f"Rows: {len(final_df):,}")
print(f"Entities: {final_df['entity_id'].nunique():,}")
print(f"Columns: {list(final_df.columns)}")
print(f"Saved as: {OUTPUT_PARQUET}")

