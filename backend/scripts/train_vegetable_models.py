"""
Train per-crop RandomForest yield models for vegetables (and fruits if data exists).

Why per-crop instead of pooled?
  The pooled vegetables model had train R²=0.88 but test R²=-0.03 (extreme overfitting).
  Per-crop models learn each crop's own district/soil/weather relationship,
  avoiding the cross-crop confusion that tanks generalisation.

Data sources (in priority order):
  1. data/crop_yields/nhb_vegetable_yields.parquet  (from download_nhb_data.py)
  2. data/features/yield_training_matrix.parquet   (existing ICRISAT data, filtered)

Usage:
    cd backend
    python -m scripts.train_vegetable_models
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import r2_score, mean_squared_error

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

VEGETABLE_CROPS = ["tomato", "onion", "potato", "brinjal", "cauliflower", "carrot"]
FRUIT_CROPS = ["mango", "banana", "grapes", "orange", "pomegranate"]

# Shared weather + soil features
BASE_FEATURES = [
    "district_encoded",
    "N_kg_ha", "P_kg_ha", "K_kg_ha", "pH",
    "annual_rainfall_mm", "annual_rainfall_deviation_pct",
    "avg_temp_c", "avg_humidity",
    "year",          # temporal trend
]

# Per-crop hyperparameters tuned for lower overfitting
# Lighter models with higher min_samples_leaf generalise better on small datasets
CROP_PARAMS = {
    "tomato":      {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 10},
    "onion":       {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 10},
    "potato":      {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 10},
    "brinjal":     {"n_estimators": 150, "max_depth": 5, "min_samples_leaf": 15},
    "cauliflower": {"n_estimators": 150, "max_depth": 5, "min_samples_leaf": 15},
    "carrot":      {"n_estimators": 150, "max_depth": 5, "min_samples_leaf": 15},
    "mango":       {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 10},
    "banana":      {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 10},
    "grapes":      {"n_estimators": 150, "max_depth": 5, "min_samples_leaf": 15},
    "orange":      {"n_estimators": 150, "max_depth": 5, "min_samples_leaf": 15},
    "pomegranate": {"n_estimators": 150, "max_depth": 5, "min_samples_leaf": 15},
}


def load_nhb_data(crop: str) -> pd.DataFrame | None:
    """Load NHB data for a crop if available."""
    paths = [
        REPO_ROOT / "data" / "crop_yields" / "nhb_vegetable_yields.parquet",
        REPO_ROOT / "data" / "crop_yields" / "nhb_fruit_yields.parquet",
    ]
    frames = []
    for p in paths:
        if p.exists():
            df = pd.read_parquet(p, engine="pyarrow")
            if "crop_name" in df.columns:
                subset = df[df["crop_name"].str.lower() == crop.lower()]
                if not subset.empty:
                    frames.append(subset)
    return pd.concat(frames, ignore_index=True) if frames else None


def load_icrisat_data(crop: str, matrix_path: Path) -> pd.DataFrame | None:
    """Load existing ICRISAT training matrix filtered to one crop."""
    if not matrix_path.exists():
        return None
    df = pd.read_parquet(matrix_path, engine="pyarrow")
    df["crop_name"] = df["crop_name"].str.strip().str.lower()
    subset = df[df["crop_name"] == crop.lower()].copy()
    return subset if not subset.empty else None


def merge_and_enrich(nhb_df: pd.DataFrame | None, icrisat_df: pd.DataFrame | None,
                     district_encoder: LabelEncoder, soil_df: pd.DataFrame | None,
                     weather_df: pd.DataFrame | None) -> pd.DataFrame | None:
    """
    Merge NHB data with soil and weather features.
    Falls back to ICRISAT training matrix (already has features joined).
    """
    if nhb_df is not None and not nhb_df.empty:
        # NHB data: needs soil + weather features joined
        df = nhb_df.copy()
        df["crop_name"] = df["crop_name"].str.lower()
        df["district"] = df["district"].str.strip()
        df["state"] = df["state"].str.strip()

        # Join soil features
        if soil_df is not None:
            df = df.merge(
                soil_df[["district", "N_kg_ha", "P_kg_ha", "K_kg_ha", "pH"]],
                on="district", how="left",
            )
        else:
            for col in ["N_kg_ha", "P_kg_ha", "K_kg_ha", "pH"]:
                df[col] = np.nan

        # Join weather features (annual averages)
        if weather_df is not None:
            annual_weather = (
                weather_df.groupby(["district", "year"])
                .agg(
                    annual_rainfall_mm=("rainfall_mm", "sum"),
                    annual_rainfall_deviation_pct=("rainfall_deviation_pct", "mean"),
                    avg_temp_c=("avg_temp_c", "mean"),
                    avg_humidity=("avg_humidity", "mean"),
                )
                .reset_index()
            )
            df = df.merge(annual_weather, on=["district", "year"], how="left")
        else:
            for col in ["annual_rainfall_mm", "annual_rainfall_deviation_pct", "avg_temp_c", "avg_humidity"]:
                df[col] = np.nan

        # Encode district
        try:
            df["district_encoded"] = district_encoder.transform(df["district"].str.lower().astype(str))
        except Exception:
            df["district_encoded"] = 0

        return df

    elif icrisat_df is not None and not icrisat_df.empty:
        # ICRISAT data: features already present in the training matrix
        df = icrisat_df.copy()
        if "district" in df.columns:
            try:
                df["district_encoded"] = district_encoder.transform(df["district"].str.lower().astype(str))
            except Exception:
                df["district_encoded"] = 0
        else:
            df["district_encoded"] = 0
        return df

    return None


def train_crop(
    crop: str,
    full_df: pd.DataFrame,
    available_features: list[str],
) -> dict | None:
    """Train a per-crop model. Returns artifact dict or None if skipped."""
    n = len(full_df)
    if n < 30:
        print(f"  [SKIP] {crop}: only {n} samples")
        return None

    # Temporal hold-out: last 3 years = test
    max_year = int(full_df["year"].max())
    train_mask = full_df["year"] < max_year - 2
    test_mask = full_df["year"] >= max_year - 2

    if train_mask.sum() < 20 or test_mask.sum() < 5:
        # Not enough temporal spread — use 80/20 random split
        from sklearn.model_selection import train_test_split
        idx_train, idx_test = train_test_split(full_df.index, test_size=0.2, random_state=42)
        train_mask = full_df.index.isin(idx_train)
        test_mask = full_df.index.isin(idx_test)
        split_type = "random-80/20"
    else:
        split_type = "temporal (last 3yr test)"

    # Fill NaN with column medians; drop all-NaN columns
    usable_features = []
    df = full_df.copy()
    for col in available_features:
        if col not in df.columns:
            continue
        median = df[col].median()
        if pd.isna(median):
            continue
        if df[col].isna().any():
            df[col] = df[col].fillna(median)
        usable_features.append(col)

    if not usable_features:
        print(f"  [SKIP] {crop}: no usable features")
        return None

    X = df[usable_features].values
    y = df["yield_kg_ha"].values

    X_train = X[train_mask.values if hasattr(train_mask, "values") else train_mask]
    X_test  = X[test_mask.values  if hasattr(test_mask,  "values") else test_mask]
    y_train = y[train_mask.values if hasattr(train_mask, "values") else train_mask]
    y_test  = y[test_mask.values  if hasattr(test_mask,  "values") else test_mask]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    params = CROP_PARAMS.get(crop, {"n_estimators": 150, "max_depth": 6, "min_samples_leaf": 10})
    rf = RandomForestRegressor(random_state=42, n_jobs=-1, **params)
    rf.fit(X_train_s, y_train)

    train_r2  = r2_score(y_train, rf.predict(X_train_s))
    test_r2   = r2_score(y_test,  rf.predict(X_test_s))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, rf.predict(X_test_s))))
    gap       = train_r2 - test_r2

    print(f"  {crop}: n={n}  split={split_type}")
    print(f"    train_R2={train_r2:.4f}  test_R2={test_r2:.4f}  gap={gap:.4f}  RMSE={test_rmse:.1f}")

    if test_r2 <= 0:
        print(f"    [SKIP SAVE] test_R2={test_r2:.4f} <= 0 — not saving")
        return None

    return {
        "model": rf,
        "scaler": scaler,
        "feature_names": usable_features,
        "crop_name": crop,
        "test_r2": round(test_r2, 4),
        "train_r2": round(train_r2, 4),
        "test_rmse": round(test_rmse, 2),
        "cv_r2_mean": round(test_r2, 4),   # backward-compat alias
        "cv_rmse_mean": round(test_rmse, 2),
        "n_samples": n,
        "trained_at": datetime.utcnow().isoformat(),
    }


def main():
    print("=" * 60)
    print("Per-Crop Vegetable / Fruit Yield Model Trainer")
    print("=" * 60)

    matrix_path = REPO_ROOT / "data" / "features" / "yield_training_matrix.parquet"
    soil_path   = REPO_ROOT / "data" / "soil-health" / "district_soil_aggregated.parquet"
    weather_path = REPO_ROOT / "data" / "features" / "weather_monthly_features.parquet"

    # Load shared reference data for feature joining
    soil_df    = pd.read_parquet(soil_path, engine="pyarrow")    if soil_path.exists()    else None
    weather_df = pd.read_parquet(weather_path, engine="pyarrow") if weather_path.exists() else None

    # Build a global district encoder across all crops
    district_encoder = LabelEncoder()
    all_districts: list[str] = []
    if matrix_path.exists():
        base = pd.read_parquet(matrix_path, engine="pyarrow")
        if "district" in base.columns:
            all_districts.extend(base["district"].str.lower().dropna().tolist())
    if soil_df is not None and "district" in soil_df.columns:
        all_districts.extend(soil_df["district"].str.lower().dropna().tolist())
    district_encoder.fit(sorted(set(all_districts)) or ["unknown"])

    crops_to_train = VEGETABLE_CROPS + FRUIT_CROPS
    results = []

    for crop in crops_to_train:
        print(f"\n--- {crop} ---")

        nhb_df     = load_nhb_data(crop)
        icrisat_df = load_icrisat_data(crop, matrix_path)

        if nhb_df is not None:
            source = "NHB"
            print(f"  Using NHB data: {len(nhb_df)} rows")
        elif icrisat_df is not None:
            source = "ICRISAT"
            print(f"  NHB not available — using ICRISAT: {len(icrisat_df)} rows")
        else:
            print(f"  [SKIP] No data for {crop}")
            continue

        full_df = merge_and_enrich(nhb_df, icrisat_df, district_encoder, soil_df, weather_df)
        if full_df is None or full_df.empty or "yield_kg_ha" not in full_df.columns:
            print(f"  [SKIP] Empty after merge")
            continue

        # Keep only rows with a valid yield
        full_df = full_df[full_df["yield_kg_ha"].notna() & (full_df["yield_kg_ha"] > 0)].copy()

        available_features = [f for f in BASE_FEATURES if f in full_df.columns]
        artifact = train_crop(crop, full_df, available_features)
        if artifact is None:
            continue

        artifact["data_source"] = source
        artifact_path = ARTIFACTS_DIR / f"yield_rf_vegetable_{crop}.joblib"
        joblib.dump(artifact, artifact_path)
        print(f"    Saved → {artifact_path.name}")

        results.append({
            "crop": crop,
            "source": source,
            "n_samples": artifact["n_samples"],
            "train_r2": artifact["train_r2"],
            "test_r2": artifact["test_r2"],
            "test_rmse": artifact["test_rmse"],
        })

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    if results:
        df_res = pd.DataFrame(results)
        print(df_res.to_string(index=False))
    else:
        print("No per-crop models trained.")
        print("Run  python -m scripts.download_nhb_data  first.")


if __name__ == "__main__":
    main()
