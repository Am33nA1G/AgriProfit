"""
Transport cost calculator schemas for API requests and responses.

This module defines Pydantic models for:
- Transport comparison requests
- Mandi comparison results with costs breakdown
- Vehicle type enumeration
"""
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
        description="Vehicle freight cost (one-way; transporter rates include return)",
        json_schema_extra={"example": 2400.0}
    )
    toll_cost: float = Field(
        ...,
        description="Highway toll charges (both ways, NHAI rates)",
        json_schema_extra={"example": 400.0}
    )
    loading_cost: float = Field(
        ...,
        description="Hamali loading charges at source (₹15/quintal)",
        json_schema_extra={"example": 150.0}
    )
    unloading_cost: float = Field(
        ...,
        description="Hamali unloading charges at destination (₹12/quintal)",
        json_schema_extra={"example": 120.0}
    )
    mandi_fee: float = Field(
        ...,
        description="Mandi market fee (1.5% of gross revenue)",
        json_schema_extra={"example": 450.0}
    )
    commission: float = Field(
        ...,
        description="Agent/arthiya commission (2.5% of gross revenue)",
        json_schema_extra={"example": 750.0}
    )
    additional_cost: float = Field(
        ...,
        description="Per-trip costs: driver allowance (₹800), maintenance (₹2/km), weighbridge (₹80), parking (₹50), docs (₹70)",
        json_schema_extra={"example": 1200.0}
    )
    total_cost: float = Field(
        ...,
        description="Sum of all costs",
        json_schema_extra={"example": 5470.0}
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

    model_config = ConfigDict(
        from_attributes=True
    )


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
