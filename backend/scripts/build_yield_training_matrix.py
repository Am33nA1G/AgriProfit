"""
Build the final training matrix by joining yield, soil, and weather data.

Usage:
    cd backend
    python -m scripts.build_yield_training_matrix
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from pathlib import Path
from sklearn.preprocessing import LabelEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    yield_path = REPO_ROOT / "data" / "crop_yields" / "yield_data_clean.parquet"
    soil_path = REPO_ROOT / "data" / "soil-health" / "district_soil_aggregated.parquet"
    weather_path = REPO_ROOT / "data" / "features" / "weather_monthly_features.parquet"
    output_dir = REPO_ROOT / "data" / "features"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "yield_training_matrix.parquet"

    # --- Yield data ---
    ydf = pd.read_parquet(yield_path, engine="pyarrow")
    ydf["district_lower"] = ydf["district"].str.strip().str.lower()
    print(f"Yield data: {ydf.shape}")

    # --- Soil data (optional) ---
    soil_df = None
    if soil_path.exists():
        soil_df = pd.read_parquet(soil_path, engine="pyarrow")
        soil_df["district_lower"] = soil_df["district"].str.strip().str.lower()
        # Take latest soil values per district (already aggregated, but deduplicate)
        soil_df = soil_df.drop_duplicates(subset=["district_lower"], keep="last")
        soil_cols = ["district_lower", "N_kg_ha", "P_kg_ha", "K_kg_ha", "pH"]
        soil_df = soil_df[[c for c in soil_cols if c in soil_df.columns]]
        print(f"Soil data: {soil_df.shape}")
    else:
        print("WARNING: Soil data not found, skipping soil features")

    # --- Weather data (optional) ---
    # NOTE: Weather parquet covers 2021-2025; yield data covers 1997-2020.
    # A year-based join would produce 100% NaN. Instead, aggregate to a
    # per-district climate normal (mean across all available years) and join
    # on district only — each yield row gets its district's long-run climate profile.
    weather_df = None
    if weather_path.exists():
        wdf = pd.read_parquet(weather_path, engine="pyarrow")
        wdf["district_lower"] = wdf["district"].str.strip().str.lower()
        weather_years = sorted(wdf["year"].unique().tolist())
        print(f"  Weather parquet years: {weather_years[0]}-{weather_years[-1]} "
              f"(using as district climate normals — no year join)")

        # Climate normal per district: mean temp/humidity across all months/years;
        # mean annual rainfall (already annual so take mean across year rows)
        weather_df = (
            wdf.groupby("district_lower")
            .agg(
                annual_rainfall_mm=("annual_rainfall_mm", "mean"),
                annual_rainfall_deviation_pct=("annual_rainfall_deviation_pct", "mean"),
                avg_temp_c=("avg_temp_c", "mean"),
                avg_humidity=("avg_humidity", "mean"),
            )
            .reset_index()
        )
        print(f"Weather climate normals: {weather_df.shape} "
              f"({weather_df['district_lower'].nunique()} districts)")
    else:
        print("WARNING: Weather data not found, skipping weather features")

    # --- Join yield to soil (latest soil for all years) ---
    merged = ydf.copy()
    if soil_df is not None:
        merged = merged.merge(soil_df, on="district_lower", how="left")

    # --- Join to district climate normals (no year dimension) ---
    if weather_df is not None:
        merged = merged.merge(weather_df, on="district_lower", how="left")

    # --- Encode categorical columns ---
    crop_encoder = LabelEncoder()
    merged["crop_encoded"] = crop_encoder.fit_transform(merged["crop_name"].astype(str))

    district_encoder = LabelEncoder()
    merged["district_encoded"] = district_encoder.fit_transform(merged["district"].astype(str))

    print(f"Encoded crops: {len(crop_encoder.classes_)}, districts: {merged['district_encoded'].nunique()}")

    # Fill NaN numerics with column medians
    numeric_cols = merged.select_dtypes(include="number").columns
    for col in numeric_cols:
        if merged[col].isna().any():
            merged[col] = merged[col].fillna(merged[col].median())

    # Select output columns
    output_cols = [
        "district", "crop_name", "year", "yield_kg_ha",
        "yield_5yr_avg",
        "crop_encoded", "district_encoded",
        "N_kg_ha", "P_kg_ha", "K_kg_ha", "pH",
        "annual_rainfall_mm", "annual_rainfall_deviation_pct",
        "avg_temp_c", "avg_humidity",
    ]
    result = merged[[c for c in output_cols if c in merged.columns]].copy()
    result.to_parquet(output_path, engine="pyarrow", index=False)

    print(f"\nSaved: {output_path}")
    print(f"Shape: {result.shape}")
    print(result.head(5).to_string())


if __name__ == "__main__":
    main()
