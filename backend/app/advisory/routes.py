"""Directional advisory routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.advisory.schemas import DirectionalAdvisoryResponse
from app.advisory.service import DirectionalAdvisoryService
from app.database.session import get_db

router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.get(
    "/commodities",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List commodities with directional advisories",
    description="Returns commodity slugs that have directional advisory artifacts.",
)
def get_commodities(db: Session = Depends(get_db)) -> list[str]:
    svc = DirectionalAdvisoryService(db)
    return svc.list_commodities()


@router.get(
    "/model-health",
    status_code=status.HTTP_200_OK,
    summary="Directional advisory model health",
    description=(
        "Returns validation and deployment metadata for each directional advisory model, "
        "including selective accuracy and abstention thresholds."
    ),
)
def model_health(db: Session = Depends(get_db)) -> dict:
    svc = DirectionalAdvisoryService(db)
    return svc.model_health()


@router.get(
    "/{commodity}/{district}",
    response_model=DirectionalAdvisoryResponse,
    status_code=status.HTTP_200_OK,
    summary="7-day directional advisory",
    description=(
        "Returns a conservative 7-day price-direction signal for a commodity and district. "
        "The endpoint abstains instead of forcing a recommendation when the model or data "
        "does not meet validation thresholds."
    ),
)
def get_advisory(
    commodity: str,
    district: str,
    db: Session = Depends(get_db),
) -> DirectionalAdvisoryResponse:
    svc = DirectionalAdvisoryService(db)
    return svc.get_advisory(commodity, district)
