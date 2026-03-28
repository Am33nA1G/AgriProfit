"""TDD tests for ORM models: ModelTrainingLog and ForecastCache (plan 04-01).

Validates that both SQLAlchemy ORM models are importable, have correct
table names, and expose all required column attributes.
"""
import pytest


# ---------------------------------------------------------------------------
# Test 1: ModelTrainingLog is importable and has correct tablename
# ---------------------------------------------------------------------------

def test_model_training_log_importable():
    """from app.models.model_training_log import ModelTrainingLog succeeds
    and __tablename__ is 'model_training_log'."""
    from app.models.model_training_log import ModelTrainingLog

    assert ModelTrainingLog.__tablename__ == "model_training_log"


# ---------------------------------------------------------------------------
# Test 2: ForecastCache is importable and has correct tablename
# ---------------------------------------------------------------------------

def test_forecast_cache_importable():
    """from app.models.forecast_cache import ForecastCache succeeds
    and __tablename__ is 'forecast_cache'."""
    from app.models.forecast_cache import ForecastCache

    assert ForecastCache.__tablename__ == "forecast_cache"


# ---------------------------------------------------------------------------
# Test 3: ForecastCache has all required column attributes
# ---------------------------------------------------------------------------

def test_forecast_cache_has_required_attributes():
    """ForecastCache has commodity_name, district_name, generated_date,
    direction, price_low, price_mid, price_high, confidence_colour,
    tier_label, expires_at."""
    from app.models.forecast_cache import ForecastCache

    required_attrs = [
        "commodity_name",
        "district_name",
        "generated_date",
        "direction",
        "price_low",
        "price_mid",
        "price_high",
        "confidence_colour",
        "tier_label",
        "expires_at",
    ]
    for attr in required_attrs:
        assert hasattr(ForecastCache, attr), (
            f"ForecastCache missing required attribute: {attr}"
        )


# ---------------------------------------------------------------------------
# Test 4: ModelTrainingLog has all required column attributes
# ---------------------------------------------------------------------------

def test_model_training_log_has_required_attributes():
    """ModelTrainingLog has commodity, rmse_mean, mape_mean,
    artifact_path, excluded_districts."""
    from app.models.model_training_log import ModelTrainingLog

    required_attrs = [
        "commodity",
        "rmse_mean",
        "mape_mean",
        "artifact_path",
        "excluded_districts",
    ]
    for attr in required_attrs:
        assert hasattr(ModelTrainingLog, attr), (
            f"ModelTrainingLog missing required attribute: {attr}"
        )
