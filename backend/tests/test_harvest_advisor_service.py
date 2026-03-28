"""Tests for HarvestAdvisorService."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.harvest_advisor.service import HarvestAdvisorService
from app.harvest_advisor.schemas import HarvestAdvisorResponse, CropRecommendation


def test_compute_recommendation_no_data_files(test_db):
    """Returns valid HarvestAdvisorResponse even when all data files are missing."""
    svc = HarvestAdvisorService(test_db)
    with patch("app.harvest_advisor.service._load_parquet_safe", return_value=None), \
         patch("app.harvest_advisor.service._load_csv_safe", return_value=None), \
         patch("app.harvest_advisor.weather_warnings.generate_all_warnings",
               return_value=([], None, "none")):
        result = svc.compute_recommendation("Maharashtra", "Nashik", "annual")

    assert isinstance(result, HarvestAdvisorResponse)
    assert result.state == "Maharashtra"
    assert result.district == "Nashik"
    assert result.season == "annual"
    assert len(result.recommendations) <= 5
    assert not result.soil_data_available
    assert not result.yield_data_available


def test_recommendations_ranked_by_profit(test_db):
    """Recommendations are sorted by expected_profit_per_ha descending."""
    svc = HarvestAdvisorService(test_db)
    with patch("app.harvest_advisor.service._load_parquet_safe", return_value=None), \
         patch("app.harvest_advisor.service._load_csv_safe", return_value=None), \
         patch("app.harvest_advisor.weather_warnings.generate_all_warnings",
               return_value=([], None, "none")):
        result = svc.compute_recommendation("Maharashtra", "Nashik", "annual")

    profits = [r.expected_profit_per_ha for r in result.recommendations]
    assert profits == sorted(profits, reverse=True)


def test_recommendation_rank_field(test_db):
    """Rank field should be 1-5 in order."""
    svc = HarvestAdvisorService(test_db)
    with patch("app.harvest_advisor.service._load_parquet_safe", return_value=None), \
         patch("app.harvest_advisor.service._load_csv_safe", return_value=None), \
         patch("app.harvest_advisor.weather_warnings.generate_all_warnings",
               return_value=([], None, "none")):
        result = svc.compute_recommendation("Punjab", "Ludhiana", "rabi")

    ranks = [r.rank for r in result.recommendations]
    assert ranks == list(range(1, len(ranks) + 1))


def test_get_weather_warnings_no_data(test_db):
    """Returns empty list when no data files available."""
    svc = HarvestAdvisorService(test_db)
    with patch("app.harvest_advisor.service._load_parquet_safe", return_value=None), \
         patch("app.harvest_advisor.service._load_csv_safe", return_value=None), \
         patch("app.harvest_advisor.weather_warnings.generate_all_warnings",
               return_value=([], None, "none")):
        result = svc.get_weather_warnings("Maharashtra", "Nashik")
    assert result == []


def test_get_districts_with_data_no_files(test_db):
    """Returns empty list when data files missing."""
    svc = HarvestAdvisorService(test_db)
    with patch("app.harvest_advisor.service._load_parquet_safe", return_value=None):
        result = svc.get_districts_with_data("Maharashtra")
    assert result == []
