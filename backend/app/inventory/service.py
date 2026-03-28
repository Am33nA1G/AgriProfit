from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app.models.inventory import Inventory
from app.models.commodity import Commodity
from app.models.mandi import Mandi
from app.models.price_history import PriceHistory
from app.inventory.schemas import InventoryCreate, InventoryUpdate
from app.transport.service import (
    calculate_net_profit,
    select_vehicle,
    haversine_distance,
    compute_verdict,
    DISTRICT_COORDINATES,
)
from app.transport.schemas import VehicleType
import logging

logger = logging.getLogger(__name__)


class InventoryAnalysisResult:
    """Result of inventory analysis for a single commodity."""
    def __init__(
        self,
        commodity_id: str,
        commodity_name: str,
        quantity: float,
        unit: str,
        best_mandis: list[dict],
        estimated_revenue_range: tuple[float, float],
    ):
        self.commodity_id = commodity_id
        self.commodity_name = commodity_name
        self.quantity = quantity
        self.unit = unit
        self.best_mandis = best_mandis
        self.estimated_revenue_range = estimated_revenue_range


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_inventory(self, user_id: UUID, skip: int = 0, limit: int = 100) -> list[Inventory]:
        return self.db.query(Inventory).options(
            joinedload(Inventory.commodity)
        ).filter(Inventory.user_id == user_id).offset(skip).limit(limit).all()

    def get_inventory_item(self, inventory_id: UUID, user_id: UUID) -> Inventory | None:
        return self.db.query(Inventory).options(
            joinedload(Inventory.commodity)
        ).filter(
            Inventory.id == inventory_id, 
            Inventory.user_id == user_id
        ).first()

    def add_inventory(self, user_id: UUID, item_in: InventoryCreate) -> Inventory:
        # Check if commodity exists
        # In a real app we might validate commodity_id explicitly or let FK constraint handle it
        
        # Check if item already exists for this commodity, update if so?
        # For simplicity, we'll assume distinct entries or update logic here.
        # Let's check for existing item of same commodity and unit to merge
        existing_item = self.db.query(Inventory).options(
            joinedload(Inventory.commodity)
        ).filter(
            Inventory.user_id == user_id,
            Inventory.commodity_id == item_in.commodity_id,
            Inventory.unit == item_in.unit
        ).first()

        if existing_item:
            existing_item.quantity += item_in.quantity
            self.db.commit()
            self.db.refresh(existing_item)
            # Re-query to get commodity loaded
            return self.db.query(Inventory).options(
                joinedload(Inventory.commodity)
            ).filter(Inventory.id == existing_item.id).first()

        new_item = Inventory(
            user_id=user_id,
            commodity_id=item_in.commodity_id,
            quantity=item_in.quantity,
            unit=item_in.unit
        )
        self.db.add(new_item)
        self.db.commit()
        self.db.refresh(new_item)
        # Re-query to get commodity loaded
        return self.db.query(Inventory).options(
            joinedload(Inventory.commodity)
        ).filter(Inventory.id == new_item.id).first()

    def update_inventory(self, item: Inventory, update_data: InventoryUpdate) -> Inventory:
        if update_data.quantity is not None:
            item.quantity = update_data.quantity
        if update_data.unit is not None:
            item.unit = update_data.unit
        
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_inventory(self, item: Inventory) -> None:
        self.db.delete(item)
        self.db.commit()

    def analyze_inventory(
        self, user_id: UUID, user_state: str | None = None, user_district: str | None = None,
    ) -> list[dict]:
        """
        Analyze user's inventory and suggest best mandis to sell each commodity.
        
        Ranks mandis by **net profit** (revenue minus transport, spoilage, fees)
        when the user's location is known, falling back to raw modal price if not.

        Args:
            user_id: The user's ID
            user_state: The user's state (for distance / interstate calc)
            user_district: The user's district (for source coordinates)
            
        Returns:
            List of analysis results for each commodity in inventory
        """
        inventory = self.get_user_inventory(user_id)
        if not inventory:
            return []

        # Resolve source coordinates from user's district
        source_coords = self._resolve_source_coords(user_district, user_state)
        has_location = source_coords is not None

        results = []

        for item in inventory:
            commodity_id = item.commodity_id
            commodity = item.commodity
            if not commodity:
                continue

            commodity_category = getattr(commodity, "category", None)

            # Quantity in kg (inventory stores in the user's chosen unit)
            quantity_kg = self._to_kg(float(item.quantity), item.unit)

            # Latest prices per mandi
            latest_date_subquery = (
                self.db.query(
                    PriceHistory.mandi_id,
                    func.max(PriceHistory.price_date).label('max_date')
                )
                .filter(PriceHistory.commodity_id == commodity_id)
                .group_by(PriceHistory.mandi_id)
                .subquery()
            )

            latest_prices = (
                self.db.query(PriceHistory)
                .join(
                    latest_date_subquery,
                    (PriceHistory.mandi_id == latest_date_subquery.c.mandi_id) &
                    (PriceHistory.price_date == latest_date_subquery.c.max_date)
                )
                .filter(PriceHistory.commodity_id == commodity_id)
                .order_by(desc(PriceHistory.modal_price))
                .limit(15)
                .all()
            )

            if not latest_prices:
                results.append({
                    'commodity_id': str(commodity_id),
                    'commodity_name': commodity.name,
                    'quantity': float(item.quantity),
                    'unit': item.unit,
                    'best_mandis': [],
                    'message': 'No price data available for this commodity',
                    'estimated_min_revenue': 0,
                    'estimated_max_revenue': 0,
                })
                continue

            # Batch-load mandis
            mandi_ids = [p.mandi_id for p in latest_prices if p.mandi_id]
            mandis_map = {}
            if mandi_ids:
                mandis_list = self.db.query(Mandi).filter(Mandi.id.in_(mandi_ids)).all()
                mandis_map = {m.id: m for m in mandis_list}

            best_mandis = []
            for price in latest_prices:
                mandi = mandis_map.get(price.mandi_id)
                if not mandi:
                    continue

                modal_price = float(price.modal_price) if price.modal_price else 0
                min_price = float(price.min_price) if price.min_price else modal_price
                max_price = float(price.max_price) if price.max_price else modal_price
                price_per_kg = modal_price / 100  # quintal → kg

                # Convert quantity for revenue in user's original unit
                quantity_quintals = float(item.quantity) / 100 if item.unit == "kg" else (
                    float(item.quantity) if item.unit == "quintal" else float(item.quantity) * 10
                )
                estimated_min = quantity_quintals * min_price
                estimated_max = quantity_quintals * max_price
                estimated_modal = quantity_quintals * modal_price

                is_local = bool(
                    user_state and mandi.state and mandi.state.lower() == user_state.lower()
                )

                entry: dict = {
                    'mandi_id': str(mandi.id),
                    'mandi_name': mandi.name,
                    'state': mandi.state,
                    'district': mandi.district,
                    'modal_price': modal_price,
                    'min_price': min_price,
                    'max_price': max_price,
                    'price_date': price.price_date.isoformat(),
                    'estimated_revenue': estimated_modal,
                    'estimated_min_revenue': estimated_min,
                    'estimated_max_revenue': estimated_max,
                    'is_local': is_local,
                    # Transport fields (defaults when location unknown)
                    'distance_km': None,
                    'transport_cost': None,
                    'net_profit': None,
                    'verdict': None,
                    'verdict_reason': None,
                }

                # If we know the user's location, compute real net profit
                if has_location and mandi.latitude and mandi.longitude:
                    src_lat, src_lon = source_coords
                    distance_km = haversine_distance(
                        src_lat, src_lon, float(mandi.latitude), float(mandi.longitude),
                    ) * 1.3  # road-to-straight adjustment

                    vehicle = select_vehicle(quantity_kg)
                    profit_data = calculate_net_profit(
                        price_per_kg=price_per_kg,
                        quantity_kg=quantity_kg,
                        distance_km=distance_km,
                        vehicle_type=vehicle,
                        source_state=user_state or "Unknown",
                        mandi_state=mandi.state or "Unknown",
                        commodity_category=commodity_category,
                    )

                    net_profit = profit_data["net_profit"]
                    total_cost = profit_data["total_cost"]
                    profit_per_kg = profit_data["profit_per_kg"]
                    gross_revenue = profit_data["gross_revenue"]

                    entry['distance_km'] = round(distance_km, 1)
                    entry['transport_cost'] = round(total_cost, 2)
                    entry['net_profit'] = round(net_profit, 2)
                    entry['estimated_min_revenue'] = round(net_profit * 0.85, 2)
                    entry['estimated_max_revenue'] = round(net_profit * 1.10, 2)
                    entry['estimated_revenue'] = round(net_profit, 2)

                    # Verdict
                    tier, reason = compute_verdict(
                        net_profit, gross_revenue, profit_per_kg, 0, 0,
                    )
                    entry['verdict'] = tier
                    entry['verdict_reason'] = reason

                best_mandis.append(entry)

            # Sort by net_profit (descending) if available, else by modal_price
            if has_location:
                # Filter out mandis with no net_profit computed
                with_profit = [m for m in best_mandis if m['net_profit'] is not None]
                without_profit = [m for m in best_mandis if m['net_profit'] is None]
                with_profit.sort(key=lambda x: x['net_profit'], reverse=True)
                best_mandis = with_profit + without_profit
            else:
                best_mandis.sort(key=lambda x: x['modal_price'], reverse=True)

            # Assign verdict ranks now that the list is sorted
            total = len([m for m in best_mandis if m.get('net_profit') is not None])
            for rank, m in enumerate(best_mandis, start=1):
                if m.get('net_profit') is not None and m.get('verdict'):
                    _, reason = compute_verdict(
                        m['net_profit'],
                        m.get('estimated_revenue', 0),
                        (m['net_profit'] / quantity_kg) if quantity_kg > 0 else 0,
                        rank,
                        total,
                    )
                    m['verdict_reason'] = reason

            top_5 = best_mandis[:5]
            if top_5:
                top_mandi = top_5[0]
                results.append({
                    'commodity_id': str(commodity_id),
                    'commodity_name': commodity.name,
                    'quantity': float(item.quantity),
                    'unit': item.unit,
                    'best_mandis': top_5,
                    'recommended_mandi': top_mandi['mandi_name'],
                    'recommended_price': top_mandi['modal_price'],
                    'estimated_min_revenue': top_mandi['estimated_min_revenue'],
                    'estimated_max_revenue': top_mandi['estimated_max_revenue'],
                })
            else:
                results.append({
                    'commodity_id': str(commodity_id),
                    'commodity_name': commodity.name,
                    'quantity': float(item.quantity),
                    'unit': item.unit,
                    'best_mandis': [],
                    'message': 'No mandi data available',
                    'estimated_min_revenue': 0,
                    'estimated_max_revenue': 0,
                })

        return results

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _to_kg(quantity: float, unit: str) -> float:
        """Convert inventory quantity to kilograms."""
        if unit == "kg":
            return quantity
        elif unit == "quintal":
            return quantity * 100
        elif unit == "ton":
            return quantity * 1000
        return quantity

    def _resolve_source_coords(
        self, district: str | None, state: str | None
    ) -> tuple[float, float] | None:
        """Resolve user's district/state into lat/lon coordinates."""
        if district:
            # Try exact district name lookup
            key = district.strip().lower()
            for k, v in DISTRICT_COORDINATES.items():
                if k.lower() == key:
                    return v

            # Try with state prefix
            if state:
                combo = f"{district.strip()}, {state.strip()}".lower()
                for k, v in DISTRICT_COORDINATES.items():
                    if k.lower() == combo:
                        return v

        # Fallback: average of mandi coordinates for the state
        if state:
            from sqlalchemy import text
            row = self.db.execute(
                text("""
                    SELECT AVG(latitude) AS lat, AVG(longitude) AS lon
                    FROM mandis
                    WHERE state ILIKE :state
                      AND latitude IS NOT NULL AND longitude IS NOT NULL
                      AND is_active = true
                """),
                {"state": f"%{state.strip()}%"},
            ).first()
            if row and row.lat and row.lon:
                return (float(row.lat), float(row.lon))

        return None
        
        return results