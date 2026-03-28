"""
Unit tests for weather feature engineering — Tier A+/B split with NaN passthrough.

TDD tests for compute_weather_features() and WEATHER_FEATURE_COLS constant.
All tests use synthetic DataFrames only (no CSV reads).
"""
import pytest
import pandas as pd
import numpy as np

from app.ml.weather_features import compute_weather_features, WEATHER_FEATURE_COLS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tier_a_plus_districts():
    """Set of Tier A+ districts (with weather coverage)."""
    return {"PATNA", "GAYA", "VARANASI"}


@pytest.fixture
def weather_df():
    """Synthetic weather DataFrame with one Tier A+ district."""
    dates = pd.date_range("2023-01-01", "2023-01-10", freq="D")
    rows = []
    for d in dates:
        rows.append({
            "date": d.strftime("%Y-%m-%d"),
            "district": "PATNA",
            "max_temp_c": 30.0 + d.day,
            "min_temp_c": 20.0 + d.day * 0.5,
            "avg_temp_c": 25.0 + d.day * 0.75,
            "avg_humidity": 60.0 + d.day,
            "max_wind_kph": 10.0 + d.day * 0.3,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def future_weather_df():
    """Weather data only after the cutoff date."""
    dates = pd.date_range("2024-01-01", "2024-01-10", freq="D")
    rows = []
    for d in dates:
        rows.append({
            "date": d.strftime("%Y-%m-%d"),
            "district": "PATNA",
            "max_temp_c": 30.0, "min_temp_c": 20.0, "avg_temp_c": 25.0,
            "avg_humidity": 60.0, "max_wind_kph": 10.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeWeatherFeatures:

    def test_tier_a_plus_returns_weather_columns(self, weather_df, tier_a_plus_districts):
        """Tier A+ district should return DataFrame with exactly 5 weather columns."""
        cutoff = pd.Timestamp("2023-01-10")
        result = compute_weather_features(weather_df, "PATNA", cutoff, tier_a_plus_districts)
        assert set(result.columns) == set(WEATHER_FEATURE_COLS)
        assert len(result) > 0

    def test_tier_b_returns_empty_dataframe(self, weather_df, tier_a_plus_districts):
        """Tier B district (not in tier_a_plus_districts) should return empty DataFrame."""
        cutoff = pd.Timestamp("2023-01-10")
        result = compute_weather_features(weather_df, "UNKNOWN_DISTRICT", cutoff, tier_a_plus_districts)
        assert len(result) == 0
        assert set(result.columns) == set(WEATHER_FEATURE_COLS)

    def test_all_rows_before_or_at_cutoff(self, weather_df, tier_a_plus_districts):
        """All returned rows must have date index <= cutoff_date."""
        cutoff = pd.Timestamp("2023-01-05")
        result = compute_weather_features(weather_df, "PATNA", cutoff, tier_a_plus_districts)
        assert result.index.max() <= cutoff

    def test_district_only_after_cutoff_returns_empty(self, future_weather_df, tier_a_plus_districts):
        """District with data only after cutoff should return empty DataFrame."""
        cutoff = pd.Timestamp("2023-12-31")
        result = compute_weather_features(future_weather_df, "PATNA", cutoff, tier_a_plus_districts)
        assert len(result) == 0

    def test_does_not_modify_input(self, weather_df, tier_a_plus_districts):
        """Function must NOT modify the input weather_df."""
        original = weather_df.copy()
        cutoff = pd.Timestamp("2023-01-10")
        compute_weather_features(weather_df, "PATNA", cutoff, tier_a_plus_districts)
        pd.testing.assert_frame_equal(weather_df, original)

    def test_weather_feature_cols_count(self):
        """WEATHER_FEATURE_COLS constant should have exactly 5 elements."""
        assert len(WEATHER_FEATURE_COLS) == 5

    def test_returned_dataframe_has_datetime_index(self, weather_df, tier_a_plus_districts):
        """Returned DataFrame should have DatetimeIndex."""
        cutoff = pd.Timestamp("2023-01-10")
        result = compute_weather_features(weather_df, "PATNA", cutoff, tier_a_plus_districts)
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_unmatched_weather_district_returns_empty(self, weather_df, tier_a_plus_districts):
        """26 weather-only unmatched districts (not in tier_a_plus_districts) return empty."""
        cutoff = pd.Timestamp("2023-01-10")
        # Simulate a weather district not in the tier A+ set
        result = compute_weather_features(weather_df, "WEATHER_ONLY_DISTRICT", cutoff, tier_a_plus_districts)
        assert len(result) == 0
        assert isinstance(result, pd.DataFrame)
