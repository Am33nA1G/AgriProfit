"""Harvest advisor routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.harvest_advisor.schemas import HarvestAdvisorResponse, WeatherWarning
from app.harvest_advisor.service import HarvestAdvisorService

router = APIRouter(prefix="/harvest-advisor", tags=["Harvest Advisor"])

VALID_SEASONS = {"kharif", "rabi", "zaid", "annual"}


@router.get(
    "/recommend",
    response_model=HarvestAdvisorResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Crop Recommendations",
    description=(
        "Get top 5 crop recommendations ranked by expected profit per hectare "
        "for the given district and season."
    ),
)
def get_recommendation(
    state: str = Query(..., description="State name"),
    district: str = Query(..., description="District name"),
    season: str = Query(default="annual", description="Season: kharif|rabi|zaid|annual"),
    db: Session = Depends(get_db),
) -> HarvestAdvisorResponse:
    if season not in VALID_SEASONS:
        season = "annual"
    svc = HarvestAdvisorService(db)
    return svc.compute_recommendation(state, district, season)


@router.get(
    "/weather-warnings",
    response_model=list[WeatherWarning],
    status_code=status.HTTP_200_OK,
    summary="Get Weather Warnings",
    description=(
        "Get weather warnings (drought, flood, heat stress) for a district "
        "based on historical and forecast data."
    ),
)
def get_weather_warnings(
    state: str = Query(..., description="State name"),
    district: str = Query(..., description="District name"),
    db: Session = Depends(get_db),
) -> list[WeatherWarning]:
    svc = HarvestAdvisorService(db)
    return svc.get_weather_warnings(state, district)


@router.get(
    "/districts",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="Get Districts with Data",
    description="Return districts with at least soil or price data for a state.",
)
def get_districts(
    state: str = Query(..., description="State name"),
    db: Session = Depends(get_db),
) -> list[str]:
    svc = HarvestAdvisorService(db)
    return svc.get_districts_with_data(state)
