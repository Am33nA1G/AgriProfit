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
    expected_soil_cols = [
        "N_high", "N_medium", "N_low",
        "P_high", "P_medium", "P_low",
        "K_high", "K_medium", "K_low",
        "OC_high", "OC_medium", "OC_low",
        "pH_high", "pH_medium", "pH_low",
    ]
    for col in expected_soil_cols:
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
    # Ensure crops meet MIN_CROP_DISTRICTS=5 threshold
    # rice: 5 districts (D1, D2, D3, D4, D5)
    # tomato: 5 districts (D1, D2, D3, D4, D5)
    # cotton: 5 districts (D1, D2, D3, D4, D5)
    # wheat: 1 district (D6) — below threshold, will be dropped
    districts = ["DIST1", "DIST2", "DIST3", "DIST4", "DIST5", "DIST6"]
    states = ["TestState"] * 6
    data = {
        "state": states,
        "district": districts,
        "crop_name": ["rice", "rice", "rice", "rice", "rice", "wheat"],
        "season": ["kharif"] * 6,
        "year": [2000] * 6,
        "area_ha": [100.0] * 6,
        "production_tonnes": [200.0] * 6,
        "yield_kg_ha": [2000.0] * 6,
        "data_source": ["test"] * 6,
    }
    df1 = pd.DataFrame(data)

    data2 = {
        "state": ["TestState"] * 5,
        "district": ["DIST1", "DIST2", "DIST3", "DIST4", "DIST5"],
        "crop_name": ["tomato"] * 5,
        "season": ["kharif"] * 5,
        "year": [2000] * 5,
        "area_ha": [100.0] * 5,
        "production_tonnes": [200.0] * 5,
        "yield_kg_ha": [2000.0] * 5,
        "data_source": ["test"] * 5,
    }
    df2 = pd.DataFrame(data2)

    data3 = {
        "state": ["TestState"] * 5,
        "district": ["DIST1", "DIST2", "DIST3", "DIST4", "DIST5"],
        "crop_name": ["cotton"] * 5,
        "season": ["kharif"] * 5,
        "year": [2000] * 5,
        "area_ha": [100.0] * 5,
        "production_tonnes": [200.0] * 5,
        "yield_kg_ha": [2000.0] * 5,
        "data_source": ["test"] * 5,
    }
    df3 = pd.DataFrame(data3)

    df_all = pd.concat([df1, df2, df3], ignore_index=True)
    csv_path = tmp_path / "yield_data_raw.csv"
    df_all.to_csv(csv_path, index=False)
    return csv_path


def test_load_yield_presence_returns_pivot_with_crop_columns(tmp_path):
    csv_path = _make_yield_csv(tmp_path)
    result = load_yield_presence(csv_path)
    # Should have state_upper, district_upper + crop columns
    # rice, tomato, cotton each appear in 5+ districts (kept)
    # wheat appears in 1 district (dropped as below MIN_CROP_DISTRICTS=5)
    assert "rice" in result.columns
    assert "tomato" in result.columns
    assert "cotton" in result.columns
    assert "wheat" not in result.columns


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
