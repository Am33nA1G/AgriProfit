"""
FastAPI routes for the Seasonal Price Calendar.

GET /api/v1/seasonal?commodity=X&state=Y
  → returns monthly price statistics from the seasonal_price_stats table.
"""
import calendar

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.seasonal.schemas import MonthlyStatPoint, SeasonalCalendarResponse


router = APIRouter(prefix="/seasonal", tags=["Seasonal"])


@router.get(
    "/commodities",
    response_model=list[str],
    summary="List commodities with seasonal data",
)
def list_seasonal_commodities(db: Session = Depends(get_db)):
    """Return sorted distinct commodity names that have seasonal price stats."""
    rows = db.execute(text(
        "SELECT DISTINCT commodity_name FROM seasonal_price_stats ORDER BY commodity_name"
    )).fetchall()
    return [r.commodity_name for r in rows]


@router.get(
    "/states",
    response_model=list[str],
    summary="List states with seasonal data",
)
def list_seasonal_states(db: Session = Depends(get_db)):
    """Return sorted distinct state names that have seasonal price stats."""
    rows = db.execute(text(
        "SELECT DISTINCT state_name FROM seasonal_price_stats ORDER BY state_name"
    )).fetchall()
    return [r.state_name for r in rows]


@router.get(
    "",
    response_model=SeasonalCalendarResponse,
    summary="Get seasonal price calendar",
    description=(
        "Returns monthly median price and IQR for a commodity in a given state, "
        "computed from up to 10 years of historical Agmarknet data. "
        "Includes best/worst month indicators and a low-confidence warning "
        "when fewer than 3 years of data are available."
    ),
)
def get_seasonal_calendar(
    commodity: str = Query(..., description="Commodity name (e.g. 'Onion')"),
    state: str = Query(..., description="State name (e.g. 'Maharashtra')"),
    db: Session = Depends(get_db),
):
    """
    Query seasonal_price_stats for the given commodity+state.
    Returns 404 if no data exists for the combination.
    """
    rows = db.execute(
        text("""
            SELECT month, median_price, q1_price, q3_price, iqr_price,
                   record_count, years_of_data, month_rank, is_best, is_worst
            FROM seasonal_price_stats
            WHERE LOWER(commodity_name) = LOWER(:commodity)
              AND LOWER(state_name) = LOWER(:state)
            ORDER BY month
        """),
        {"commodity": commodity, "state": state},
    ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No seasonal data found for commodity='{commodity}', state='{state}'. "
                "This combination may not exist in our dataset, or the aggregation "
                "pipeline has not been run yet."
            ),
        )

    # Determine confidence level from the data
    max_years = max(r.years_of_data for r in rows)

    months = []
    for r in rows:
        months.append(MonthlyStatPoint(
            month=r.month,
            month_name=calendar.month_abbr[r.month],
            median_price=float(r.median_price),
            q1_price=float(r.q1_price),
            q3_price=float(r.q3_price),
            iqr_price=float(r.iqr_price),
            record_count=r.record_count,
            years_of_data=r.years_of_data,
            month_rank=r.month_rank,
            is_best=r.is_best,
            is_worst=r.is_worst,
        ))

    return SeasonalCalendarResponse(
        commodity=commodity,
        state=state,
        total_years=max_years,
        low_confidence=max_years < 3,
        months=months,
    )
