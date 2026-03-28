"""
Arbitrage module Pydantic schemas.

ArbitrageResult: Single destination mandi with all cost/profit fields.
ArbitrageResponse: Full response envelope returned by GET /arbitrage/{commodity}/{district}.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ArbitrageResult(BaseModel):
    """
    Single destination mandi arbitrage signal.

    All financial figures are per-quintal (100 kg) for consistent
    comparison regardless of the farmer's actual shipment quantity.
    """
    mandi_name: str = Field(..., description="Destination mandi display name")
    district: str = Field(..., description="District where destination mandi is located")
    state: str = Field(..., description="State where destination mandi is located")

    # Distance & logistics
    distance_km: float = Field(..., description="Road distance from source district to this mandi (km)")
    travel_time_hours: float = Field(..., description="Estimated round-trip travel time (hours)")
    is_interstate: bool = Field(..., description="True if crossing state boundary")

    # Financial (all per-quintal)
    freight_cost_per_quintal: float = Field(
        ...,
        description="Total logistics cost per quintal (₹): freight + tolls + hamali + fees + commission. "
                    "Computed as costs.total_cost when compare_mandis() is called with quantity_kg=100.",
    )
    spoilage_percent: float = Field(
        ...,
        description="Estimated quantity loss due to spoilage during transit (%)",
    )
    net_profit_per_quintal: float = Field(
        ...,
        description="Net profit per quintal after all costs and spoilage (₹). "
                    "Computed as profit_per_kg * 100.",
    )

    # Verdict
    verdict: str = Field(
        ...,
        description="Transport verdict: excellent / good / marginal / not_viable",
    )

    # Data freshness
    price_date: date = Field(..., description="Date of the price data used for this result")
    days_since_update: int = Field(
        ...,
        description="Days between price_date and data_reference_date (MAX price_date in dataset). "
                    "999 when price_date is unknown.",
    )
    is_stale: bool = Field(
        ...,
        description="True when days_since_update > 7 — price data may be outdated",
    )
    stale_warning: str | None = Field(
        default=None,
        description="Human-readable staleness warning; set only when is_stale=True",
    )

    model_config = ConfigDict(from_attributes=True)


class ArbitrageResponse(BaseModel):
    """
    Full arbitrage response for a commodity/district query.

    Returns up to 3 destination mandis ranked by net_profit_per_quintal descending.
    Results below the margin threshold are suppressed (not returned) but counted.
    """
    commodity: str = Field(..., description="Commodity name queried")
    origin_district: str = Field(..., description="Farmer's source district")

    results: list[ArbitrageResult] = Field(
        ...,
        max_length=3,
        description="Top destination mandis ranked by net_profit_per_quintal descending (max 3)",
    )

    suppressed_count: int = Field(
        ...,
        ge=0,
        description="Number of mandis filtered out because net margin < threshold_pct",
    )
    threshold_pct: float = Field(
        ...,
        description="Net margin threshold used for filtering (%). "
                    "Mandis with (net_profit / gross_revenue) * 100 < threshold_pct are suppressed.",
    )
    data_reference_date: date = Field(
        ...,
        description="MAX(price_date) across the dataset — used as reference for freshness computation. "
                    "Never date.today().",
    )
    has_stale_data: bool = Field(
        ...,
        description="True if any result in `results` has is_stale=True",
    )
    distance_note: str | None = Field(
        default=None,
        description="Set when any distance used the haversine fallback instead of live OSRM routing",
    )

    model_config = ConfigDict(from_attributes=True)
