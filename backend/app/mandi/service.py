from uuid import UUID
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, desc, asc, distinct

from app.models import Mandi
from app.models.price_history import PriceHistory
from app.models.commodity import Commodity
from app.mandi.schemas import MandiCreate, MandiUpdate


class MandiService:
    """Service class for Mandi operations."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two lat/lon points in kilometers using Haversine formula."""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c

    def get_by_id(self, mandi_id: UUID) -> Mandi | None:
        """Get a mandi by ID."""
        return self.db.query(Mandi).filter(
            Mandi.id == mandi_id,
            Mandi.is_active == True,
        ).first()

    def get_by_market_code(self, market_code: str) -> Mandi | None:
        """Get a mandi by market code."""
        return self.db.query(Mandi).filter(
            Mandi.market_code == market_code.upper(),
            Mandi.is_active == True,
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        state: str | None = None,
        district: str | None = None,
        is_active: bool | None = None,
        include_inactive: bool = False,
    ) -> list[Mandi]:
        """Get all mandis with optional filtering."""
        query = self.db.query(Mandi)

        # Handle is_active filter
        if is_active is not None:
            query = query.filter(Mandi.is_active == is_active)
        elif not include_inactive:
            query = query.filter(Mandi.is_active == True)

        if state:
            query = query.filter(Mandi.state == state)

        if district:
            # Case-insensitive matching for district
            query = query.filter(Mandi.district.ilike(district.strip()))

        return query.order_by(Mandi.name).offset(skip).limit(limit).all()

    def _build_mandi_dict(self, mandi, distance, top_prices):
        """Convert a Mandi ORM object to a response dictionary."""
        return {
            "id": str(mandi.id),
            "name": mandi.name,
            "state": mandi.state,
            "district": mandi.district,
            "address": mandi.address,
            "market_code": mandi.market_code,
            "latitude": mandi.latitude,
            "longitude": mandi.longitude,
            "pincode": mandi.pincode,
            "phone": mandi.phone,
            "email": mandi.email,
            "website": mandi.website,
            "opening_time": str(mandi.opening_time) if mandi.opening_time else None,
            "closing_time": str(mandi.closing_time) if mandi.closing_time else None,
            "operating_days": mandi.operating_days,
            "facilities": {
                "weighbridge": mandi.has_weighbridge,
                "storage": mandi.has_storage,
                "loading_dock": mandi.has_loading_dock,
                "cold_storage": mandi.has_cold_storage,
            },
            "payment_methods": mandi.payment_methods,
            "commodities_accepted": mandi.commodities_accepted,
            "rating": mandi.rating,
            "total_reviews": mandi.total_reviews,
            "distance_km": distance,
            "top_prices": top_prices,
        }

    def _resolve_user_coordinates(self, user_lat, user_lon, user_district, user_state):
        """Resolve user coordinates from district/state if not provided directly."""
        if user_district and user_state and not (user_lat and user_lon):
            from app.integrations.district_geocodes import get_district_geocode
            coords = get_district_geocode(user_district, user_state)
            if coords:
                return coords[0], coords[1]
        return user_lat, user_lon

    def get_all_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        states: list[str] | None = None,
        district: str | None = None,
        commodity: str | None = None,
        max_distance_km: float | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        user_district: str | None = None,
        user_state: str | None = None,
        has_facility: str | None = None,  # "weighbridge", "storage", "loading_dock", "cold_storage"
        min_rating: float | None = None,
        sort_by: str = "name",  # "name", "distance", "rating"
        sort_order: str = "asc",
    ) -> dict:
        """Get all mandis with advanced filtering and distance from user."""

        # Resolve user coordinates from district/state if not provided
        user_lat, user_lon = self._resolve_user_coordinates(
            user_lat, user_lon, user_district, user_state
        )

        query = self.db.query(Mandi).filter(Mandi.is_active == True)

        # Search filter — search by name, district, state, address, or market code
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Mandi.name.ilike(search_term)) |
                (Mandi.district.ilike(search_term)) |
                (Mandi.state.ilike(search_term)) |
                (Mandi.address.ilike(search_term)) |
                (Mandi.market_code.ilike(search_term))
            )

        # State filter
        if states and len(states) > 0:
            query = query.filter(Mandi.state.in_(states))

        # District filter
        if district:
            query = query.filter(Mandi.district.ilike(f"%{district}%"))

        # Commodity filter
        if commodity:
            query = query.filter(
                Mandi.commodities_accepted.any(commodity)
            )

        # Facility filters
        if has_facility:
            facility_map = {
                "weighbridge": Mandi.has_weighbridge,
                "storage": Mandi.has_storage,
                "loading_dock": Mandi.has_loading_dock,
                "cold_storage": Mandi.has_cold_storage,
            }
            facility_col = facility_map.get(has_facility)
            if facility_col is not None:
                query = query.filter(facility_col == True)

        # Rating filter
        if min_rating is not None:
            query = query.filter(Mandi.rating >= min_rating)

        # Determine if we need distance-based processing
        needs_distance = (sort_by == "distance" or max_distance_km is not None) and \
                         user_lat is not None and user_lon is not None

        if needs_distance:
            # For distance sort/filter: fetch ALL matching mandis, calculate distances,
            # filter by max_distance, sort by distance, then paginate in Python.
            # This ensures correct sorting across the entire result set.
            all_mandis = query.all()

            # Calculate distances and filter
            mandis_with_distance = []
            for mandi in all_mandis:
                distance = None
                if mandi.latitude and mandi.longitude:
                    distance = round(self.haversine_distance(
                        user_lat, user_lon, mandi.latitude, mandi.longitude
                    ), 2)

                    # Apply max distance filter
                    if max_distance_km is not None and distance > max_distance_km:
                        continue
                else:
                    # Mandis without coordinates — skip if filtering by distance
                    if max_distance_km is not None:
                        continue

                mandis_with_distance.append((mandi, distance))

            # Sort by distance
            if sort_by == "distance":
                mandis_with_distance.sort(
                    key=lambda x: x[1] if x[1] is not None else float('inf'),
                    reverse=(sort_order == "desc")
                )
            else:
                # Non-distance sort with distance filter applied
                if sort_by == "name":
                    mandis_with_distance.sort(
                        key=lambda x: (x[0].name or "").lower(),
                        reverse=(sort_order == "desc")
                    )
                elif sort_by == "rating":
                    mandis_with_distance.sort(
                        key=lambda x: x[0].rating if x[0].rating is not None else 0,
                        reverse=(sort_order != "asc")
                    )

            total = len(mandis_with_distance)

            # Apply pagination
            paginated = mandis_with_distance[skip:skip + limit]

            # Batch fetch top prices
            mandi_ids = [m.id for m, _ in paginated]
            batch_top_prices = self.get_batch_top_prices(mandi_ids, limit_per_mandi=3)

            # Build result
            result_mandis = []
            for mandi, distance in paginated:
                top_prices = batch_top_prices.get(mandi.id, [])
                result_mandis.append(self._build_mandi_dict(mandi, distance, top_prices))
        else:
            # Standard path: SQL-level sorting and pagination (efficient)
            total = query.count()

            # Sorting
            if sort_by == "name":
                query = query.order_by(asc(Mandi.name) if sort_order == "asc" else desc(Mandi.name))
            elif sort_by == "rating":
                query = query.order_by(
                    (desc(Mandi.rating) if sort_order == "desc" else asc(Mandi.rating)),
                    asc(Mandi.name)  # Secondary sort by name for consistency
                )
            elif sort_by == "state":
                query = query.order_by(asc(Mandi.state) if sort_order == "asc" else desc(Mandi.state))

            # Get paginated mandis
            mandis = query.offset(skip).limit(limit).all()

            # Batch fetch top prices
            mandi_ids = [mandi.id for mandi in mandis]
            batch_top_prices = self.get_batch_top_prices(mandi_ids, limit_per_mandi=3)

            # Build result with optional distance calculation
            result_mandis = []
            for mandi in mandis:
                distance = None
                if user_lat is not None and user_lon is not None and mandi.latitude and mandi.longitude:
                    distance = round(self.haversine_distance(
                        user_lat, user_lon, mandi.latitude, mandi.longitude
                    ), 2)

                top_prices = batch_top_prices.get(mandi.id, [])
                result_mandis.append(self._build_mandi_dict(mandi, distance, top_prices))

        return {
            "mandis": result_mandis,
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "limit": limit,
            "has_more": (skip + limit) < total,
        }

    def get_mandi_top_prices(self, mandi_id: UUID, limit: int = 5) -> list[dict]:
        """Get top commodity prices at a specific mandi."""
        # CRITICAL: Add date bounds to avoid full table scan on 25M+ row price_history
        date_cutoff = (datetime.now().date() - timedelta(days=14))

        # Get most recent price for each commodity at this mandi
        subquery = self.db.query(
            PriceHistory.commodity_id,
            func.max(PriceHistory.price_date).label("max_date")
        ).filter(
            PriceHistory.mandi_id == mandi_id,
            PriceHistory.price_date >= date_cutoff
        ).group_by(PriceHistory.commodity_id).subquery()

        prices = self.db.query(
            PriceHistory.commodity_id,
            Commodity.name.label("commodity_name"),
            Commodity.unit.label("unit"),
            PriceHistory.modal_price,
            PriceHistory.min_price,
            PriceHistory.max_price,
            PriceHistory.price_date
        ).join(
            subquery,
            (PriceHistory.commodity_id == subquery.c.commodity_id) &
            (PriceHistory.price_date == subquery.c.max_date)
        ).join(
            Commodity, PriceHistory.commodity_id == Commodity.id
        ).filter(
            PriceHistory.mandi_id == mandi_id
        ).order_by(
            desc(PriceHistory.modal_price)
        ).limit(limit).all()
        
        return [
            {
                "commodity_id": str(p.commodity_id),
                "commodity_name": p.commodity_name,
                "unit": "quintal",
                "modal_price": round(float(p.modal_price), 2),
                "min_price": round(float(p.min_price), 2) if p.min_price else None,
                "max_price": round(float(p.max_price), 2) if p.max_price else None,
                "as_of": str(p.price_date),
            }
            for p in prices
        ]

    def get_batch_top_prices(self, mandi_ids: list[UUID], limit_per_mandi: int = 3) -> dict[UUID, list[dict]]:
        """Get top commodity prices for multiple mandis in a single query (OPTIMIZED).

        Uses DISTINCT ON for efficient latest-per-group lookups with date bounds
        to avoid full table scans on price_history (25M+ rows).

        Args:
            mandi_ids: List of mandi UUIDs to fetch prices for
            limit_per_mandi: Maximum number of top prices to return per mandi

        Returns:
            Dictionary mapping mandi_id to list of top price dictionaries
        """
        if not mandi_ids:
            return {}

        from sqlalchemy import text

        # CRITICAL: Date bounds to avoid full table scan on 25M+ row price_history
        # Use 7-day window for mandi top prices (recent enough, much less data to scan)
        date_cutoff = (datetime.now().date() - timedelta(days=7))

        # Build parameterized IN clause for mandi_ids
        id_params = {f"mid_{i}": str(mid) for i, mid in enumerate(mandi_ids)}
        id_placeholders = ", ".join(f":mid_{i}::uuid" for i in range(len(mandi_ids)))

        # Use DISTINCT ON to get latest price per (mandi, commodity) efficiently
        # Then sort by modal_price DESC to get top prices
        query = text(f"""
            SELECT mandi_id, commodity_id, commodity_name, modal_price,
                   min_price, max_price, price_date
            FROM (
                SELECT DISTINCT ON (ph.mandi_id, ph.commodity_id)
                    ph.mandi_id,
                    ph.commodity_id,
                    c.name AS commodity_name,
                    ph.modal_price,
                    ph.min_price,
                    ph.max_price,
                    ph.price_date
                FROM price_history ph
                JOIN commodities c ON c.id = ph.commodity_id
                WHERE ph.mandi_id IN ({id_placeholders})
                  AND ph.price_date >= :date_cutoff
                ORDER BY ph.mandi_id, ph.commodity_id, ph.price_date DESC
            ) latest
            ORDER BY mandi_id, modal_price DESC
        """)

        rows = self.db.execute(query, {**id_params, "date_cutoff": date_cutoff}).fetchall()

        # Group by mandi_id and limit per mandi
        result = {}
        for mandi_id in mandi_ids:
            result[mandi_id] = []

        for row in rows:
            mid = row.mandi_id
            if mid in result and len(result[mid]) < limit_per_mandi:
                result[mid].append({
                    "commodity_id": str(row.commodity_id),
                    "commodity_name": row.commodity_name,
                    "unit": "quintal",
                    "modal_price": round(float(row.modal_price), 2),
                    "min_price": round(float(row.min_price), 2) if row.min_price else None,
                    "max_price": round(float(row.max_price), 2) if row.max_price else None,
                    "as_of": str(row.price_date),
                })

        return result

    def get_details(self, mandi_id: UUID, user_lat: float | None = None, user_lon: float | None = None) -> dict | None:
        """Get detailed information about a mandi with prices and facilities."""
        mandi = self.get_by_id(mandi_id)
        if not mandi:
            return None
        
        # Calculate distance if user coordinates provided
        distance = None
        if user_lat is not None and user_lon is not None and mandi.latitude and mandi.longitude:
            distance = round(self.haversine_distance(user_lat, user_lon, mandi.latitude, mandi.longitude), 2)
        
        # Get current prices for all commodities at this mandi
        current_prices = self.get_mandi_top_prices(mandi_id, limit=50)
        
        # Get price trends (last 30 days trend)
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        
        # Batch fetch old prices for all commodities (OPTIMIZED - Single Query)
        # This eliminates the N+1 query problem in price trend calculation
        commodity_ids = [p["commodity_id"] for p in current_prices]
        
        if commodity_ids:
            old_prices_query = self.db.query(
                PriceHistory.commodity_id,
                func.avg(PriceHistory.modal_price).label("avg_price")
            ).filter(
                PriceHistory.mandi_id == mandi_id,
                PriceHistory.commodity_id.in_(commodity_ids),
                PriceHistory.price_date <= thirty_days_ago
            ).group_by(PriceHistory.commodity_id).all()
            
            old_prices_map = {str(row.commodity_id): row.avg_price for row in old_prices_query}
        else:
            old_prices_map = {}
        
        price_trends = []
        for price_item in current_prices:
            old_price_quintal = old_prices_map.get(price_item["commodity_id"])
            
            change = None
            if old_price_quintal and old_price_quintal > 0:
                # Convert old price from quintal to kg
                old_price_kg = float(old_price_quintal) / 100
                change = round(((price_item["modal_price"] - old_price_kg) / old_price_kg) * 100, 2)
            
            price_trends.append({
                **price_item,
                "price_change_30d": change,
            })
        
        return {
            "id": str(mandi.id),
            "name": mandi.name,
            "state": mandi.state,
            "district": mandi.district,
            "address": mandi.address,
            "market_code": mandi.market_code,
            "pincode": mandi.pincode,
            "location": {
                "latitude": mandi.latitude,
                "longitude": mandi.longitude,
            },
            "contact": {
                "phone": mandi.phone,
                "email": mandi.email,
                "website": mandi.website,
            },
            "operating_hours": {
                "opening_time": str(mandi.opening_time) if mandi.opening_time else None,
                "closing_time": str(mandi.closing_time) if mandi.closing_time else None,
                "operating_days": mandi.operating_days,
            },
            "facilities": {
                "weighbridge": mandi.has_weighbridge,
                "storage": mandi.has_storage,
                "loading_dock": mandi.has_loading_dock,
                "cold_storage": mandi.has_cold_storage,
            },
            "payment_methods": mandi.payment_methods,
            "commodities_accepted": mandi.commodities_accepted,
            "rating": mandi.rating,
            "total_reviews": mandi.total_reviews,
            "distance_km": distance,
            "current_prices": price_trends,
        }

    def get_states(self) -> list[str]:
        """Get all unique states with mandis."""
        try:
            states = self.db.query(distinct(Mandi.state)).filter(
                Mandi.is_active == True
            ).order_by(Mandi.state).limit(100).all()
            return [s[0] for s in states if s[0]]
        except Exception as e:
            print(f"Error fetching states: {e}")
            # Return empty list instead of crashing
            return []

    def get_districts_by_state(self, state: str) -> list[str]:
        """Get all districts in a specific state."""
        try:
            districts = self.db.query(distinct(Mandi.district)).filter(
                Mandi.is_active == True,
                Mandi.state == state
            ).order_by(Mandi.district).limit(200).all()
            return [d[0] for d in districts if d[0]]
        except Exception as e:
            print(f"Error fetching districts for state {state}: {e}")
            return []

    def compare(self, mandi_ids: list[UUID], user_lat: float | None = None, user_lon: float | None = None) -> dict:
        """Compare multiple mandis side by side."""
        mandis_data = []
        
        for mandi_id in mandi_ids[:5]:  # Max 5 mandis
            details = self.get_details(mandi_id, user_lat, user_lon)
            if details:
                mandis_data.append(details)
        
        return {
            "mandis": mandis_data,
            "comparison_date": datetime.now().isoformat(),
        }

    def get_by_district(self, district: str) -> list[Mandi]:
        """Get all mandis in a specific district."""
        return self.db.query(Mandi).filter(
            Mandi.district.ilike(district.strip()),
            Mandi.is_active == True,
        ).order_by(Mandi.name).all()

    def create(self, mandi_data: MandiCreate) -> Mandi:
        """Create a new mandi."""
        try:
            mandi = Mandi(
                name=mandi_data.name,
                state=mandi_data.state,
                district=mandi_data.district,
                address=mandi_data.address,
                market_code=mandi_data.market_code,
                latitude=mandi_data.latitude,
                longitude=mandi_data.longitude,
                is_active=mandi_data.is_active,
            )
            self.db.add(mandi)
            self.db.commit()
            self.db.refresh(mandi)
            return mandi
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Mandi with market code '{mandi_data.market_code}' already exists")
        except Exception:
            self.db.rollback()
            raise

    def update(self, mandi_id: UUID, mandi_data: MandiUpdate) -> Mandi | None:
        """Update an existing mandi."""
        mandi = self.db.query(Mandi).filter(Mandi.id == mandi_id).first()

        if not mandi:
            return None

        update_data = mandi_data.model_dump(exclude_unset=True)

        if not update_data:
            return mandi

        try:
            for field, value in update_data.items():
                setattr(mandi, field, value)

            self.db.commit()
            self.db.refresh(mandi)
            return mandi
        except IntegrityError:
            self.db.rollback()
            code = update_data.get("market_code", "unknown")
            raise ValueError(f"Mandi with market code '{code}' already exists")
        except Exception:
            self.db.rollback()
            raise

    def delete(self, mandi_id: UUID) -> bool:
        """Soft delete a mandi by setting is_active=False."""
        mandi = self.db.query(Mandi).filter(Mandi.id == mandi_id).first()

        if not mandi:
            return False

        try:
            mandi.is_active = False
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def restore(self, mandi_id: UUID) -> Mandi | None:
        """Restore a soft-deleted mandi."""
        mandi = self.db.query(Mandi).filter(
            Mandi.id == mandi_id,
            Mandi.is_active == False,
        ).first()

        if not mandi:
            return None

        try:
            mandi.is_active = True
            self.db.commit()
            self.db.refresh(mandi)
            return mandi
        except Exception:
            self.db.rollback()
            raise

    def count(
        self,
        state: str | None = None,
        district: str | None = None,
        include_inactive: bool = False,
    ) -> int:
        """Count mandis with optional filtering."""
        query = self.db.query(Mandi)

        if not include_inactive:
            query = query.filter(Mandi.is_active == True)

        if state:
            query = query.filter(Mandi.state == state)

        if district:
            # Normalize district for consistent matching
            query = query.filter(Mandi.district == district.strip().title())

        return query.count()

    def search(self, query: str, limit: int = 10) -> list[Mandi]:
        """Search mandis by name or market code."""
        search_term = f"%{query.strip()}%"
        return self.db.query(Mandi).filter(
            Mandi.is_active == True,
            (Mandi.name.ilike(search_term) | Mandi.market_code.ilike(search_term)),
        ).order_by(Mandi.name).limit(limit).all()