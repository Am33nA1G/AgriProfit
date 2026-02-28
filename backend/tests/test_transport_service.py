import pytest
from unittest.mock import MagicMock
from app.transport.service import (
    haversine_distance,
    select_vehicle,
    calculate_transport_cost,
    calculate_net_profit,
    compare_mandis
)
from app.transport.schemas import TransportCompareRequest
from app.transport.schemas import VehicleType

class TestHaversineDistance:
    def test_known_distance_delhi_to_ludhiana(self):
        # Delhi: 28.6139°N, 77.2090°E
        # Ludhiana: 30.9010°N, 75.8573°E
        # Expected: ~285 km (Straight line)
        distance = haversine_distance(28.6139, 77.2090, 30.9010, 75.8573)
        assert 280 <= distance <= 290

    def test_same_location_returns_zero(self):
        distance = haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
        assert distance == 0

    def test_equator_crossing(self):
        # Test coordinates crossing equator
        distance = haversine_distance(-10.0, 20.0, 10.0, 20.0)
        assert distance > 0

    def test_negative_coordinates(self):
        # Verify southern hemisphere works
        distance = haversine_distance(-33.8688, 151.2093, -37.8136, 144.9631)
        # Sydney to Melbourne ~700km
        assert 650 <= distance <= 750

class TestSelectVehicle:
    def test_small_quantity_selects_tempo(self):
        vehicle = select_vehicle(1000)
        assert vehicle == VehicleType.TEMPO

    def test_boundary_1800kg_selects_tempo(self):
        # 90% of 2000 kg TEMPO capacity = 1800 kg practical threshold
        vehicle = select_vehicle(1800)
        assert vehicle == VehicleType.TEMPO

    def test_1801kg_selects_small_truck(self):
        # Exceeds TEMPO practical capacity (1800 kg) → TRUCK_SMALL
        vehicle = select_vehicle(1801)
        assert vehicle == VehicleType.TRUCK_SMALL

    def test_2001kg_selects_small_truck(self):
        vehicle = select_vehicle(2001)
        assert vehicle == VehicleType.TRUCK_SMALL

    def test_5000kg_selects_small_truck(self):
        vehicle = select_vehicle(5000)
        assert vehicle == VehicleType.TRUCK_SMALL

    def test_5001kg_selects_small_truck(self):
        # TRUCK_SMALL practical capacity is 7000 * 0.9 = 6300 kg; 5001 still fits
        vehicle = select_vehicle(5001)
        assert vehicle == VehicleType.TRUCK_SMALL

    def test_6301kg_selects_large_truck(self):
        # Exceeds TRUCK_SMALL practical capacity (6300 kg) → TRUCK_LARGE
        vehicle = select_vehicle(6301)
        assert vehicle == VehicleType.TRUCK_LARGE

    def test_very_large_quantity_selects_large_truck(self):
        vehicle = select_vehicle(50000)
        assert vehicle == VehicleType.TRUCK_LARGE

class TestCalculateTransportCost:
    def test_tempo_100km(self):
        # TEMPO: ₹18/km (one-way per trip)
        cost = calculate_transport_cost(100, VehicleType.TEMPO)
        assert cost == 1800

    def test_small_truck_250km(self):
        # TRUCK_SMALL: ₹28/km (one-way per trip)
        cost = calculate_transport_cost(250, VehicleType.TRUCK_SMALL)
        assert cost == 7000

    def test_large_truck_500km(self):
        # TRUCK_LARGE: ₹38/km (one-way per trip)
        cost = calculate_transport_cost(500, VehicleType.TRUCK_LARGE)
        assert cost == 19000

    def test_zero_distance(self):
        cost = calculate_transport_cost(0, VehicleType.TEMPO)
        assert cost == 0

    def test_fractional_distance(self):
        # TRUCK_SMALL: ₹28/km × 123.45 km = 3456.6
        cost = calculate_transport_cost(123.45, VehicleType.TRUCK_SMALL)
        assert cost == pytest.approx(3456.6, rel=0.01)

class TestCalculateNetProfit:
    def test_complete_calculation(self):
        # 5000 kg Wheat, ₹30/kg, 250km, TRUCK_SMALL
        # New model uses real freight (economics.py) + spoilage (spoilage.py)
        result = calculate_net_profit(
            price_per_kg=30.0,
            quantity_kg=5000,
            distance_km=250,
            vehicle_type=VehicleType.TRUCK_SMALL
        )

        # Gross revenue: 5000 * 30 = 150,000 — unchanged
        assert result['gross_revenue'] == 150000

        # Net profit exists and is a number
        assert 'net_profit' in result
        assert isinstance(result['net_profit'], float)

        # All required fields present
        for field in ('transport_cost', 'toll_cost', 'loading_cost', 'unloading_cost',
                      'mandi_fee', 'commission', 'additional_cost', 'total_cost',
                      'net_profit', 'profit_per_kg', 'trips', 'toll_plazas',
                      'spoilage_percent', 'travel_time_hours', 'is_interstate',
                      'driver_bata', 'cleaner_bata', 'halt_cost'):
            assert field in result, f"Missing field: {field}"

        # Total cost must be positive
        assert result['total_cost'] > 0

        # With ₹30/kg for 5000 kg, profit should be substantially positive
        assert result['net_profit'] > 0

    def test_zero_distance_minimal_costs(self):
        # Same mandi, no transport
        result = calculate_net_profit(
            price_per_kg=25.0,
            quantity_kg=1000,
            distance_km=0,
            vehicle_type=VehicleType.TEMPO
        )

        # Raw transport should be 0 (no km driven)
        assert result['transport_cost'] == 0
        assert result['gross_revenue'] == 25000
        assert result['net_profit'] > 0

    def test_negative_profit_possible(self):
        # Very high transport cost, low price
        result = calculate_net_profit(
            price_per_kg=2.0,  # Low price
            quantity_kg=10000,
            distance_km=1000,  # Very far
            vehicle_type=VehicleType.TRUCK_LARGE
        )

        # Should result in negative profit
        assert result['net_profit'] < 0

    def test_compute_verdict_tiers(self):
        from app.transport.service import compute_verdict

        # excellent: 25% margin
        tier, reason = compute_verdict(2500, 10000, 25.0, 1, 5)
        assert tier == "excellent"
        assert "₹25/kg" in reason
        assert "#1 of 5" in reason

        # good: 15% margin
        tier, _ = compute_verdict(1500, 10000, 15.0, 2, 5)
        assert tier == "good"

        # marginal: 5% margin
        tier, _ = compute_verdict(500, 10000, 5.0, 3, 5)
        assert tier == "marginal"

        # not_viable: negative
        tier, reason = compute_verdict(-300, 10000, -3.0, 4, 5)
        assert tier == "not_viable"
        assert "Loss" in reason

        # guard: gross_revenue = 0
        tier, _ = compute_verdict(0, 0, 0, 1, 1)
        assert tier == "not_viable"

class TestCompareMandis:
    @pytest.fixture
    def sample_request(self):
        # Ludhiana is in DISTRICT_COORDINATES so no db fallback needed for source coords
        return TransportCompareRequest(
            commodity="Wheat",
            quantity_kg=5000,
            source_state="Punjab",
            source_district="Ludhiana"
        )

    @pytest.fixture
    def mock_db(self):
        # Minimal db mock: commodity query returns a commodity object with a known id
        commodity = MagicMock()
        commodity.id = "test-commodity-id"
        commodity.category = None
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = commodity
        return db

    @pytest.fixture
    def sample_mandis(self):
        return [
            {
                "id": None,
                "name": "Delhi Azadpur",
                "state": "Delhi",
                "district": "North Delhi",
                "price_per_kg": 30.0,
                "latitude": 28.6139,
                "longitude": 77.2090,
            },
            {
                "id": None,
                "name": "Chandigarh Mandi",
                "state": "Chandigarh",
                "district": "Chandigarh",
                "price_per_kg": 28.0,
                "latitude": 30.7333,
                "longitude": 76.7794,
            },
            {
                "id": None,
                "name": "Amritsar Mandi",
                "state": "Punjab",
                "district": "Amritsar",
                "price_per_kg": 26.0,
                "latitude": 31.6340,
                "longitude": 74.8723,
            },
        ]

    def test_compare_multiple_mandis(self, sample_request, sample_mandis, mock_db, monkeypatch):
        from app.transport.price_analytics import PriceAnalytics
        from datetime import date

        monkeypatch.setattr(
            "app.transport.service.get_mandis_for_commodity",
            lambda *a, **kw: sample_mandis,
        )
        monkeypatch.setattr(
            "app.transport.routing.routing_service.get_distance_km",
            lambda *a, **kw: (100.0, "estimated"),
        )
        monkeypatch.setattr(
            "app.transport.service.compute_price_analytics",
            lambda *a, **kw: PriceAnalytics(
                volatility_pct=2.0,
                price_trend="stable",
                confidence_score=85,
                n_records=7,
                latest_price_date=date.today(),
            ),
        )

        result, has_estimated = compare_mandis(sample_request, db=mock_db)

        assert len(result) == 3
        for comparison in result:
            assert comparison.vehicle_type is not None
            assert comparison.vehicle_type == VehicleType.TRUCK_SMALL

        # Results must be sorted by net_profit descending
        profits = [c.net_profit for c in result]
        assert profits == sorted(profits, reverse=True)

    def test_empty_mandi_list(self, sample_request, mock_db, monkeypatch):
        monkeypatch.setattr(
            "app.transport.service.get_mandis_for_commodity",
            lambda *a, **kw: [],
        )

        result, has_estimated = compare_mandis(sample_request, db=mock_db)
        assert result == []

    def test_single_mandi(self, sample_request, mock_db, monkeypatch):
        from app.transport.price_analytics import PriceAnalytics
        from datetime import date

        monkeypatch.setattr(
            "app.transport.service.get_mandis_for_commodity",
            lambda *a, **kw: [{
                "id": None,
                "name": "Test Mandi",
                "state": "Punjab",
                "district": "Ludhiana",
                "price_per_kg": 25.0,
                "latitude": 30.9010,
                "longitude": 75.8573,
            }],
        )
        monkeypatch.setattr(
            "app.transport.routing.routing_service.get_distance_km",
            lambda *a, **kw: (50.0, "osrm"),
        )
        monkeypatch.setattr(
            "app.transport.service.compute_price_analytics",
            lambda *a, **kw: PriceAnalytics(
                volatility_pct=1.5,
                price_trend="stable",
                confidence_score=90,
                n_records=5,
                latest_price_date=date.today(),
            ),
        )

        result, has_estimated = compare_mandis(sample_request, db=mock_db)
        assert len(result) == 1
        assert result[0].mandi_name == "Test Mandi"
