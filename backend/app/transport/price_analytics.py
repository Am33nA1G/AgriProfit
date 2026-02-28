"""
Price credibility analytics — 7-day volatility, trend, and confidence scoring.

Query pulls at most 7 rows per mandi×commodity. Safe on 25M-row price_history.
"""
from __future__ import annotations
import statistics
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

HIGH_VOLATILITY_THRESHOLD: float = 8.0
STALE_PRICE_DAYS: int = 3
TREND_UP_THRESHOLD: float = 1.03
TREND_DOWN_THRESHOLD: float = 0.97
CONFIDENCE_PENALTY_VOLATILE: int = 20
CONFIDENCE_PENALTY_STALE: int = 15
CONFIDENCE_PENALTY_THIN: int = 25
CONFIDENCE_FLOOR: int = 10


@dataclass
class PriceAnalytics:
    volatility_pct: float
    price_trend: str
    confidence_score: int
    n_records: int
    latest_price_date: date | None


def compute_price_analytics(
    commodity_id: str,
    mandi_name: str,
    db: Session,
) -> PriceAnalytics:
    """Compute 7-day price volatility, trend, and confidence for a mandi×commodity pair."""
    query = text("""
        SELECT modal_price, price_date
        FROM price_history
        WHERE commodity_id = CAST(:cid AS UUID)
          AND mandi_name = :mandi
        ORDER BY price_date DESC
        LIMIT 7
    """)
    try:
        rows = db.execute(query, {"cid": str(commodity_id), "mandi": mandi_name}).fetchall()
    except Exception:
        rows = []

    if not rows:
        return PriceAnalytics(
            volatility_pct=0.0,
            price_trend="stable",
            confidence_score=CONFIDENCE_FLOOR,
            n_records=0,
            latest_price_date=None,
        )

    prices = [float(r.modal_price) for r in rows]
    dates = [r.price_date for r in rows]
    latest_date = dates[0] if dates else None
    latest_price = prices[0]
    mean_price = statistics.mean(prices)

    volatility_pct = 0.0
    if len(prices) >= 2 and mean_price > 0:
        volatility_pct = (statistics.stdev(prices) / mean_price) * 100

    price_trend = "stable"
    if mean_price > 0:
        ratio = latest_price / mean_price
        if ratio >= TREND_UP_THRESHOLD:
            price_trend = "rising"
        elif ratio <= TREND_DOWN_THRESHOLD:
            price_trend = "falling"

    confidence = 100
    if volatility_pct > HIGH_VOLATILITY_THRESHOLD:
        confidence -= CONFIDENCE_PENALTY_VOLATILE
    if latest_date and (date.today() - latest_date).days > STALE_PRICE_DAYS:
        confidence -= CONFIDENCE_PENALTY_STALE
    if len(prices) == 1:
        confidence -= CONFIDENCE_PENALTY_THIN
    confidence = max(CONFIDENCE_FLOOR, confidence)

    return PriceAnalytics(
        volatility_pct=round(volatility_pct, 2),
        price_trend=price_trend,
        confidence_score=confidence,
        n_records=len(prices),
        latest_price_date=latest_date,
    )
