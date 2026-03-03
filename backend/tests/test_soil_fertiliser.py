"""Unit tests for app.soil_advisor.fertiliser pure functions.

RED phase: These tests are written before the implementation exists.
They must fail with ImportError or AttributeError until Task 4 creates fertiliser.py.
"""
from app.soil_advisor.fertiliser import FERTILISER_ADVICE, generate_fertiliser_advice


def test_advice_generated_above_threshold():
    """generate_fertiliser_advice returns 1 advice card when N low_pct > 50."""
    profile = {"Nitrogen": {"high": 0, "medium": 4, "low": 96}}
    result = generate_fertiliser_advice(profile)
    assert len(result) == 1
    card = result[0]
    assert card["nutrient"] == "Nitrogen"
    assert card["low_pct"] == 96
    assert card["message"].startswith("96")
    assert "Urea" in card["fertiliser_recommendation"]


def test_no_advice_below_threshold():
    """generate_fertiliser_advice returns empty list when low_pct < 50."""
    profile = {"Phosphorus": {"high": 30, "medium": 30, "low": 40}}
    result = generate_fertiliser_advice(profile)
    assert result == []


def test_threshold_boundary_at_50():
    """generate_fertiliser_advice returns empty list when low_pct == 50 (strict >)."""
    profile = {"Nitrogen": {"high": 20, "medium": 30, "low": 50}}
    result = generate_fertiliser_advice(profile)
    assert result == []


def test_threshold_boundary_at_51():
    """generate_fertiliser_advice returns 1 item when low_pct == 51."""
    profile = {"Nitrogen": {"high": 20, "medium": 29, "low": 51}}
    result = generate_fertiliser_advice(profile)
    assert len(result) == 1


def test_ph_not_in_advice():
    """generate_fertiliser_advice never emits advice for pH (Potential Of Hydrogen)."""
    profile = {"Potential Of Hydrogen": {"high": 5, "medium": 15, "low": 80}}
    result = generate_fertiliser_advice(profile)
    assert result == []


def test_empty_profile_returns_empty_list():
    """generate_fertiliser_advice returns empty list for empty profile dict."""
    result = generate_fertiliser_advice({})
    assert result == []


def test_multiple_deficiencies():
    """generate_fertiliser_advice returns 2 cards when both N and OC are deficient."""
    profile = {
        "Nitrogen": {"high": 0, "medium": 4, "low": 96},
        "Organic Carbon": {"high": 5, "medium": 15, "low": 80},
    }
    result = generate_fertiliser_advice(profile)
    assert len(result) == 2
    nutrients = {card["nutrient"] for card in result}
    assert "Nitrogen" in nutrients
    assert "Organic Carbon" in nutrients
