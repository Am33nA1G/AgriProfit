# backend/scripts/train_soil_suitability.py
"""
Train a multi-output RandomForest crop suitability model.

Data sources (both already in repo, no external cost):
  - soil_profiles DB table  → district-level NPK/OC/pH distributions
  - data/crop_yields/yield_data_raw.csv → which crops were grown in each district

Output artifact: ml/artifacts/soil_crop_suitability_rf.joblib

Usage:
    cd backend
    python -m scripts.train_soil_suitability
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

YIELD_CSV = REPO_ROOT / "data" / "crop_yields" / "yield_data_raw.csv"
ARTIFACT_PATH = ARTIFACTS_DIR / "soil_crop_suitability_rf.joblib"

NUTRIENT_MAP = {
    "Nitrogen": "N",
    "Phosphorus": "P",
    "Potassium": "K",
    "Organic Carbon": "OC",
    "Potential Of Hydrogen": "pH",
}

# 15 soil features + 1 state encoding
FEATURE_COLS = [
    "N_high", "N_medium", "N_low",
    "P_high", "P_medium", "P_low",
    "K_high", "K_medium", "K_low",
    "OC_high", "OC_medium", "OC_low",
    "pH_high", "pH_medium", "pH_low",
    "state_enc",
]

# Aggregate crop names — not real crops, skip as labels
SKIP_CROPS = frozenset({
    "total foodgrain", "pulses total", "oilseeds total",
    "other cereals & millets", "other_oilseeds", "other_pulses",
    "other_fruits", "other_vegetables", "small_millets",
    "peas & beans (pulses)", "cond-spcs other", "jute & mesta",
})

# Minimum number of districts a crop must appear in to be a valid label.
# Crops below this threshold have too few positive examples for RF to learn.
MIN_CROP_DISTRICTS = 5


def pivot_soil_rows(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert long-format soil query results to wide-format district profiles.

    Input columns: state, district, nutrient, high_avg, med_avg, low_avg
    Output: one row per (state, district) with 15 nutrient columns
            (N_high, N_medium, N_low, P_high, ..., pH_low)

    Districts missing any of the 5 required nutrients are dropped.
    """
    raw_df = raw_df.copy()
    raw_df["state"] = raw_df["state"].str.strip().str.upper()
    raw_df["district"] = raw_df["district"].str.strip().str.upper()

    rows: dict[tuple, dict] = {}
    for _, row in raw_df.iterrows():
        key = (row["state"], row["district"])
        if key not in rows:
            rows[key] = {"state": key[0], "district": key[1]}
        prefix = NUTRIENT_MAP.get(row["nutrient"])
        if prefix:
            rows[key][f"{prefix}_high"] = float(row["high_avg"])
            rows[key][f"{prefix}_medium"] = float(row["med_avg"])
            rows[key][f"{prefix}_low"] = float(row["low_avg"])

    df = pd.DataFrame(list(rows.values()))
    soil_cols = [c for c in FEATURE_COLS if c != "state_enc"]
    return df.dropna(subset=soil_cols).reset_index(drop=True)


STATE_ALIASES = {
    "ANDAMAN AND NICOBAR ISLANDS": "ANDAMAN & NICOBAR",
    "JAMMU AND KASHMIR": "JAMMU & KASHMIR",
}


def load_yield_presence(yield_csv: Path) -> pd.DataFrame:
    """
    Build binary crop-presence pivot from yield CSV.

    Returns a DataFrame with columns:
        state_upper, district_upper, <crop1>, <crop2>, ...
    Values are 0 or 1 (was this crop grown in this district at all?).
    Meta-aggregate crops and crops present in < MIN_CROP_DISTRICTS are excluded.
    """
    df = pd.read_csv(yield_csv)
    df["state_upper"] = df["state"].str.strip().str.upper().replace(STATE_ALIASES)
    df["district_upper"] = df["district"].str.strip().str.upper()
    df["crop_name"] = df["crop_name"].str.strip().str.lower()

    df = df[~df["crop_name"].isin(SKIP_CROPS)]

    # Binary presence: 1 if crop grown in district (any year)
    presence = (
        df.groupby(["state_upper", "district_upper", "crop_name"])
        .size()
        .reset_index(name="count")
    )
    presence["present"] = 1

    pivot = presence.pivot_table(
        index=["state_upper", "district_upper"],
        columns="crop_name",
        values="present",
        fill_value=0,
    ).reset_index()
    pivot.columns.name = None  # remove the "crop_name" axis label

    # Drop crops that are too rare (fewer than MIN_CROP_DISTRICTS)
    crop_cols = [c for c in pivot.columns if c not in ("state_upper", "district_upper")]
    n_present = pivot[crop_cols].sum()
    valid_crops = n_present[n_present >= MIN_CROP_DISTRICTS].index.tolist()
    keep_cols = ["state_upper", "district_upper"] + valid_crops

    dropped = len(crop_cols) - len(valid_crops)
    if dropped:
        print(f"  Dropped {dropped} rare crops (< {MIN_CROP_DISTRICTS} districts)")

    return pivot[keep_cols]


def build_training_matrix(
    soil_df: pd.DataFrame,
    presence_df: pd.DataFrame,
    state_encoder: LabelEncoder,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Inner-join soil profiles with yield presence on (state, district).

    Fits the state_encoder on training states.
    Returns (merged_df_with_state_enc, list_of_crop_columns).
    Raises ValueError if the join produces 0 rows (name mismatch).
    """
    merged = soil_df.merge(
        presence_df,
        left_on=["state", "district"],
        right_on=["state_upper", "district_upper"],
        how="inner",
    )

    if merged.empty:
        raise ValueError(
            "No districts matched between soil and yield data. "
            "Check state/district name normalisation (both must be UPPER)."
        )

    merged["state_enc"] = state_encoder.fit_transform(merged["state"])

    crop_cols = [
        c for c in merged.columns
        if c not in ("state", "district", "state_upper", "district_upper", "state_enc")
        and c not in FEATURE_COLS
    ]

    return merged, crop_cols


def load_soil_from_db(engine) -> pd.DataFrame:
    """Aggregate soil_profiles table to district level via SQL."""
    from sqlalchemy import text

    sql = text("""
        SELECT state, district, nutrient,
               AVG(high_pct)   AS high_avg,
               AVG(medium_pct) AS med_avg,
               AVG(low_pct)    AS low_avg
        FROM soil_profiles
        GROUP BY state, district, nutrient
    """)
    raw = pd.read_sql(sql, engine)
    return pivot_soil_rows(raw)


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
    except ImportError:
        pass

    import os
    from sqlalchemy import create_engine

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in backend/.env")
        return

    engine = create_engine(db_url)

    if not YIELD_CSV.exists():
        print(f"ERROR: Yield CSV not found at {YIELD_CSV}")
        print("  Run: backend/scripts/download_yield_data.py first")
        return

    print("Loading soil district profiles from DB...")
    soil_df = load_soil_from_db(engine)
    print(f"  {len(soil_df)} districts with complete soil profiles")

    print(f"Loading yield presence matrix from {YIELD_CSV.name}...")
    presence_df = load_yield_presence(YIELD_CSV)
    crop_col_count = len([c for c in presence_df.columns if c not in ("state_upper", "district_upper")])
    print(f"  {len(presence_df)} district rows, {crop_col_count} valid crops")

    state_encoder = LabelEncoder()

    print("Building training matrix (inner join on state × district)...")
    merged, crop_cols = build_training_matrix(soil_df, presence_df, state_encoder)
    print(f"  {len(merged)} training districts matched, {len(crop_cols)} crop labels")

    if len(merged) < 20:
        print(f"WARNING: Only {len(merged)} training rows — model may be unreliable.")

    X = merged[FEATURE_COLS].values.astype(float)
    y = merged[crop_cols].values.astype(int)

    print("Training RandomForestClassifier (multi-output, class_weight=balanced)...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)

    # Sanity check: train-set accuracy across all labels
    y_pred = model.predict(X)
    train_acc = accuracy_score(y.ravel(), y_pred.ravel())
    print(f"  Train accuracy (all crops, all districts): {train_acc:.4f}")

    artifact = {
        "model": model,
        "feature_names": FEATURE_COLS,
        "crop_names": crop_cols,
        "state_encoder": state_encoder,
        "train_accuracy": round(train_acc, 4),
        "n_districts": len(merged),
        "n_crops": len(crop_cols),
        "trained_at": datetime.utcnow().isoformat(),
    }

    joblib.dump(artifact, ARTIFACT_PATH)
    print(f"\nSaved -> {ARTIFACT_PATH}")
    print(f"Covers {len(crop_cols)} crops (vs 15 in previous rule-based system)")


if __name__ == "__main__":
    main()
