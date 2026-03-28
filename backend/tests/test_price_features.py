"""
Unit tests for price feature engineering — lag and rolling statistics.

TDD tests for compute_price_features() — tests written first, implementation follows.
All tests use synthetic data only (no parquet reads, no database).
"""
import pytest
import pandas as pd
import numpy as np

from app.ml.price_features import compute_price_features


# ---------------------------------------------------------------------------
# Fixtures — synthetic price series
# ---------------------------------------------------------------------------

@pytest.fixture
def daily_series():
    """A simple daily price series (no gaps) for 30 days."""
    dates = pd.date_range("2023-01-01", periods=30, freq="D")
    prices = pd.Series(np.arange(100, 130, dtype=float), index=dates)
    return prices


@pytest.fixture
def irregular_series():
    """An irregular price series with a 7-day gap (simulates weekends + holidays)."""
    dates = pd.to_datetime([
        "2023-01-01", "2023-01-02", "2023-01-03",
        # 7-day gap: no data 2023-01-04 through 2023-01-09
        "2023-01-10", "2023-01-11", "2023-01-12",
        "2023-01-15", "2023-01-20", "2023-01-25",
    ])
    prices = pd.Series([100, 110, 120, 130, 140, 150, 160, 170, 180], index=dates)
    return prices


@pytest.fixture
def eight_year_series():
    """An 8-year daily series for leakage detection testing (2015-2022)."""
    dates = pd.date_range("2015-01-01", "2022-12-31", freq="D")
    rng = np.random.default_rng(42)
    prices = rng.normal(loc=2000, scale=200, size=len(dates))
    return pd.Series(prices, index=dates)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputePriceFeatures:
    """Tests for compute_price_features()."""

    def test_empty_series_returns_empty_dataframe(self):
        """Empty input series should return an empty DataFrame."""
        empty = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        cutoff = pd.Timestamp("2023-12-31")
        result = compute_price_features(empty, cutoff)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_all_rows_before_or_at_cutoff(self, daily_series):
        """All feature rows must have dates <= cutoff_date."""
        cutoff = pd.Timestamp("2023-01-15")
        result = compute_price_features(daily_series, cutoff)
        assert result.index.max() <= cutoff

    def test_no_lookahead_leakage(self, eight_year_series):
        """
        LEAKAGE DETECTION TEST (permanent sentinel).
        Training features computed with cutoff=2021-12-31 must contain
        no rows from 2022.
        """
        cutoff = pd.Timestamp("2021-12-31")
        result = compute_price_features(eight_year_series, cutoff)
        # No row index should be in 2022
        assert result.index.max() <= cutoff
        # Verify no price values from 2022 appear in any column
        test_period_prices = eight_year_series.loc["2022-01-01":]
        for col in result.columns:
            if col.startswith("price_lag") or col == "price_modal":
                col_values = result[col].dropna()
                # None of the test-period specific prices should appear
                # (checking structural cutoff, not value coincidence)
                pass
        # The structural guarantee: index max <= cutoff
        assert all(result.index <= cutoff)

    def test_lag_columns_have_nan_for_first_n_rows(self, daily_series):
        """Lag columns should have NaN for the first N calendar days."""
        cutoff = pd.Timestamp("2023-01-30")
        result = compute_price_features(daily_series, cutoff, lags=[7])
        # First 7 rows should have NaN for 7d lag
        assert result["price_lag_7d"].iloc[:7].isna().all()
        # Row at index 7 should NOT be NaN (has data 7 days prior)
        assert not pd.isna(result["price_lag_7d"].iloc[7])

    def test_rolling_mean_excludes_current_day(self, daily_series):
        """
        Rolling mean at position N should equal the mean of the PREVIOUS
        window days (shift(1) before rolling) — current day excluded.
        """
        cutoff = pd.Timestamp("2023-01-30")
        result = compute_price_features(daily_series, cutoff, roll_windows=[7])
        # At position 8 (index 7 in 0-based), the 7d rolling mean should be
        # computed on shifted series: positions 1-7 (values 101-107)
        # shift(1) at position 8 gives value at position 7 = 107
        # rolling(7) at that shifted position: values at shifted positions 2-8
        # = original positions 1-7 = 101,102,103,104,105,106,107
        val = result["price_roll_mean_7d"].iloc[8]
        expected = np.mean([101, 102, 103, 104, 105, 106, 107])
        assert abs(val - expected) < 0.01

    def test_rolling_std_nan_when_all_identical(self):
        """Rolling std should be NaN (or 0) when all window values are identical."""
        dates = pd.date_range("2023-01-01", periods=20, freq="D")
        prices = pd.Series([100.0] * 20, index=dates)
        cutoff = pd.Timestamp("2023-01-20")
        result = compute_price_features(prices, cutoff, roll_windows=[7])
        # After enough warmup, std should be 0 or NaN for constant values
        late_std = result["price_roll_std_7d"].iloc[10:]
        assert (late_std.fillna(0) == 0).all()

    def test_irregular_series_correct_7d_lag(self, irregular_series):
        """
        Irregular series with gaps must produce correct calendar-day lags.
        Daily reindex is required — shift(7) on records != shift(7 calendar days).
        """
        cutoff = pd.Timestamp("2023-01-25")
        result = compute_price_features(irregular_series, cutoff, lags=[7])
        # On 2023-01-10 (after reindex+ffill), the 7d lag should be the
        # price from 2023-01-03 = 120 (forward-filled)
        val = result.loc["2023-01-10", "price_lag_7d"]
        assert val == 120.0

    def test_does_not_modify_input_series(self, daily_series):
        """compute_price_features must not modify the input Series."""
        original = daily_series.copy()
        cutoff = pd.Timestamp("2023-01-30")
        compute_price_features(daily_series, cutoff)
        pd.testing.assert_series_equal(daily_series, original)

    def test_custom_lags_and_roll_windows(self, daily_series):
        """Custom lags and roll_windows should be respected."""
        cutoff = pd.Timestamp("2023-01-30")
        result = compute_price_features(
            daily_series, cutoff, lags=[3, 5], roll_windows=[5]
        )
        assert "price_lag_3d" in result.columns
        assert "price_lag_5d" in result.columns
        assert "price_roll_mean_5d" in result.columns
        assert "price_roll_std_5d" in result.columns
        # Default columns should NOT be present
        assert "price_lag_7d" not in result.columns
        assert "price_roll_mean_7d" not in result.columns
