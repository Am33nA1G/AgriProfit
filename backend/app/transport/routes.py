"""
Transport cost calculator routes.

This module provides endpoints for:
- Comparing transport costs to different mandis
- Finding optimal selling location based on net profit
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.transport.schemas import (
    TransportCompareRequest,
    TransportCompareResponse,
    VehicleType,
)
from app.transport.service import (
    compare_mandis,
    VEHICLES,
    DISTRICT_COORDINATES,
    LOADING_COST_PER_KG,
    UNLOADING_COST_PER_KG,
    MANDI_FEE_RATE,
    COMMISSION_RATE,
)
from pydantic import BaseModel, Field


class TransportCalculateRequest(BaseModel):
    """Schema for simple transport cost calculation."""
    commodity: str = Field(..., description="Commodity name")
    quantity_kg: float = Field(..., gt=0, le=50000, description="Quantity in kg")
    distance_km: float = Field(..., gt=0, le=1000, description="Distance in km")
    vehicle_type: str = Field(default="tempo", description="Vehicle type: tempo, truck_small, truck_large, pickup")


router = APIRouter(prefix="/transport", tags=["Transport"])


@router.post(
    "/calculate",
    status_code=status.HTTP_200_OK,
    summary="Calculate Transport Cost",
    description="""
Calculate transport cost for moving a commodity between two locations.

Simple endpoint for quick transport cost estimates based on distance and quantity.
""",
    responses={
        200: {"description": "Transport cost calculated"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"},
    },
)
async def calculate_transport_cost(
    request: TransportCalculateRequest,
    db: Session = Depends(get_db),
):
    """
    Calculate transport cost for a commodity.
    
    Args:
        request: TransportCalculateRequest with commodity, quantity, distance, vehicle type
        db: Database session
    
    Returns:
        Dict with transport cost estimate
    """
    # Extract from request
    commodity = request.commodity
    quantity_kg = request.quantity_kg
    distance_km = request.distance_km
    vehicle_type = request.vehicle_type
    
    # Map vehicle type string to enum
    vehicle_map = {
        "tempo": VehicleType.TEMPO,
        "truck_small": VehicleType.TRUCK_SMALL,
        "truck_large": VehicleType.TRUCK_LARGE,
        "pickup": VehicleType.TEMPO,  # Alias for tempo
    }
    
    vehicle = vehicle_map.get(vehicle_type.lower())
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid vehicle type. Use: {', '.join(vehicle_map.keys())}"
        )
    
    # Check if vehicle can handle the load
    vehicle_capacity = VEHICLES[vehicle]["capacity_kg"]
    if quantity_kg > vehicle_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{vehicle_type} can only carry up to {vehicle_capacity} kg. Use a larger vehicle."
        )
    
    # Calculate costs
    transport_cost = distance_km * VEHICLES[vehicle]["cost_per_km"] * 2  # Round trip
    loading_cost = quantity_kg * LOADING_COST_PER_KG
    unloading_cost = quantity_kg * UNLOADING_COST_PER_KG
    total_cost = transport_cost + loading_cost + unloading_cost
    
    return {
        "commodity": commodity,
        "quantity_kg": quantity_kg,
        "distance_km": distance_km,
        "vehicle_type": vehicle.value,
        "vehicle_capacity_kg": vehicle_capacity,
        "costs": {
            "transport_cost": round(transport_cost, 2),
            "loading_cost": round(loading_cost, 2),
            "unloading_cost": round(unloading_cost, 2),
            "total_cost": round(total_cost, 2),
        },
        "estimated_time_hours": round(distance_km / 50, 1),  # Assume 50 km/h average
        "cost_per_km": VEHICLES[vehicle]["cost_per_km"],
    }


@router.post(
    "/compare",
    response_model=TransportCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Transport Options",
    description="""
Compare transport costs and net profits for selling a commodity at different mandis.

This endpoint helps farmers make informed decisions about where to sell their produce
by calculating:
- Distance to each mandi
- Transport costs (based on vehicle type and distance)
- Loading/unloading charges
- Mandi fees and commissions
- Net profit after all deductions

Results are sorted by net profit (highest first).
""",
    responses={
        200: {
            "description": "Comparison results",
            "model": TransportCompareResponse,
        },
        400: {
            "description": "Invalid request (unknown commodity or district)",
            "content": {
                "application/json": {
                    "examples": {
                        "commodity_not_found": {
                            "summary": "Commodity not found",
                            "value": {"detail": "Commodity with name '...' not found"},
                        },
                        "unknown_district": {
                            "summary": "Unknown district",
                            "value": {
                                "detail": "Unknown district 'XYZ'. Please provide source_latitude and source_longitude."
                            },
                        },
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
        },
    },
)
async def compare_transport_options(
    request: TransportCompareRequest,
    db: Session = Depends(get_db),
) -> TransportCompareResponse:
    """
    Compare transport options to find the most profitable mandi.

    Given a commodity, quantity, and source location, this endpoint
    analyzes all available mandis and returns a ranked list based
    on net profit after transport and market costs.

    **Vehicle Selection:**
    - Tempo: Up to 2,000 kg (₹12/km)
    - Small Truck: Up to 5,000 kg (₹18/km)
    - Large Truck: Up to 10,000 kg (₹25/km)

    **Cost Components:**
    - Transport: Round-trip vehicle cost
    - Loading: ₹0.40/kg at source
    - Unloading: ₹0.40/kg at destination
    - Mandi Fee: 2% of gross revenue
    - Commission: 2.5% of gross revenue

    Args:
        request: TransportCompareRequest with commodity, quantity, source
        db: Database session (injected)

    Returns:
        TransportCompareResponse with ranked mandi comparisons

    Raises:
        HTTPException 400: Commodity not found or unknown district
        HTTPException 422: Validation error (invalid quantity, coordinates, etc.)
    """
    try:
        comparisons, has_estimated = compare_mandis(request, db)

        best_mandi = comparisons[0] if comparisons else None
        distance_note = (
            "Some distances are estimated — routing service unavailable."
            if has_estimated else None
        )

        return TransportCompareResponse(
            commodity=request.commodity,
            quantity_kg=request.quantity_kg,
            source_district=request.source_district,
            comparisons=comparisons,
            best_mandi=best_mandi,
            total_mandis_analyzed=len(comparisons),
            distance_note=distance_note,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/vehicles",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Vehicle Options",
    description="Get available vehicle types with their capacities and costs.",
    responses={
        200: {
            "description": "Vehicle specifications",
            "content": {
                "application/json": {
                    "example": {
                        "vehicles": {
                            "tempo": {
                                "capacity_kg": 2000,
                                "cost_per_km": 12.0,
                                "description": "Small vehicle for loads up to 2000 kg",
                            },
                            "truck_small": {
                                "capacity_kg": 5000,
                                "cost_per_km": 18.0,
                                "description": "Medium truck for loads up to 5000 kg",
                            },
                            "truck_large": {
                                "capacity_kg": 10000,
                                "cost_per_km": 25.0,
                                "description": "Large truck for loads up to 10000 kg",
                            },
                        },
                        "loading_cost_per_kg": 0.40,
                        "unloading_cost_per_kg": 0.40,
                        "mandi_fee_rate": 0.02,
                        "commission_rate": 0.025,
                    }
                }
            },
        }
    },
)
async def get_vehicle_options() -> dict:
    """
    Get available vehicle types and cost parameters.

    Returns all vehicle options with their specifications,
    plus loading/unloading costs and market fee rates.

    This information helps users understand the cost structure
    before making transport comparisons.

    Returns:
        Dictionary with vehicle specs and cost parameters
    """
    return {
        "vehicles": {
            vtype.value: {
                "capacity_kg": spec["capacity_kg"],
                "cost_per_km": spec["cost_per_km"],
                "description": spec["description"],
            }
            for vtype, spec in VEHICLES.items()
        },
        "loading_cost_per_kg": LOADING_COST_PER_KG,
        "unloading_cost_per_kg": UNLOADING_COST_PER_KG,
        "mandi_fee_rate": MANDI_FEE_RATE,
        "commission_rate": COMMISSION_RATE,
    }


@router.get(
    "/districts",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Supported Districts",
    description="Get list of Kerala districts with default coordinates.",
    responses={
        200: {
            "description": "District coordinates",
            "content": {
                "application/json": {
                    "example": {
                        "state": "Kerala",
                        "districts": {
                            "Ernakulam": {
                                "latitude": 9.9312,
                                "longitude": 76.2673,
                            },
                            "Thrissur": {
                                "latitude": 10.5276,
                                "longitude": 76.2144,
                            },
                        },
                    }
                }
            },
        }
    },
)
async def get_supported_districts() -> dict:
    """
    Get list of supported Kerala districts.

    Returns all districts with their default coordinates.
    These coordinates are used when the user doesn't provide
    specific source_latitude and source_longitude.

    Returns:
        Dictionary with state name and district coordinates
    """
    districts = {
        name: {"latitude": coords[0], "longitude": coords[1]}
        for name, coords in DISTRICT_COORDINATES.items()
    }

    return {
        "state": "Kerala",
        "districts": districts,
    }
