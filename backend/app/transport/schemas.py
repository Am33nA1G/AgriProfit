"""
Transport cost calculator schemas for API requests and responses.

This module defines Pydantic models for:
- Transport comparison requests
- Mandi comparison results with costs breakdown
- Vehicle type enumeration
"""
from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StressTestResult(BaseModel):
    """Worst-case scenario simulation results."""
    worst_case_profit: float = Field(..., description="Net profit after diesel+15%, toll+25%, price-12%, spoilage+5pp, grade_discount+3pp")
    break_even_price_per_kg: float = Field(..., description="Minimum price per kg to break even under stress")
    margin_of_safety_pct: float = Field(..., description="Buffer between normal and worst-case profit (%)")
    verdict_survives_stress: bool = Field(..., description="True if worst_case_profit > 0")
    model_config = ConfigDict(from_attributes=True)


class VehicleType(str, Enum):
    """
    Vehicle types available for transport.

    Each vehicle has different capacity and cost characteristics:
    - TEMPO: Small vehicle for quantities up to 2000 kg
    - TRUCK_SMALL: Medium truck for 2001-5000 kg
    - TRUCK_LARGE: Large truck for quantities above 5000 kg
    """
    TEMPO = "TEMPO"
    TRUCK_SMALL = "TRUCK_SMALL"
    TRUCK_LARGE = "TRUCK_LARGE"


class TransportCompareRequest(BaseModel):
    """
    Schema for transport comparison request.

    Calculates optimal transport options for selling a commodity
    at different mandis, considering distance, vehicle costs,
    and market fees.
    """
    commodity: str = Field(
        ...,
        description="Name of the commodity to transport (e.g. 'Wheat')",
        json_schema_extra={"example": "Wheat"}
    )
    quantity_kg: float = Field(
        ...,
        gt=0,
        le=50000,
        description="Quantity in kilograms (1 - 50,000 kg)",
        json_schema_extra={"example": 1000}
    )
    source_state: str = Field(
        default="Kerala",
        max_length=100,
        description="Source state (defaults to Kerala)",
        json_schema_extra={"example": "Kerala"}
    )
    source_district: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Source district within the state",
        json_schema_extra={"example": "Ernakulam"}
    )
    source_latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Source latitude for precise distance calculation",
        json_schema_extra={"example": 9.9312}
    )
    source_longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Source longitude for precise distance calculation",
        json_schema_extra={"example": 76.2673}
    )
    max_distance_km: float | None = Field(
        default=None,
        gt=0,
        le=1000,
        description="Maximum distance to consider (optional filter)",
        json_schema_extra={"example": 200}
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of mandis to return",
        json_schema_extra={"example": 10}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Basic request",
                    "value": {
                        "commodity": "Wheat",
                        "quantity_kg": 1000,
                        "source_district": "Ernakulam"
                    }
                }
            ]
        }
    )


class CostBreakdown(BaseModel):
    """Detailed breakdown of transport costs."""
    transport_cost: float = Field(
        ...,
        description="Vehicle freight cost (round-trip)",
        json_schema_extra={"example": 2160.0}
    )
    toll_cost: float = Field(
        ...,
        description="Highway toll charges (both ways)",
        json_schema_extra={"example": 400.0}
    )
    loading_cost: float = Field(
        ...,
        description="Loading charges at source (Hamali)",
        json_schema_extra={"example": 35.0}
    )
    unloading_cost: float = Field(
        ...,
        description="Unloading charges at destination",
        json_schema_extra={"example": 30.0}
    )
    mandi_fee: float = Field(
        ...,
        description="Mandi market fee (1.5% of gross)",
        json_schema_extra={"example": 450.0}
    )
    commission: float = Field(
        ...,
        description="Agent commission (2.5% of gross)",
        json_schema_extra={"example": 750.0}
    )
    additional_cost: float = Field(..., description="Fixed costs per trip (weighbridge, parking, docs)", json_schema_extra={"example": 200.0})
    driver_bata: float = Field(default=0.0, description="Driver daily bata for trip duration")
    cleaner_bata: float = Field(default=0.0, description="Cleaner bata (trucks only; 0 for tempo)")
    halt_cost: float = Field(default=0.0, description="Night halt cost (applied when round-trip > 12 hours)")
    breakdown_reserve: float = Field(default=0.0, description="Breakdown buffer at ₹1/km (both ways)")
    permit_cost: float = Field(default=0.0, description="Interstate permit cost (₹1,200 if crossing state boundary)")
    rto_buffer: float = Field(default=0.0, description="RTO friction buffer (1.5% intrastate / 2.5% interstate)")
    loading_hamali: float = Field(default=0.0, description="Regional loading hamali at source")
    unloading_hamali: float = Field(default=0.0, description="Regional unloading hamali at mandi")
    total_cost: float = Field(
        ...,
        description="Sum of all costs",
        json_schema_extra={"example": 4025.0}
    )

    model_config = ConfigDict(from_attributes=True)


class MandiComparison(BaseModel):
    """
    Comparison result for a single mandi.

    Contains all details needed to evaluate selling at this mandi
    including distance, pricing, costs, and net profit.
    """
    mandi_id: UUID | None = Field(None, description="Mandi unique identifier")
    mandi_name: str = Field(..., description="Mandi display name")
    district: str = Field(..., description="District where mandi is located")
    state: str = Field(..., description="State where mandi is located")

    distance_km: float = Field(
        ...,
        description="Road distance in kilometers",
        json_schema_extra={"example": 85.5}
    )

    price_per_kg: float = Field(
        ...,
        description="Current modal price per kg at this mandi",
        json_schema_extra={"example": 30.0}
    )
    gross_revenue: float = Field(
        ...,
        description="Total revenue before costs (price * quantity)",
        json_schema_extra={"example": 30000.0}
    )

    costs: CostBreakdown = Field(
        ...,
        description="Detailed cost breakdown"
    )

    net_profit: float = Field(
        ...,
        description="Gross revenue minus total costs",
        json_schema_extra={"example": 25975.0}
    )
    profit_per_kg: float = Field(
        ...,
        description="Net profit divided by quantity",
        json_schema_extra={"example": 25.98}
    )
    roi_percentage: float = Field(
        ...,
        description="Return on investment (net profit / total cost * 100)",
        json_schema_extra={"example": 645.2}
    )

    vehicle_type: VehicleType = Field(
        ...,
        description="Recommended vehicle based on quantity",
        json_schema_extra={"example": "TEMPO"}
    )
    vehicle_capacity_kg: int = Field(
        ...,
        description="Maximum capacity of selected vehicle",
        json_schema_extra={"example": 2000}
    )
    trips_required: int = Field(
        ...,
        description="Number of trips needed for quantity",
        json_schema_extra={"example": 1}
    )

    recommendation: str = Field(
        default="recommended",
        description="Whether selling at this mandi is recommended",
        json_schema_extra={"example": "recommended"}
    )

    verdict: str = Field(
        default="not_viable",
        description="Sell verdict: excellent / good / marginal / not_viable",
    )
    verdict_reason: str = Field(
        default="",
        description="Human-readable explanation of the verdict",
    )
    distance_source: str = Field(default="estimated", description="Distance data source: 'osrm' or 'estimated'")
    # Route & time
    travel_time_hours: float = Field(default=0.0, description="Estimated round-trip travel time in hours")
    route_type: str = Field(default="mixed", description="Road category: 'highway' | 'mixed' | 'hill'")
    is_interstate: bool = Field(default=False, description="True if source state differs from mandi state")
    diesel_price_used: float = Field(default=98.0, description="Diesel price (₹/L) used in freight calculation")
    # Perishability
    spoilage_percent: float = Field(default=0.0, description="Estimated quantity loss to spoilage (%)")
    weight_loss_percent: float = Field(default=0.0, description="Moisture/weight shrinkage during transit (%)")
    grade_discount_percent: float = Field(default=0.0, description="Auction grade discount applied (%)")
    net_saleable_quantity_kg: float = Field(default=0.0, description="Quantity after spoilage and weight loss (kg)")
    # Price analytics
    price_volatility_7d: float = Field(default=0.0, description="7-day price volatility (CV%)")
    price_trend: str = Field(default="stable", description="Price direction: 'rising' | 'falling' | 'stable'")
    # Risk
    risk_score: float = Field(default=0.0, description="Composite risk score 0–100 (higher = riskier)")
    confidence_score: int = Field(default=100, description="Price data confidence 0–100")
    stability_class: str = Field(default="stable", description="Risk tier: 'stable' | 'moderate' | 'volatile'")
    # Stress test & guardrail
    stress_test: StressTestResult | None = Field(default=None, description="Worst-case scenario simulation")
    economic_warning: str | None = Field(default=None, description="Set when economic anomaly detected")

    model_config = ConfigDict(from_attributes=True)


class TransportCompareResponse(BaseModel):
    """
    Response containing transport comparison results.

    Lists mandis ranked by net profit (highest first),
    with complete cost breakdowns for informed decision making.
    """
    commodity: str = Field(..., description="Commodity name being transported")
    quantity_kg: float = Field(..., description="Quantity in kg")
    source_district: str = Field(..., description="Source location")

    comparisons: list[MandiComparison] = Field(
        ...,
        description="List of mandi comparisons sorted by net profit (descending)"
    )

    best_mandi: MandiComparison | None = Field(
        None,
        description="Mandi with highest net profit (convenience field)"
    )

    total_mandis_analyzed: int = Field(
        ...,
        description="Total number of mandis considered"
    )

    distance_note: str | None = Field(
        default=None,
        description="Set when any distance used the haversine fallback instead of live routing data",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "commodity_name": "Tomato",
                "quantity_kg": 1000,
                "source_district": "Ernakulam",
                "comparisons": [],
                "best_option": None,
                "total_mandis_analyzed": 15
            }
        }
    )
