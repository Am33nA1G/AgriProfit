"""
Unit tests for soil feature engineering — block-level NPK/pH profile lookup.

TDD tests for compute_soil_features() and SOIL_NUTRIENT_COLS constant.
All tests use synthetic DataFrames matching the verified soil CSV schema.
"""
import pytest
import pandas as pd
import numpy as np

from app.ml.soil_features import compute_soil_features, SOIL_NUTRIENT_COLS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def block_df():
    """Synthetic soil DataFrame for one block — matches real CSV schema."""
    return pd.DataFrame([
        {"cycle": "2023-24", "state": "BIHAR", "district": "PATNA", "block": "BARH - 1234",
         "nutrient": "Nitrogen", "high": "10%", "medium": "60%", "low": "30%"},
        {"cycle": "2023-24", "state": "BIHAR", "district": "PATNA", "block": "BARH - 1234",
         "nutrient": "Phosphorus", "high": "5%", "medium": "45%", "low": "50%"},
        {"cycle": "2023-24", "state": "BIHAR", "district": "PATNA", "block": "BARH - 1234",
         "nutrient": "Potassium", "high": "20%", "medium": "70%", "low": "10%"},
        {"cycle": "2023-24", "state": "BIHAR", "district": "PATNA", "block": "BARH - 1234",
         "nutrient": "Organic Carbon", "high": "0%", "medium": "15%", "low": "85%"},
        {"cycle": "2023-24", "state": "BIHAR", "district": "PATNA", "block": "BARH - 1234",
         "nutrient": "Potential Of Hydrogen", "high": "0%", "medium": "25%", "low": "75%"},
    ])


@pytest.fixture
def incomplete_block_df():
    """Block with only 3 of 5 nutrients — missing Organic Carbon and pH."""
    return pd.DataFrame([
        {"cycle": "2023-24", "state": "TEST", "district": "TEST", "block": "TEST",
         "nutrient": "Nitrogen", "high": "10%", "medium": "60%", "low": "30%"},
        {"cycle": "2023-24", "state": "TEST", "district": "TEST", "block": "TEST",
         "nutrient": "Phosphorus", "high": "5%", "medium": "45%", "low": "50%"},
        {"cycle": "2023-24", "state": "TEST", "district": "TEST", "block": "TEST",
         "nutrient": "Potassium", "high": "20%", "medium": "70%", "low": "10%"},
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeSoilFeatures:

    def test_returns_soil_nutrient_cols(self, block_df):
        """Returns DataFrame with SOIL_NUTRIENT_COLS for a block with known nutrient data."""
        result = compute_soil_features(block_df)
        assert len(result) == 1
        assert set(result.columns) == set(SOIL_NUTRIENT_COLS)

    def test_soil_nutrient_cols_count(self):
        """SOIL_NUTRIENT_COLS should contain exactly 15 columns (5 nutrients x 3 levels)."""
        assert len(SOIL_NUTRIENT_COLS) == 15

    def test_unknown_block_returns_empty(self):
        """Unknown / empty block DataFrame returns empty DataFrame (not error)."""
        result = compute_soil_features(pd.DataFrame())
        assert len(result) == 0
        assert set(result.columns) == set(SOIL_NUTRIENT_COLS)

    def test_none_input_returns_empty(self):
        """None input returns empty DataFrame."""
        result = compute_soil_features(None)
        assert len(result) == 0

    def test_does_not_modify_input(self, block_df):
        """Function must NOT modify the input soil_df."""
        original = block_df.copy()
        compute_soil_features(block_df)
        pd.testing.assert_frame_equal(block_df, original)

    def test_values_sum_to_approximately_100(self, block_df):
        """High + Medium + Low should sum to approximately 100% for each nutrient."""
        result = compute_soil_features(block_df)
        row = result.iloc[0]
        for prefix in ["N", "P", "K", "OC", "pH"]:
            total = row[f"{prefix}_high"] + row[f"{prefix}_medium"] + row[f"{prefix}_low"]
            assert abs(total - 100.0) < 0.1, f"{prefix} sum is {total}, expected ~100"

    def test_incomplete_nutrients_return_empty(self, incomplete_block_df):
        """Block with missing nutrients should return empty DataFrame — not partial results."""
        result = compute_soil_features(incomplete_block_df)
        assert len(result) == 0
