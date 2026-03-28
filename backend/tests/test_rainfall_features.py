"""
Unit tests for rainfall feature engineering — deficit/surplus and completeness checking.

TDD tests for compute_longterm_rainfall_avg(), compute_rainfall_deficit(), and
check_rainfall_completeness(). All tests use synthetic DataFrames only (no parquet reads).
Synthetic data uses UPPER CASE column names (STATE, DISTRICT) to match real parquet schema.
"""
import pytest
import pandas as pd
import numpy as np

from app.ml.rainfall_features import (
    compute_longterm_rainfall_avg,
    compute_rainfall_deficit,
    check_rainfall_completeness,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic rainfall DataFrames
# ---------------------------------------------------------------------------

@pytest.fixture
def rainfall_df():
    """Synthetic rainfall DataFrame covering 2015-2022 with 2 districts, 12 months each."""
    rows = []
    for year in range(2015, 2023):
        for month in range(1, 13):
            for district in ["PATNA", "GAYA"]:
                rainfall = 100 + month * 10 + (year - 2015) * 5
                rows.append({
                    "STATE": "BIHAR",
                    "DISTRICT": district,
                    "year": year,
                    "month": month,
                    "rainfall": float(rainfall),
                })
    return pd.DataFrame(rows)


@pytest.fixture
def partial_year_df():
    """
    Like rainfall_df but with 2026 having only 1 month for both districts.
    Simulates real-world incomplete data.
    """
    rows = []
    for year in range(2015, 2023):
        for month in range(1, 13):
            for district in ["PATNA", "GAYA"]:
                rainfall = 100 + month * 10
                rows.append({
                    "STATE": "BIHAR",
                    "DISTRICT": district,
                    "year": year,
                    "month": month,
                    "rainfall": float(rainfall),
                })
    # 2026 with only January
    for district in ["PATNA", "GAYA"]:
        rows.append({
            "STATE": "BIHAR",
            "DISTRICT": district,
            "year": 2026,
            "month": 1,
            "rainfall": 110.0,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def zero_rainfall_df():
    """DataFrame with zero longterm avg for one month (to test ZeroDivisionError handling)."""
    rows = []
    for year in range(2015, 2021):
        for month in range(1, 13):
            rainfall = 0.0 if month == 6 else 100.0
            rows.append({
                "STATE": "TESTSTATE",
                "DISTRICT": "TESTDISTRICT",
                "year": year,
                "month": month,
                "rainfall": rainfall,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests for compute_longterm_rainfall_avg
# ---------------------------------------------------------------------------

class TestComputeLongtermRainfallAvg:

    def test_excludes_years_after_baseline(self, rainfall_df):
        """Years > baseline_end_year should not be included in the average."""
        avg1 = compute_longterm_rainfall_avg(rainfall_df, baseline_end_year=2018)
        avg2 = compute_longterm_rainfall_avg(rainfall_df, baseline_end_year=2022)
        # With different baselines, the averages should differ
        # (because 2019-2022 data is excluded from avg1)
        patna_jan_1 = avg1[(avg1["DISTRICT"] == "PATNA") & (avg1["month"] == 1)]["longterm_avg_mm"].values[0]
        patna_jan_2 = avg2[(avg2["DISTRICT"] == "PATNA") & (avg2["month"] == 1)]["longterm_avg_mm"].values[0]
        assert patna_jan_1 != patna_jan_2

    def test_one_row_per_district_month(self, rainfall_df):
        """Output should have exactly one row per (DISTRICT, month) combination."""
        avg = compute_longterm_rainfall_avg(rainfall_df, baseline_end_year=2020)
        # 2 districts * 12 months = 24 rows
        assert len(avg) == 24
        # Verify uniqueness
        assert avg.duplicated(subset=["DISTRICT", "month"]).sum() == 0


# ---------------------------------------------------------------------------
# Tests for compute_rainfall_deficit
# ---------------------------------------------------------------------------

class TestComputeRainfallDeficit:

    def test_deficit_pct_formula(self, rainfall_df):
        """rainfall_deficit_pct = (rainfall - longterm_avg) / longterm_avg * 100."""
        avg = compute_longterm_rainfall_avg(rainfall_df, baseline_end_year=2017)
        result = compute_rainfall_deficit(rainfall_df, avg)
        # Check a specific row
        row = result[
            (result["DISTRICT"] == "PATNA") &
            (result["year"] == 2020) &
            (result["month"] == 1)
        ].iloc[0]
        expected = (row["rainfall_mm"] - row["longterm_avg_mm"]) / row["longterm_avg_mm"] * 100
        assert abs(row["rainfall_deficit_pct"] - expected) < 0.01

    def test_surplus_positive_deficit_negative(self, rainfall_df):
        """Surplus months have positive pct, deficit months have negative pct."""
        avg = compute_longterm_rainfall_avg(rainfall_df, baseline_end_year=2017)
        result = compute_rainfall_deficit(rainfall_df, avg)
        # Since rainfall increases each year (formula: 100 + month*10 + (year-2015)*5),
        # years after the baseline (2018-2022) should have positive deficit (surplus)
        surplus_rows = result[result["year"] > 2017]
        assert (surplus_rows["rainfall_deficit_pct"].dropna() > 0).all()

    def test_zero_longterm_avg_returns_nan(self, zero_rainfall_df):
        """Zero longterm average should produce NaN, not ZeroDivisionError."""
        avg = compute_longterm_rainfall_avg(zero_rainfall_df, baseline_end_year=2020)
        # Month 6 has zero rainfall for all baseline years, so longterm_avg_mm = 0
        result = compute_rainfall_deficit(zero_rainfall_df, avg)
        june_rows = result[result["month"] == 6]
        # Should be NaN, not an error
        assert june_rows["rainfall_deficit_pct"].isna().all()

    def test_does_not_modify_input(self, rainfall_df):
        """compute_rainfall_deficit must not modify input DataFrames."""
        original_rain = rainfall_df.copy()
        avg = compute_longterm_rainfall_avg(rainfall_df, baseline_end_year=2020)
        original_avg = avg.copy()
        compute_rainfall_deficit(rainfall_df, avg)
        pd.testing.assert_frame_equal(rainfall_df, original_rain)
        pd.testing.assert_frame_equal(avg, original_avg)


# ---------------------------------------------------------------------------
# Tests for check_rainfall_completeness
# ---------------------------------------------------------------------------

class TestCheckRainfallCompleteness:

    def test_complete_years_marked_true(self, rainfall_df):
        """District-years with >= 10 months should be is_complete=True."""
        completeness = check_rainfall_completeness(rainfall_df)
        # All years in the fixture have 12 months
        assert completeness["is_complete"].all()
        assert (completeness["month_count"] == 12).all()

    def test_partial_year_marked_false(self, partial_year_df):
        """District-years with < 10 months should be is_complete=False."""
        completeness = check_rainfall_completeness(partial_year_df)
        incomplete = completeness[completeness["year"] == 2026]
        assert len(incomplete) == 2  # 2 districts
        assert (~incomplete["is_complete"]).all()
        assert (incomplete["month_count"] == 1).all()

    def test_month_count_accuracy(self, partial_year_df):
        """month_count should reflect the actual number of months per district-year."""
        completeness = check_rainfall_completeness(partial_year_df)
        patna_2020 = completeness[
            (completeness["DISTRICT"] == "PATNA") & (completeness["year"] == 2020)
        ].iloc[0]
        assert patna_2020["month_count"] == 12
        patna_2026 = completeness[
            (completeness["DISTRICT"] == "PATNA") & (completeness["year"] == 2026)
        ].iloc[0]
        assert patna_2026["month_count"] == 1
