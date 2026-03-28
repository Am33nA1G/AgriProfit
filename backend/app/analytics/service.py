from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models import (
    Commodity,
    Mandi,
    PriceHistory,
    PriceForecast,
    CommunityPost,
    User,
    Notification,
)
from app.analytics.schemas import (
    PriceTrendResponse,
    PriceTrendListResponse,
    PriceStatisticsResponse,
    MarketSummaryResponse,
    UserActivityResponse,
    TopCommodityItem,
    TopMandiItem,
    MandiPriceItem,
    CommodityPriceComparisonResponse,
    MandiPerformanceResponse,
    DashboardResponse,
)


class AnalyticsService:
    """Service class for analytics operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_price_trends(
        self,
        commodity_id: UUID,
        mandi_id: UUID | None = None,
        days: int = 30,
    ) -> list[PriceTrendResponse]:
        """Get price trends with commodity and mandi names."""
        start_date = date.today() - timedelta(days=days)

        query = self.db.query(
            PriceHistory.commodity_id,
            Commodity.name.label("commodity_name"),
            PriceHistory.mandi_id,
            Mandi.name.label("mandi_name"),
            PriceHistory.price_date,
            PriceHistory.modal_price.label("price"),
        ).join(
            Commodity, PriceHistory.commodity_id == Commodity.id
        ).join(
            Mandi, PriceHistory.mandi_id == Mandi.id
        ).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date >= start_date,
        )

        if mandi_id:
            query = query.filter(PriceHistory.mandi_id == mandi_id)

        results = query.order_by(PriceHistory.price_date.asc()).all()

        return [
            PriceTrendResponse(
                commodity_id=row.commodity_id,
                commodity_name=row.commodity_name,
                mandi_id=row.mandi_id,
                mandi_name=row.mandi_name,
                price_date=row.price_date,
                modal_price=row.price,
            )
            for row in results
        ]

    def get_price_trends_list(
        self,
        commodity_id: UUID,
        mandi_id: UUID,
        days: int = 30,
    ) -> PriceTrendListResponse:
        """Get price trends with metadata."""
        start_date = date.today() - timedelta(days=days)
        end_date = date.today()

        items = self.get_price_trends(
            commodity_id=commodity_id,
            mandi_id=mandi_id,
            days=days,
        )

        return PriceTrendListResponse(
            items=items,
            commodity_id=commodity_id,
            mandi_id=mandi_id,
            start_date=start_date,
            end_date=end_date,
            data_points=len(items),
        )

    def get_price_statistics(
        self,
        commodity_id: UUID,
        mandi_id: UUID | None = None,
        days: int = 30,
    ) -> PriceStatisticsResponse | None:
        """Calculate price statistics for a commodity."""
        start_date = date.today() - timedelta(days=days)

        query = self.db.query(
            PriceHistory.commodity_id,
            Commodity.name.label("commodity_name"),
            func.avg(PriceHistory.modal_price).label("avg_price"),
            func.min(PriceHistory.modal_price).label("min_price"),
            func.max(PriceHistory.modal_price).label("max_price"),
            func.count(PriceHistory.id).label("data_points"),
        ).join(
            Commodity, PriceHistory.commodity_id == Commodity.id
        ).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date >= start_date,
        )

        if mandi_id:
            query = query.join(
                Mandi, PriceHistory.mandi_id == Mandi.id
            ).filter(PriceHistory.mandi_id == mandi_id)
            query = query.group_by(
                PriceHistory.commodity_id,
                Commodity.name,
                PriceHistory.mandi_id,
                Mandi.name,
            )
            query = query.add_columns(
                PriceHistory.mandi_id,
                Mandi.name.label("mandi_name"),
            )
        else:
            query = query.group_by(PriceHistory.commodity_id, Commodity.name)

        result = query.first()

        if not result or result.data_points == 0:
            return None

        # Calculate price change percentage
        price_change_percent = self._calculate_price_change(
            commodity_id=commodity_id,
            mandi_id=mandi_id,
            days=days,
        )

        return PriceStatisticsResponse(
            commodity_id=result.commodity_id,
            commodity_name=result.commodity_name,
            mandi_id=mandi_id,  # Keep as None if not provided
            mandi_name=getattr(result, "mandi_name", None),
            avg_price=round(float(result.avg_price), 2),
            min_price=round(float(result.min_price), 2),
            max_price=round(float(result.max_price), 2),
            price_change_percent=price_change_percent,
            data_points=result.data_points,
            start_date=start_date,
            end_date=date.today(),
        )

    def _calculate_price_change(
        self,
        commodity_id: UUID,
        mandi_id: UUID | None = None,
        days: int = 30,
    ) -> float:
        """Calculate percentage price change from first to last price."""
        start_date = date.today() - timedelta(days=days)

        query = self.db.query(PriceHistory).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date >= start_date,
        )

        if mandi_id:
            query = query.filter(PriceHistory.mandi_id == mandi_id)

        # Get first and last prices
        first_record = query.order_by(PriceHistory.price_date.asc()).first()
        last_record = query.order_by(PriceHistory.price_date.desc()).first()

        if not first_record or not last_record or first_record.modal_price == 0:
            return 0.0

        first_price = float(first_record.modal_price)
        last_price = float(last_record.modal_price)

        price_change = ((last_price - first_price) / first_price) * 100
        return round(price_change, 2)

    def get_market_summary(self) -> MarketSummaryResponse:
        """Get overall market summary statistics."""
        from sqlalchemy import text

        try:
            # PostgreSQL-optimised: approximate row count via pg_class for the 25M-row table
            query = text("""
                SELECT
                    (SELECT COUNT(*) FROM commodities) as total_commodities,
                    (SELECT COUNT(*) FROM mandis) as total_mandis,
                    (SELECT GREATEST(reltuples::bigint, 0) FROM pg_class
                     WHERE relname = 'price_history') as total_price_records,
                    (SELECT COUNT(*) FROM price_forecasts
                     WHERE forecast_date >= CURRENT_DATE) as total_forecasts,
                    (SELECT COUNT(*) FROM community_posts
                     WHERE deleted_at IS NULL) as total_posts,
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT MAX(price_date) FROM price_history) as last_updated
            """)
            result = self.db.execute(query).fetchone()
            total_commodities = result[0] or 0
            total_mandis = result[1] or 0
            total_price_records = result[2] or 0
            total_forecasts = result[3] or 0
            total_posts = result[4] or 0
            total_users = result[5] or 0
            last_updated_raw = result[6]
        except Exception:
            # SQLite-compatible fallback (used in tests)
            from datetime import date as date_type
            total_commodities = self.db.query(func.count(Commodity.id)).scalar() or 0
            total_mandis = self.db.query(func.count(Mandi.id)).scalar() or 0
            total_price_records = self.db.query(func.count(PriceHistory.id)).scalar() or 0
            total_forecasts = self.db.query(func.count(PriceForecast.id)).filter(
                PriceForecast.forecast_date >= date_type.today()
            ).scalar() or 0
            total_posts = self.db.query(func.count(CommunityPost.id)).filter(
                CommunityPost.deleted_at.is_(None)
            ).scalar() or 0
            total_users = self.db.query(func.count(User.id)).scalar() or 0
            last_updated_raw = self.db.query(func.max(PriceHistory.price_date)).scalar()

        if last_updated_raw is None:
            last_updated = datetime.now(timezone.utc)
        elif isinstance(last_updated_raw, date) and not isinstance(last_updated_raw, datetime):
            # Convert date to datetime at midnight UTC
            last_updated = datetime.combine(last_updated_raw, datetime.min.time(), tzinfo=timezone.utc)
        elif last_updated_raw.tzinfo is None:
            last_updated = last_updated_raw.replace(tzinfo=timezone.utc)
        else:
            last_updated = last_updated_raw

        # Calculate data freshness
        now = datetime.now(timezone.utc)
        hours_since_update = (now - last_updated).total_seconds() / 3600
        data_is_stale = hours_since_update > 24

        return MarketSummaryResponse(
            total_commodities=total_commodities,
            total_mandis=total_mandis,
            total_price_records=total_price_records,
            total_forecasts=total_forecasts,
            total_posts=total_posts,
            total_users=total_users,
            last_updated=last_updated,
            data_is_stale=data_is_stale,
            hours_since_update=round(hours_since_update, 1),
        )


    def get_top_commodities_by_price_change(
        self,
        limit: int = 10,
        days: int = 30,
    ) -> list[TopCommodityItem]:
        """Get commodities with highest price change percentage.

        Uses aggregate MIN/MAX on price_date per commodity to find first/last
        prices, then joins back to get actual prices. Avoids expensive window
        functions over millions of rows.
        """
        from sqlalchemy import text

        start_date = date.today() - timedelta(days=days)

        # Use MIN/MAX per commodity to get first/last prices — works on both
        # PostgreSQL and SQLite (avoids DISTINCT ON which is PG-specific).
        query = text("""
            WITH date_bounds AS (
                SELECT
                    commodity_id,
                    MIN(price_date) AS first_date,
                    MAX(price_date) AS last_date,
                    COUNT(*) AS record_count
                FROM price_history
                WHERE price_date >= :start_date
                GROUP BY commodity_id
                HAVING COUNT(*) >= 2
                   AND MIN(price_date) != MAX(price_date)
            ),
            first_prices AS (
                SELECT ph.commodity_id, MIN(ph.modal_price) AS first_price
                FROM price_history ph
                JOIN date_bounds db ON db.commodity_id = ph.commodity_id
                    AND ph.price_date = db.first_date
                GROUP BY ph.commodity_id
            ),
            last_prices AS (
                SELECT ph.commodity_id, MIN(ph.modal_price) AS last_price
                FROM price_history ph
                JOIN date_bounds db ON db.commodity_id = ph.commodity_id
                    AND ph.price_date = db.last_date
                GROUP BY ph.commodity_id
            )
            SELECT
                db.commodity_id,
                c.name,
                db.record_count,
                CASE WHEN fp.first_price > 0
                    THEN ABS(((lp.last_price - fp.first_price) / fp.first_price) * 100)
                    ELSE 0
                END AS price_change
            FROM date_bounds db
            JOIN commodities c ON c.id = db.commodity_id
            JOIN first_prices fp ON fp.commodity_id = db.commodity_id
            JOIN last_prices lp ON lp.commodity_id = db.commodity_id
            ORDER BY price_change DESC
            LIMIT :limit
        """)

        rows = self.db.execute(query, {
            "start_date": start_date,
            "limit": limit,
        }).fetchall()

        return [
            TopCommodityItem(
                commodity_id=row.commodity_id,
                name=row.name,
                record_count=row.record_count,
            )
            for row in rows
        ]

    def get_top_mandis_by_records(self, limit: int = 10) -> list[TopMandiItem]:
        """Get mandis with most price records (last 30 days)."""
        cutoff = date.today() - timedelta(days=30)
        results = self.db.query(
            Mandi.id.label("mandi_id"),
            Mandi.name,
            func.count(PriceHistory.id).label("record_count"),
        ).join(
            PriceHistory, PriceHistory.mandi_id == Mandi.id
        ).filter(
            PriceHistory.price_date >= cutoff
        ).group_by(
            Mandi.id, Mandi.name
        ).order_by(
            desc("record_count")
        ).limit(limit).all()

        return [
            TopMandiItem(
                mandi_id=row.mandi_id,
                name=row.name,
                record_count=row.record_count,
            )
            for row in results
        ]

    def get_user_activity(self, user_id: UUID) -> UserActivityResponse | None:
        """Get user activity summary."""
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            return None

        # Count posts (non-deleted)
        posts_count = self.db.query(func.count(CommunityPost.id)).filter(
            CommunityPost.user_id == user_id,
            CommunityPost.deleted_at.is_(None),
        ).scalar() or 0

        # Count notifications
        notifications_count = self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
        ).scalar() or 0

        # Get last activity (most recent post or notification)
        last_post = self.db.query(CommunityPost.created_at).filter(
            CommunityPost.user_id == user_id,
            CommunityPost.deleted_at.is_(None),
        ).order_by(CommunityPost.created_at.desc()).first()

        last_notification = self.db.query(Notification.created_at).filter(
            Notification.user_id == user_id,
        ).order_by(Notification.created_at.desc()).first()

        last_active = None
        if last_post and last_notification:
            last_active = max(last_post[0], last_notification[0])
        elif last_post:
            last_active = last_post[0]
        elif last_notification:
            last_active = last_notification[0]

        return UserActivityResponse(
            user_id=user.id,
            username=getattr(user, 'name', None),
            phone=user.phone_number,
            posts_count=posts_count,
            notifications_count=notifications_count,
            last_active=last_active,
        )

    def get_commodity_price_comparison(
        self,
        commodity_id: UUID,
    ) -> CommodityPriceComparisonResponse | None:
        """Compare prices for a commodity across all mandis.

        OPTIMIZED: Single query using DISTINCT ON to get latest price
        per mandi plus average, instead of N+1 queries.
        """
        from sqlalchemy import text

        commodity = self.db.query(Commodity).filter(Commodity.id == commodity_id).first()

        if not commodity:
            return None

        query = text("""
            WITH latest_prices AS (
                SELECT DISTINCT ON (ph.mandi_id)
                    m.id AS mandi_id,
                    m.name AS mandi_name,
                    ph.modal_price AS current_price
                FROM price_history ph
                JOIN mandis m ON m.id = ph.mandi_id
                WHERE ph.commodity_id = :commodity_id
                ORDER BY ph.mandi_id, ph.price_date DESC
            ),
            avg_prices AS (
                SELECT
                    ph.mandi_id,
                    AVG(ph.modal_price) AS avg_price
                FROM price_history ph
                WHERE ph.commodity_id = :commodity_id
                GROUP BY ph.mandi_id
            )
            SELECT
                lp.mandi_id,
                lp.mandi_name,
                lp.current_price,
                ap.avg_price
            FROM latest_prices lp
            JOIN avg_prices ap ON ap.mandi_id = lp.mandi_id
        """)

        rows = self.db.execute(query, {"commodity_id": commodity_id}).fetchall()

        if not rows:
            return None

        mandi_prices = [
            MandiPriceItem(
                mandi_id=row.mandi_id,
                mandi_name=row.mandi_name,
                current_price=round(float(row.current_price), 2),
                avg_price=round(float(row.avg_price), 2),
            )
            for row in rows
        ]

        # Find lowest and highest
        lowest = min(mandi_prices, key=lambda x: x.current_price)
        highest = max(mandi_prices, key=lambda x: x.current_price)
        price_spread = highest.current_price - lowest.current_price

        return CommodityPriceComparisonResponse(
            commodity_id=commodity_id,
            commodity_name=commodity.name,
            mandi_prices=mandi_prices,
            lowest_price_mandi=lowest.mandi_name,
            highest_price_mandi=highest.mandi_name,
            price_spread=round(price_spread, 2),
        )

    def get_weekly_price_trends(self) -> list:
        """Get average prices for the last 7 days that have data for dashboard chart."""
        from datetime import datetime

        # Restrict to last 30 days to avoid scanning all 25M rows
        cutoff = date.today() - timedelta(days=30)
        dates_with_data = self.db.query(
            PriceHistory.price_date,
            func.avg(PriceHistory.modal_price).label('avg_price')
        ).filter(
            PriceHistory.price_date >= cutoff
        ).group_by(
            PriceHistory.price_date
        ).order_by(
            PriceHistory.price_date.desc()
        ).limit(7).all()
        
        # Reverse to get chronological order
        dates_with_data = list(reversed(dates_with_data))
        
        day_names = ["M", "T", "W", "T", "F", "S", "S"]
        weekly_data = []
        
        for date_record in dates_with_data:
            target_date = date_record.price_date
            avg_price = date_record.avg_price
            
            # Convert to quintal if needed (prices < 200 are in kg)
            if avg_price and avg_price < 200:
                avg_price = avg_price * 100
            
            weekly_data.append({
                "day": day_names[target_date.weekday()],
                "date": str(target_date),
                "value": round(float(avg_price), 2) if avg_price else 0
            })
        
        return weekly_data

    def get_dashboard(self) -> DashboardResponse:
        """Get combined dashboard data (OPTIMIZED)."""
        market_summary = self.get_market_summary()  # Now optimized to 1 query
        top_commodities = self.get_top_commodities_by_price_change(limit=5, days=7)
        top_mandis = self.get_top_mandis_by_records(limit=5)
        weekly_trends = self.get_weekly_price_trends()

        # REMOVED: Expensive loop that was calling get_price_statistics() 5 times
        # This was causing 5-10 additional database queries and 2-5s delay
        # The dashboard already shows top_commodities which provides similar info
        
        return DashboardResponse(
            market_summary=market_summary,
            recent_price_changes=[],  # Empty - removed for performance
            top_commodities=top_commodities,
            top_mandis=top_mandis,
            weekly_trends=weekly_trends,
        )