"""
Arbitrage service: freshness gate, margin threshold, top-3 ranking.

Public API: get_arbitrage_results(commodity, district, db) -> ArbitrageResponse

Key design decisions:
- data_reference_date = MAX(latest_price_date) across returned mandis, NEVER date.today()
- Stale mandis (days_since_update > 7) are INCLUDED in results with is_stale=True — not dropped
- Margin threshold filters: (net_profit / gross_revenue) * 100 >= settings.arbitrage_margin_threshold_pct
- freight_cost_per_quintal = costs.total_cost directly, because compare_mandis() is called with
  quantity_kg=100 (1 quintal), so costs.total_cost IS the per-quintal cost already
- net_profit_per_quintal = profit_per_kg * 100 (profit_per_kg is already per-kg from transport service)
- Results sorted by net_profit_per_quintal descending, hard-limited to top 3
"""
import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.arbitrage.schemas import ArbitrageResponse, ArbitrageResult
from app.core.config import settings
from app.transport.schemas import TransportCompareRequest
from app.transport.service import compare_mandis

logger = logging.getLogger(__name__)

# Normalisation quantity for per-quintal calculations
_QUINTAL_KG = 100.0


def get_arbitrage_results(
    commodity: str,
    district: str,
    db: Session,
    max_distance_km: float | None = None,
) -> ArbitrageResponse:
    """
    Return top-3 destination mandis ranked by net profit per quintal.

    Steps:
    1. Call compare_mandis() with quantity_kg=100 (1 quintal normalisation)
    2. Determine data_reference_date = MAX(latest_price_date) across returned mandis
       (falls back to DB query if all price dates are None)
    3. Compute freshness: mandis older than (ref_date - 7 days) get is_stale=True
    4. Apply margin threshold: suppress mandis where (net_profit/gross_revenue)*100 < threshold
    5. Sort passing mandis by net_profit_per_quintal descending; take top 3
    6. Return ArbitrageResponse
    """
    # --- Step 1: fetch candidates via transport service ---
    request = TransportCompareRequest(
        commodity=commodity,
        quantity_kg=_QUINTAL_KG,
        source_district=district,
        source_state="Unknown",
        limit=50,
        max_distance_km=max_distance_km,
    )
    comparisons, has_estimated = compare_mandis(request, db)

    # --- Step 2: determine data_reference_date ---
    known_dates = [
        c.latest_price_date
        for c in comparisons
        if c.latest_price_date is not None
    ]

    if known_dates:
        data_reference_date = max(known_dates)
    else:
        # Fallback: query DB for MAX(price_date) for this commodity
        data_reference_date = _query_max_price_date(commodity, db)

    freshness_cutoff = data_reference_date - timedelta(days=7)

    # --- Steps 3-4: freshness annotation + margin filter ---
    passing: list[ArbitrageResult] = []
    suppressed_count = 0

    for comp in comparisons:
        # Freshness
        if comp.latest_price_date is not None:
            days_since = (data_reference_date - comp.latest_price_date).days
        else:
            days_since = 999  # unknown date — treat as maximally stale

        is_stale = days_since > 7
        stale_warning = (
            f"Data last updated {comp.latest_price_date} — signal may be outdated"
            if is_stale
            else None
        )

        # Margin threshold
        margin_pct = (
            (comp.net_profit / comp.gross_revenue) * 100
            if comp.gross_revenue > 0
            else 0.0
        )
        if margin_pct < settings.arbitrage_margin_threshold_pct:
            suppressed_count += 1
            continue

        # Per-quintal financial figures
        # costs.total_cost is the TOTAL cost for the 100 kg shipment (quantity_kg=100),
        # so it equals the per-quintal cost directly — no division needed.
        freight_cost_per_quintal = round(comp.costs.total_cost, 2)
        net_profit_per_quintal = round(comp.profit_per_kg * _QUINTAL_KG, 2)

        # Use data_reference_date as fallback when price_date is unknown
        price_date = comp.latest_price_date if comp.latest_price_date is not None else data_reference_date

        passing.append(
            ArbitrageResult(
                mandi_name=comp.mandi_name,
                district=comp.district,
                state=comp.state,
                distance_km=comp.distance_km,
                travel_time_hours=comp.travel_time_hours,
                is_interstate=comp.is_interstate,
                freight_cost_per_quintal=freight_cost_per_quintal,
                spoilage_percent=comp.spoilage_percent,
                net_profit_per_quintal=net_profit_per_quintal,
                verdict=comp.verdict,
                price_date=price_date,
                days_since_update=days_since,
                is_stale=is_stale,
                stale_warning=stale_warning,
            )
        )

    # --- Step 5: sort + top-3 ---
    passing.sort(key=lambda r: r.net_profit_per_quintal, reverse=True)
    top3 = passing[:3]

    # --- Step 6: build response ---
    has_stale_data = any(r.is_stale for r in top3)
    distance_note = (
        "Some distances are estimated (haversine × 1.35) — road routing unavailable"
        if has_estimated
        else None
    )

    return ArbitrageResponse(
        commodity=commodity,
        origin_district=district,
        results=top3,
        suppressed_count=suppressed_count,
        threshold_pct=settings.arbitrage_margin_threshold_pct,
        data_reference_date=data_reference_date,
        has_stale_data=has_stale_data,
        distance_note=distance_note,
    )


def _query_max_price_date(commodity: str, db: Session) -> date:
    """
    Query MAX(price_date) from price_history for this commodity.
    Falls back to today's date if DB query fails or returns nothing.
    """
    try:
        row = db.execute(
            text("""
                SELECT MAX(ph.price_date)
                FROM price_history ph
                JOIN commodities c ON c.id = ph.commodity_id
                WHERE c.name ILIKE :commodity
            """),
            {"commodity": commodity},
        ).scalar()
        if row:
            return row if isinstance(row, date) else row.date()
    except Exception as exc:
        logger.warning("Failed to query max price_date for %s: %s", commodity, exc)

    # Absolute fallback — should rarely happen in production
    from datetime import date as _date_cls
    return _date_cls.today()
