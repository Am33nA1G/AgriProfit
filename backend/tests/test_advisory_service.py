"""Unit tests for the directional advisory service."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.advisory.service import DirectionalAdvisoryService


class DummyDirectionModel:
    """Minimal classifier stub with deterministic probabilities."""

    def __init__(self, probabilities: list[float]):
        self._probabilities = probabilities

    def predict_proba(self, _matrix):
        return [self._probabilities]


COMMON_FEATURE_COLUMNS = [
    "modal_price",
    "history_index",
    "lag_1",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_30",
    "return_1",
    "return_3",
    "return_7",
    "return_14",
    "return_30",
    "rolling_mean_7",
    "rolling_std_7",
    "gap_to_mean_7",
    "volatility_7",
    "rolling_mean_14",
    "rolling_std_14",
    "gap_to_mean_14",
    "volatility_14",
    "rolling_mean_30",
    "rolling_std_30",
    "gap_to_mean_30",
    "volatility_30",
    "sin_annual",
    "cos_annual",
    "sin_weekly",
    "cos_weekly",
    "sin_monthly",
    "cos_monthly",
    "recent_7d_change_pct",
    "recent_30d_change_pct",
    "district__pune",
]


def _seed_history(test_db, commodity_name: str = "Onion", district: str = "Pune", days: int = 90) -> None:
    commodity_id = str(uuid4())
    mandi_id = str(uuid4())
    mandi_name = f"{district} Market"
    market_code = f"{district[:3].upper()}001"

    test_db.execute(
        text(
            """
            INSERT INTO commodities (id, name)
            VALUES (:id, :name)
            """
        ),
        {"id": commodity_id, "name": commodity_name},
    )
    test_db.execute(
        text(
            """
            INSERT INTO mandis (id, name, state, district, market_code, is_active)
            VALUES (:id, :name, :state, :district, :market_code, 1)
            """
        ),
        {
            "id": mandi_id,
            "name": mandi_name,
            "state": "Maharashtra",
            "district": district,
            "market_code": market_code,
        },
    )

    start = date.today() - timedelta(days=days - 1)
    for offset in range(days):
        test_db.execute(
            text(
                """
                INSERT INTO price_history (
                    id, commodity_id, mandi_id, mandi_name, price_date,
                    modal_price, min_price, max_price
                )
                VALUES (
                    :id, :commodity_id, :mandi_id, :mandi_name, :price_date,
                    :modal_price, :min_price, :max_price
                )
                """
            ),
            {
                "id": str(uuid4()),
                "commodity_id": commodity_id,
                "mandi_id": mandi_id,
                "mandi_name": mandi_name,
                "price_date": start + timedelta(days=offset),
                "modal_price": float(2000 + (offset * 4)),
                "min_price": float(1950 + (offset * 4)),
                "max_price": float(2050 + (offset * 4)),
            },
        )
    test_db.commit()


def test_advisory_abstains_without_meta(test_db):
    service = DirectionalAdvisoryService(test_db)

    with patch("app.advisory.service.load_direction_meta", return_value=None):
        result = service.get_advisory("Onion", "Pune")

    assert result.signal == "abstain"
    assert result.recommendation_available is False
    assert "No validated directional advisory model" in result.reason


def test_advisory_returns_direction_when_confident(test_db):
    _seed_history(test_db, days=120)
    service = DirectionalAdvisoryService(test_db)
    meta = {
        "deployable": True,
        "horizon_days": 7,
        "min_history_days": 60,
        "max_data_staleness_days": 30,
        "balanced_accuracy": 0.62,
        "validation_samples": 240,
        "recommended_confidence_threshold": 0.70,
        "covered_districts": ["Pune"],
        "class_labels": ["down", "flat", "up"],
        "feature_columns": COMMON_FEATURE_COLUMNS,
    }
    bundle = {
        "model": DummyDirectionModel([0.10, 0.15, 0.75]),
        "class_labels": ["down", "flat", "up"],
        "feature_columns": COMMON_FEATURE_COLUMNS,
    }

    with patch("app.advisory.service.load_direction_meta", return_value=meta), \
         patch("app.advisory.service.load_direction_bundle", return_value=bundle):
        result = service.get_advisory("Onion", "Pune")

    assert result.signal == "up"
    assert result.recommendation_available is True
    assert result.confidence_score == pytest.approx(0.75)
    assert result.probabilities.up == pytest.approx(0.75)
    assert result.current_price is not None


def test_advisory_abstains_below_confidence_threshold(test_db):
    _seed_history(test_db, days=120)
    service = DirectionalAdvisoryService(test_db)
    meta = {
        "deployable": True,
        "horizon_days": 7,
        "min_history_days": 60,
        "max_data_staleness_days": 30,
        "balanced_accuracy": 0.58,
        "validation_samples": 180,
        "recommended_confidence_threshold": 0.80,
        "covered_districts": ["Pune"],
        "class_labels": ["down", "flat", "up"],
        "feature_columns": COMMON_FEATURE_COLUMNS,
    }
    bundle = {
        "model": DummyDirectionModel([0.25, 0.45, 0.30]),
        "class_labels": ["down", "flat", "up"],
        "feature_columns": COMMON_FEATURE_COLUMNS,
    }

    with patch("app.advisory.service.load_direction_meta", return_value=meta), \
         patch("app.advisory.service.load_direction_bundle", return_value=bundle):
        result = service.get_advisory("Onion", "Pune")

    assert result.signal == "abstain"
    assert result.recommendation_available is False
    assert "below the deployment threshold" in result.reason
    assert result.probabilities.flat == pytest.approx(0.45)
