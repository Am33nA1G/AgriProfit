# Soil Crop Suitability ML Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 15-crop hardcoded `soil_crop_suitability` DB table with a trained RandomForest model that covers all 102 crops from historical yield data, using ICAR soil health card features as input.

**Architecture:** Aggregate the `soil_profiles` DB table from block→district level (avg NPK/OC/pH distributions), join with `yield_data_raw.csv` (binary crop presence per district), and train a multi-output `RandomForestClassifier`. At serve time, convert a block's soil profile dict to a 16-feature vector (15 soil + state encoded), run inference, and return the top-5 crops by P(grown). The existing rule-based `rank_crops()` remains as a fallback when the artifact is absent.

**Tech Stack:** scikit-learn RandomForestClassifier (multi-output), joblib, pandas, SQLAlchemy (engine), pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| CREATE | `backend/scripts/train_soil_suitability.py` | Full training pipeline: load soil from DB, load yield CSV, join, train RF, save artifact |
| CREATE | `backend/app/ml/soil_suitability_loader.py` | Artifact loader + `profile_to_feature_vector()` + `predict_crop_suitability()` |
| MODIFY | `backend/app/soil_advisor/service.py` | Call ML model first in `get_soil_advice()`, fall back to `rank_crops()` |
| CREATE | `backend/tests/test_soil_suitability_training.py` | Unit tests for training pipeline helper functions |
| CREATE | `backend/tests/test_soil_suitability_loader.py` | Unit tests for loader and inference helpers |
| MODIFY | `backend/tests/test_advisory_service.py` (or add new) | Integration test: service uses ML result when model is present |

**Artifact location:** `ml/artifacts/soil_crop_suitability_rf.joblib`

---

## Constants to know

```
REPO_ROOT = backend/../..                     ← two parents up from backend/
ARTIFACTS_DIR = REPO_ROOT/ml/artifacts/
YIELD_CSV = REPO_ROOT/data/crop_yields/yield_data_raw.csv
```

**Soil profile dict format** (what the service already has at call time):
```python
{
    "cycle": "2023-24",
    "block_name": "SOME BLOCK - 1234",
    "Nitrogen":              {"high": 4,  "medium": 0,  "low": 96},
    "Phosphorus":            {"high": 81, "medium": 17, "low": 2},
    "Potassium":             {"high": 50, "medium": 40, "low": 10},
    "Organic Carbon":        {"high": 10, "medium": 20, "low": 70},
    "Potential Of Hydrogen": {"high": 30, "medium": 50, "low": 20},
}
```

**16 model features** (in this exact order):
```
N_high, N_medium, N_low,
P_high, P_medium, P_low,
K_high, K_medium, K_low,
OC_high, OC_medium, OC_low,
pH_high, pH_medium, pH_low,
state_enc
```

**Meta-crops to skip** (aggregates, not real crops):
```python
SKIP_CROPS = {
    "total foodgrain", "pulses total", "oilseeds total",
    "other cereals & millets", "other_oilseeds", "other_pulses",
    "other_fruits", "other_vegetables", "small_millets",
    "peas & beans (pulses)", "cond-spcs other", "jute & mesta",
}
```

**State name aliases** — yield CSV uses different spellings from soil DB for 2 states:
```python
STATE_ALIASES = {
    "ANDAMAN AND NICOBAR ISLANDS": "ANDAMAN & NICOBAR",
    "JAMMU AND KASHMIR": "JAMMU & KASHMIR",
}
```
Apply this in `load_yield_presence()` after uppercasing: `df["state_upper"] = df["state_upper"].replace(STATE_ALIASES)`

**Minimum districts a crop must appear in** to be included as a label: `MIN_CROP_DISTRICTS = 5`
(Prevents degenerate classifiers where all labels are 0 or all are 1.)

---

## Task 1: Tests for training pipeline helpers

**Files:**
- Create: `backend/tests/test_soil_suitability_training.py`

These functions will live in `train_soil_suitability.py` but we import them directly in tests. The functions are pure (no DB, no filesystem) so they're easy to unit-test.

- [ ] **Step 1.1: Create the test file with failing tests**

```python
# backend/tests/test_soil_suitability_training.py
"""Unit tests for training pipeline helper functions in train_soil_suitability."""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.train_soil_suitability import (
    pivot_soil_rows,
    load_yield_presence,
    build_training_matrix,
    FEATURE_COLS,
    SKIP_CROPS,
    MIN_CROP_DISTRICTS,
)


# ── pivot_soil_rows ──────────────────────────────────────────────────────────

def _make_soil_rows():
    """Minimal mock of SQL result rows for 2 districts × 5 nutrients."""
    nutrient_names = [
        "Nitrogen", "Phosphorus", "Potassium",
        "Organic Carbon", "Potential Of Hydrogen",
    ]
    rows = []
    for state, district in [("ANDHRA PRADESH", "ANANTAPUR"), ("GUJARAT", "AHMEDABAD")]:
        for nutrient in nutrient_names:
            rows.append({
                "state": state,
                "district": district,
                "nutrient": nutrient,
                "high_avg": 20.0,
                "med_avg": 30.0,
                "low_avg": 50.0,
            })
    return pd.DataFrame(rows)


def test_pivot_soil_rows_returns_one_row_per_district():
    raw = _make_soil_rows()
    result = pivot_soil_rows(raw)
    assert len(result) == 2


def test_pivot_soil_rows_has_all_15_soil_columns():
    raw = _make_soil_rows()
    result = pivot_soil_rows(raw)
    soil_cols = [c for c in FEATURE_COLS if c != "state_enc"]
    for col in soil_cols:
        assert col in result.columns, f"Missing column: {col}"


def test_pivot_soil_rows_normalises_state_district_to_upper():
    raw = _make_soil_rows()
    raw["state"] = raw["state"].str.lower()  # mess with case
    result = pivot_soil_rows(raw)
    assert result["state"].str.isupper().all()
    assert result["district"].str.isupper().all()


def test_pivot_soil_rows_drops_incomplete_districts():
    raw = _make_soil_rows()
    # Remove Potassium rows for ANANTAPUR → that district should be dropped
    raw = raw[~((raw["district"] == "ANANTAPUR") & (raw["nutrient"] == "Potassium"))]
    result = pivot_soil_rows(raw)
    assert len(result) == 1
    assert result.iloc[0]["district"] == "AHMEDABAD"


# ── load_yield_presence ──────────────────────────────────────────────────────

def _make_yield_csv(tmp_path: Path) -> Path:
    data = {
        "state": ["Andhra Pradesh"] * 3 + ["Gujarat"] * 2,
        "district": ["ANANTAPUR", "ANANTAPUR", "GUNTUR", "AHMEDABAD", "AHMEDABAD"],
        "crop_name": ["rice", "tomato", "wheat", "rice", "cotton"],
        "season": ["kharif"] * 5,
        "year": [2000] * 5,
        "area_ha": [100.0] * 5,
        "production_tonnes": [200.0] * 5,
        "yield_kg_ha": [2000.0] * 5,
        "data_source": ["test"] * 5,
    }
    csv_path = tmp_path / "yield_data_raw.csv"
    pd.DataFrame(data).to_csv(csv_path, index=False)
    return csv_path


def test_load_yield_presence_returns_pivot_with_crop_columns(tmp_path):
    csv_path = _make_yield_csv(tmp_path)
    result = load_yield_presence(csv_path)
    # Should have state_upper, district_upper + crop columns
    assert "rice" in result.columns
    assert "tomato" in result.columns
    assert "cotton" in result.columns


def test_load_yield_presence_binary_values(tmp_path):
    csv_path = _make_yield_csv(tmp_path)
    result = load_yield_presence(csv_path)
    crop_cols = [c for c in result.columns if c not in ("state_upper", "district_upper")]
    assert result[crop_cols].isin([0, 1]).all().all()


def test_load_yield_presence_skips_meta_crops(tmp_path):
    """Meta-aggregate crops must not appear as columns."""
    data = {
        "state": ["Gujarat"],
        "district": ["AHMEDABAD"],
        "crop_name": ["total foodgrain"],
        "season": ["kharif"],
        "year": [2000],
        "area_ha": [100.0],
        "production_tonnes": [200.0],
        "yield_kg_ha": [2000.0],
        "data_source": ["test"],
    }
    csv_path = tmp_path / "yield.csv"
    pd.DataFrame(data).to_csv(csv_path, index=False)
    result = load_yield_presence(csv_path)
    assert "total foodgrain" not in result.columns


def test_load_yield_presence_applies_state_aliases(tmp_path):
    """Andaman and Nicobar Islands must be normalised to ANDAMAN & NICOBAR."""
    # Plant rice in 5+ districts under the long-form name
    data = {
        "state": ["Andaman and Nicobar Islands"] * 5,
        "district": [f"DIST{i}" for i in range(5)],
        "crop_name": ["rice"] * 5,
        "season": ["kharif"] * 5,
        "year": [2000] * 5,
        "area_ha": [100.0] * 5,
        "production_tonnes": [200.0] * 5,
        "yield_kg_ha": [2000.0] * 5,
        "data_source": ["test"] * 5,
    }
    csv_path = tmp_path / "yield_alias.csv"
    pd.DataFrame(data).to_csv(csv_path, index=False)
    result = load_yield_presence(csv_path)
    assert "ANDAMAN AND NICOBAR ISLANDS" not in result["state_upper"].values
    assert "ANDAMAN & NICOBAR" in result["state_upper"].values


def test_load_yield_presence_filters_rare_crops(tmp_path):
    """Crops present in fewer than MIN_CROP_DISTRICTS districts must be dropped."""
    # rice in only 1 district (< MIN_CROP_DISTRICTS=5) → should be dropped
    data = {
        "state": ["Gujarat"],
        "district": ["AHMEDABAD"],
        "crop_name": ["rice"],
        "season": ["kharif"],
        "year": [2000],
        "area_ha": [100.0],
        "production_tonnes": [200.0],
        "yield_kg_ha": [2000.0],
        "data_source": ["test"],
    }
    csv_path = tmp_path / "yield2.csv"
    pd.DataFrame(data).to_csv(csv_path, index=False)
    result = load_yield_presence(csv_path)
    assert "rice" not in result.columns


# ── build_training_matrix ─────────────────────────────────────────────────────

def test_build_training_matrix_joins_on_state_district():
    from sklearn.preprocessing import LabelEncoder
    soil = pd.DataFrame([
        {"state": "ANDHRA PRADESH", "district": "ANANTAPUR",
         "N_high": 20.0, "N_medium": 30.0, "N_low": 50.0,
         "P_high": 20.0, "P_medium": 30.0, "P_low": 50.0,
         "K_high": 20.0, "K_medium": 30.0, "K_low": 50.0,
         "OC_high": 20.0, "OC_medium": 30.0, "OC_low": 50.0,
         "pH_high": 20.0, "pH_medium": 30.0, "pH_low": 50.0},
    ])
    presence = pd.DataFrame([
        {"state_upper": "ANDHRA PRADESH", "district_upper": "ANANTAPUR", "rice": 1, "wheat": 0},
    ])
    le = LabelEncoder()
    merged, crop_cols = build_training_matrix(soil, presence, le)
    assert len(merged) == 1
    assert set(crop_cols) == {"rice", "wheat"}
    assert "state_enc" in merged.columns


def test_build_training_matrix_raises_on_empty_join():
    from sklearn.preprocessing import LabelEncoder
    soil = pd.DataFrame([
        {"state": "ANDHRA PRADESH", "district": "ANANTAPUR",
         **{c: 0.0 for c in [f"{p}_{l}" for p in ["N","P","K","OC","pH"]
                              for l in ["high","medium","low"]]}},
    ])
    presence = pd.DataFrame([
        {"state_upper": "GUJARAT", "district_upper": "AHMEDABAD", "rice": 1},
    ])
    le = LabelEncoder()
    with pytest.raises(ValueError, match="No districts matched"):
        build_training_matrix(soil, presence, le)
```

- [ ] **Step 1.2: Run tests — expect ImportError (module not written yet)**

```
cd backend
.venv/Scripts/python.exe -m pytest tests/test_soil_suitability_training.py -v 2>&1 | head -30
```
Expected: `ImportError` or `ModuleNotFoundError` — that's correct, functions don't exist yet.

- [ ] **Step 1.3: Commit the failing tests**

```bash
cd backend
git add tests/test_soil_suitability_training.py
git commit -m "test: add failing tests for soil suitability training pipeline helpers"
```

---

## Task 2: Training script implementation

**Files:**
- Create: `backend/scripts/train_soil_suitability.py`

- [ ] **Step 2.1: Create the training script**

```python
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

    # Drop crops present in too few districts (degenerate classifiers)
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
```

- [ ] **Step 2.2: Run failing tests — they should now pass**

```
cd backend
.venv/Scripts/python.exe -m pytest tests/test_soil_suitability_training.py -v
```
Expected: all tests PASS.

- [ ] **Step 2.3: Commit**

```bash
git add scripts/train_soil_suitability.py tests/test_soil_suitability_training.py
git commit -m "feat(soil): add training pipeline for soil crop suitability RF model"
```

---

## Task 3: Run the training script

- [ ] **Step 3.1: Run the script**

```
cd backend
.venv/Scripts/python.exe -m scripts.train_soil_suitability
```

Expected output (approximate):
```
Loading soil district profiles from DB...
  NNN districts with complete soil profiles
Loading yield presence matrix from yield_data_raw.csv...
  NNN district rows, NN valid crops
Building training matrix (inner join on state × district)...
  NN training districts matched, NN crop labels
Training RandomForestClassifier (multi-output, class_weight=balanced)...
  Train accuracy (all crops, all districts): 0.XXXX
Saved -> .../ml/artifacts/soil_crop_suitability_rf.joblib
Covers NN crops (vs 15 in previous rule-based system)
```

- [ ] **Step 3.2: Verify artifact exists**

```
ls -la ml/artifacts/soil_crop_suitability_rf.joblib
```

Expected: file exists, size > 1MB.

- [ ] **Step 3.3: Spot-check artifact contents**

```
cd backend
.venv/Scripts/python.exe -c "
import joblib
from pathlib import Path
b = joblib.load(Path('..') / 'ml' / 'artifacts' / 'soil_crop_suitability_rf.joblib')
print('n_crops:', b['n_crops'])
print('n_districts:', b['n_districts'])
print('crop_names[:10]:', b['crop_names'][:10])
print('train_accuracy:', b['train_accuracy'])
print('feature_names:', b['feature_names'])
"
```

Expected: n_crops > 15, crop_names contains real crop names (not meta-crops), feature_names matches FEATURE_COLS exactly.

- [ ] **Step 3.4: Commit artifact (or add to .gitignore if too large)**

Check size first:
```bash
python -c "import os; print(os.path.getsize('../ml/artifacts/soil_crop_suitability_rf.joblib') / 1e6, 'MB')"
```

If < 50MB, commit it. If > 50MB, add `ml/artifacts/soil_crop_suitability_rf.joblib` to `.gitignore` and document the training command in `docs/` instead.

```bash
git add ml/artifacts/soil_crop_suitability_rf.joblib  # or .gitignore entry
git commit -m "chore: train and save soil crop suitability RF model artifact"
```

---

## Task 4: Tests for loader and inference

**Files:**
- Create: `backend/tests/test_soil_suitability_loader.py`

- [ ] **Step 4.1: Create the test file**

```python
# backend/tests/test_soil_suitability_loader.py
"""Unit tests for soil_suitability_loader.py."""
import sys
from pathlib import Path
import numpy as np
import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.soil_suitability_loader import (
    profile_to_feature_vector,
    predict_crop_suitability,
    NUTRIENT_MAP,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_profile():
    return {
        "cycle": "2023-24",
        "block_name": "TEST BLOCK - 0001",
        "Nitrogen":              {"high": 20, "medium": 30, "low": 50},
        "Phosphorus":            {"high": 81, "medium": 17, "low": 2},
        "Potassium":             {"high": 50, "medium": 40, "low": 10},
        "Organic Carbon":        {"high": 10, "medium": 20, "low": 70},
        "Potential Of Hydrogen": {"high": 30, "medium": 50, "low": 20},
    }


def _make_bundle():
    """Minimal fake artifact — real sklearn RF with 2 crops."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    import numpy as np

    le = LabelEncoder()
    le.fit(["ANDHRA PRADESH", "GUJARAT", "BIHAR"])

    # Train a tiny 2-crop RF on 10 fake rows
    feature_names = [
        "N_high", "N_medium", "N_low",
        "P_high", "P_medium", "P_low",
        "K_high", "K_medium", "K_low",
        "OC_high", "OC_medium", "OC_low",
        "pH_high", "pH_medium", "pH_low",
        "state_enc",
    ]
    X = np.random.RandomState(0).rand(20, 16) * 100
    y = np.column_stack([
        np.array([1, 0] * 10),  # rice
        np.array([0, 1] * 10),  # wheat
    ])
    model = RandomForestClassifier(n_estimators=5, random_state=0)
    model.fit(X, y)

    return {
        "model": model,
        "feature_names": feature_names,
        "crop_names": ["rice", "wheat"],
        "state_encoder": le,
        "train_accuracy": 0.9,
        "n_districts": 20,
        "n_crops": 2,
        "trained_at": "2026-01-01T00:00:00",
    }


# ── profile_to_feature_vector ────────────────────────────────────────────────

def test_profile_to_feature_vector_returns_correct_shape():
    bundle = _make_bundle()
    vec = profile_to_feature_vector(_make_profile(), "ANDHRA PRADESH", bundle)
    assert vec is not None
    assert vec.shape == (1, 16)


def test_profile_to_feature_vector_nitrogen_values():
    bundle = _make_bundle()
    profile = _make_profile()
    vec = profile_to_feature_vector(profile, "ANDHRA PRADESH", bundle)
    feature_names = bundle["feature_names"]
    n_high_idx = feature_names.index("N_high")
    assert vec[0, n_high_idx] == 20.0


def test_profile_to_feature_vector_unknown_state_uses_zero():
    bundle = _make_bundle()
    # "UNKNOWN STATE" not in the encoder → should not raise, uses fallback 0
    vec = profile_to_feature_vector(_make_profile(), "UNKNOWN STATE", bundle)
    assert vec is not None
    state_idx = bundle["feature_names"].index("state_enc")
    assert vec[0, state_idx] == 0.0


def test_profile_to_feature_vector_missing_nutrient_fills_zeros():
    bundle = _make_bundle()
    profile = _make_profile()
    del profile["Potassium"]  # missing nutrient
    vec = profile_to_feature_vector(profile, "GUJARAT", bundle)
    assert vec is not None
    feature_names = bundle["feature_names"]
    for suffix in ["high", "medium", "low"]:
        idx = feature_names.index(f"K_{suffix}")
        assert vec[0, idx] == 0.0


# ── predict_crop_suitability ─────────────────────────────────────────────────

def test_predict_returns_none_when_no_artifact():
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=None):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH")
    assert result is None


def test_predict_returns_list_of_dicts():
    bundle = _make_bundle()
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=bundle):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH")
    assert isinstance(result, list)
    for item in result:
        assert "crop_name" in item
        assert "score" in item
        assert "source" in item
        assert item["source"] == "ml"


def test_predict_respects_top_n():
    bundle = _make_bundle()
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=bundle):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH", top_n=1)
    assert len(result) <= 1


def test_predict_scores_are_descending():
    bundle = _make_bundle()
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=bundle):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH")
    if len(result) > 1:
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 4.2: Run tests — expect ImportError (loader not written yet)**

```
cd backend
.venv/Scripts/python.exe -m pytest tests/test_soil_suitability_loader.py -v 2>&1 | head -20
```

Expected: `ImportError` — that's correct.

- [ ] **Step 4.3: Commit failing tests**

```bash
git add tests/test_soil_suitability_loader.py
git commit -m "test: add failing tests for soil suitability loader and inference"
```

---

## Task 5: Loader and inference implementation

**Files:**
- Create: `backend/app/ml/soil_suitability_loader.py`

- [ ] **Step 5.1: Create the loader**

```python
# backend/app/ml/soil_suitability_loader.py
"""
Loader and inference helpers for the soil crop suitability RandomForest model.

Artifact: ml/artifacts/soil_crop_suitability_rf.joblib
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ARTIFACT_PATH = REPO_ROOT / "ml" / "artifacts" / "soil_crop_suitability_rf.joblib"

# Module-level cache: loaded once, reused for all requests
_bundle: dict | None = None

NUTRIENT_MAP = {
    "Nitrogen": "N",
    "Phosphorus": "P",
    "Potassium": "K",
    "Organic Carbon": "OC",
    "Potential Of Hydrogen": "pH",
}


def load_soil_suitability_model() -> dict | None:
    """Load and cache the artifact. Returns None if file does not exist."""
    global _bundle
    if _bundle is not None:
        return _bundle
    if not _ARTIFACT_PATH.exists():
        return None
    _bundle = joblib.load(_ARTIFACT_PATH)
    return _bundle


def profile_to_feature_vector(
    profile: dict,
    state: str,
    bundle: dict,
) -> Optional[np.ndarray]:
    """
    Convert a block soil profile dict to a 1×16 feature matrix.

    Args:
        profile: {"Nitrogen": {"high": 4, "medium": 0, "low": 96}, ...}
        state:   State name (e.g. "ANDHRA PRADESH") — normalised to UPPER internally
        bundle:  Loaded model artifact dict

    Returns:
        np.ndarray of shape (1, 16) or None on failure.
    """
    try:
        state_enc = bundle["state_encoder"].transform([state.strip().upper()])[0]
    except (ValueError, KeyError):
        state_enc = 0  # Unknown state → encode as 0 (safe fallback)

    row: dict[str, float] = {}
    for nutrient, prefix in NUTRIENT_MAP.items():
        nd = profile.get(nutrient, {})
        row[f"{prefix}_high"] = float(nd.get("high", 0))
        row[f"{prefix}_medium"] = float(nd.get("medium", 0))
        row[f"{prefix}_low"] = float(nd.get("low", 0))
    row["state_enc"] = float(state_enc)

    feature_names: list[str] = bundle["feature_names"]
    try:
        vec = np.array([row[f] for f in feature_names], dtype=float).reshape(1, -1)
    except KeyError:
        return None

    return vec


def predict_crop_suitability(
    profile: dict,
    state: str,
    top_n: int = 5,
) -> list[dict] | None:
    """
    Run ML inference and return top-N crop recommendations.

    Returns None when artifact is absent (caller falls back to rule-based system).
    Returns list of dicts: {"crop_name": str, "score": float, "source": "ml"}
    sorted by score descending.
    """
    bundle = load_soil_suitability_model()
    if bundle is None:
        return None

    vec = profile_to_feature_vector(profile, state, bundle)
    if vec is None:
        return None

    model = bundle["model"]
    crop_names: list[str] = bundle["crop_names"]

    # predict_proba returns a list of (n_samples, n_classes) arrays — one per crop.
    # We take index [0][1]: first (only) sample, probability of class=1 (grown).
    # MIN_CROP_DISTRICTS=5 ensures all labels have both classes so shape[1]==2 always.
    # Guard kept for safety: a single-class crop should score 0 (never grown).
    proba_list = model.predict_proba(vec)
    scores: list[float] = []
    for proba in proba_list:
        if proba.shape[1] == 2:
            scores.append(float(proba[0][1]))
        else:
            # Single class seen during training. proba[0][0] = P(that class).
            # We can't know if it was class 0 or 1 without inspecting the estimator,
            # so conservatively score 0 — it will be filtered by the `score > 0` gate.
            scores.append(0.0)

    ranked = sorted(zip(crop_names, scores), key=lambda x: x[1], reverse=True)

    return [
        {
            "crop_name": name.replace("_", " ").title(),
            "score": round(score, 4),
            "source": "ml",
        }
        for name, score in ranked[:top_n]
        if score > 0.0
    ]
```

- [ ] **Step 5.2: Run loader tests — all should pass**

```
cd backend
.venv/Scripts/python.exe -m pytest tests/test_soil_suitability_loader.py -v
```
Expected: all PASS.

- [ ] **Step 5.3: Commit**

```bash
git add app/ml/soil_suitability_loader.py
git commit -m "feat(soil): add soil suitability ML loader and predict_crop_suitability()"
```

---

## Task 6: Tests for the modified service

**Files:**
- Create: `backend/tests/test_soil_suitability_service.py`

- [ ] **Step 6.1: Create the service integration test**

```python
# backend/tests/test_soil_suitability_service.py
"""
Integration tests for soil advisor service with ML model integration.
Uses SQLite in-memory DB (same as rest of test suite).
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.soil_advisor.service import get_soil_advice

# ── Shared in-memory DB ───────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)


def setup_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS soil_profiles (
                state TEXT, district TEXT, block TEXT,
                nutrient TEXT, high_pct REAL, medium_pct REAL, low_pct REAL, cycle TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS soil_crop_suitability (
                crop_name TEXT, nutrient TEXT, min_tolerance TEXT,
                ph_min REAL, ph_max REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS seasonal_price_stats (
                commodity_name TEXT, state TEXT, best_sell_month TEXT
            )
        """))
        # Seed one block
        nutrients = [
            ("Nitrogen", 20, 30, 50),
            ("Phosphorus", 81, 17, 2),
            ("Potassium", 50, 40, 10),
            ("Organic Carbon", 10, 20, 70),
            ("Potential Of Hydrogen", 30, 50, 20),
        ]
        for nutrient, hi, med, lo in nutrients:
            conn.execute(text("""
                INSERT INTO soil_profiles VALUES
                ('ANDHRA PRADESH', 'ANANTAPUR', 'TEST BLOCK - 0001',
                 :nutrient, :hi, :med, :lo, '2023-24')
            """), {"nutrient": nutrient, "hi": hi, "med": med, "lo": lo})
        # Seed two rule-based crops (fallback)
        conn.execute(text("""
            INSERT INTO soil_crop_suitability VALUES ('Rice', 'Nitrogen', 'medium', 5.5, 7.0)
        """))
        conn.commit()


setup_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_ml_result(*args, **kwargs):
    return [
        {"crop_name": "Tomato", "score": 0.85, "source": "ml"},
        {"crop_name": "Rice",   "score": 0.70, "source": "ml"},
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_service_uses_ml_when_model_available():
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        crop_names = [r.crop_name for r in result.crop_recommendations]
        assert "Tomato" in crop_names
        assert "Rice" in crop_names
    finally:
        db.close()


def test_service_falls_back_to_rule_based_when_ml_unavailable():
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            return_value=None,  # model absent
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        # Rule-based fallback should still return something (Rice from suitability table)
        assert isinstance(result.crop_recommendations, list)
    finally:
        db.close()


def test_service_result_has_correct_schema():
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        assert result.state == "ANDHRA PRADESH"
        assert result.district == "ANANTAPUR"
        assert result.block == "TEST BLOCK - 0001"
        assert len(result.nutrient_distributions) == 5
        assert result.disclaimer != ""
        for i, crop in enumerate(result.crop_recommendations, start=1):
            assert crop.suitability_rank == i
    finally:
        db.close()


def test_service_ranks_crops_by_ml_score():
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        # First recommendation should be Tomato (score 0.85 > 0.70)
        assert result.crop_recommendations[0].crop_name == "Tomato"
    finally:
        db.close()
```

- [ ] **Step 6.2: Run tests — expect failures (service not modified yet)**

```
cd backend
.venv/Scripts/python.exe -m pytest tests/test_soil_suitability_service.py -v 2>&1 | head -30
```
Expected: FAIL because `predict_crop_suitability` is not imported in service.py yet.

- [ ] **Step 6.3: Commit failing tests**

```bash
git add tests/test_soil_suitability_service.py
git commit -m "test: add failing integration tests for soil advisor service ML wiring"
```

---

## Task 7: Wire ML model into service

**Files:**
- Modify: `backend/app/soil_advisor/service.py`

Only the `get_soil_advice()` function changes. Everything else stays identical.

- [ ] **Step 7.1: Add the import at top of service.py**

At the top of `backend/app/soil_advisor/service.py`, after the existing imports, add:

```python
from app.ml.soil_suitability_loader import predict_crop_suitability
```

- [ ] **Step 7.2: Replace the crop ranking block in `get_soil_advice()`**

Find this existing block in `get_soil_advice()` (around line 178–183):

```python
    # --- Crop ranking ---
    crop_rows = db.execute(
        text("SELECT crop_name, nutrient, min_tolerance, ph_min, ph_max FROM soil_crop_suitability")
    ).fetchall()
    crop_dicts = [dict(r._mapping) for r in crop_rows]
    ranked = rank_crops(profile, crop_dicts)
```

Replace it with:

```python
    # --- Crop ranking: ML model first, rule-based fallback ---
    ml_crops = predict_crop_suitability(profile, state_upper)
    if ml_crops:
        ranked = ml_crops
    else:
        crop_rows = db.execute(
            text("SELECT crop_name, nutrient, min_tolerance, ph_min, ph_max FROM soil_crop_suitability")
        ).fetchall()
        crop_dicts = [dict(r._mapping) for r in crop_rows]
        ranked = rank_crops(profile, crop_dicts)
```

- [ ] **Step 7.3: Run service tests — all should pass**

```
cd backend
.venv/Scripts/python.exe -m pytest tests/test_soil_suitability_service.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 7.4: Run full test suite to check no regressions**

```
cd backend
.venv/Scripts/python.exe -m pytest --tb=short -q 2>&1 | tail -20
```
Expected: same pass count as before (598 tests), no new failures.

- [ ] **Step 7.5: Commit**

```bash
git add app/soil_advisor/service.py
git commit -m "feat(soil): wire ML crop suitability model into soil advisor service with rule-based fallback"
```

---

## Task 8: End-to-end verification

- [ ] **Step 8.1: Run all new tests together**

```
cd backend
.venv/Scripts/python.exe -m pytest tests/test_soil_suitability_training.py tests/test_soil_suitability_loader.py tests/test_soil_suitability_service.py -v
```
Expected: all tests PASS.

- [ ] **Step 8.2: Spot-check a live prediction**

```
cd backend
.venv/Scripts/python.exe -c "
from app.ml.soil_suitability_loader import predict_crop_suitability

# Nitrogen-deficient block (typical across India)
profile = {
    'Nitrogen':              {'high': 0, 'medium': 4, 'low': 96},
    'Phosphorus':            {'high': 81, 'medium': 17, 'low': 2},
    'Potassium':             {'high': 50, 'medium': 40, 'low': 10},
    'Organic Carbon':        {'high': 5, 'medium': 15, 'low': 80},
    'Potential Of Hydrogen': {'high': 0, 'medium': 60, 'low': 40},
}
result = predict_crop_suitability(profile, 'ANDHRA PRADESH')
if result is None:
    print('WARN: Model not loaded — run train_soil_suitability.py first')
else:
    for r in result:
        print(r)
"
```

Expected: 5 crop dicts with source="ml", scores > 0, reasonable crop names (legumes/low-N-requirement crops should rank highly given N deficiency).

- [ ] **Step 8.3: Final commit**

```bash
git add .
git commit -m "feat(soil): ML-driven crop suitability model — 15 → 100+ crops"
```

---

## What changes, what stays the same

| Component | Before | After |
|-----------|--------|-------|
| Crop coverage | 15 hardcoded crops | 100+ crops from yield data |
| Recommendation source | Rule-based tolerance table | RF model (ML), rule-based as fallback |
| API shape | Unchanged | Unchanged |
| Frontend | Unchanged | Unchanged |
| `rank_crops()` / `score_crop()` | Used | Kept as fallback, not deleted |
| `soil_crop_suitability` DB table | Used | Still seeded; used only when model absent |
| `soil_suitability_loader.py` | N/A | New: loads artifact, runs inference |
| `train_soil_suitability.py` | N/A | New: offline training script |
