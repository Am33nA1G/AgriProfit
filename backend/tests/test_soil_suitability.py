"""Unit tests for app.soil_advisor.suitability pure functions.

RED phase: These tests are written before the implementation exists.
They must fail with ImportError or AttributeError until Task 4 creates suitability.py.
"""
from app.soil_advisor.suitability import COVERED_STATES, is_deficient, score_crop, rank_crops


def test_covered_states_count():
    """COVERED_STATES must contain exactly 21 states."""
    assert len(COVERED_STATES) == 21


def test_covered_states_no_lowercase():
    """All state names must be uppercase — no mixed-case entries."""
    for state in COVERED_STATES:
        assert state == state.upper(), f"State '{state}' is not fully uppercase"


def test_jk_uses_ampersand():
    """COVERED_STATES must use 'JAMMU & KASHMIR', not 'JAMMU AND KASHMIR'."""
    assert "JAMMU & KASHMIR" in COVERED_STATES


def test_is_deficient_above_threshold():
    """is_deficient returns True when low_pct > 50."""
    profile = {"Nitrogen": {"high": 0, "medium": 4, "low": 96}}
    assert is_deficient(profile, "Nitrogen") is True


def test_is_deficient_at_threshold():
    """is_deficient returns False when low_pct == 50 (threshold is strict >)."""
    profile = {"Nitrogen": {"high": 30, "medium": 20, "low": 50}}
    assert is_deficient(profile, "Nitrogen") is False


def test_is_deficient_below_threshold():
    """is_deficient returns False when low_pct < 50."""
    profile = {"Nitrogen": {"high": 40, "medium": 30, "low": 30}}
    assert is_deficient(profile, "Nitrogen") is False


def test_rank_crops_nitrogen_deficient():
    """rank_crops returns non-empty list for an N-deficient block profile."""
    n_deficient_profile = {"Nitrogen": {"high": 0, "medium": 4, "low": 96}}
    crop_rows = [
        {"crop_name": "Soybean", "nutrient": "Nitrogen", "min_tolerance": "low", "ph_min": None, "ph_max": None},
        {"crop_name": "Chickpea", "nutrient": "Nitrogen", "min_tolerance": "low", "ph_min": None, "ph_max": None},
        {"crop_name": "Wheat", "nutrient": "Nitrogen", "min_tolerance": "high", "ph_min": None, "ph_max": None},
    ]
    result = rank_crops(n_deficient_profile, crop_rows)
    assert len(result) > 0


def test_nitrogen_tolerant_crops_rank_higher():
    """A crop with N_min='low' scores higher than N_min='high' in N-deficient soil."""
    low_n_crop = {"crop_name": "Soybean", "nutrient": "Nitrogen", "min_tolerance": "low", "ph_min": None, "ph_max": None}
    high_n_crop = {"crop_name": "Wheat", "nutrient": "Nitrogen", "min_tolerance": "high", "ph_min": None, "ph_max": None}
    n_deficient_profile = {"Nitrogen": {"high": 0, "medium": 4, "low": 96}}
    assert score_crop(n_deficient_profile, low_n_crop) > score_crop(n_deficient_profile, high_n_crop)


def test_rank_crops_max_five_results():
    """rank_crops returns at most 5 results even when given 10 crop rows."""
    profile = {"Nitrogen": {"high": 5, "medium": 45, "low": 50}}
    crop_rows = [
        {"crop_name": f"Crop{i}", "nutrient": "Nitrogen", "min_tolerance": "low", "ph_min": None, "ph_max": None}
        for i in range(10)
    ]
    result = rank_crops(profile, crop_rows)
    assert len(result) <= 5


def test_rank_crops_zero_score_excluded():
    """rank_crops excludes crops where score == 0 (unsuitable for the block)."""
    # High N-deficiency: min_tolerance='high' crops should score 0 and be excluded
    n_deficient_profile = {"Nitrogen": {"high": 0, "medium": 4, "low": 96}}
    crop_rows = [
        {"crop_name": "Wheat", "nutrient": "Nitrogen", "min_tolerance": "high", "ph_min": None, "ph_max": None},
        {"crop_name": "Cotton", "nutrient": "Nitrogen", "min_tolerance": "high", "ph_min": None, "ph_max": None},
    ]
    result = rank_crops(n_deficient_profile, crop_rows)
    # Both high-N crops should score 0 and be excluded from results
    for item in result:
        assert item["score"] > 0
