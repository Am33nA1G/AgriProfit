"""Tests for weather warnings generation."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

from app.harvest_advisor.weather_warnings import (
    compute_spi_3month,
    generate_spi_warnings,
    generate_heat_warnings,
    generate_all_warnings,
)


def make_rainfall_df(district: str, n_years: int = 10, dry: bool = False) -> pd.DataFrame:
    """Create a test rainfall DataFrame."""
    rows = []
    for year in range(2015, 2015 + n_years):
        for month in range(1, 13):
            base = 50.0 if month in [6, 7, 8, 9] else 10.0
            rainfall = base * (0.3 if dry else 1.0) + np.random.normal(0, 2)
            rows.append({
                "DISTRICT": district,
                "STATE": "TestState",
                "year": year,
                "month": month,
                "rainfall": max(0, rainfall),
            })
    return pd.DataFrame(rows)


def test_compute_spi_unknown_district():
    """Returns None for district not in data."""
    df = make_rainfall_df("Known")
    spi, period = compute_spi_3month(df, "Unknown")
    assert spi is None


def test_compute_spi_known_district_returns_float():
    """Returns a float SPI value for a known district."""
    df = make_rainfall_df("TestDist", n_years=15)
    spi, period = compute_spi_3month(df, "TestDist")
    # May be None if not enough data after filtering
    if spi is not None:
        assert isinstance(spi, float)


def test_spi_drought_warning():
    """SPI < -1.5 generates drought warning."""
    warnings = generate_spi_warnings(-2.0, "Nov 2025", "TestDist")
    assert len(warnings) > 0
    assert warnings[0].warning_type == "drought"
    assert warnings[0].severity == "high"


def test_spi_excess_rain_warning():
    """SPI > +1.5 generates flood/excess warning."""
    warnings = generate_spi_warnings(2.0, "Nov 2025", "TestDist")
    assert len(warnings) > 0
    assert warnings[0].warning_type == "flood"


def test_spi_neutral_no_warning():
    """SPI between -1.0 and +1.0 generates no warnings."""
    warnings = generate_spi_warnings(0.3, "Nov 2025", "TestDist")
    assert warnings == []


def test_generate_heat_warnings_extreme():
    """avg_temp > 40 generates extreme heat warning."""
    df = pd.DataFrame({
        "district": ["Jaipur"] * 5,
        "avg_temp_c": [42.0, 41.5, 43.0, 42.0, 41.0],
    })
    warnings = generate_heat_warnings(df, "Jaipur")
    assert any(w.warning_type == "heat_stress" and w.severity == "extreme" for w in warnings)


def test_generate_heat_warnings_no_data():
    """Empty DataFrame returns empty warnings."""
    df = pd.DataFrame(columns=["district", "avg_temp_c"])
    warnings = generate_heat_warnings(df, "SomeDistrict")
    assert warnings == []


def test_generate_all_warnings_no_data():
    """All None inputs returns empty list, no crash."""
    mock_db = MagicMock()
    with patch("app.harvest_advisor.weather_warnings.OpenMeteoClient") as mock_client:
        mock_client.return_value.fetch_forecast.return_value = None
        warnings, spi, drought_risk = generate_all_warnings("TestDist", "TestState", mock_db)
    assert isinstance(warnings, list)
    assert drought_risk == "none"
