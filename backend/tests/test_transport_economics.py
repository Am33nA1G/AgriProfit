"""
Tests for economics.py — Real Indian freight cost calculation.

All assertions validated against the design doc worked example:
  truck_small, 292 km intrastate, 5500 kg, diesel ₹98, 42 km/h
  → total_freight ≈ ₹23,581 (±600 tolerance)
"""
import pytest
from app.transport.economics import (
    compute_travel_time,
    compute_freight,
    FreightResult,
    BATA,
    PRACTICAL_CAPACITY_FACTOR,
)
from app.transport.schemas import VehicleType


class TestTravelTime:
    def test_intrastate_plain_mixed_speed(self):
        # 292 km, mixed speed 42 km/h → round trip = 292/42*2 ≈ 13.9h
        hours = compute_travel_time(292.0, "Punjab", "Punjab")
        assert 13.5 <= hours <= 14.5

    def test_hill_state_destination(self):
        # Himachal Pradesh is a hill state → 32 km/h
        hours_hill = compute_travel_time(200.0, "Punjab", "Himachal Pradesh")
        hours_plain = compute_travel_time(200.0, "Punjab", "Punjab")
        assert hours_hill > hours_plain

    def test_zero_distance(self):
        hours = compute_travel_time(0.0, "Kerala", "Kerala")
        assert hours == 0.0

    def test_urban_congestion_applied(self):
        # Specify urban=True → +15% travel time
        hours_urban = compute_travel_time(100.0, "Maharashtra", "Maharashtra", urban=True)
        hours_plain = compute_travel_time(100.0, "Maharashtra", "Maharashtra", urban=False)
        assert pytest.approx(hours_urban, rel=0.01) == hours_plain * 1.15


class TestFreightResult:
    def test_worked_example_intrastate(self):
        """
        Validated example from design doc:
        truck_small, 292 km, 5500 kg, diesel ₹98, 42 km/h, intrastate Punjab
        Expected total_freight ≈ ₹23,581 (±600)
        """
        result = compute_freight(
            distance_km=292.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5500.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        assert isinstance(result, FreightResult)
        assert 23_000 <= result.total_freight <= 24_200

    def test_interstate_adds_permit(self):
        result_intra = compute_freight(
            distance_km=300.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        result_inter = compute_freight(
            distance_km=300.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Haryana",
            diesel_price=98.0,
        )
        assert result_inter.permit_cost == 1200.0
        assert result_intra.permit_cost == 0.0
        assert result_inter.total_freight > result_intra.total_freight

    def test_diesel_spike_increases_freight(self):
        result_base = compute_freight(
            distance_km=200.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1500.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        result_spike = compute_freight(
            distance_km=200.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1500.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=112.7,  # +15%
        )
        assert result_spike.raw_transport > result_base.raw_transport

    def test_night_halt_triggered_beyond_12h(self):
        # 400 km at 42 km/h → 400/42*2 ≈ 19h → halt triggered
        result = compute_freight(
            distance_km=400.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        assert result.halt_cost > 0

    def test_no_night_halt_short_trip(self):
        # 150 km at 42 km/h → 150/42*2 ≈ 7.1h → no halt
        result = compute_freight(
            distance_km=150.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        assert result.halt_cost == 0.0

    def test_tempo_has_no_cleaner_bata(self):
        result = compute_freight(
            distance_km=100.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1000.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        assert result.cleaner_bata == 0.0

    def test_practical_capacity_90_percent_one_trip(self):
        # 1 trip capacity for TEMPO: 2000 * 0.9 = 1800 kg
        result = compute_freight(
            distance_km=100.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1800.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        assert result.trips == 1

    def test_practical_capacity_90_percent_two_trips(self):
        # 1801 kg needs 2 trips (practical capacity exceeded)
        result2 = compute_freight(
            distance_km=100.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1801.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        assert result2.trips == 2

    def test_breakdown_reserve_scales_with_distance(self):
        r_short = compute_freight(100.0, VehicleType.TEMPO, 1000.0, "Punjab", "Punjab", 98.0)
        r_long  = compute_freight(500.0, VehicleType.TEMPO, 1000.0, "Punjab", "Punjab", 98.0)
        # breakdown_reserve = ₹1/km * distance * 2
        assert r_long.breakdown_reserve > r_short.breakdown_reserve
