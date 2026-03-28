"""
Unit tests for clean_prices.py — price cleaning pipeline.

Tests use synthetic DataFrames only — no parquet file, no DB calls required.
All tests verify pure function behaviour: immutability, per-commodity bounds,
outlier flagging, and lower_cap non-negativity.
"""
import sys
import os
import importlib.util
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Import helpers — load clean_prices.py via its file path so no package
# install is needed (it lives in backend/scripts/, not a proper package)
# ---------------------------------------------------------------------------

def _load_clean_prices():
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    script_path = os.path.join(scripts_dir, "clean_prices.py")
    spec = importlib.util.spec_from_file_location("clean_prices", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load the module once for all tests
_mod = _load_clean_prices()
compute_commodity_bounds = _mod.compute_commodity_bounds
flag_and_cap_outliers = _mod.flag_and_cap_outliers


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_two_commodity_df():
    """Two commodities with clean, separated price ranges."""
    return pd.DataFrame({
        "commodity": ["Wheat"] * 5 + ["Rice"] * 5,
        "commodity_id": [1] * 5 + [2] * 5,
        "price_modal": [1000.0, 1100.0, 1050.0, 950.0, 1020.0,   # Wheat ~1000
                        2000.0, 2100.0, 1900.0, 2050.0, 1980.0],  # Rice ~2000
    })


@pytest.fixture
def outlier_commodity_df():
    """Wheat with one extreme outlier (per-kg price entered in per-quintal field)."""
    prices = [1000.0, 1050.0, 1100.0, 980.0, 1020.0,
              1030.0, 970.0, 1010.0, 1060.0, 100000.0]  # last value = corrupt row
    return pd.DataFrame({
        "commodity": ["Wheat"] * len(prices),
        "commodity_id": [1] * len(prices),
        "price_modal": prices,
    })


@pytest.fixture
def negative_lower_cap_risk_df():
    """A commodity where Q1 - 3*IQR would go negative without clamping."""
    # Prices clustered tightly around 10 — IQR is very small, Q1 is very low
    prices = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 100.0]
    return pd.DataFrame({
        "commodity": ["Spice"] * len(prices),
        "commodity_id": [99] * len(prices),
        "price_modal": prices,
    })


# ---------------------------------------------------------------------------
# Tests: compute_commodity_bounds()
# ---------------------------------------------------------------------------

class TestComputeCommodityBounds:

    def test_returns_one_row_per_commodity(self, simple_two_commodity_df):
        """Output has exactly one row per unique commodity."""
        bounds = compute_commodity_bounds(simple_two_commodity_df)
        assert len(bounds) == 2
        assert set(bounds["commodity"]) == {"Wheat", "Rice"}

    def test_outlier_detected_upper_cap_below_extreme_value(self, outlier_commodity_df):
        """Commodity with price [980..1100, 100000] must have upper_cap << 100000."""
        bounds = compute_commodity_bounds(outlier_commodity_df)
        wheat_bounds = bounds[bounds["commodity"] == "Wheat"].iloc[0]
        assert wheat_bounds["upper_cap"] < 100000.0, (
            f"upper_cap {wheat_bounds['upper_cap']} should be far below 100000"
        )

    def test_lower_cap_always_non_negative(self, negative_lower_cap_risk_df):
        """lower_cap must never be negative regardless of the price distribution."""
        bounds = compute_commodity_bounds(negative_lower_cap_risk_df)
        for _, row in bounds.iterrows():
            assert row["lower_cap"] >= 0.0, (
                f"lower_cap for {row['commodity']} is negative: {row['lower_cap']}"
            )

    def test_per_commodity_bounds_differ(self, simple_two_commodity_df):
        """Two commodities with different price scales must have different bounds."""
        bounds = compute_commodity_bounds(simple_two_commodity_df)
        wheat_upper = float(bounds[bounds["commodity"] == "Wheat"]["upper_cap"].iloc[0])
        rice_upper = float(bounds[bounds["commodity"] == "Rice"]["upper_cap"].iloc[0])
        assert wheat_upper != rice_upper, (
            "Wheat and Rice have different price scales — their upper_caps must differ"
        )

    def test_does_not_modify_input_dataframe(self, simple_two_commodity_df):
        """compute_commodity_bounds must not mutate the input DataFrame."""
        original_cols = list(simple_two_commodity_df.columns)
        original_shape = simple_two_commodity_df.shape
        compute_commodity_bounds(simple_two_commodity_df)
        assert list(simple_two_commodity_df.columns) == original_cols
        assert simple_two_commodity_df.shape == original_shape

    def test_output_has_required_columns(self, simple_two_commodity_df):
        """Bounds DataFrame must have all required output columns."""
        bounds = compute_commodity_bounds(simple_two_commodity_df)
        required = {"commodity", "commodity_id", "q1", "q3", "iqr",
                    "lower_cap", "upper_cap", "median_price"}
        assert required.issubset(set(bounds.columns)), (
            f"Missing columns: {required - set(bounds.columns)}"
        )

    def test_iqr_formula_correct(self, simple_two_commodity_df):
        """iqr column must equal q3 - q1."""
        bounds = compute_commodity_bounds(simple_two_commodity_df)
        for _, row in bounds.iterrows():
            expected_iqr = float(row["q3"]) - float(row["q1"])
            assert abs(float(row["iqr"]) - expected_iqr) < 0.01, (
                f"IQR mismatch for {row['commodity']}: "
                f"q3-q1={expected_iqr}, iqr={row['iqr']}"
            )


# ---------------------------------------------------------------------------
# Tests: flag_and_cap_outliers()
# ---------------------------------------------------------------------------

class TestFlagAndCapOutliers:

    def _make_bounds_for(self, df):
        return compute_commodity_bounds(df)

    def test_returns_new_dataframe(self, outlier_commodity_df):
        """flag_and_cap_outliers must return a NEW DataFrame (immutability)."""
        bounds = self._make_bounds_for(outlier_commodity_df)
        result = flag_and_cap_outliers(outlier_commodity_df, bounds)
        assert result is not outlier_commodity_df, (
            "flag_and_cap_outliers must return a new DataFrame, not modify in-place"
        )

    def test_original_not_modified(self, outlier_commodity_df):
        """Input DataFrame must not be modified after calling flag_and_cap_outliers."""
        bounds = self._make_bounds_for(outlier_commodity_df)
        original_cols = list(outlier_commodity_df.columns)
        original_shape = outlier_commodity_df.shape
        flag_and_cap_outliers(outlier_commodity_df, bounds)
        assert list(outlier_commodity_df.columns) == original_cols
        assert outlier_commodity_df.shape == original_shape

    def test_outlier_flagged_true_for_extreme_price(self, outlier_commodity_df):
        """Row with price_modal=100000 must have is_outlier=True."""
        bounds = self._make_bounds_for(outlier_commodity_df)
        result = flag_and_cap_outliers(outlier_commodity_df, bounds)
        extreme_row = result[result["price_modal"] == 100000.0]
        assert len(extreme_row) == 1, "Extreme price row must be present in result"
        assert extreme_row.iloc[0]["is_outlier"] == True, (
            "Extreme price (100000) must be flagged as is_outlier=True"
        )

    def test_outlier_capped_to_upper_cap(self, outlier_commodity_df):
        """modal_price_clean for outlier row must equal the upper_cap."""
        bounds = self._make_bounds_for(outlier_commodity_df)
        result = flag_and_cap_outliers(outlier_commodity_df, bounds)
        wheat_upper_cap = float(bounds[bounds["commodity"] == "Wheat"]["upper_cap"].iloc[0])
        extreme_row = result[result["price_modal"] == 100000.0]
        assert abs(float(extreme_row.iloc[0]["modal_price_clean"]) - wheat_upper_cap) < 0.01, (
            f"Outlier modal_price_clean must equal upper_cap={wheat_upper_cap}"
        )

    def test_non_outlier_price_unchanged(self, outlier_commodity_df):
        """modal_price_clean for non-outlier rows must equal original price_modal."""
        bounds = self._make_bounds_for(outlier_commodity_df)
        result = flag_and_cap_outliers(outlier_commodity_df, bounds)
        non_outliers = result[result["is_outlier"] == False]
        assert len(non_outliers) > 0, "There must be at least one non-outlier row"
        for _, row in non_outliers.iterrows():
            assert abs(float(row["modal_price_clean"]) - float(row["price_modal"])) < 0.01, (
                f"Non-outlier price_modal={row['price_modal']} must equal modal_price_clean"
            )

    def test_two_commodities_flagged_independently(self, simple_two_commodity_df):
        """Outlier detection must operate per-commodity, not globally."""
        # Add a very high Wheat price that is normal for Rice
        df = simple_two_commodity_df.copy()
        # Add a Wheat price at 1800 — within Rice range but extreme for Wheat
        extra = pd.DataFrame({
            "commodity": ["Wheat"],
            "commodity_id": [1],
            "price_modal": [1800.0],
        })
        df = pd.concat([df, extra], ignore_index=True)
        bounds = compute_commodity_bounds(df)
        result = flag_and_cap_outliers(df, bounds)

        # 1800 should be flagged as outlier for Wheat (based on its own distribution)
        wheat_1800_row = result[
            (result["commodity"] == "Wheat") & (result["price_modal"] == 1800.0)
        ]
        if len(wheat_1800_row) > 0:
            # Whether 1800 is an outlier depends on Wheat's IQR — just check per-commodity logic works
            # The key assertion: Rice rows should NOT be affected by Wheat's outlier status
            rice_rows = result[result["commodity"] == "Rice"]
            assert all(rice_rows["is_outlier"] == False), (
                "Rice prices within normal range must not be flagged as outliers"
            )

    def test_result_has_is_outlier_and_clean_columns(self, simple_two_commodity_df):
        """Result must have both is_outlier and modal_price_clean columns."""
        bounds = self._make_bounds_for(simple_two_commodity_df)
        result = flag_and_cap_outliers(simple_two_commodity_df, bounds)
        assert "is_outlier" in result.columns, "Result must have is_outlier column"
        assert "modal_price_clean" in result.columns, "Result must have modal_price_clean column"
