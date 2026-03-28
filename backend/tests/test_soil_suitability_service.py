"""
Integration tests for soil advisor service with ML model integration.
Uses SQLite in-memory DB (same as rest of test suite).
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.soil_advisor.service import get_soil_advice

# ── Shared in-memory DB ───────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)


def setup_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS soil_profiles (
                state TEXT, district TEXT, block TEXT,
                nutrient TEXT, high_pct REAL, medium_pct REAL, low_pct REAL, cycle TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS soil_crop_suitability (
                crop_name TEXT, nutrient TEXT, min_tolerance TEXT,
                ph_min REAL, ph_max REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS seasonal_price_stats (
                commodity_name TEXT, state TEXT, best_sell_month TEXT
            )
        """))
        # Seed one block with nutrient data
        nutrients = [
            ("Nitrogen", 20, 30, 50),
            ("Phosphorus", 81, 17, 2),
            ("Potassium", 50, 40, 10),
            ("Organic Carbon", 10, 20, 70),
            ("Potential Of Hydrogen", 30, 50, 20),
        ]
        for nutrient, hi, med, lo in nutrients:
            conn.execute(text("""
                INSERT INTO soil_profiles VALUES
                ('ANDHRA PRADESH', 'ANANTAPUR', 'TEST BLOCK - 0001',
                 :nutrient, :hi, :med, :lo, '2023-24')
            """), {"nutrient": nutrient, "hi": hi, "med": med, "lo": lo})
        # Seed two rule-based crops (fallback)
        conn.execute(text("""
            INSERT INTO soil_crop_suitability VALUES ('Rice', 'Nitrogen', 'medium', 5.5, 7.0)
        """))
        conn.execute(text("""
            INSERT INTO soil_crop_suitability VALUES ('Tomato', 'Phosphorus', 'high', 6.0, 7.0)
        """))
        conn.commit()


setup_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_ml_result(*args, **kwargs):
    """Simulate ML model returning ranked crops."""
    return [
        {"crop_name": "Tomato", "score": 0.85, "source": "ml"},
        {"crop_name": "Rice",   "score": 0.70, "source": "ml"},
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_service_uses_ml_when_model_available():
    """Test that service integrates ML model predictions when available."""
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        crop_names = [r.crop_name for r in result.crop_recommendations]
        assert "Tomato" in crop_names
        assert "Rice" in crop_names
    finally:
        db.close()


def test_service_falls_back_to_rule_based_when_ml_unavailable():
    """Test that service falls back gracefully when ML model is absent."""
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            return_value=None,  # model absent
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        # Rule-based fallback should still return something
        assert isinstance(result.crop_recommendations, list)
        assert len(result.crop_recommendations) > 0
    finally:
        db.close()


def test_service_result_has_correct_schema():
    """Test that service response has expected schema and structure."""
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        assert result.state == "ANDHRA PRADESH"
        assert result.district == "ANANTAPUR"
        assert result.block == "TEST BLOCK - 0001"
        assert len(result.nutrient_distributions) == 5
        assert result.disclaimer != ""
        assert result.cycle == "2023-24"

        # Verify crops have correct rank (1-indexed)
        for i, crop in enumerate(result.crop_recommendations, start=1):
            assert crop.suitability_rank == i
            assert crop.crop_name != ""
            assert crop.suitability_score >= 0
    finally:
        db.close()


def test_service_ranks_crops_by_ml_score():
    """Test that crops are ranked by ML model score (highest first)."""
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        # First recommendation should be Tomato (score 0.85 > 0.70)
        assert result.crop_recommendations[0].crop_name == "Tomato"
        assert result.crop_recommendations[0].suitability_score == 0.85
        # Second should be Rice
        assert result.crop_recommendations[1].crop_name == "Rice"
        assert result.crop_recommendations[1].suitability_score == 0.70
    finally:
        db.close()


def test_service_includes_nutrient_distributions():
    """Test that nutrient distributions are correctly populated."""
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        assert len(result.nutrient_distributions) == 5
        nutrients = [nd.nutrient for nd in result.nutrient_distributions]
        expected = [
            "Nitrogen",
            "Phosphorus",
            "Potassium",
            "Organic Carbon",
            "Potential Of Hydrogen",
        ]
        assert nutrients == expected

        # Verify percentages sum to 100
        for nd in result.nutrient_distributions:
            assert nd.high_pct + nd.medium_pct + nd.low_pct == 100
    finally:
        db.close()


def test_service_generates_fertiliser_advice():
    """Test that fertiliser advice is generated based on nutrient levels."""
    db = Session()
    try:
        with patch(
            "app.soil_advisor.service.predict_crop_suitability",
            side_effect=_fake_ml_result,
        ):
            result = get_soil_advice(db, "ANDHRA PRADESH", "ANANTAPUR", "TEST BLOCK - 0001")

        # Fertiliser advice should be present (depends on nutrient deficiencies)
        assert isinstance(result.fertiliser_advice, list)
        for advice in result.fertiliser_advice:
            assert advice.nutrient != ""
            assert advice.message != ""
            assert advice.fertiliser_recommendation != ""
    finally:
        db.close()
