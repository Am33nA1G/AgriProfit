"""
Train RandomForest yield prediction models per crop category.

Phase 8 additions:
  - KNN imputation (k=5, distance-weighted) for soil features — preserves spatial
    correlation better than median fill.
  - Per-crop RF models for HIGH_DATA_CROPS (rice, wheat, onion, …) saved as
    yield_rf_{slug}.joblib, used when sufficient data is available.
  - Feature importance logging to validate soil/weather contribution.

Usage:
    cd backend
    python -m scripts.train_yield_model
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import KNNImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import r2_score, mean_squared_error

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

CROP_CATEGORIES = {
    "food_grains": ["rice", "wheat", "maize", "bajra", "jowar", "barley"],
    "pulses": ["arhar", "moong", "urad", "chana", "lentil"],
    "oilseeds": ["groundnut", "mustard", "soybean", "sunflower"],
    "vegetables": ["tomato", "onion", "potato", "brinjal", "cauliflower", "carrot"],
    "fruits": ["mango", "banana", "grapes", "orange", "pomegranate"],
    "cash_crops": ["cotton", "sugarcane", "jute", "coffee"],
}

# Per-crop models trained in addition to category models
HIGH_DATA_CROPS = [
    "rice", "wheat", "maize", "cotton", "onion", "potato", "tomato",
    "sugarcane", "groundnut", "soybean",
]

# Soil/weather split — KNN for soil (spatial correlation), ffill for weather
SOIL_FEATURES = ["N_kg_ha", "P_kg_ha", "K_kg_ha", "pH", "OC_pct", "EC_dS_m"]
WEATHER_FEATURES = ["annual_rainfall_mm", "annual_rainfall_deviation_pct", "avg_temp_c", "avg_humidity"]

FEATURE_COLS = [
    "crop_encoded",
    "district_encoded",
    "yield_5yr_avg",
    "N_kg_ha", "P_kg_ha", "K_kg_ha", "pH",
    "annual_rainfall_mm", "annual_rainfall_deviation_pct",
    "avg_temp_c", "avg_humidity",
]


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def impute_soil_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    KNN imputation (k=5, distance-weighted) for soil features.
    Preserves spatial correlation better than median fill.
    Weather features use forward-fill only.
    """
    df = df.copy()

    soil_cols = [c for c in SOIL_FEATURES if c in df.columns]
    weather_cols = [c for c in WEATHER_FEATURES if c in df.columns]

    if soil_cols:
        soil_data = df[soil_cols].values
        if np.isnan(soil_data).any():
            imputer = KNNImputer(n_neighbors=5, weights="distance")
            df[soil_cols] = imputer.fit_transform(soil_data)

    for col in weather_cols:
        if df[col].isna().any():
            df[col] = df[col].ffill().fillna(0)

    return df


def log_feature_importance(
    model: RandomForestRegressor,
    feature_names: list[str],
    crop_or_category: str,
) -> None:
    """Log top feature importances; warn if soil features are near-zero."""
    importances = pd.Series(model.feature_importances_, index=feature_names)
    top5 = importances.nlargest(5)
    print(f"  Top features for {crop_or_category}:")
    for feat, imp in top5.items():
        print(f"    {feat}: {imp:.3f}")

    soil_importance = importances[
        [c for c in SOIL_FEATURES if c in importances.index]
    ].sum() if any(c in importances.index for c in SOIL_FEATURES) else 0.0

    if soil_importance < 0.05:
        print(f"  [WARN] soil features contribute only {soil_importance:.1%} — check imputation")


def train_per_crop_model(
    df: pd.DataFrame,
    crop: str,
    feature_cols: list[str],
) -> tuple:
    """
    Train individual RF model for a high-data crop.
    Saves as yield_rf_{slug}.joblib if test R² > 0 on temporal hold-out.
    Returns (model_or_None, test_r2).
    """
    crop_df = df[df["crop_name"].str.lower() == crop.lower()].copy()
    if len(crop_df) < 50:
        print(f"  [SKIP] {crop}: only {len(crop_df)} rows — need ≥ 50")
        return None, 0.0

    crop_df = impute_soil_features(crop_df)

    available_features = [c for c in feature_cols if c in crop_df.columns]
    if not available_features:
        print(f"  [SKIP] {crop}: no usable feature columns")
        return None, 0.0

    # Remaining NaN cleanup after imputation
    for col in available_features:
        col_median = crop_df[col].median()
        if not pd.isna(col_median) and crop_df[col].isna().any():
            crop_df[col] = crop_df[col].fillna(col_median)

    X = crop_df[available_features].values
    y = crop_df["yield_kg_ha"].values

    # Temporal split: last 3 years as test
    split_year = int(crop_df["year"].max()) - 3
    train_mask = crop_df["year"] <= split_year
    test_mask = crop_df["year"] > split_year

    if train_mask.sum() < 30 or test_mask.sum() < 10:
        print(
            f"  [SKIP] {crop}: insufficient train ({train_mask.sum()}) or "
            f"test ({test_mask.sum()}) rows"
        )
        return None, 0.0

    X_train, X_test = X[train_mask.values], X[test_mask.values]
    y_train, y_test = y[train_mask.values], y[test_mask.values]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train_scaled, y_train)

    train_r2 = r2_score(y_train, rf.predict(X_train_scaled))
    test_r2 = r2_score(y_test, rf.predict(X_test_scaled))
    overfit_gap = train_r2 - test_r2

    print(
        f"  {crop}: train_R²={train_r2:.3f}, test_R²={test_r2:.3f}, "
        f"gap={overfit_gap:.3f}"
    )

    if test_r2 <= 0:
        print(f"  [SKIP] {crop}: test R²={test_r2:.3f} — not saving")
        return None, test_r2

    if overfit_gap > 0.4:
        print(f"  [WARN] {crop}: high overfit gap ({overfit_gap:.3f})")

    log_feature_importance(rf, available_features, crop)

    out_path = ARTIFACTS_DIR / f"yield_rf_{slugify(crop)}.joblib"
    joblib.dump({
        "model": rf,
        "scaler": scaler,
        "feature_names": available_features,
        "crop_name": crop,
        "test_r2": round(test_r2, 4),
        "train_r2": round(train_r2, 4),
        "trained_at": datetime.utcnow().isoformat(),
    }, out_path)
    print(f"  [SAVED] {out_path.name} (test R²={test_r2:.3f})")
    return rf, test_r2

def main():
    # Load dotenv for DB logging
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
    except ImportError:
        pass

    data_path = REPO_ROOT / "data" / "features" / "yield_training_matrix.parquet"
    df = pd.read_parquet(data_path, engine="pyarrow")
    df["crop_name"] = df["crop_name"].str.strip().str.lower()
    print(f"Loaded training matrix: {df.shape}")

    # --- Encode categorical columns with LabelEncoder ---
    crop_encoder = LabelEncoder()
    df["crop_encoded"] = crop_encoder.fit_transform(df["crop_name"].astype(str))

    district_col = "district" if "district" in df.columns else None
    district_encoder = LabelEncoder()
    if district_col is not None:
        df["district_encoded"] = district_encoder.fit_transform(df[district_col].astype(str))
    else:
        df["district_encoded"] = 0
        print("WARNING: 'district' column not found — district_encoded set to 0")

    print(f"  Encoded crops: {len(crop_encoder.classes_)}, districts: {df['district_encoded'].nunique()}")

    # Only use features that actually exist in the data
    available_features = [c for c in FEATURE_COLS if c in df.columns]
    if not available_features:
        print("ERROR: No feature columns found in training matrix!")
        return
    print(f"Using features: {available_features}")

    results = []

    for category, crops in CROP_CATEGORIES.items():
        cat_df = df[df["crop_name"].isin(crops)].copy()
        crops_in_data = cat_df["crop_name"].unique().tolist()

        if len(cat_df) < 30:
            print(f"\n[SKIP] {category}: only {len(cat_df)} samples (need >= 30)")
            continue

        print(f"\n--- {category} ({len(cat_df)} samples, crops: {crops_in_data}) ---")

        # KNN imputation for soil features (Phase 8); median fallback for others
        cat_df = impute_soil_features(cat_df)

        # Drop columns where the entire column is NaN after imputation
        cat_features = []
        for col in available_features:
            col_median = cat_df[col].median()
            if pd.isna(col_median):
                print(f"  WARNING: '{col}' is entirely NaN for {category} — dropping feature")
                continue
            if cat_df[col].isna().any():
                cat_df[col] = cat_df[col].fillna(col_median)
            cat_features.append(col)

        if not cat_features:
            print(f"  [SKIP] {category}: no usable features after NaN removal")
            continue

        X = cat_df[cat_features].values
        y = cat_df["yield_kg_ha"].values

        # Split: last 3 years = test, rest = train
        max_year = int(cat_df["year"].max())
        train_mask = cat_df["year"] < max_year - 2
        test_mask = cat_df["year"] >= max_year - 2

        if train_mask.sum() == 0 or test_mask.sum() == 0:
            X_train, X_test = X, X
            y_train, y_test = y, y
            print("  WARNING: Using full data as both train and test")
        else:
            X_train, X_test = X[train_mask.values], X[test_mask.values]
            y_train, y_test = y[train_mask.values], y[test_mask.values]

        # Scale features (at this point no column should be all-NaN)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train
        rf = RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )
        rf.fit(X_train_scaled, y_train)

        # Temporal hold-out evaluation (last 3 years as test set)
        y_pred_test = rf.predict(X_test_scaled)
        test_r2 = r2_score(y_test, y_pred_test)
        test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_test)))

        # Training-set R² to expose overfitting gap
        y_pred_train = rf.predict(X_train_scaled)
        train_r2 = r2_score(y_train, y_pred_train)

        overfit_gap = train_r2 - test_r2
        print(f"  train_R2={train_r2:.4f}  test_R2={test_r2:.4f}  RMSE={test_rmse:.1f}  gap={overfit_gap:.4f}")

        # Only persist artifact if model is actually better than baseline (R² > 0)
        if test_r2 <= 0:
            print(f"  [SKIP SAVE] {category}: test_R2={test_r2:.4f} <= 0 — model worse than baseline, not saving")
            continue

        # Save artifact
        artifact_path = ARTIFACTS_DIR / f"yield_rf_{category}.joblib"
        artifact = {
            "model": rf,
            "scaler": scaler,
            "feature_names": cat_features,  # actual features used (NaN columns excluded)
            "crop_encoder": crop_encoder,
            "district_encoder": district_encoder,
            "crop_names": crops_in_data,
            "test_r2": round(test_r2, 4),       # temporal hold-out R² (honest metric)
            "train_r2": round(train_r2, 4),     # training R² (for diagnosing overfitting)
            "test_rmse": round(test_rmse, 2),
            "cv_r2_mean": round(test_r2, 4),    # backward-compat alias (same value as test_r2)
            "cv_rmse_mean": round(test_rmse, 2),
            "trained_at": datetime.utcnow().isoformat(),
        }
        joblib.dump(artifact, artifact_path)
        print(f"  Saved -> {artifact_path.name}")
        log_feature_importance(rf, cat_features, category)

        results.append({
            "category": category,
            "n_samples": len(cat_df),
            "n_crops": len(crops_in_data),
            "train_r2": round(train_r2, 4),
            "test_r2": round(test_r2, 4),
            "overfit_gap": round(overfit_gap, 4),
            "test_rmse": round(test_rmse, 2),
        })

        # DB logging (best-effort)
        try:
            import os
            db_url = os.getenv("DATABASE_URL", "")
            if db_url:
                from sqlalchemy import create_engine, text
                engine = create_engine(db_url)
                with engine.connect() as conn:
                    conn.execute(
                        text(
                            "INSERT INTO yield_model_log "
                            "(crop_category, n_samples, n_crops, cv_r2_mean, cv_rmse_mean, artifact_path) "
                            "VALUES (:cat, :ns, :nc, :r2, :rmse, :path)"
                        ),
                        {
                            "cat": category,
                            "ns": len(cat_df),
                            "nc": len(crops_in_data),
                            "r2": test_r2,
                            "rmse": test_rmse,
                            "path": str(artifact_path),
                        },
                    )
                    conn.commit()
        except Exception as e:
            print(f"  DB log skipped: {e}")

    # Summary table
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY — Category Models")
    print("=" * 60)
    if results:
        summary = pd.DataFrame(results)
        print(summary.to_string(index=False))
    else:
        print("No category models trained.")

    # ── Phase 8: Per-crop models for high-data crops ───────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 8: Per-Crop Models for High-Data Crops")
    print("=" * 60)

    per_crop_results = []
    for crop in HIGH_DATA_CROPS:
        print(f"\n[PER-CROP] {crop}")
        try:
            _, test_r2 = train_per_crop_model(df, crop, FEATURE_COLS)
            per_crop_results.append({"crop": crop, "test_r2": round(test_r2, 4)})
        except Exception as e:
            print(f"  [ERR] {crop}: {e}")

    if per_crop_results:
        print("\nPer-crop model results:")
        for r in per_crop_results:
            status = "SAVED" if r["test_r2"] > 0 else "SKIPPED (R²≤0)"
            print(f"  {r['crop']}: test_R²={r['test_r2']:.4f} [{status}]")


if __name__ == "__main__":
    main()
