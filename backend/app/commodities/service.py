from uuid import UUID
from datetime import datetime, timedelta
import time

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from app.models import Commodity
from app.models.price_history import PriceHistory
from app.models.mandi import Mandi
from app.commodities.schemas import CommodityCreate, CommodityUpdate

# Cache for batch price lookups (cache for 30 seconds)
_price_cache = {"data": None, "timestamp": 0}
_CACHE_TTL = 120  # seconds (2 minutes - prices don't change more frequently)


class CommodityService:
    """Service class for Commodity operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, commodity_id: UUID) -> Commodity | None:
        """Get a commodity by ID."""
        return self.db.query(Commodity).filter(
            Commodity.id == commodity_id,
        ).first()

    def get_by_name(self, name: str) -> Commodity | None:
        """Get a commodity by name."""
        return self.db.query(Commodity).filter(
            Commodity.name == name,
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        category: str | None = None,
    ) -> list[Commodity]:
        """Get all commodities with pagination and optional filtering."""
        query = self.db.query(Commodity).filter(Commodity.is_active == True)
        if category:
            query = query.filter(Commodity.category == category)
        return query.order_by(Commodity.name).offset(skip).limit(limit).all()

    def get_all_with_prices(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        categories: list[str] | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        trend: str | None = None,  # "rising", "falling", "stable"
        in_season: bool | None = None,
        sort_by: str = "name",  # "name", "price", "change"
        sort_order: str = "asc",
    ) -> dict:
        """Get all commodities with price data and advanced filtering."""
        
        query = self.db.query(Commodity).filter(Commodity.is_active == True)
        
        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Commodity.name.ilike(search_term)) |
                (Commodity.name_local.ilike(search_term)) |
                (Commodity.description.ilike(search_term))
            )
        
        # Category filter
        if categories and len(categories) > 0:
            query = query.filter(Commodity.category.in_(categories))
        
        # Season filter
        if in_season:
            current_month = datetime.now().month
            query = query.filter(
                (Commodity.peak_season_start.isnot(None)) &
                (Commodity.peak_season_end.isnot(None)) &
                (
                    # Handle normal seasons (e.g., 3-8)
                    ((Commodity.peak_season_start <= Commodity.peak_season_end) &
                     (Commodity.peak_season_start <= current_month) &
                     (Commodity.peak_season_end >= current_month)) |
                    # Handle wrap-around seasons (e.g., 11-2)
                    ((Commodity.peak_season_start > Commodity.peak_season_end) &
                     ((current_month >= Commodity.peak_season_start) |
                      (current_month <= Commodity.peak_season_end)))
                )
            )
        
        # Get total count before pagination
        total = query.count()
        
        # BATCH PRICE LOOKUP from PostgreSQL (uses fresh synced data)
        # Must be done BEFORE pagination when sorting by price/change
        all_prices = self._get_commodity_prices_from_db()
        
        # For price/change sorting, we need to fetch ALL commodities, enrich with prices, then paginate
        # For name/category sorting, we can paginate first (more efficient)
        if sort_by in ["price", "change"]:
            # Get ALL commodities (no pagination yet)
            commodities = query.all()
        else:
            # Sorting by name/category - can paginate first
            if sort_by == "name":
                query = query.order_by(asc(Commodity.name) if sort_order == "asc" else desc(Commodity.name))
            elif sort_by == "category":
                query = query.order_by(asc(Commodity.category) if sort_order == "asc" else desc(Commodity.category))
            
            commodities = query.offset(skip).limit(limit).all()
        
        # Enrich with price data
        result_commodities = []
        for commodity in commodities:
            # Get price data from batch lookup
            price_data = all_prices.get(commodity.name.lower(), {})
            current_price = price_data.get('price')
            change_1d = price_data.get('change_1d')
            change_7d = price_data.get('change_7d')
            change_30d = price_data.get('change_30d')
            
            # Apply price range filter
            if min_price is not None and current_price is not None and current_price < min_price:
                total -= 1
                continue
            if max_price is not None and current_price is not None and current_price > max_price:
                total -= 1
                continue
            
            # Apply trend filter
            if trend:
                if trend == "rising" and (change_7d is None or change_7d <= 0.5):
                    total -= 1
                    continue
                elif trend == "falling" and (change_7d is None or change_7d >= -0.5):
                    total -= 1
                    continue
                elif trend == "stable" and (change_7d is None or abs(change_7d) > 0.5):
                    total -= 1
                    continue

            result_commodities.append({
                "id": str(commodity.id),
                "name": commodity.name,
                "name_local": commodity.name_local,
                "category": commodity.category,
                "unit": commodity.unit,
                "description": commodity.description,
                "current_price": current_price,
                "last_updated": None,  # Skip expensive query
                "price_change_1d": change_1d,
                "price_change_7d": change_7d,
                "price_change_30d": change_30d,
                "is_in_season": self.is_in_season(commodity),
                "peak_season": f"{commodity.peak_season_start}-{commodity.peak_season_end}" if commodity.peak_season_start else None,
                "major_states": commodity.major_producing_states,
            })
        
        # Sort by price or change if requested
        if sort_by == "price" and result_commodities:
            result_commodities.sort(
                key=lambda x: x["current_price"] if x["current_price"] else 0,
                reverse=(sort_order == "desc")
            )
            # Apply pagination AFTER sorting
            result_commodities = result_commodities[skip:skip + limit]
        elif sort_by == "change" and result_commodities:
            # Sort by 1-day change to show most recent movers
            result_commodities.sort(
                key=lambda x: x["price_change_1d"] if x["price_change_1d"] else 0,
                reverse=(sort_order == "desc")
            )
            # Apply pagination AFTER sorting
            result_commodities = result_commodities[skip:skip + limit]
        
        return {
            "commodities": result_commodities,
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "limit": limit,
            "has_more": (skip + len(result_commodities)) < total,
        }

    def get_current_price(self, commodity_id: UUID) -> float | None:
        """Get the national average current price for a commodity."""
        # Get average of most recent prices across all mandis
        subquery = self.db.query(
            PriceHistory.mandi_name,
            func.max(PriceHistory.price_date).label("max_date")
        ).filter(
            PriceHistory.commodity_id == commodity_id
        ).group_by(PriceHistory.mandi_name).subquery()

        avg_price = self.db.query(func.avg(PriceHistory.modal_price)).join(
            subquery,
            (PriceHistory.mandi_name == subquery.c.mandi_name) &
            (PriceHistory.price_date == subquery.c.max_date)
        ).filter(
            PriceHistory.commodity_id == commodity_id
        ).scalar()

        return float(avg_price) if avg_price else None

    def calculate_price_change(self, commodity_id: UUID, days: int = 1) -> float | None:
        """Calculate price change percentage over last N days."""
        current_price = self.get_current_price(commodity_id)
        if not current_price:
            return None

        # Use a 3-day window around the target date for data availability
        past_date = datetime.now().date() - timedelta(days=days)

        past_price = self.db.query(func.avg(PriceHistory.modal_price)).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date >= past_date - timedelta(days=3),
            PriceHistory.price_date <= past_date,
        ).scalar()

        if not past_price or past_price == 0:
            return None

        change_pct = ((current_price - float(past_price)) / float(past_price)) * 100
        return round(change_pct, 2)

    def is_in_season(self, commodity: Commodity) -> bool:
        """Check if commodity is currently in peak season."""
        if not commodity.peak_season_start or not commodity.peak_season_end:
            return False
        
        current_month = datetime.now().month
        
        # Handle wrap-around seasons (e.g., Nov-Feb = 11,12,1,2)
        if commodity.peak_season_start <= commodity.peak_season_end:
            return commodity.peak_season_start <= current_month <= commodity.peak_season_end
        else:
            return current_month >= commodity.peak_season_start or current_month <= commodity.peak_season_end

    def _normalize_price(self, price: float) -> float:
        """Return prices in per quintal.

        Data from data.gov.in is stored in per quintal (100 kg).
        """
        return round(price, 2)

    def get_details(self, commodity_id: UUID) -> dict | None:
        """Get detailed information about a commodity with price history and mandi data."""
        commodity = self.get_by_id(commodity_id)
        if not commodity:
            return None

        # Use batch DB lookup for current price + short-term changes (cached)
        all_prices = self._get_commodity_prices_from_db()
        price_data = all_prices.get(commodity.name.lower(), {})
        current_price = price_data.get('price') or self.get_current_price(commodity_id)
        change_1d = price_data.get('change_1d')
        change_7d = price_data.get('change_7d')
        change_30d = price_data.get('change_30d')
        change_90d = self.calculate_price_change(commodity_id, 90)

        # Price history from database (last 365 days, grouped by date)
        price_history = self.db.query(
            PriceHistory.price_date,
            func.avg(PriceHistory.modal_price).label("avg_price")
        ).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date >= datetime.now().date() - timedelta(days=365)
        ).group_by(
            PriceHistory.price_date
        ).order_by(
            PriceHistory.price_date
        ).all()

        # Top 5 mandis by price (highest paying, last 30 days)
        top_mandis = self.db.query(
            PriceHistory.mandi_name,
            Mandi.state,
            Mandi.district,
            PriceHistory.modal_price,
            PriceHistory.price_date
        ).outerjoin(
            Mandi, PriceHistory.mandi_id == Mandi.id
        ).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date >= datetime.now().date() - timedelta(days=30)
        ).order_by(
            desc(PriceHistory.modal_price)
        ).limit(5).all()

        # Bottom 5 mandis by price (lowest paying, last 30 days)
        bottom_mandis = self.db.query(
            PriceHistory.mandi_name,
            Mandi.state,
            Mandi.district,
            PriceHistory.modal_price,
            PriceHistory.price_date
        ).outerjoin(
            Mandi, PriceHistory.mandi_id == Mandi.id
        ).filter(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date >= datetime.now().date() - timedelta(days=30)
        ).order_by(
            asc(PriceHistory.modal_price)
        ).limit(5).all()

        return {
            "id": str(commodity.id),
            "name": commodity.name,
            "name_local": commodity.name_local,
            "category": commodity.category,
            "unit": commodity.unit,
            "description": commodity.description,
            "current_price": current_price,
            "price_changes": {
                "1d": change_1d,
                "7d": change_7d,
                "30d": change_30d,
                "90d": change_90d,
            },
            "seasonal_info": {
                "is_in_season": self.is_in_season(commodity),
                "growing_months": commodity.growing_months,
                "harvest_months": commodity.harvest_months,
                "peak_season_start": commodity.peak_season_start,
                "peak_season_end": commodity.peak_season_end,
            },
            "major_producing_states": commodity.major_producing_states,
            "price_history": [
                {
                    "date": str(p.price_date),
                    "price": self._normalize_price(float(p.avg_price))
                }
                for p in price_history if p.avg_price is not None
            ],
            "top_mandis": [
                {
                    "name": m.mandi_name,
                    "state": m.state,
                    "district": m.district,
                    "price": self._normalize_price(float(m.modal_price)),
                    "as_of": str(m.price_date),
                }
                for m in top_mandis
            ],
            "bottom_mandis": [
                {
                    "name": m.mandi_name,
                    "state": m.state,
                    "district": m.district,
                    "price": self._normalize_price(float(m.modal_price)),
                    "as_of": str(m.price_date),
                }
                for m in bottom_mandis
            ],
        }

    def get_categories(self) -> list[str]:
        """Get all unique commodity categories."""
        categories = self.db.query(Commodity.category).filter(
            Commodity.is_active == True,
            Commodity.category.isnot(None)
        ).distinct().order_by(Commodity.category).all()
        return [c[0] for c in categories if c[0]]

    def compare(self, commodity_ids: list[UUID]) -> dict:
        """Compare multiple commodities side by side."""
        commodities_data = []
        
        for commodity_id in commodity_ids[:5]:  # Max 5 commodities
            details = self.get_details(commodity_id)
            if details:
                commodities_data.append(details)
        
        return {
            "commodities": commodities_data,
            "comparison_date": datetime.now().isoformat(),
        }

    def search(self, query: str, limit: int = 10) -> list[Commodity]:
        """Search commodities by name."""
        # Escape SQL LIKE wildcards to prevent injection
        escaped_query = query.replace('%', r'\%').replace('_', r'\_')
        return self.db.query(Commodity).filter(
            Commodity.is_active == True,
            Commodity.name.ilike(f"%{escaped_query}%", escape='\\'),
        ).order_by(Commodity.name).limit(limit).all()

    def create(self, commodity_data: CommodityCreate) -> Commodity:
        """Create a new commodity."""
        # Check for duplicate name
        existing = self.get_by_name(commodity_data.name)
        if existing:
            raise ValueError(f"Commodity with name '{commodity_data.name}' already exists")

        try:
            commodity = Commodity(
                name=commodity_data.name,
                name_local=commodity_data.name_local,
                category=commodity_data.category,
                unit=commodity_data.unit,
            )
            self.db.add(commodity)
            self.db.commit()
            self.db.refresh(commodity)
            return commodity
        except Exception:
            self.db.rollback()
            raise

    def update(self, commodity_id: UUID, commodity_data: CommodityUpdate) -> Commodity | None:
        """Update an existing commodity."""
        commodity = self.get_by_id(commodity_id)
        if not commodity:
            return None

        update_data = commodity_data.model_dump(exclude_unset=True)

        if not update_data:
            return commodity

        # Check for duplicate name if name is being updated
        if "name" in update_data:
            existing = self.get_by_name(update_data["name"])
            if existing and existing.id != commodity_id:
                raise ValueError(f"Commodity with name '{update_data['name']}' already exists")

        try:
            for field, value in update_data.items():
                setattr(commodity, field, value)
            self.db.commit()
            self.db.refresh(commodity)
            return commodity
        except Exception:
            self.db.rollback()
            raise

    def delete(self, commodity_id: UUID) -> bool:
        """Delete a commodity."""
        commodity = self.get_by_id(commodity_id)
        if not commodity:
            return False

        try:
            self.db.delete(commodity)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def count(self, category: str | None = None) -> int:
        """Count total commodities with optional category filter."""
        query = self.db.query(Commodity).filter(Commodity.is_active == True)
        if category:
            query = query.filter(Commodity.category == category)
        return query.count()

    def _get_commodity_prices_from_db(self) -> dict:
        """
        Get current prices and changes for ALL commodities from PostgreSQL.
        Returns: dict {commodity_name_lower: {price, change_1d, change_7d, change_30d}}

        OPTIMIZED: Single query with date-range aggregation instead of 4N queries.
        Cached for 30 seconds to avoid expensive queries on every request.
        """
        global _price_cache

        # Check cache
        current_time = time.time()
        if _price_cache["data"] is not None and (current_time - _price_cache["timestamp"]) < _CACHE_TTL:
            return _price_cache["data"]

        from datetime import date, timedelta
        from sqlalchemy import text

        # Use the latest date with actual data instead of today
        # (data may lag by a day or more)
        latest_date_row = self.db.execute(
            text("SELECT MAX(price_date) FROM price_history")
        ).scalar()
        latest = latest_date_row if latest_date_row else date.today()

        date_1d = latest - timedelta(days=1)
        date_1d_start = date_1d - timedelta(days=2)
        date_7d = latest - timedelta(days=7)
        date_7d_start = date_7d - timedelta(days=2)
        date_30d = latest - timedelta(days=30)
        date_30d_start = date_30d - timedelta(days=2)

        # Single query: get avg prices for latest date and historical windows
        query = text("""
            SELECT
                c.id,
                c.name,
                AVG(CASE WHEN ph.price_date = :latest THEN ph.modal_price END) AS price_today,
                AVG(CASE WHEN ph.price_date >= :d1_start AND ph.price_date <= :d1_end THEN ph.modal_price END) AS price_1d,
                AVG(CASE WHEN ph.price_date >= :d7_start AND ph.price_date <= :d7_end THEN ph.modal_price END) AS price_7d,
                AVG(CASE WHEN ph.price_date >= :d30_start AND ph.price_date <= :d30_end THEN ph.modal_price END) AS price_30d
            FROM commodities c
            JOIN price_history ph ON ph.commodity_id = c.id
            WHERE c.is_active = true
              AND ph.price_date >= :d30_start
            GROUP BY c.id, c.name
            HAVING AVG(CASE WHEN ph.price_date = :latest THEN ph.modal_price END) IS NOT NULL
               AND AVG(CASE WHEN ph.price_date = :latest THEN ph.modal_price END) > 0
        """)

        rows = self.db.execute(query, {
            "latest": latest,
            "d1_start": date_1d_start, "d1_end": date_1d,
            "d7_start": date_7d_start, "d7_end": date_7d,
            "d30_start": date_30d_start, "d30_end": date_30d,
        }).fetchall()

        result = {}
        for row in rows:
            current_price = float(row.price_today)

            # Apply unit conversion (prices < 200 are in kg, convert to quintal)
            if current_price < 200:
                current_price = current_price * 100

            def _calc_change(hist_price_raw):
                if hist_price_raw is None or hist_price_raw <= 0:
                    return None
                hist_price = float(hist_price_raw)
                if hist_price < 200:
                    hist_price = hist_price * 100
                if hist_price > 0:
                    return round(((current_price - hist_price) / hist_price) * 100, 2)
                return None

            result[row.name.lower()] = {
                'price': current_price,
                'change_1d': _calc_change(row.price_1d),
                'change_7d': _calc_change(row.price_7d),
                'change_30d': _calc_change(row.price_30d),
            }

        # Update cache
        _price_cache["data"] = result
        _price_cache["timestamp"] = time.time()

        return result
