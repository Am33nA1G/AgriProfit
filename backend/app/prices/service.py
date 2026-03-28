from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import PriceHistory
from app.prices.schemas import PriceHistoryCreate, PriceHistoryUpdate


class PriceHistoryService:
    """Service class for PriceHistory operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, price_data: PriceHistoryCreate) -> PriceHistory:
        """Create a new price history record."""
        try:
            price = PriceHistory(
                commodity_id=price_data.commodity_id,
                mandi_id=price_data.mandi_id,
                price_date=price_data.price_date,
                min_price=price_data.min_price,
                max_price=price_data.max_price,
                modal_price=price_data.modal_price,
            )
            self.db.add(price)
            self.db.commit()
            self.db.refresh(price)
            return price
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Price record for this commodity, mandi, and date already exists") from e
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, price_id: UUID) -> PriceHistory | None:
        """Get a single price history record by ID."""
        return self.db.query(PriceHistory).filter(PriceHistory.id == price_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        commodity_id: UUID | None = None,
        mandi_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PriceHistory]:
        """Get price history records with optional filtering."""
        query = self.db.query(PriceHistory)

        if commodity_id:
            query = query.filter(PriceHistory.commodity_id == commodity_id)

        if mandi_id:
            query = query.filter(PriceHistory.mandi_id == mandi_id)

        if start_date:
            query = query.filter(PriceHistory.price_date >= start_date)

        if end_date:
            query = query.filter(PriceHistory.price_date <= end_date)

        return query.order_by(PriceHistory.price_date.desc()).offset(skip).limit(limit).all()

    def get_latest(self, commodity_id: UUID, mandi_id: UUID) -> PriceHistory | None:
        """Get the latest price record for a commodity at a mandi."""
        return self.db.query(PriceHistory).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.mandi_id == mandi_id,
        ).order_by(PriceHistory.price_date.desc()).first()

    def get_by_commodity(
        self,
        commodity_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[PriceHistory]:
        """Get all price records for a specific commodity."""
        query = self.db.query(PriceHistory).filter(PriceHistory.commodity_id == commodity_id)

        if start_date:
            query = query.filter(PriceHistory.price_date >= start_date)

        if end_date:
            query = query.filter(PriceHistory.price_date <= end_date)

        return query.order_by(PriceHistory.price_date.desc()).limit(limit).all()

    def get_by_mandi(
        self,
        mandi_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[PriceHistory]:
        """Get all price records for a specific mandi."""
        query = self.db.query(PriceHistory).filter(PriceHistory.mandi_id == mandi_id)

        if start_date:
            query = query.filter(PriceHistory.price_date >= start_date)

        if end_date:
            query = query.filter(PriceHistory.price_date <= end_date)

        return query.order_by(PriceHistory.price_date.desc()).limit(limit).all()

    def get_on_date(
        self,
        commodity_id: UUID,
        mandi_id: UUID,
        price_date: date,
    ) -> PriceHistory | None:
        """Get price record for a specific commodity, mandi, and date."""
        return self.db.query(PriceHistory).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.mandi_id == mandi_id,
            PriceHistory.price_date == price_date,
        ).first()

    def update(self, price_id: UUID, price_data: PriceHistoryUpdate) -> PriceHistory | None:
        """Update an existing price history record."""
        price = self.db.query(PriceHistory).filter(PriceHistory.id == price_id).first()

        if not price:
            return None

        update_data = price_data.model_dump(exclude_unset=True)

        if not update_data:
            return price

        try:
            for field, value in update_data.items():
                setattr(price, field, value)

            self.db.commit()
            self.db.refresh(price)
            return price
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError("Price record for this commodity, mandi, and date already exists") from e
        except Exception:
            self.db.rollback()
            raise

    def delete(self, price_id: UUID) -> bool:
        """Hard delete a price history record."""
        price = self.db.query(PriceHistory).filter(PriceHistory.id == price_id).first()

        if not price:
            return False

        try:
            self.db.delete(price)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def count(
        self,
        commodity_id: UUID | None = None,
        mandi_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """Count price history records with optional filtering."""
        query = self.db.query(PriceHistory)

        if commodity_id:
            query = query.filter(PriceHistory.commodity_id == commodity_id)

        if mandi_id:
            query = query.filter(PriceHistory.mandi_id == mandi_id)

        if start_date:
            query = query.filter(PriceHistory.price_date >= start_date)

        if end_date:
            query = query.filter(PriceHistory.price_date <= end_date)

        return query.count()

    def get_current_prices_list(
        self,
        commodity: str | None = None,
        state: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """Get latest prices with commodity and mandi details and price changes.

        Uses DISTINCT ON to get the latest price per commodity+mandi pair,
        then a second lookup for previous price. Restricted to last 7 days
        to avoid scanning the full 25M-row table.
        """
        from sqlalchemy import text

        # Build dynamic WHERE clauses
        conditions = []
        params: dict = {"limit": limit}
        if commodity:
            conditions.append("c.name ILIKE :commodity")
            params["commodity"] = f"%{commodity}%"
        if state and state.lower() != "all":
            conditions.append("m.state ILIKE :state")
            params["state"] = f"%{state}%"

        where_clause = (" AND " + " AND ".join(conditions)) if conditions else ""

        # Use DISTINCT ON to get the latest price per commodity+mandi,
        # then a lateral subquery for the previous price. Only scan last 14 days.
        query = text(f"""
            WITH latest AS (
                SELECT DISTINCT ON (ph.commodity_id, ph.mandi_id)
                    ph.id,
                    ph.commodity_id,
                    ph.mandi_id,
                    ph.modal_price AS price,
                    ph.min_price,
                    ph.max_price,
                    ph.price_date,
                    ph.created_at AS updated_at
                FROM price_history ph
                WHERE ph.price_date >= CURRENT_DATE - INTERVAL '14 days'
                  AND ph.mandi_id IS NOT NULL
                ORDER BY ph.commodity_id, ph.mandi_id, ph.price_date DESC
            )
            SELECT
                l.id,
                c.name AS commodity,
                l.commodity_id,
                m.name AS mandi_name,
                l.mandi_id,
                m.state,
                m.district,
                l.price,
                l.min_price,
                l.max_price,
                l.price_date,
                l.updated_at,
                prev.modal_price AS prev_price,
                avg_7d.avg_price AS avg_7d_price,
                range_30d.min_price_30d,
                range_30d.max_price_30d
            FROM latest l
            JOIN commodities c ON c.id = l.commodity_id
            JOIN mandis m ON m.id = l.mandi_id
            LEFT JOIN LATERAL (
                SELECT ph2.modal_price
                FROM price_history ph2
                WHERE ph2.commodity_id = l.commodity_id
                  AND ph2.mandi_id = l.mandi_id
                  AND ph2.price_date < l.price_date
                  AND ph2.price_date >= l.price_date - INTERVAL '7 days'
                ORDER BY ph2.price_date DESC
                LIMIT 1
            ) prev ON true
            LEFT JOIN LATERAL (
                SELECT AVG(ph3.modal_price) AS avg_price
                FROM price_history ph3
                WHERE ph3.commodity_id = l.commodity_id
                  AND ph3.mandi_id = l.mandi_id
                  AND ph3.price_date >= l.price_date - INTERVAL '7 days'
                  AND ph3.price_date <= l.price_date
            ) avg_7d ON true
            LEFT JOIN LATERAL (
                SELECT 
                    MIN(ph4.modal_price) AS min_price_30d,
                    MAX(ph4.modal_price) AS max_price_30d
                FROM price_history ph4
                WHERE ph4.commodity_id = l.commodity_id
                  AND ph4.mandi_id = l.mandi_id
                  AND ph4.price_date >= l.price_date - INTERVAL '30 days'
                  AND ph4.price_date <= l.price_date
            ) range_30d ON true
            WHERE 1=1 {where_clause}
            ORDER BY l.price_date DESC
            LIMIT :limit
        """)

        results = self.db.execute(query, params).fetchall()

        price_data = []
        for r in results:
            # Prices are in ₹ per quintal (100 kg) as received from data.gov.in
            price = float(r.price)
            current_price = price

            # Calculate price range
            min_price = float(r.min_price) if r.min_price else current_price
            min_price_adj = min_price
            max_price = float(r.max_price) if r.max_price else current_price
            max_price_adj = max_price

            # Calculate 7-day average
            avg_7d = None
            if r.avg_7d_price is not None:
                avg_raw = float(r.avg_7d_price)
                avg_7d = avg_raw

            # Calculate 30-day range
            min_30d = None
            max_30d = None
            if r.min_price_30d is not None:
                min_raw = float(r.min_price_30d)
                min_30d = min_raw
            if r.max_price_30d is not None:
                max_raw = float(r.max_price_30d)
                max_30d = max_raw

            # Calculate trend vs 7-day average
            trend = "stable"
            if avg_7d and avg_7d > 0:
                diff_percent = ((current_price - avg_7d) / avg_7d) * 100
                if diff_percent > 3:
                    trend = "up"
                elif diff_percent < -3:
                    trend = "down"

            change_percent = 0.0
            change_amount = 0.0

            if r.prev_price is not None:
                prev_raw = float(r.prev_price)
                prev_price = prev_raw
                if prev_price > 0:
                    change_amount = current_price - prev_price
                    change_percent = (change_amount / prev_price) * 100

            price_data.append({
                "id": r.id,
                "commodity_id": r.commodity_id,
                "commodity": r.commodity,
                "mandi_name": r.mandi_name,
                "state": r.state,
                "district": r.district,
                "price_per_quintal": round(current_price, 2),
                "min_price": round(min_price_adj, 2),
                "max_price": round(max_price_adj, 2),
                "avg_7d": round(avg_7d, 2) if avg_7d else None,
                "min_30d": round(min_30d, 2) if min_30d else None,
                "max_30d": round(max_30d, 2) if max_30d else None,
                "trend": trend,
                "change_percent": round(change_percent, 2),
                "change_amount": round(change_amount, 2),
                "updated_at": r.updated_at
            })

        return price_data

    def get_historical_prices(
        self,
        commodity: str,
        mandi_id: str = "all",
        days: int = 30
    ) -> list[dict]:
        """Get historical price trend with unit-aware normalization and outlier detection."""
        from app.models import Commodity
        from sqlalchemy import func
        from datetime import datetime, timedelta

        start_date = datetime.now().date() - timedelta(days=days)
        
        # Get commodity to check unit
        commodity_obj = self.db.query(Commodity).filter(
            Commodity.name.ilike(f"%{commodity}%")
        ).first()
        
        # Get raw price data
        query = (
            self.db.query(
                PriceHistory.price_date,
                PriceHistory.modal_price,
                PriceHistory.mandi_name
            )
            .join(Commodity, PriceHistory.commodity_id == Commodity.id)
            .filter(
                Commodity.name.ilike(f"%{commodity}%"),
                PriceHistory.price_date >= start_date,
                PriceHistory.modal_price.isnot(None),
                PriceHistory.modal_price > 0  # Filter out invalid prices
            )
        )

        if mandi_id and mandi_id.lower() != "all":
            try:
                mandi_uuid = UUID(mandi_id)
                query = query.filter(PriceHistory.mandi_id == mandi_uuid)
            except ValueError:
                pass # Ignore invalid UUID if not "all"

        # Get all matching records
        records = query.order_by(PriceHistory.price_date.asc()).all()
        
        # Normalize prices with outlier detection
        normalized_data = {}
        for record in records:
            date_key = record.price_date
            # Prices are in per quintal
            price = float(record.modal_price)
            
            # Group by date and calculate average
            if date_key not in normalized_data:
                normalized_data[date_key] = []
            normalized_data[date_key].append(price)
        
        # Calculate daily averages
        return [
            {
                "date": date,
                "price": round(sum(prices) / len(prices), 2)
            }
            for date, prices in sorted(normalized_data.items())
        ]

    def get_top_movers(self, limit: int = 5) -> dict:
        """Get top gainers and losers based on ACTUAL price change from recent data."""
        from datetime import date, timedelta
        from sqlalchemy import text
        
        # Calculate average prices for today and 7 days ago (to have more stable comparison)
        query = text("""
            WITH recent_prices AS (
                SELECT 
                    c.id as commodity_id,
                    c.name as commodity,
                    ph.price_date,
                    AVG(ph.modal_price) as avg_price
                FROM price_history ph
                JOIN commodities c ON c.id = ph.commodity_id
                WHERE ph.price_date >= CURRENT_DATE - INTERVAL '14 days'
                  AND ph.modal_price IS NOT NULL
                GROUP BY c.id, c.name, ph.price_date
            ),
            latest_avg AS (
                SELECT 
                    commodity_id,
                    commodity,
                    AVG(avg_price) as current_price
                FROM recent_prices
                WHERE price_date >= CURRENT_DATE - INTERVAL '3 days'
                GROUP BY commodity_id, commodity
                HAVING COUNT(*) >= 1
            ),
            previous_avg AS (
                SELECT 
                    commodity_id,
                    commodity,
                    AVG(avg_price) as previous_price
                FROM recent_prices
                WHERE price_date >= CURRENT_DATE - INTERVAL '14 days'
                  AND price_date < CURRENT_DATE - INTERVAL '7 days'
                GROUP BY commodity_id, commodity
                HAVING COUNT(*) >= 1
            )
            SELECT 
                l.commodity,
                l.current_price,
                p.previous_price,
                CASE 
                    WHEN p.previous_price > 0 THEN
                        ROUND(((l.current_price - p.previous_price) / p.previous_price * 100)::numeric, 2)
                    ELSE 0
                END as change_percent
            FROM latest_avg l
            INNER JOIN previous_avg p ON l.commodity_id = p.commodity_id
            WHERE p.previous_price > 0
            ORDER BY change_percent DESC
        """)
        
        results = self.db.execute(query).fetchall()
        
        movers = []
        for r in results:
            # Prices are in per quintal
            price = float(r.current_price)
            
            movers.append({
                "commodity": r.commodity,
                "price": round(price, 2),
                "change_percent": float(r.change_percent)
            })
        
        # Split into positive and negative changes
        gainers = [m for m in movers if m["change_percent"] > 0]
        losers = [m for m in movers if m["change_percent"] < 0]
        
        # Sort for consistent ordering
        gainers.sort(key=lambda x: x["change_percent"], reverse=True)
        losers.sort(key=lambda x: x["change_percent"])
        
        return {
            "gainers": gainers[:limit],  # Top gainers with highest positive changes
            "losers": losers[:limit]  # Top losers with most negative changes
        }