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
    
    def test_boundary_2000kg_selects_tempo(self):
        vehicle = select_vehicle(2000)
        assert vehicle == VehicleType.TEMPO
    
    def test_2001kg_selects_small_truck(self):
        vehicle = select_vehicle(2001)
        assert vehicle == VehicleType.TRUCK_SMALL
    
    def test_5000kg_selects_small_truck(self):
        vehicle = select_vehicle(5000)
        assert vehicle == VehicleType.TRUCK_SMALL
    
    def test_5001kg_selects_small_truck(self):
        # TRUCK_SMALL capacity is 7000 kg
        vehicle = select_vehicle(5001)
        assert vehicle == VehicleType.TRUCK_SMALL

    def test_7001kg_selects_large_truck(self):
        vehicle = select_vehicle(7001)
        assert vehicle == VehicleType.TRUCK_LARGE
    
    def test_very_large_quantity_selects_large_truck(self):
        vehicle = select_vehicle(50000)
        assert vehicle == VehicleType.TRUCK_LARGE

class TestCalculateTransportCost:
    def test_tempo_100km(self):
        # TEMPO: ₹18/km
        cost = calculate_transport_cost(100, VehicleType.TEMPO)
        assert cost == 1800

    def test_small_truck_250km(self):
        # TRUCK_SMALL: ₹28/km
        cost = calculate_transport_cost(250, VehicleType.TRUCK_SMALL)
        assert cost == 7000

    def test_large_truck_500km(self):
        # TRUCK_LARGE: ₹35/km
        cost = calculate_transport_cost(500, VehicleType.TRUCK_LARGE)
        assert cost == 17500

    def test_zero_distance(self):
        cost = calculate_transport_cost(0, VehicleType.TEMPO)
        assert cost == 0

    def test_fractional_distance(self):
        # TRUCK_SMALL: ₹28/km → 123.45 * 28 = 3456.6
        cost = calculate_transport_cost(123.45, VehicleType.TRUCK_SMALL)
        assert cost == pytest.approx(3456.6, rel=0.01)

class TestCalculateNetProfit:
    def test_complete_calculation(self):
        # 5000 kg Wheat, ₹30/kg, 250km, TRUCK_SMALL (capacity 7000 kg → 1 trip)
        result = calculate_net_profit(
            price_per_kg=30.0,
            quantity_kg=5000,
            distance_km=250,
            vehicle_type=VehicleType.TRUCK_SMALL
        )

        # Gross revenue: 5000 * 30 = 150,000
        assert result['gross_revenue'] == 150000

        # Transport: 250 * 28 = 7,000 (one-way, 1 trip)
        assert result['transport_cost'] == 7000

        # Toll: round(250/60) = 4 plazas × ₹200/plaza × 2 ways × 1 trip = 1,600
        assert result['toll_cost'] == 1600

        # Loading: 5000 * 0.15 = 750
        assert result['loading_cost'] == 750

        # Unloading: 5000 * 0.12 = 600
        assert result['unloading_cost'] == 600

        # Mandi fee: 150,000 * 0.015 = 2,250
        assert result['mandi_fee'] == 2250

        # Commission: 150,000 * 0.025 = 3,750
        assert result['commission'] == 3750

        # Additional: (800 + 80 + 50 + 70 + 2*250) × 1 = 1500
        assert result['additional_cost'] == 1500

        # Total cost: 7000 + 1600 + 750 + 600 + 2250 + 3750 + 1500 = 17,450
        assert result['total_cost'] == 17450

        # Net profit: 150,000 - 17,450 = 132,550
        assert result['net_profit'] == 132550

        # Profit per kg: 132,550 / 5000 = 26.51
        assert result['profit_per_kg'] == pytest.approx(26.51, rel=0.01)
    
    def test_zero_distance_minimal_costs(self):
        # Same mandi, no transport
        result = calculate_net_profit(
            price_per_kg=25.0,
            quantity_kg=1000,
            distance_km=0,
            vehicle_type=VehicleType.TEMPO
        )
        
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

class TestCompareMandis:
    @pytest.fixture
    def sample_request(self):
        return TransportCompareRequest(
            commodity="Wheat",
            quantity_kg=5000,
            source_state="Punjab",
            source_district="Ludhiana"
        )
    
    @pytest.fixture
    def sample_mandis(self):
        # Mock mandi data with coordinates
        return [
            {
                "name": "Delhi Azadpur",
                "state": "Delhi",
                "district": "North Delhi",
                "price_per_kg": 30.0,
                "latitude": 28.6139,
                "longitude": 77.2090
            },
            {
                "name": "Chandigarh Mandi",
                "state": "Chandigarh",
                "district": "Chandigarh",
                "price_per_kg": 28.0,
                "latitude": 30.7333,
                "longitude": 76.7794
            },
            {
                "name": "Amritsar Mandi",
                "state": "Punjab",
                "district": "Amritsar",
                "price_per_kg": 26.0,
                "latitude": 31.6340,
                "longitude": 74.8723
            }
        ]
    
    def test_compare_multiple_mandis(self, sample_request, sample_mandis, monkeypatch):
        # Mock database query for mandis and commodity lookup
        def mock_get_mandis(*args, **kwargs):
            return sample_mandis

        mock_commodity = MagicMock()
        mock_commodity.id = "test-commodity-id"
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_commodity

        monkeypatch.setattr("app.transport.service.get_mandis_for_commodity", mock_get_mandis)

        result = compare_mandis(sample_request, db=mock_db)

        # Should return 3 comparisons
        assert len(result) == 3

        # All should have vehicle_type TRUCK_SMALL (5000 kg < 7000 capacity)
        for comparison in result:
            assert comparison.vehicle_type is not None
            assert comparison.vehicle_type == VehicleType.TRUCK_SMALL

        # Should be sorted by net_profit descending
        profits = [c.net_profit for c in result]
        assert profits == sorted(profits, reverse=True)

    def test_empty_mandi_list(self, sample_request, monkeypatch):
        def mock_get_mandis(*args, **kwargs):
            return []

        mock_commodity = MagicMock()
        mock_commodity.id = "test-commodity-id"
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_commodity

        monkeypatch.setattr("app.transport.service.get_mandis_for_commodity", mock_get_mandis)

        result = compare_mandis(sample_request, db=mock_db)
        assert result == []

    def test_single_mandi(self, sample_request, monkeypatch):
        def mock_get_mandis(*args, **kwargs):
            return [{
                "name": "Test Mandi",
                "state": "Punjab",
                "district": "Ludhiana",
                "price_per_kg": 25.0,
                "latitude": 30.9010,
                "longitude": 75.8573
            }]

        mock_commodity = MagicMock()
        mock_commodity.id = "test-commodity-id"
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_commodity

        monkeypatch.setattr("app.transport.service.get_mandis_for_commodity", mock_get_mandis)

        result = compare_mandis(sample_request, db=mock_db)
        assert len(result) == 1
        assert result[0].mandi_name == "Test Mandi"
