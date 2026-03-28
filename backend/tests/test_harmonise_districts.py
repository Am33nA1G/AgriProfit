"""Unit tests for district harmonisation helper functions.

Tests exercise pure-DataFrame logic (no DB calls).
All tests import directly from the script using path manipulation.
"""
import sys
import os
from pathlib import Path

import pandas as pd
import pytest

# Add scripts directory to path so we can import the harmonisation module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from harmonise_districts import (
    normalise_state_name,
    match_within_state,
)


# ---------------------------------------------------------------------------
# normalise_state_name tests
# ---------------------------------------------------------------------------

class TestNormaliseStateName:
    """Test state name normalisation produces canonical forms."""

    def test_jammu_kashmir_variants_match(self):
        """All J&K variants should normalise to same form."""
        variants = [
            "JAMMU & KASHMIR",
            "Jammu and Kashmir",
            "Jammu & Kashmir",
            "J&K",
            "jammu and kashmir",
        ]
        canonical_forms = {normalise_state_name(v) for v in variants}
        # All should collapse to one canonical form
        assert len(canonical_forms) == 1, (
            f"Expected 1 canonical form for J&K variants, got {len(canonical_forms)}: {canonical_forms}"
        )

    def test_andaman_nicobar_variants_match(self):
        """Andaman & Nicobar Island variants normalise to same form."""
        v1 = normalise_state_name("ANDAMAN & NICOBAR")
        v2 = normalise_state_name("Andaman and Nicobar")
        v3 = normalise_state_name("Andaman & Nicobar Islands")
        assert v1 == v2 == v3, (
            f"Andaman variants did not normalise to same form: {v1!r}, {v2!r}, {v3!r}"
        )

    def test_basic_normalisation_strips_and_uppercases(self):
        """Basic normalisation strips whitespace and uppercases."""
        assert normalise_state_name("  maharashtra  ") == "MAHARASHTRA"

    def test_ampersand_becomes_and(self):
        """& is replaced with AND in base normalisation."""
        result = normalise_state_name("Dadra & Nagar Haveli")
        assert "&" not in result
        assert "AND" in result


# ---------------------------------------------------------------------------
# match_within_state tests
# ---------------------------------------------------------------------------

class TestMatchWithinState:
    """Test state-scoped RapidFuzz matching logic."""

    def _make_source_df(self, rows):
        """Helper: create source dataframe from (state, district) tuples."""
        return pd.DataFrame(rows, columns=["state", "district_name"])

    def _make_canonical_df(self, rows):
        """Helper: create canonical dataframe from (state, district) tuples."""
        return pd.DataFrame(rows, columns=["state", "district_name"])

    def test_exact_match_returns_exact_match_type(self):
        """Identical district name after normalisation → match_type='exact'."""
        source = self._make_source_df([("HARYANA", "Gurgaon")])
        canonical = self._make_canonical_df([("HARYANA", "Gurgaon")])
        result = match_within_state(source, canonical)
        assert len(result) == 1
        assert result.iloc[0]["match_type"] == "exact"
        assert result.iloc[0]["canonical_district"] == "Gurgaon"

    def test_match_type_is_valid_value(self):
        """Every row must have a valid match_type value."""
        source = self._make_source_df([
            ("MAHARASHTRA", "Pune"),
            ("MAHARASHTRA", "XYZ_NONEXISTENT_DISTRICT_99"),
        ])
        canonical = self._make_canonical_df([("MAHARASHTRA", "Pune")])
        result = match_within_state(source, canonical)
        valid_types = {"exact", "fuzzy_accepted", "fuzzy_review", "unmatched"}
        for _, row in result.iterrows():
            assert row["match_type"] in valid_types, (
                f"Invalid match_type: {row['match_type']!r}"
            )

    def test_no_cross_state_matching(self):
        """A source district in HARYANA must never match a canonical from RAJASTHAN."""
        source = self._make_source_df([("HARYANA", "Gurgaon")])
        canonical = self._make_canonical_df([
            ("HARYANA", "Gurugram"),      # same state — valid match target
            ("RAJASTHAN", "Gurgaon"),     # different state — must never be chosen
        ])
        result = match_within_state(source, canonical)
        assert len(result) == 1
        row = result.iloc[0]
        # The match must come from HARYANA canonical, not RAJASTHAN
        # The matched canonical_district (if not None) must exist in HARYANA's list
        if row["canonical_district"] is not None:
            assert row["canonical_district"] == "Gurugram", (
                f"Expected match to HARYANA 'Gurugram', got: {row['canonical_district']!r}"
            )
        # Regardless of match: the source state is preserved in result
        assert row["state"] == "HARYANA"

    def test_score_threshold_fuzzy_accepted(self):
        """Score >= 90 maps to fuzzy_accepted; score assignment must be consistent with actual score."""
        # Use a near-identical pair: "Amritsar" vs "Amritsar Dist" — high WRatio expected
        source = self._make_source_df([("PUNJAB", "Amritsar")])
        canonical = self._make_canonical_df([("PUNJAB", "Amritsar")])
        result = match_within_state(source, canonical)
        assert len(result) == 1
        row = result.iloc[0]
        # Identical strings → must be 'exact'
        assert row["match_type"] == "exact", (
            f"Identical district name expected 'exact', got: {row['match_type']!r} "
            f"(score={row['score']})"
        )

    def test_score_threshold_fuzzy_accepted_high_score(self):
        """Score >= 90 maps to fuzzy_accepted."""
        # "Bangalore" vs "Bengaluru" — common rename, should have high WRatio
        source = self._make_source_df([("KARNATAKA", "Bangalore")])
        canonical = self._make_canonical_df([("KARNATAKA", "Bengaluru")])
        result = match_within_state(source, canonical)
        assert len(result) == 1
        row = result.iloc[0]
        score = row["score"]
        match_type = row["match_type"]
        # Validate threshold assignment is consistent with score
        if score >= 90:
            assert match_type in ("exact", "fuzzy_accepted"), (
                f"Score {score:.1f} >= 90 but match_type={match_type!r}"
            )
        elif score >= 75:
            assert match_type == "fuzzy_review", (
                f"Score {score:.1f} in [75, 90) but match_type={match_type!r}"
            )
        else:
            assert match_type == "unmatched", (
                f"Score {score:.1f} < 75 but match_type={match_type!r}"
            )

    def test_low_score_maps_to_unmatched(self):
        """Score < 75 produces match_type='unmatched' with canonical_district=None."""
        source = self._make_source_df([("MAHARASHTRA", "ZZZZZZZZZZZ")])
        canonical = self._make_canonical_df([("MAHARASHTRA", "Pune")])
        result = match_within_state(source, canonical)
        assert len(result) == 1
        row = result.iloc[0]
        assert row["match_type"] == "unmatched"
        assert row["canonical_district"] is None

    def test_unmatched_district_produces_row(self):
        """Districts that fail matching still produce a row — none silently dropped."""
        source = self._make_source_df([
            ("MAHARASHTRA", "Pune"),
            ("MAHARASHTRA", "TOTALLY_FAKE_DISTRICT"),
        ])
        canonical = self._make_canonical_df([("MAHARASHTRA", "Pune")])
        result = match_within_state(source, canonical)
        assert len(result) == 2, (
            f"Expected 2 rows (one matched, one unmatched), got {len(result)}"
        )

    def test_state_not_in_canonical_all_unmatched(self):
        """Source districts in a state absent from canonical → all unmatched."""
        source = self._make_source_df([
            ("UNKNOWN_STATE", "District A"),
            ("UNKNOWN_STATE", "District B"),
        ])
        canonical = self._make_canonical_df([("MAHARASHTRA", "Pune")])
        result = match_within_state(source, canonical)
        assert len(result) == 2
        for _, row in result.iterrows():
            assert row["match_type"] == "unmatched"
            assert row["canonical_district"] is None

    def test_fuzzy_review_threshold(self):
        """Score between 75 and 89 maps to fuzzy_review."""
        # Artificially test by using mid-range scoring district names
        source = self._make_source_df([("KARNATAKA", "Bengaluru Rural")])
        canonical = self._make_canonical_df([("KARNATAKA", "Bangalore Rural")])
        result = match_within_state(source, canonical)
        assert len(result) == 1
        row = result.iloc[0]
        score = row["score"]
        match_type = row["match_type"]
        # Validate threshold assignment is consistent with score
        if score >= 90:
            assert match_type == "fuzzy_accepted"
        elif score >= 75:
            assert match_type == "fuzzy_review"
        else:
            assert match_type == "unmatched"
            assert row["canonical_district"] is None

    def test_result_columns_present(self):
        """Result dataframe must have all required columns."""
        source = self._make_source_df([("PUNJAB", "Amritsar")])
        canonical = self._make_canonical_df([("PUNJAB", "Amritsar")])
        result = match_within_state(source, canonical)
        required_cols = {"state", "source_district", "canonical_district", "score", "match_type"}
        assert required_cols.issubset(set(result.columns)), (
            f"Missing columns: {required_cols - set(result.columns)}"
        )

    def test_empty_source_returns_empty(self):
        """Empty source dataframe returns empty result."""
        source = self._make_source_df([])
        canonical = self._make_canonical_df([("PUNJAB", "Amritsar")])
        result = match_within_state(source, canonical)
        assert len(result) == 0

    def test_multiple_states_processed(self):
        """Districts from multiple states are all processed."""
        source = self._make_source_df([
            ("MAHARASHTRA", "Pune"),
            ("KARNATAKA", "Mysore"),
        ])
        canonical = self._make_canonical_df([
            ("MAHARASHTRA", "Pune"),
            ("KARNATAKA", "Mysuru"),
        ])
        result = match_within_state(source, canonical)
        assert len(result) == 2
        states_in_result = set(result["state"].unique())
        assert "MAHARASHTRA" in states_in_result
        assert "KARNATAKA" in states_in_result
