from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app.models.inventory import Inventory
from app.models.commodity import Commodity
from app.models.mandi import Mandi
from app.models.price_history import PriceHistory
from app.inventory.schemas import InventoryCreate, InventoryUpdate


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
        ).filter(
            Inventory.user_id == user_id,
            Inventory.quantity > 0
        ).offset(skip).limit(limit).all()

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

    def get_available_stock(self, user_id: UUID) -> list[dict]:
        """
        Get aggregated available stock per commodity (summing across units normalized to kg).
        Returns list of {commodity_id, commodity_name, quantity, unit} for each inventory row.
        """
        items = self.db.query(Inventory).options(
            joinedload(Inventory.commodity)
        ).filter(
            Inventory.user_id == user_id,
            Inventory.quantity > 0
        ).all()

        result = []
        for item in items:
            result.append({
                'commodity_id': str(item.commodity_id),
                'commodity_name': item.commodity.name if item.commodity else None,
                'quantity': float(item.quantity),
                'unit': item.unit,
            })
        return result

    def get_stock_for_commodity(self, user_id: UUID, commodity_id: UUID, unit: str) -> float:
        """Get total available quantity for a commodity in a specific unit."""
        items = self.db.query(Inventory).filter(
            Inventory.user_id == user_id,
            Inventory.commodity_id == commodity_id,
            Inventory.unit == unit,
            Inventory.quantity > 0
        ).all()
        return sum(float(item.quantity) for item in items)

    def analyze_inventory(self, user_id: UUID, user_state: str | None = None) -> list[dict]:
        """
        Analyze user's inventory and suggest best mandis to sell each commodity.
        
        For each commodity in the user's inventory:
        1. Find mandis with recent price data
        2. Rank mandis by modal price (highest first)
        3. Calculate estimated revenue based on inventory quantity
        4. Prioritize mandis in the user's state if available
        
        Args:
            user_id: The user's ID
            user_state: The user's state (for prioritizing nearby mandis)
            
        Returns:
            List of analysis results for each commodity in inventory
        """
        # Get user's inventory
        inventory = self.get_user_inventory(user_id)
        
        if not inventory:
            return []
        
        results = []
        
        for item in inventory:
            commodity_id = item.commodity_id
            commodity = item.commodity
            
            if not commodity:
                continue
            
            # Get latest prices for this commodity across all mandis
            # Subquery to get the latest price date per mandi
            latest_date_subquery = (
                self.db.query(
                    PriceHistory.mandi_id,
                    func.max(PriceHistory.price_date).label('max_date')
                )
                .filter(PriceHistory.commodity_id == commodity_id)
                .group_by(PriceHistory.mandi_id)
                .subquery()
            )
            
            # Get the actual price records for the latest dates
            latest_prices = (
                self.db.query(PriceHistory)
                .join(
                    latest_date_subquery,
                    (PriceHistory.mandi_id == latest_date_subquery.c.mandi_id) &
                    (PriceHistory.price_date == latest_date_subquery.c.max_date)
                )
                .filter(PriceHistory.commodity_id == commodity_id)
                .order_by(desc(PriceHistory.modal_price))
                .limit(10)  # Top 10 mandis
                .all()
            )
            
            if not latest_prices:
                # No price data available for this commodity
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

            # Batch-load all mandis for this set of prices (avoid N+1)
            mandi_ids = [p.mandi_id for p in latest_prices if p.mandi_id]
            mandis_map = {}
            if mandi_ids:
                mandis_list = self.db.query(Mandi).filter(Mandi.id.in_(mandi_ids)).all()
                mandis_map = {m.id: m for m in mandis_list}

            # Build list of best mandis
            best_mandis = []

            for price in latest_prices:
                # Get mandi details from batch lookup
                mandi = mandis_map.get(price.mandi_id)
                if not mandi:
                    continue

                # Calculate priority (prefer user's state)
                priority_boost = 0
                if user_state and mandi.state.lower() == user_state.lower():
                    priority_boost = 1

                # Prices are in per quintal
                modal_price = float(price.modal_price) if price.modal_price else 0
                min_price = float(price.min_price) if price.min_price else modal_price
                max_price = float(price.max_price) if price.max_price else modal_price

                # Calculate estimated revenue
                # Quantity is in kg, prices are per quintal, so divide qty by 100
                quantity_quintals = float(item.quantity) / 100
                estimated_min = quantity_quintals * min_price
                estimated_max = quantity_quintals * max_price
                estimated_modal = quantity_quintals * modal_price

                best_mandis.append({
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
                    'is_local': user_state and mandi.state.lower() == user_state.lower(),
                    'priority_score': modal_price + (priority_boost * 100),
                })
            
            # Sort by priority score (price + local boost)
            best_mandis.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # Remove priority_score from output
            for m in best_mandis:
                del m['priority_score']
            
            # Calculate overall revenue range
            if best_mandis:
                top_mandi = best_mandis[0]
                results.append({
                    'commodity_id': str(commodity_id),
                    'commodity_name': commodity.name,
                    'quantity': float(item.quantity),
                    'unit': item.unit,
                    'best_mandis': best_mandis[:5],  # Top 5 mandis
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