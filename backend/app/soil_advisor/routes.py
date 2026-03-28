"""FastAPI router for Soil Advisor endpoints.

Registers 4 GET endpoints under the /soil-advisor prefix:
- GET /states              — list of 21 covered state names
- GET /districts           — distinct districts for a state
- GET /blocks              — distinct blocks for a state+district
- GET /profile             — full soil advisor response for a block

All endpoints use Query parameters (not path parameters) for state/district/block
to handle values containing hyphens, spaces, and special characters safely.

All handlers are sync (def), matching the project pattern for DB routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.soil_advisor.schemas import SoilAdvisorResponse
from app.soil_advisor.service import (
    get_blocks_for_district,
    get_districts_for_state,
    get_soil_advice,
    get_states,
)
from app.soil_advisor.suitability import COVERED_STATES

router = APIRouter(prefix="/soil-advisor", tags=["Soil Advisor"])


@router.get(
    "/states",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List Covered States",
    description="Return the 21 states covered by the ICAR soil health card dataset.",
)
def list_states(db: Session = Depends(get_db)) -> list[str]:
    """Return sorted list of covered state names."""
    return get_states(db)


@router.get(
    "/districts",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List Districts for a State",
    description="Return distinct districts with soil data for the given state.",
)
def list_districts(
    state: str = Query(..., description="State name (case-insensitive)"),
    db: Session = Depends(get_db),
) -> list[str]:
    """Return distinct districts for a state, sorted alphabetically."""
    return get_districts_for_state(db, state)


@router.get(
    "/blocks",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List Blocks for a District",
    description="Return distinct blocks with soil data for the given state and district.",
)
def list_blocks(
    state: str = Query(..., description="State name (case-insensitive)"),
    district: str = Query(..., description="District name (case-insensitive)"),
    db: Session = Depends(get_db),
) -> list[str]:
    """Return distinct blocks for a state+district, sorted alphabetically."""
    return get_blocks_for_district(db, state, district)


@router.get(
    "/profile",
    response_model=SoilAdvisorResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Soil Advisor Profile",
    description="""
Return the soil health profile and crop recommendations for a specific block.

Includes:
- 5 nutrient distributions (N, P, K, OC, pH) as percentage bars
- Up to 5 ranked crop recommendations based on ICAR suitability rules
- Fertiliser advice cards for deficient nutrients (low_pct > 50%)
- Mandatory disclaimer (always present, non-dismissable)

Returns 404 with `coverage_gap=true` for states not in the 21-state dataset.
""",
    responses={
        404: {
            "description": "State not in covered set or no data for this block",
            "content": {
                "application/json": {
                    "examples": {
                        "coverage_gap": {
                            "summary": "State not covered",
                            "value": {
                                "detail": {
                                    "coverage_gap": True,
                                    "message": "Soil data not available for PUNJAB. Available for 21 states only.",
                                }
                            },
                        }
                    }
                }
            },
        }
    },
)
def get_soil_advisor_profile(
    state: str = Query(..., description="State name (case-insensitive)"),
    district: str = Query(..., description="District name (case-insensitive)"),
    block: str = Query(..., description="Block name (may contain hyphens and spaces)"),
    db: Session = Depends(get_db),
) -> SoilAdvisorResponse:
    """Return soil advisor profile with nutrient distributions, crop recommendations,
    and fertiliser advice for a specific block.

    Raises:
        HTTPException 404: State not covered, or no soil data for this block.
    """
    # Coverage gate — only check /profile, not the list endpoints
    if state.upper().strip() not in COVERED_STATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "coverage_gap": True,
                "message": (
                    f"Soil data not available for {state}. "
                    "Available for 21 states only."
                ),
            },
        )

    return get_soil_advice(db, state, district, block)
