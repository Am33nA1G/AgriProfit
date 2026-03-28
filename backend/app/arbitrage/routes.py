"""
Arbitrage API routes.

GET /arbitrage/{commodity}/{district}
  → ArbitrageResponse with top-3 mandis ranked by net_profit_per_quintal.

IMPORTANT: Handler is def (not async def) — OSRM routing calls block the event loop.
FastAPI runs synchronous route handlers in a thread pool, preventing starvation.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.arbitrage.schemas import ArbitrageResponse
from app.arbitrage.service import get_arbitrage_results

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arbitrage", tags=["Arbitrage"])


@router.get(
    "/commodities",
    response_model=list[str],
    summary="List commodities available for arbitrage",
    description="Returns distinct commodity names that have price history data, sorted alphabetically.",
)
def list_arbitrage_commodities(db: Session = Depends(get_db)):
    """Return sorted distinct commodity names that have price history records."""
    from sqlalchemy import text as _text
    rows = db.execute(_text(
        """
        SELECT DISTINCT c.name
        FROM commodities c
        INNER JOIN price_history ph ON ph.commodity_id = c.id
        WHERE ph.modal_price > 0
        ORDER BY c.name
        """
    )).fetchall()
    return [r.name for r in rows]


@router.get(
    "/states",
    response_model=list[str],
    summary="List states available for arbitrage",
    description="Returns distinct state names from mandis that have price history data, sorted alphabetically.",
)
def list_arbitrage_states(db: Session = Depends(get_db)):
    """Return sorted distinct state names from mandis with price data."""
    from sqlalchemy import text as _text
    rows = db.execute(_text(
        """
        SELECT DISTINCT m.state
        FROM mandis m
        INNER JOIN price_history ph ON ph.mandi_id = m.id
        WHERE m.state IS NOT NULL
          AND ph.modal_price > 0
        ORDER BY m.state
        """
    )).fetchall()
    return [r.state for r in rows]


@router.get(
    "/districts",
    response_model=list[str],
    summary="List districts in a state for arbitrage",
    description="Returns distinct district names within a given state from mandis that have price history data, sorted alphabetically.",
)
def list_arbitrage_districts(
    state: str = Query(..., description="State name to filter districts by"),
    db: Session = Depends(get_db),
):
    """Return sorted distinct district names from mandis in the given state with price data."""
    from sqlalchemy import text as _text
    rows = db.execute(_text(
        """
        SELECT DISTINCT m.district
        FROM mandis m
        INNER JOIN price_history ph ON ph.mandi_id = m.id
        WHERE m.state ILIKE :state
          AND m.district IS NOT NULL
          AND ph.modal_price > 0
        ORDER BY m.district
        """
    ), {"state": state}).fetchall()
    return [r.district for r in rows]


@router.get(
    "/{commodity}/{district}",
    response_model=ArbitrageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Mandi Arbitrage Signals",
    description=(
        "Returns top 3 destination mandis ranked by net profit per quintal after freight and spoilage. "
        "Only shows results where net margin exceeds the configurable threshold (default 10%). "
        "Price freshness is relative to the dataset's MAX(price_date) — not today's date. "
        "Stale results (data older than 7 days from reference date) are included with is_stale=True."
    ),
)
def get_arbitrage_signals(   # MUST be def, not async def — OSRM calls block event loop
    commodity: str,
    district: str,
    max_distance_km: float | None = Query(default=None, gt=0, le=1000, description="Optional maximum distance filter (km)"),
    db: Session = Depends(get_db),
) -> ArbitrageResponse:
    """
    Fetch arbitrage signals for a commodity from the given origin district.

    Args:
        commodity: Commodity name (case-insensitive, e.g. "Wheat")
        district: Farmer's source district (e.g. "Ernakulam")
        max_distance_km: Optional distance filter; only mandis within this range are considered
        db: Database session (injected)

    Returns:
        ArbitrageResponse with up to 3 destination mandis and suppression metadata

    Raises:
        404: Commodity not found in the database
        400: Cannot resolve coordinates for the given district
        500: Unexpected internal error
    """
    try:
        return get_arbitrage_results(
            commodity=commodity,
            district=district,
            db=db,
            max_distance_km=max_distance_km,
        )
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        # Other ValueError: typically coordinate resolution failure
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error in arbitrage endpoint: commodity=%s district=%s",
            commodity,
            district,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while computing arbitrage signals",
        ) from exc
