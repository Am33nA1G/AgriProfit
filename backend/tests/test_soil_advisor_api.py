"""Integration tests for the Soil Advisor API endpoints.

Uses a local SQLite in-memory fixture with soil_profiles and
soil_crop_suitability tables. Does NOT modify conftest.py.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.session import get_db


# ---------------------------------------------------------------------------
# Local test database (independent of conftest.py)
# ---------------------------------------------------------------------------

SOIL_TEST_DB_URL = "sqlite:///:memory:"

soil_test_engine = create_engine(
    SOIL_TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SoilTestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=soil_test_engine,
)

# Minimal seed data for tests
_SEED_SQL = [
    """
    CREATE TABLE IF NOT EXISTS soil_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT NOT NULL,
        district TEXT NOT NULL,
        block TEXT NOT NULL,
        cycle TEXT NOT NULL,
        nutrient TEXT NOT NULL,
        high_pct INTEGER NOT NULL DEFAULT 0,
        medium_pct INTEGER NOT NULL DEFAULT 0,
        low_pct INTEGER NOT NULL DEFAULT 0,
        seeded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (state, district, block, cycle, nutrient)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS soil_crop_suitability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        nutrient TEXT NOT NULL,
        min_tolerance TEXT NOT NULL,
        ph_min REAL,
        ph_max REAL,
        fertiliser_advice TEXT,
        UNIQUE (crop_name, nutrient)
    )
    """,
    # 5 nutrient rows for ANANTAPUR - 4689 (matches the plan example)
    "INSERT OR IGNORE INTO soil_profiles (state, district, block, cycle, nutrient, high_pct, medium_pct, low_pct) VALUES ('ANDHRA PRADESH', 'ANANTAPUR', 'ANANTAPUR - 4689', '2025-26', 'Nitrogen', 0, 4, 96)",
    "INSERT OR IGNORE INTO soil_profiles (state, district, block, cycle, nutrient, high_pct, medium_pct, low_pct) VALUES ('ANDHRA PRADESH', 'ANANTAPUR', 'ANANTAPUR - 4689', '2025-26', 'Phosphorus', 81, 17, 2)",
    "INSERT OR IGNORE INTO soil_profiles (state, district, block, cycle, nutrient, high_pct, medium_pct, low_pct) VALUES ('ANDHRA PRADESH', 'ANANTAPUR', 'ANANTAPUR - 4689', '2025-26', 'Potassium', 83, 14, 3)",
    "INSERT OR IGNORE INTO soil_profiles (state, district, block, cycle, nutrient, high_pct, medium_pct, low_pct) VALUES ('ANDHRA PRADESH', 'ANANTAPUR', 'ANANTAPUR - 4689', '2025-26', 'Organic Carbon', 0, 4, 96)",
    "INSERT OR IGNORE INTO soil_profiles (state, district, block, cycle, nutrient, high_pct, medium_pct, low_pct) VALUES ('ANDHRA PRADESH', 'ANANTAPUR', 'ANANTAPUR - 4689', '2025-26', 'Potential Of Hydrogen', 0, 0, 100)",
    # 3 crop rows (low/medium/high tolerance to Nitrogen)
    "INSERT OR IGNORE INTO soil_crop_suitability (crop_name, nutrient, min_tolerance, ph_min, ph_max) VALUES ('Groundnut', 'Nitrogen', 'low', 5.5, 7.0)",
    "INSERT OR IGNORE INTO soil_crop_suitability (crop_name, nutrient, min_tolerance, ph_min, ph_max) VALUES ('Chickpea', 'Nitrogen', 'low', 6.0, 7.5)",
    "INSERT OR IGNORE INTO soil_crop_suitability (crop_name, nutrient, min_tolerance, ph_min, ph_max) VALUES ('Wheat', 'Nitrogen', 'high', 6.0, 7.5)",
]


def _setup_soil_db(engine) -> None:
    """Create tables and seed test data."""
    with engine.connect() as conn:
        for sql in _SEED_SQL:
            conn.execute(text(sql))
        conn.commit()


def _teardown_soil_db(engine) -> None:
    """Drop soil-advisor tables."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS soil_profiles"))
        conn.execute(text("DROP TABLE IF EXISTS soil_crop_suitability"))
        conn.commit()


@pytest.fixture(scope="function")
def soil_test_db():
    """Provide a SQLite session with soil_profiles and soil_crop_suitability."""
    _setup_soil_db(soil_test_engine)
    db = SoilTestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        _teardown_soil_db(soil_test_engine)


@pytest.fixture(scope="function")
def soil_client(soil_test_db):
    """TestClient with the soil_advisor DB override."""
    def _override_get_db():
        try:
            yield soil_test_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSoilAdvisorStates:
    """GET /api/v1/soil-advisor/states"""

    def test_returns_21_states(self, soil_client):
        resp = soil_client.get("/api/v1/soil-advisor/states")
        assert resp.status_code == 200
        states = resp.json()
        assert isinstance(states, list)
        assert len(states) == 21

    def test_states_are_strings(self, soil_client):
        resp = soil_client.get("/api/v1/soil-advisor/states")
        states = resp.json()
        for s in states:
            assert isinstance(s, str)

    def test_states_sorted(self, soil_client):
        resp = soil_client.get("/api/v1/soil-advisor/states")
        states = resp.json()
        assert states == sorted(states)


class TestSoilAdvisorDistricts:
    """GET /api/v1/soil-advisor/districts?state=..."""

    def test_returns_districts_for_covered_state(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/districts", params={"state": "ANDHRA PRADESH"}
        )
        assert resp.status_code == 200
        districts = resp.json()
        assert isinstance(districts, list)
        assert len(districts) >= 1
        assert "ANANTAPUR" in districts

    def test_case_insensitive_state_param(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/districts", params={"state": "andhra pradesh"}
        )
        assert resp.status_code == 200
        districts = resp.json()
        assert "ANANTAPUR" in districts

    def test_no_districts_for_unknown_state(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/districts", params={"state": "NONEXISTENT"}
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestSoilAdvisorBlocks:
    """GET /api/v1/soil-advisor/blocks?state=...&district=..."""

    def test_returns_blocks_for_district(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/blocks",
            params={"state": "ANDHRA PRADESH", "district": "ANANTAPUR"},
        )
        assert resp.status_code == 200
        blocks = resp.json()
        assert isinstance(blocks, list)
        assert "ANANTAPUR - 4689" in blocks

    def test_case_insensitive_params(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/blocks",
            params={"state": "andhra pradesh", "district": "anantapur"},
        )
        assert resp.status_code == 200
        blocks = resp.json()
        assert "ANANTAPUR - 4689" in blocks


class TestSoilAdvisorProfile:
    """GET /api/v1/soil-advisor/profile?state=...&district=...&block=..."""

    def _get_profile(self, client):
        return client.get(
            "/api/v1/soil-advisor/profile",
            params={
                "state": "ANDHRA PRADESH",
                "district": "ANANTAPUR",
                "block": "ANANTAPUR - 4689",
            },
        )

    def test_returns_200_for_valid_block(self, soil_client):
        resp = self._get_profile(soil_client)
        assert resp.status_code == 200

    def test_response_shape(self, soil_client):
        resp = self._get_profile(soil_client)
        data = resp.json()
        assert "state" in data
        assert "district" in data
        assert "block" in data
        assert "cycle" in data
        assert "disclaimer" in data
        assert "nutrient_distributions" in data
        assert "crop_recommendations" in data
        assert "fertiliser_advice" in data

    def test_disclaimer_contains_block_name(self, soil_client):
        resp = self._get_profile(soil_client)
        data = resp.json()
        assert "ANANTAPUR - 4689" in data["disclaimer"]

    def test_disclaimer_always_present(self, soil_client):
        resp = self._get_profile(soil_client)
        data = resp.json()
        assert data["disclaimer"] != ""

    def test_five_nutrient_distributions(self, soil_client):
        resp = self._get_profile(soil_client)
        data = resp.json()
        assert len(data["nutrient_distributions"]) == 5

    def test_nutrient_distribution_fields(self, soil_client):
        resp = self._get_profile(soil_client)
        nutrients = resp.json()["nutrient_distributions"]
        for n in nutrients:
            assert "nutrient" in n
            assert "high_pct" in n
            assert "medium_pct" in n
            assert "low_pct" in n

    def test_at_least_two_crop_recommendations(self, soil_client):
        resp = self._get_profile(soil_client)
        data = resp.json()
        # Groundnut and Chickpea have low N tolerance → should be ranked
        assert len(data["crop_recommendations"]) >= 2

    def test_crop_recommendations_sorted_by_score_desc(self, soil_client):
        resp = self._get_profile(soil_client)
        recs = resp.json()["crop_recommendations"]
        scores = [r["suitability_score"] for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_fertiliser_advice_for_nitrogen_deficient_block(self, soil_client):
        resp = self._get_profile(soil_client)
        advice = resp.json()["fertiliser_advice"]
        # Nitrogen low_pct=96 > 50 → must have advice
        nutrients_advised = [a["nutrient"] for a in advice]
        assert "Nitrogen" in nutrients_advised

    def test_cycle_is_most_recent(self, soil_client):
        resp = self._get_profile(soil_client)
        data = resp.json()
        assert data["cycle"] == "2025-26"


class TestSoilAdvisorProfileUncoveredState:
    """Profile endpoint returns 404 for states not in COVERED_STATES."""

    def test_404_for_uncovered_state(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/profile",
            params={"state": "PUNJAB", "district": "X", "block": "Y"},
        )
        assert resp.status_code == 404

    def test_coverage_gap_flag_in_detail(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/profile",
            params={"state": "PUNJAB", "district": "X", "block": "Y"},
        )
        detail = resp.json().get("detail", {})
        assert detail.get("coverage_gap") is True

    def test_message_mentions_21_states(self, soil_client):
        resp = soil_client.get(
            "/api/v1/soil-advisor/profile",
            params={"state": "PUNJAB", "district": "X", "block": "Y"},
        )
        detail = resp.json().get("detail", {})
        assert "21" in detail.get("message", "")
