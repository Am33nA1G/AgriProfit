"""
Transport cost calculation service.

Refactored to functional style for direct testing and usage.
"""
import json
import logging
import math
from datetime import date as _date
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
from app.transport.economics import (
    compute_freight,
    compute_travel_time,
    VEHICLE_CAPACITY_KG,
    PRACTICAL_CAPACITY_FACTOR,
)
from app.transport.spoilage import compute_spoilage, compute_hamali
from app.transport.price_analytics import compute_price_analytics
from app.transport.risk_engine import (
    compute_risk_score,
    run_stress_test,
    apply_behavioral_corrections,
    check_guardrails,
)
from app.core.config import settings

_audit_log = logging.getLogger("transport.audit")

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

# Loading/unloading costs (legacy — kept for routes.py /calculate and /vehicles endpoints)
# Actual hamali costs in compare_mandis() use spoilage.compute_hamali() with regional rates.
LOADING_COST_PER_KG = 0.15   # ₹15 per quintal
UNLOADING_COST_PER_KG = 0.20  # ₹20 per quintal

# Mandi fees (varies by state, using average)
MANDI_FEE_RATE = 0.015  # 1.5%
COMMISSION_RATE = 0.025  # 2.5% agent commission

# Additional charges per trip
WEIGHBRIDGE_FEE = 80.0  # ₹ per weighing
PARKING_FEE = 50.0      # ₹ per trip
DOCUMENTATION_FEE = 70.0  # ₹ per trip (receipts, permits)

# Distance calculations (legacy — used for toll_plazas count in return dict)
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
    """Select vehicle type using 90% practical capacity thresholds."""
    if quantity_kg <= VEHICLE_CAPACITY_KG["TEMPO"] * PRACTICAL_CAPACITY_FACTOR:
        return VehicleType.TEMPO
    elif quantity_kg <= VEHICLE_CAPACITY_KG["TRUCK_SMALL"] * PRACTICAL_CAPACITY_FACTOR:
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
    vehicle_type: VehicleType,
    source_state: str = "Unknown",
    mandi_state: str = "Unknown",
    commodity_category: str | None = None,
    round_trip_hours: float | None = None,
    volatility_pct: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate detailed cost breakdown and net profit using real Indian freight model.

    Uses economics.py for freight and spoilage.py for perishability.
    Falls back to legacy model if source/mandi state not provided.
    """
    diesel_price = getattr(settings, "diesel_price_per_liter", 98.0)

    # Real freight calculation
    freight = compute_freight(
        distance_km=distance_km,
        vehicle_type=vehicle_type,
        quantity_kg=quantity_kg,
        source_state=source_state,
        mandi_state=mandi_state,
        diesel_price=diesel_price,
    )

    # Spoilage
    travel_hours = round_trip_hours if round_trip_hours is not None else freight.round_trip_hours
    spo = compute_spoilage(commodity_category, travel_hours, volatility_pct)
    hamali = compute_hamali(mandi_state, quantity_kg)

    # Revenue accounting for spoilage
    gross_revenue = price_per_kg * quantity_kg
    net_qty = spo.net_saleable_quantity(quantity_kg)
    net_revenue = net_qty * price_per_kg * (1 - spo.grade_discount_fraction)

    # Mandi fees on gross revenue (standard APMC)
    mandi_fee = gross_revenue * MANDI_FEE_RATE
    commission = gross_revenue * COMMISSION_RATE

    # Additional fixed costs (weighbridge, parking, docs)
    additional_cost = (WEIGHBRIDGE_FEE + PARKING_FEE + DOCUMENTATION_FEE) * freight.trips

    # Total
    total_cost = (
        freight.total_freight
        + hamali.loading_hamali
        + hamali.unloading_hamali
        + mandi_fee
        + commission
        + additional_cost
    )

    net_profit = net_revenue - total_cost
    profit_per_kg = net_profit / quantity_kg if quantity_kg > 0 else 0
    roi_percentage = (net_profit / total_cost * 100) if total_cost > 0 else 0

    return {
        # Revenue
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "net_saleable_quantity_kg": net_qty,

        # Freight components (from economics.py)
        "transport_cost": freight.raw_transport,
        "toll_cost": freight.toll_cost,
        "driver_bata": freight.driver_bata,
        "cleaner_bata": freight.cleaner_bata,
        "halt_cost": freight.halt_cost,
        "breakdown_reserve": freight.breakdown_reserve,
        "permit_cost": freight.permit_cost,
        "rto_buffer": freight.rto_buffer,

        # Hamali (from spoilage.py)
        "loading_hamali": hamali.loading_hamali,
        "unloading_hamali": hamali.unloading_hamali,

        # Legacy fields (kept for backward compat)
        "loading_cost": hamali.loading_hamali,
        "unloading_cost": hamali.unloading_hamali,

        # Market costs
        "mandi_fee": mandi_fee,
        "commission": commission,
        "additional_cost": additional_cost,

        # Totals
        "total_cost": total_cost,
        "net_profit": net_profit,
        "profit_per_kg": profit_per_kg,
        "roi_percentage": roi_percentage,
        "trips": freight.trips,
        "toll_plazas": max(0, round(distance_km / TOLL_PLAZA_SPACING_KM)),

        # Spoilage
        "spoilage_percent": round(spo.spoilage_fraction * 100, 2),
        "weight_loss_percent": round(spo.weight_loss_fraction * 100, 2),
        "grade_discount_percent": round(spo.grade_discount_fraction * 100, 2),

        # Route metadata
        "travel_time_hours": freight.round_trip_hours,
        "route_type": freight.route_type,
        "is_interstate": freight.is_interstate,
        "diesel_price_used": freight.diesel_price_used,
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
    5. Calculates real freight + spoilage + risk per mandi
    6. Sorts by net profit, assigns rank-aware verdicts with behavioral corrections
    7. Returns (comparisons[:limit], has_estimated)
    """
    from app.transport.routing import routing_service
    from app.transport.schemas import StressTestResult as PydanticStressTestResult

    if not db:
        raise ValueError("Database session required")

    # Resolve commodity
    from app.models import Commodity
    commodity = db.query(Commodity).filter(
        Commodity.name.ilike(request.commodity)
    ).first()
    if not commodity:
        raise ValueError(f"Commodity '{request.commodity}' not found")

    commodity_category = getattr(commodity, "category", None)

    # Fetch mandis with prices
    raw_mandis = get_mandis_for_commodity(str(commodity.id), db, limit=200)

    # Source coords
    coords = get_source_coordinates(request, db)
    if coords is None:
        raise ValueError(
            f"Could not determine coordinates for district '{request.source_district}'. "
            f"Please provide source_latitude and source_longitude."
        )

    source_lat, source_lon = coords
    vehicle_type = select_vehicle(request.quantity_kg)

    # Pre-filter: price-sorted top N (hard cap from settings)
    max_eval = getattr(settings, "transport_max_mandis_evaluated", 25)
    osrm_candidate_limit = max(request.limit * 3, max_eval)

    eligible = [
        m for m in raw_mandis
        if m.get("latitude") and m.get("longitude") and m.get("price_per_kg") is not None
    ]
    eligible.sort(key=lambda m: m["price_per_kg"], reverse=True)
    candidates = eligible[:osrm_candidate_limit]

    # Batch price analytics (one query per mandi — fast with 7-row limit)
    price_analytics_map: dict[str, Any] = {}
    for m in candidates:
        pa = compute_price_analytics(str(commodity.id), m["name"], db)
        price_analytics_map[m["name"]] = pa

    # Parallel OSRM distances
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_distance(m: dict) -> tuple[dict, float, str]:
        dist, src = routing_service.get_distance_km(
            source_lat, source_lon, m["latitude"], m["longitude"], db
        )
        return m, dist, src

    distances: dict[str, tuple[float, str]] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_distance, m): m for m in candidates}
        for future in as_completed(futures):
            m, road_dist, dist_source = future.result()
            distances[m["name"]] = (road_dist, dist_source)

    diesel_price = getattr(settings, "diesel_price_per_liter", 98.0)
    diesel_baseline = getattr(settings, "diesel_baseline_price", 98.0)
    weather_risk_weight = getattr(settings, "transport_weather_risk_weight", 0.3)

    raw_comparisons: list[MandiComparison] = []
    has_estimated = False

    for m in candidates:
        road_dist, dist_source = distances[m["name"]]
        if dist_source == "estimated":
            has_estimated = True
        if request.max_distance_km and road_dist > request.max_distance_km:
            continue

        pa = price_analytics_map.get(m["name"])
        volatility_pct = pa.volatility_pct if pa else 0.0
        confidence_score = pa.confidence_score if pa else 100
        price_trend = pa.price_trend if pa else "stable"

        profit_data = calculate_net_profit(
            price_per_kg=m["price_per_kg"],
            quantity_kg=request.quantity_kg,
            distance_km=road_dist,
            vehicle_type=vehicle_type,
            source_state=request.source_state or "Unknown",
            mandi_state=m.get("state") or "Unknown",
            commodity_category=commodity_category,
            volatility_pct=volatility_pct,
        )

        # Risk score
        risk_result = compute_risk_score(
            volatility_pct=volatility_pct,
            distance_km=road_dist,
            spoilage_fraction=profit_data["spoilage_percent"] / 100,
            diesel_price=diesel_price,
            diesel_baseline=diesel_baseline,
            is_interstate=profit_data["is_interstate"],
            weather_risk_weight=weather_risk_weight,
        )

        # Stress test
        stress_raw = run_stress_test(
            normal_profit=profit_data["net_profit"],
            normal_net_quantity=profit_data["net_saleable_quantity_kg"],
            normal_total_cost=profit_data["total_cost"],
            price_per_kg=m["price_per_kg"],
            toll_cost=profit_data["toll_cost"],
            raw_transport=profit_data["transport_cost"],
            spoilage_fraction=profit_data["spoilage_percent"] / 100,
            grade_discount_fraction=profit_data["grade_discount_percent"] / 100,
        )
        stress = PydanticStressTestResult(
            worst_case_profit=stress_raw.worst_case_profit,
            break_even_price_per_kg=stress_raw.break_even_price_per_kg,
            margin_of_safety_pct=stress_raw.margin_of_safety_pct,
            verdict_survives_stress=stress_raw.verdict_survives_stress,
        )

        # Guardrails
        gross_rev = profit_data["gross_revenue"]
        economic_warning = check_guardrails(
            roi_percentage=profit_data["roi_percentage"],
            net_margin=(profit_data["net_profit"] / gross_rev) if gross_rev > 0 else 0.0,
            cost_to_gross_ratio=(profit_data["total_cost"] / gross_rev) if gross_rev > 0 else 0.0,
            profit_per_kg=profit_data["profit_per_kg"],
            price_per_kg=m["price_per_kg"],
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
            driver_bata=round(profit_data["driver_bata"], 2),
            cleaner_bata=round(profit_data["cleaner_bata"], 2),
            halt_cost=round(profit_data["halt_cost"], 2),
            breakdown_reserve=round(profit_data["breakdown_reserve"], 2),
            permit_cost=round(profit_data["permit_cost"], 2),
            rto_buffer=round(profit_data["rto_buffer"], 2),
            loading_hamali=round(profit_data["loading_hamali"], 2),
            unloading_hamali=round(profit_data["unloading_hamali"], 2),
        )

        capacity = VEHICLE_CAPACITY_KG[vehicle_type.value]

        # Populate latest_price_date from price_analytics_map
        pa_entry = price_analytics_map.get(m["name"])

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
            vehicle_capacity_kg=int(capacity),
            trips_required=profit_data["trips"],
            recommendation="recommended" if profit_data["net_profit"] > 0 else "not_recommended",
            distance_source=dist_source,
            verdict="not_viable",
            verdict_reason="",
            # New fields
            travel_time_hours=round(profit_data["travel_time_hours"], 2),
            route_type=profit_data["route_type"],
            is_interstate=profit_data["is_interstate"],
            diesel_price_used=profit_data["diesel_price_used"],
            spoilage_percent=profit_data["spoilage_percent"],
            weight_loss_percent=profit_data["weight_loss_percent"],
            grade_discount_percent=profit_data["grade_discount_percent"],
            net_saleable_quantity_kg=round(profit_data["net_saleable_quantity_kg"], 1),
            price_volatility_7d=volatility_pct,
            price_trend=price_trend,
            risk_score=risk_result.risk_score,
            confidence_score=confidence_score,
            stability_class=risk_result.stability_class,
            stress_test=stress,
            economic_warning=economic_warning,
            # Arbitrage freshness field
            latest_price_date=pa_entry.latest_price_date if pa_entry else None,
        )
        raw_comparisons.append(comp)

    # ── Pass 1: preliminary profit sort → compute verdicts + behavioral corrections
    raw_comparisons.sort(key=lambda x: x.net_profit, reverse=True)
    total = len(raw_comparisons)
    best_profit = raw_comparisons[0].net_profit if raw_comparisons else 0.0

    for rank, comp in enumerate(raw_comparisons, start=1):
        tier, reason = compute_verdict(
            comp.net_profit, comp.gross_revenue, comp.profit_per_kg, rank, total
        )
        # Behavioral correction
        profit_diff_pct = (
            ((best_profit - comp.net_profit) / abs(best_profit) * 100)
            if best_profit != 0 else 0.0
        )
        adjusted_tier = apply_behavioral_corrections(
            verdict=tier,
            distance_km=comp.distance_km,
            profit_diff_pct=profit_diff_pct,
            risk_score=comp.risk_score,
        )
        # If stress test failed, downgrade verdict one additional tier if still excellent
        if (comp.stress_test and not comp.stress_test.verdict_survives_stress
                and adjusted_tier == "excellent"):
            adjusted_tier = "good"

        comp.verdict = adjusted_tier
        comp.verdict_reason = reason

    # ── Pass 2: re-sort by verdict tier (excellent first), then net profit within tier
    _VERDICT_ORDER = {"excellent": 0, "good": 1, "marginal": 2, "not_viable": 3}
    raw_comparisons.sort(
        key=lambda x: (_VERDICT_ORDER.get(x.verdict, 9), -x.net_profit)
    )

    # ── Pass 3: update rank strings and emit audit logs with final ordering
    for rank, comp in enumerate(raw_comparisons, start=1):
        _, reason = compute_verdict(
            comp.net_profit, comp.gross_revenue, comp.profit_per_kg, rank, total
        )
        comp.verdict_reason = reason

        # Audit log (structured JSON per comparison)
        pa_entry = price_analytics_map.get(comp.mandi_name)
        _audit_log.info(json.dumps({
            "event": "transport_comparison",
            "mandi_id": str(comp.mandi_id) if comp.mandi_id else None,
            "mandi_name": comp.mandi_name,
            "price_date": str(pa_entry.latest_price_date) if pa_entry and pa_entry.latest_price_date else None,
            "distance_source": comp.distance_source,
            "diesel_price": diesel_price,
            "spoilage_pct": comp.spoilage_percent,
            "volatility_pct": comp.price_volatility_7d,
            "stress_test_worst_case": comp.stress_test.worst_case_profit if comp.stress_test else None,
            "risk_score": comp.risk_score,
            "verdict": comp.verdict,
            "travel_time_hours": comp.travel_time_hours,
            "is_interstate": comp.is_interstate,
        }))

    return raw_comparisons[:request.limit], has_estimated
