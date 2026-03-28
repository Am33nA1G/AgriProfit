"""
Unit tests for seasonal price calendar aggregator.

Tests use synthetic DataFrames only — no parquet file, no DB calls required.
All tests verify pure function behaviour of compute_seasonal_stats().
"""
import pandas as pd
import pytest

from app.ml.seasonal.aggregator import compute_seasonal_stats


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def single_commodity_low_data():
    """Single commodity, single state, 1 year of data (5 months)."""
    rows = []
    for month in [1, 2, 3, 4, 5]:
        for day_price in [100.0 + month * 10, 105.0 + month * 10, 95.0 + month * 10]:
            rows.append({
                "commodity": "Wheat",
                "state": "Maharashtra",
                "price_modal": day_price,
                "month": month,
                "year": 2023,
            })
    return pd.DataFrame(rows)


@pytest.fixture
def single_commodity_sufficient_data():
    """Single commodity, single state, 4 years of data, 12 months."""
    rows = []
    # Create data where months have clearly different medians
    # Month 10 and 11 should have the highest prices (is_best)
    # Month 4 should have the lowest price (is_worst)
    month_base_prices = {
        1: 500, 2: 520, 3: 480, 4: 400,     # April cheapest
        5: 550, 6: 600, 7: 650, 8: 700,
        9: 750, 10: 900, 11: 950, 12: 800,  # Oct, Nov most expensive
    }
    for year in [2020, 2021, 2022, 2023]:
        for month, base in month_base_prices.items():
            for offset in [-20, 0, 20, 10, -10]:
                rows.append({
                    "commodity": "Onion",
                    "state": "Maharashtra",
                    "price_modal": float(base + offset + year * 0.1),
                    "month": month,
                    "year": year,
                })
    return pd.DataFrame(rows)


@pytest.fixture
def multi_commodity_mixed_data():
    """Two commodities: Onion (4 years), Carrot (2 years)."""
    rows = []
    # Onion: 4 years → should get is_best/is_worst
    for year in [2020, 2021, 2022, 2023]:
        for month in range(1, 13):
            base = 500 + month * 50
            rows.append({
                "commodity": "Onion",
                "state": "Maharashtra",
                "price_modal": float(base),
                "month": month,
                "year": year,
            })
    # Carrot: only 2 years → should NOT get is_best/is_worst
    for year in [2022, 2023]:
        for month in range(1, 7):
            rows.append({
                "commodity": "Carrot",
                "state": "Delhi",
                "price_modal": float(200 + month * 30),
                "month": month,
                "year": year,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests: compute_seasonal_stats()
# ---------------------------------------------------------------------------

class TestComputeSeasonalStats:

    def test_low_data_no_best_worst_labels(self, single_commodity_low_data):
        """When years_of_data < 3, is_best and is_worst must be False for all months."""
        result = compute_seasonal_stats(single_commodity_low_data)
        assert len(result) == 5  # 5 months
        assert result["is_best"].sum() == 0, "is_best must be False for all months with < 3 years"
        assert result["is_worst"].sum() == 0, "is_worst must be False for all months with < 3 years"

    def test_sufficient_data_best_worst_labels(self, single_commodity_sufficient_data):
        """When years_of_data >= 3, top-2 months get is_best, bottom-1 gets is_worst."""
        result = compute_seasonal_stats(single_commodity_sufficient_data)
        assert len(result) == 12  # 12 months

        best_months = result[result["is_best"] == True]["month"].tolist()
        worst_months = result[result["is_worst"] == True]["month"].tolist()

        assert len(best_months) == 2, f"Expected 2 best months, got {len(best_months)}"
        assert len(worst_months) == 1, f"Expected 1 worst month, got {len(worst_months)}"

        # Best months should be 10 and 11 (highest base prices)
        assert 10 in best_months or 11 in best_months, (
            f"Expected month 10 or 11 in best months, got {best_months}"
        )

        # Worst month should be 4 (lowest base price = 400)
        assert 4 in worst_months, f"Expected month 4 as worst, got {worst_months}"

    def test_month_rank_highest_price_is_rank_1(self, single_commodity_sufficient_data):
        """month_rank=1 must correspond to the month with highest median_price."""
        result = compute_seasonal_stats(single_commodity_sufficient_data)
        rank1_row = result[result["month_rank"] == 1].iloc[0]
        max_median = result["median_price"].max()
        assert rank1_row["median_price"] == max_median, (
            f"month_rank=1 should have the highest median_price ({max_median}), "
            f"got {rank1_row['median_price']}"
        )

    def test_iqr_equals_q3_minus_q1(self, single_commodity_sufficient_data):
        """iqr_price must equal q3_price - q1_price for every row."""
        result = compute_seasonal_stats(single_commodity_sufficient_data)
        for _, row in result.iterrows():
            expected_iqr = row["q3_price"] - row["q1_price"]
            assert abs(row["iqr_price"] - expected_iqr) < 0.01, (
                f"IQR mismatch for month {row['month']}: "
                f"q3-q1={expected_iqr}, iqr={row['iqr_price']}"
            )

    def test_iqr_never_negative(self, single_commodity_sufficient_data):
        """iqr_price must never be negative (q3 >= q1 by definition)."""
        result = compute_seasonal_stats(single_commodity_sufficient_data)
        assert (result["iqr_price"] >= 0).all(), "iqr_price must never be negative"

    def test_mixed_data_independent_labelling(self, multi_commodity_mixed_data):
        """Commodity with >= 3 years gets labels; one with < 3 years does not."""
        result = compute_seasonal_stats(multi_commodity_mixed_data)

        onion = result[result["commodity_name"] == "Onion"]
        carrot = result[result["commodity_name"] == "Carrot"]

        # Onion (4 years) should have best/worst labels
        assert onion["is_best"].sum() == 2, "Onion should have 2 best months"
        assert onion["is_worst"].sum() == 1, "Onion should have 1 worst month"

        # Carrot (2 years) should NOT have any labels
        assert carrot["is_best"].sum() == 0, "Carrot (2 years) must not have is_best"
        assert carrot["is_worst"].sum() == 0, "Carrot (2 years) must not have is_worst"

    def test_output_column_names(self, single_commodity_low_data):
        """Output must have the correct column names matching the DB schema."""
        result = compute_seasonal_stats(single_commodity_low_data)
        required = {
            "commodity_name", "state_name", "month", "median_price",
            "q1_price", "q3_price", "iqr_price", "record_count",
            "years_of_data", "month_rank", "is_best", "is_worst",
        }
        assert required.issubset(set(result.columns)), (
            f"Missing columns: {required - set(result.columns)}"
        )

    def test_years_of_data_correct(self, single_commodity_sufficient_data):
        """years_of_data should match the distinct year count in input."""
        result = compute_seasonal_stats(single_commodity_sufficient_data)
        assert result["years_of_data"].iloc[0] == 4, (
            f"Expected 4 years of data, got {result['years_of_data'].iloc[0]}"
        )

    def test_empty_dataframe(self):
        """Empty input should return an empty DataFrame with correct columns."""
        df = pd.DataFrame(columns=["commodity", "state", "price_modal", "month", "year"])
        result = compute_seasonal_stats(df)
        assert len(result) == 0
        assert "commodity_name" in result.columns

    def test_record_count_correct(self, single_commodity_low_data):
        """record_count should match the number of observations per month."""
        result = compute_seasonal_stats(single_commodity_low_data)
        # Each month has 3 observations in the fixture
        for _, row in result.iterrows():
            assert row["record_count"] == 3, (
                f"Expected 3 records for month {row['month']}, got {row['record_count']}"
            )
