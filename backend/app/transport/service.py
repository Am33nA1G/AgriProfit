"""
Transport cost calculation service.

Refactored to functional style for direct testing and usage.
"""
import math
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Mandi, Commodity, PriceHistory
from app.transport.schemas import (
    VehicleType,
    TransportCompareRequest,
    TransportCompareResponse,
    MandiComparison,
    CostBreakdown,
)

# =============================================================================
# CONSTANTS (Updated with 2026 Indian Market Rates)
# =============================================================================

VEHICLES = {
    VehicleType.TEMPO: {
        "capacity_kg": 2000,
        "cost_per_km": 18.0,  # Increased for diesel ~₹98/L
        "toll_per_plaza": 100,
        "description": "Tata Ace / Mini Truck (up to 2 tons)"
    },
    VehicleType.TRUCK_SMALL: {
        "capacity_kg": 7000,  # Increased capacity (LCV)
        "cost_per_km": 28.0,
        "toll_per_plaza": 200,
        "description": "Light Commercial Vehicle (3-7 tons)"
    },
    VehicleType.TRUCK_LARGE: {
        "capacity_kg": 15000,  # Increased capacity (HCV)
        "cost_per_km": 38.0,
        "toll_per_plaza": 350,
        "description": "Heavy Commercial Vehicle (10-15 tons)"
    },
}

# Loading/unloading costs (Hamali charges)
# Source: APMC bylaws and market surveys across states (2025-26)
# Loading at farm/source: ₹10-25/quintal typical; using ₹15/quintal (conservative mid-range)
# Unloading at mandi: ₹15-35/quintal typical; using ₹20/quintal (conservative mid-range)
LOADING_COST_PER_KG = 0.15   # ₹15 per quintal
UNLOADING_COST_PER_KG = 0.20  # ₹20 per quintal

# Mandi fees (varies by state, using average)
MANDI_FEE_RATE = 0.015  # 1.5%
COMMISSION_RATE = 0.025  # 2.5% agent commission

# Additional charges per trip
WEIGHBRIDGE_FEE = 80.0  # ₹ per weighing
PARKING_FEE = 50.0      # ₹ per trip
DOCUMENTATION_FEE = 70.0  # ₹ per trip (receipts, permits)

# Distance calculations
ROAD_DISTANCE_MULTIPLIER = 1.4  # Haversine to actual road distance
TOLL_PLAZA_SPACING_KM = 60  # Average spacing on highways

import json as _json
import pathlib as _pathlib

DISTRICT_COORDINATES: dict[str, tuple[float, float]] = {
    k: tuple(v)
    for k, v in _json.loads(
        (_pathlib.Path(__file__).parent / "district_coords.json").read_text(encoding="utf-8")
    ).items()
}

# =============================================================================
# CORE LOGIC FUNCTIONS
# =============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points (km)."""
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def select_vehicle(quantity_kg: float) -> VehicleType:
    """Select appropriate vehicle based on quantity."""
    if quantity_kg <= VEHICLES[VehicleType.TEMPO]["capacity_kg"]:
        return VehicleType.TEMPO
    elif quantity_kg <= VEHICLES[VehicleType.TRUCK_SMALL]["capacity_kg"]:
        return VehicleType.TRUCK_SMALL
    else:
        return VehicleType.TRUCK_LARGE

def calculate_transport_cost(distance_km: float, vehicle_type: VehicleType) -> float:
    """Calculate basic transport cost for one trip (distance * rate)."""
    cost_per_km = VEHICLES[vehicle_type]["cost_per_km"]
    return distance_km * cost_per_km

def calculate_net_profit(
    price_per_kg: float,
    quantity_kg: float,
    distance_km: float,
    vehicle_type: VehicleType
) -> Dict[str, float]:
    """
    Calculate detailed cost breakdown and net profit.

    Includes: freight, toll, loading, unloading, mandi fees, commission,
    weighbridge, parking, and documentation charges.
    """
    gross_revenue = price_per_kg * quantity_kg

    # Calculate trips
    capacity = VEHICLES[vehicle_type]["capacity_kg"]
    trips = math.ceil(quantity_kg / capacity)

    # 1. Freight Cost (round-trip)
    one_way_freight = calculate_transport_cost(distance_km, vehicle_type)
    total_transport_cost = one_way_freight * trips * 2  # Round trip

    # 2. Toll Charges (both ways)
    # max(0,...) intentional: trips < 30km use local/district roads with no NH toll plazas
    toll_plazas = max(0, round(distance_km / TOLL_PLAZA_SPACING_KM))
    toll_cost_per_trip = toll_plazas * VEHICLES[vehicle_type]["toll_per_plaza"] * 2
    total_toll_cost = toll_cost_per_trip * trips

    # 3. Loading & Unloading
    loading_cost = quantity_kg * LOADING_COST_PER_KG
    unloading_cost = quantity_kg * UNLOADING_COST_PER_KG

    # 4. Mandi Fees & Commission
    mandi_fee = gross_revenue * MANDI_FEE_RATE
    commission = gross_revenue * COMMISSION_RATE

    # 5. Additional Charges (per trip)
    additional_cost = (WEIGHBRIDGE_FEE + PARKING_FEE + DOCUMENTATION_FEE) * trips

    # Total Cost
    total_cost = (total_transport_cost + total_toll_cost + loading_cost +
                  unloading_cost + mandi_fee + commission + additional_cost)

    # Net Profit
    net_profit = gross_revenue - total_cost
    profit_per_kg = net_profit / quantity_kg if quantity_kg > 0 else 0
    roi_percentage = (net_profit / total_cost * 100) if total_cost > 0 else 0

    return {
        "gross_revenue": gross_revenue,
        "transport_cost": total_transport_cost,
        "toll_cost": total_toll_cost,
        "loading_cost": loading_cost,
        "unloading_cost": unloading_cost,
        "mandi_fee": mandi_fee,
        "commission": commission,
        "additional_cost": additional_cost,
        "total_cost": total_cost,
        "net_profit": net_profit,
        "profit_per_kg": profit_per_kg,
        "roi_percentage": roi_percentage,
        "trips": trips,
        "toll_plazas": toll_plazas
    }

def compute_verdict(
    net_profit: float,
    gross_revenue: float,
    profit_per_kg: float,
    rank: int,
    total: int,
) -> tuple[str, str]:
    """
    Compute a tiered sell verdict for a farmer.

    Tiers by profit margin (net_profit / gross_revenue):
      excellent  >= 20%  — strong return
      good       10–19%  — worth the trip
      marginal    1–9%   — thin margin
      not_viable  <= 0%  — loss after costs
    """
    if gross_revenue <= 0:
        return "not_viable", "No revenue data available"

    margin = net_profit / gross_revenue
    rank_ctx = f" · #{rank} of {total} mandis"

    if margin >= 0.20:
        return "excellent", f"Strong return — ₹{profit_per_kg:.0f}/kg net{rank_ctx}"
    elif margin >= 0.10:
        return "good", f"Worth the trip — ₹{profit_per_kg:.0f}/kg net{rank_ctx}"
    elif margin > 0:
        return "marginal", f"Thin margin — ₹{profit_per_kg:.0f}/kg net, weigh carefully{rank_ctx}"
    else:
        return "not_viable", f"Loss of ₹{abs(profit_per_kg):.0f}/kg after all costs{rank_ctx}"


# =============================================================================
# DATA ACCESS & INTEGRATION
# =============================================================================

def get_mandis_for_commodity(commodity_id: str, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch mandis that have recent price data for a commodity.

    Uses a date-bounded CTE for performance on the 25M-row price_history table.
    Prices are converted from per-quintal (DB) to per-kg for calculations.
    """
    if not db:
        return []

    from sqlalchemy import text

    # Get reference date (latest data date for this commodity)
    max_date = db.execute(
        text("SELECT MAX(price_date) FROM price_history WHERE commodity_id = CAST(:cid AS UUID)"),
        {"cid": str(commodity_id)}
    ).scalar()

    if not max_date:
        return []

    params = {
        "commodity_id": str(commodity_id),
        "max_date": str(max_date),
        "limit": limit,
    }

    # CTE: latest price per mandi_name within last 30 days
    # Then LEFT JOIN mandis to get coordinates and location info
    query = text("""
        WITH recent_prices AS (
            SELECT DISTINCT ON (ph.mandi_name)
                ph.mandi_name,
                ph.mandi_id,
                ph.modal_price,
                ph.price_date
            FROM price_history ph
            WHERE ph.commodity_id = CAST(:commodity_id AS UUID)
              AND ph.price_date >= (CAST(:max_date AS date) - INTERVAL '30 days')
              AND ph.modal_price > 0
            ORDER BY ph.mandi_name, ph.price_date DESC
        )
        SELECT
            rp.mandi_name,
            rp.modal_price,
            rp.price_date,
            m.id as mandi_id,
            m.state,
            m.district,
            m.latitude,
            m.longitude
        FROM recent_prices rp
        LEFT JOIN mandis m ON m.id = rp.mandi_id
        ORDER BY rp.modal_price DESC
        LIMIT :limit
    """)

    rows = db.execute(query, params).fetchall()

    results = []
    for row in rows:
        # modal_price is in ₹ per quintal (100 kg) - convert to per-kg
        price_per_quintal = float(row.modal_price)
        price_per_kg = price_per_quintal / 100.0

        lat = float(row.latitude) if row.latitude else None
        lon = float(row.longitude) if row.longitude else None

        # Fallback: use district coordinates if mandi has no geocode
        if not (lat and lon):
            district = (row.district or "").strip().title()
            if district in DISTRICT_COORDINATES:
                lat, lon = DISTRICT_COORDINATES[district]

        results.append({
            "id": row.mandi_id,
            "name": row.mandi_name,
            "state": row.state,
            "district": row.district,
            "price_per_kg": price_per_kg,
            "price_per_quintal": price_per_quintal,
            "latitude": lat,
            "longitude": lon
        })
    return results


def get_source_coordinates(
    request: TransportCompareRequest,
    db: Session = None,
) -> tuple[float, float] | None:
    """
    Resolve the farmer's source location to (lat, lon).

    Priority:
    1. Explicit coordinates from request
    2. Hardcoded DISTRICT_COORDINATES lookup
    3. DB lookup: average coordinates of mandis in that district
    4. DB lookup: average coordinates of mandis in that state
    """
    if request.source_latitude and request.source_longitude:
        return (request.source_latitude, request.source_longitude)

    district = request.source_district.strip().title()
    if district in DISTRICT_COORDINATES:
        return DISTRICT_COORDINATES[district]

    # DB fallback: find coordinates from mandis in the same district
    if db:
        from sqlalchemy import text

        row = db.execute(
            text("""
                SELECT AVG(latitude) as lat, AVG(longitude) as lon
                FROM mandis
                WHERE district ILIKE :district
                  AND latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND is_active = true
            """),
            {"district": f"%{district}%"},
        ).first()
        if row and row.lat and row.lon:
            return (float(row.lat), float(row.lon))

        # State-level fallback
        if request.source_state:
            state = request.source_state.strip()
            row = db.execute(
                text("""
                    SELECT AVG(latitude) as lat, AVG(longitude) as lon
                    FROM mandis
                    WHERE state ILIKE :state
                      AND latitude IS NOT NULL
                      AND longitude IS NOT NULL
                      AND is_active = true
                """),
                {"state": f"%{state}%"},
            ).first()
            if row and row.lat and row.lon:
                return (float(row.lat), float(row.lon))

    return None


def compare_mandis(
    request: TransportCompareRequest, db: Session = None
) -> tuple[List[MandiComparison], bool]:
    """
    Compare transport options to find the most profitable mandi.

    1. Resolves commodity name → ID
    2. Fetches mandis with recent prices for that commodity
    3. Resolves source coordinates
    4. Calls RoutingService for road distances (OSRM with fallback)
    5. Calculates costs and net profit for each mandi
    6. Sorts by net profit, assigns rank-aware verdicts
    7. Returns (comparisons[:limit], has_estimated)
    """
    from app.transport.routing import routing_service

    if not db:
        raise ValueError("Database session required")

    # Resolve commodity name to ID
    from app.models import Commodity
    commodity = db.query(Commodity).filter(
        Commodity.name.ilike(request.commodity)
    ).first()

    if not commodity:
        raise ValueError(f"Commodity '{request.commodity}' not found")

    # Fetch mandis with recent price data (more than limit, we'll trim later)
    raw_mandis = get_mandis_for_commodity(
        str(commodity.id), db, limit=200
    )

    # Resolve source coordinates
    coords = get_source_coordinates(request, db)
    if coords is None:
        raise ValueError(
            f"Could not determine coordinates for district '{request.source_district}'. "
            f"Please provide source_latitude and source_longitude."
        )

    source_lat, source_lon = coords
    vehicle_type = select_vehicle(request.quantity_kg)
    capacity = VEHICLES[vehicle_type]["capacity_kg"]
    trips = math.ceil(request.quantity_kg / capacity)

    raw_comparisons: list[MandiComparison] = []
    has_estimated = False

    for m in raw_mandis:
        if not m.get("latitude") or not m.get("longitude") or m.get("price_per_kg") is None:
            continue

        road_dist, dist_source = routing_service.get_distance_km(
            source_lat, source_lon, m["latitude"], m["longitude"], db
        )
        if dist_source == "estimated":
            has_estimated = True

        if request.max_distance_km and road_dist > request.max_distance_km:
            continue

        profit_data = calculate_net_profit(
            price_per_kg=m["price_per_kg"],
            quantity_kg=request.quantity_kg,
            distance_km=road_dist,
            vehicle_type=vehicle_type
        )

        costs = CostBreakdown(
            transport_cost=round(profit_data["transport_cost"], 2),
            toll_cost=round(profit_data["toll_cost"], 2),
            loading_cost=round(profit_data["loading_cost"], 2),
            unloading_cost=round(profit_data["unloading_cost"], 2),
            mandi_fee=round(profit_data["mandi_fee"], 2),
            commission=round(profit_data["commission"], 2),
            additional_cost=round(profit_data["additional_cost"], 2),
            total_cost=round(profit_data["total_cost"], 2),
        )

        comp = MandiComparison(
            mandi_id=m.get("id"),
            mandi_name=m["name"],
            state=m.get("state") or "Unknown",
            district=m.get("district") or "Unknown",
            distance_km=round(road_dist, 1),
            price_per_kg=round(m["price_per_kg"], 2),
            gross_revenue=round(profit_data["gross_revenue"], 2),
            costs=costs,
            net_profit=round(profit_data["net_profit"], 2),
            profit_per_kg=round(profit_data["profit_per_kg"], 2),
            roi_percentage=round(profit_data["roi_percentage"], 1),
            vehicle_type=vehicle_type,
            vehicle_capacity_kg=capacity,
            trips_required=trips,
            recommendation="recommended" if profit_data["net_profit"] > 0 else "not_recommended",
            distance_source=dist_source,
            verdict="not_viable",    # placeholder — assigned in second pass
            verdict_reason="",       # placeholder — assigned in second pass
        )
        raw_comparisons.append(comp)

    # Sort by net_profit descending, then assign rank-aware verdicts
    raw_comparisons.sort(key=lambda x: x.net_profit, reverse=True)
    total = len(raw_comparisons)
    for rank, comp in enumerate(raw_comparisons, start=1):
        tier, reason = compute_verdict(
            comp.net_profit, comp.gross_revenue, comp.profit_per_kg, rank, total
        )
        comp.verdict = tier
        comp.verdict_reason = reason

    return raw_comparisons[: request.limit], has_estimated
