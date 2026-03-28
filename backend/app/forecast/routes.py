"""
Forecast routes — FastAPI endpoint for price forecasts.

GET /api/v1/forecast/{commodity}/{district}
GET /api/v1/forecast/commodities
GET /api/v1/forecast/model-health

IMPORTANT: Uses `def` (not `async def`) because get_or_load_model()
calls joblib.load() which is disk I/O. FastAPI runs `def` handlers in
a threadpool automatically, avoiding event loop blocking.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.forecast.schemas import ForecastResponse
from app.forecast.service import ForecastService
from app.forecast.service_7d import ForecastService7D
from app.ml.loader import list_commodity_slugs, load_meta
from app.ml.loader_7d import (
    is_good_7d_slug,
    list_7d_slugs,
    list_good_7d_slugs,
    list_slugs_for_district,
    get_states_for_commodity,
    get_districts_for_commodity_state,
)

router = APIRouter(prefix="/forecast", tags=["Forecast"])


def _needs_retrain(meta: dict) -> bool:
    """Return True if the model is stale / poor quality and should be retrained."""
    trained_at = meta.get("trained_at")
    if not trained_at:
        return True
    try:
        age = datetime.utcnow() - datetime.fromisoformat(trained_at)
        if age > timedelta(days=30):
            return True
    except (ValueError, TypeError):
        return True
    if (meta.get("r2_score") or 0.0) < 0.3:
        return True
    if (meta.get("interval_coverage_80pct") or 1.0) < 0.50:
        return True
    return False


@router.get(
    "/commodities",
    response_model=list[str],
    summary="List available commodities",
    description="Returns sorted list of commodity slugs that have trained ML artifacts.",
)
def get_commodities() -> list[str]:
    """List commodity slugs with reliable v5 models only (MAPE h7 < 25%)."""
    return list_good_7d_slugs()


@router.get(
    "/commodities/{district}",
    response_model=list[str],
    summary="List commodities available for a district",
    description="Returns slugs that have ≥14 price records for this district — guaranteed non-404.",
)
def get_commodities_for_district(district: str) -> list[str]:
    """List commodity slugs that will return a valid forecast for this district."""
    return list_slugs_for_district(district)


@router.get(
    "/model-health",
    summary="Model health dashboard",
    description=(
        "Returns quality metrics for all trained models: R², tier, MAPE, "
        "interval calibration coverage, and staleness flags."
    ),
)
def model_health() -> dict:
    """Return health metrics for all trained models."""
    from app.ml.loader_7d import load_7d_meta

    results = []

    # v5 7-day models (preferred)
    for slug in list_7d_slugs():
        meta = load_7d_meta(slug)
        if not meta:
            continue
        results.append({
            "commodity": slug,
            "model_version": "v5",
            "tier": "v5-7day",
            "test_mape_h1": meta.get("test_mape_h1"),
            "test_mape_h7": meta.get("test_mape_h7"),
            "test_r2_h7": meta.get("test_r2_h7"),
            "n_districts": meta.get("n_districts"),
            "last_data_date": meta.get("last_data_date"),
            "trained_at": meta.get("trained_at"),
            "needs_retrain": False,
        })

    v5_slugs = {r["commodity"] for r in results}

    # Legacy models (for commodities not yet in v5)
    for slug in list_commodity_slugs():
        if slug in v5_slugs:
            continue
        meta = load_meta(slug)
        if not meta:
            continue
        results.append({
            "commodity": slug,
            "model_version": "v3/v4",
            "r2_score": meta.get("r2_score"),
            "tier": meta.get("tier", "unknown"),
            "strategy": meta.get("strategy", "unknown"),
            "prophet_mape": meta.get("prophet_mape"),
            "n_districts": meta.get("n_districts"),
            "last_data_date": meta.get("last_data_date"),
            "trained_at": meta.get("trained_at"),
            "needs_retrain": _needs_retrain(meta),
        })

    v5_count = sum(1 for r in results if r.get("model_version") == "v5")
    legacy_count = len(results) - v5_count

    return {
        "models": results,
        "total": len(results),
        "v5_count": v5_count,
        "legacy_count": legacy_count,
        "needs_retrain": sum(1 for r in results if r.get("needs_retrain")),
    }


@router.get(
    "/states/{commodity}",
    response_model=list[str],
    summary="List states with v5 data for a commodity",
    description="Returns sorted list of state names that have price history for this commodity in the v5 model.",
)
def get_states_for_commodity_route(commodity: str) -> list[str]:
    """States that have v5 data for this commodity."""
    if not is_good_7d_slug(commodity):
        raise HTTPException(status_code=404, detail=f"No v5 model for '{commodity}'.")
    return get_states_for_commodity(commodity)


@router.get(
    "/districts/{commodity}/{state}",
    response_model=list[str],
    summary="List districts with v5 data for a commodity+state",
    description="Returns sorted district names in *state* that have price history for this commodity.",
)
def get_districts_for_commodity_state_route(commodity: str, state: str) -> list[str]:
    """Districts in *state* that have v5 data for this commodity."""
    if not is_good_7d_slug(commodity):
        raise HTTPException(status_code=404, detail=f"No v5 model for '{commodity}'.")
    return get_districts_for_commodity_state(commodity, state)


@router.get(
    "/{commodity}/{district}",
    response_model=ForecastResponse,
    summary="Price Forecast",
    description="Returns a 7-day price forecast from a quality-gated v5 LightGBM model (MAPE < 25%).",
)
def get_forecast(
    commodity: str,
    district: str,
    horizon: int = Query(
        default=7,
        ge=7,
        le=7,
        description="Always 7 days — v5 models are direct 7-step models.",
    ),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    """Get a 7-day price forecast for a commodity-district pair.

    Only serves commodities with a quality v5 model (MAPE h7 < 25%).
    Returns 404 for commodities not in the quality set.
    """
    if not is_good_7d_slug(commodity):
        raise HTTPException(
            status_code=404,
            detail=f"No reliable forecast available for '{commodity}'. "
                   "This commodity either has no v5 model or exceeds the 25% MAPE quality threshold.",
        )

    svc7 = ForecastService7D(db)
    result = svc7.get_forecast(commodity, district)
    if result is not None:
        return result

    # v5 service couldn't build a forecast for this district (not enough recent
    # price data). Fall back to the legacy v4 seasonal service.
    logger.info(
        "v5 service returned None for %s/%s — falling back to legacy v4 service",
        commodity, district,
    )
    svc_legacy = ForecastService(db)
    return svc_legacy.get_forecast(commodity, district, horizon=7)
