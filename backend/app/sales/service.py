from uuid import UUID
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text
from app.models.sale import Sale
from app.models.inventory import Inventory
from app.models.commodity import Commodity
from app.sales.schemas import SaleCreate, SaleUpdate, SalesAnalytics


class SalesService:
    def __init__(self, db: Session):
        self.db = db

    def _get_available_stock(self, user_id: UUID, commodity_id: UUID, unit: str) -> float:
        """Get total available quantity for a commodity+unit in inventory."""
        items = self.db.query(Inventory).filter(
            Inventory.user_id == user_id,
            Inventory.commodity_id == commodity_id,
            Inventory.unit == unit,
            Inventory.quantity > 0
        ).all()
        return sum(float(item.quantity) for item in items)

    def _deduct_inventory(self, user_id: UUID, commodity_id: UUID, unit: str, quantity: float) -> None:
        """Deduct quantity from inventory items (FIFO order). Deletes items that reach 0."""
        inventory_items = self.db.query(Inventory).filter(
            Inventory.user_id == user_id,
            Inventory.commodity_id == commodity_id,
            Inventory.unit == unit
        ).order_by(Inventory.created_at).all()

        remaining = quantity
        for item in inventory_items:
            if remaining <= 0:
                break
            if float(item.quantity) >= remaining:
                item.quantity = float(item.quantity) - remaining
                if float(item.quantity) <= 0:
                    self.db.delete(item)
                else:
                    self.db.add(item)
                remaining = 0
            else:
                remaining -= float(item.quantity)
                self.db.delete(item)  # Remove empty inventory rows

    def _restore_inventory(self, user_id: UUID, commodity_id: UUID, unit: str, quantity: float) -> None:
        """Restore quantity back to inventory (add to existing or create new)."""
        existing = self.db.query(Inventory).filter(
            Inventory.user_id == user_id,
            Inventory.commodity_id == commodity_id,
            Inventory.unit == unit
        ).first()

        if existing:
            existing.quantity = float(existing.quantity) + quantity
            self.db.add(existing)
        else:
            new_item = Inventory(
                user_id=user_id,
                commodity_id=commodity_id,
                quantity=quantity,
                unit=unit
            )
            self.db.add(new_item)

    def create_sale(self, user_id: UUID, sale_in: SaleCreate) -> Sale:
        # Check available stock
        available = self._get_available_stock(user_id, sale_in.commodity_id, sale_in.unit)
        if available < sale_in.quantity:
            if available <= 0:
                raise ValueError(
                    f"No {sale_in.unit} stock available in inventory for this commodity. "
                    f"Add stock to inventory first."
                )
            raise ValueError(
                f"Insufficient stock. Available: {available} {sale_in.unit}, "
                f"Requested: {sale_in.quantity} {sale_in.unit}"
            )

        # Calculate total (price_per_unit is per kg)
        unit = (sale_in.unit or "").lower()
        quantity_in_kg = sale_in.quantity
        if unit == "quintal":
            quantity_in_kg = sale_in.quantity * 100
        elif unit == "ton":
            quantity_in_kg = sale_in.quantity * 1000

        total_amount = quantity_in_kg * sale_in.price_per_unit

        # Create sale record
        sale = Sale(
            user_id=user_id,
            commodity_id=sale_in.commodity_id,
            quantity=sale_in.quantity,
            unit=sale_in.unit,
            price_per_unit=sale_in.price_per_unit,
            total_amount=total_amount,
            buyer_name=sale_in.buyer_name,
            sale_date=sale_in.sale_date
        )
        self.db.add(sale)

        # Deduct from inventory
        self._deduct_inventory(user_id, sale_in.commodity_id, sale_in.unit, sale_in.quantity)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to record sale and update inventory: {str(e)}")

        self.db.refresh(sale)
        # Re-query with commodity loaded
        return self.db.query(Sale).options(
            joinedload(Sale.commodity)
        ).filter(Sale.id == sale.id).first()

    def get_user_sales(self, user_id: UUID, skip: int = 0, limit: int = 100) -> list[Sale]:
        return self.db.query(Sale).options(
            joinedload(Sale.commodity)
        ).filter(Sale.user_id == user_id).order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()

    def update_sale(self, user_id: UUID, sale_id: UUID, update_data: SaleUpdate) -> Sale | None:
        sale = self.db.query(Sale).options(
            joinedload(Sale.commodity)
        ).filter(
            Sale.id == sale_id,
            Sale.user_id == user_id,
        ).first()

        if not sale:
            return None

        old_quantity = float(sale.quantity)
        old_unit = sale.unit

        # Apply updates
        if update_data.quantity is not None:
            sale.quantity = update_data.quantity
        if update_data.unit is not None:
            sale.unit = update_data.unit
        if update_data.price_per_unit is not None:
            sale.price_per_unit = update_data.price_per_unit
        if update_data.buyer_name is not None:
            sale.buyer_name = update_data.buyer_name
        if update_data.sale_date is not None:
            sale.sale_date = update_data.sale_date

        new_quantity = float(sale.quantity)
        new_unit = sale.unit

        # Handle inventory adjustment if quantity/unit changed
        if new_quantity != old_quantity or new_unit != old_unit:
            # Restore old quantity to inventory
            self._restore_inventory(user_id, sale.commodity_id, old_unit, old_quantity)

            # Check if new quantity is available
            available = self._get_available_stock(user_id, sale.commodity_id, new_unit)
            if available < new_quantity:
                # Rollback the restore
                self.db.rollback()
                raise ValueError(
                    f"Insufficient stock for update. Available: {available} {new_unit}, "
                    f"Requested: {new_quantity} {new_unit}"
                )

            # Deduct new quantity
            self._deduct_inventory(user_id, sale.commodity_id, new_unit, new_quantity)

        # Recalculate total_amount
        unit = (sale.unit or "").lower()
        quantity_in_kg = float(sale.quantity)
        if unit == "quintal":
            quantity_in_kg = float(sale.quantity) * 100
        elif unit == "ton":
            quantity_in_kg = float(sale.quantity) * 1000

        sale.total_amount = quantity_in_kg * float(sale.price_per_unit)

        self.db.commit()
        self.db.refresh(sale)
        return sale

    def delete_sale(self, user_id: UUID, sale_id: UUID) -> bool:
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.user_id == user_id,
        ).first()

        if not sale:
            return False

        # Restore inventory before deleting
        self._restore_inventory(
            user_id, sale.commodity_id, sale.unit, float(sale.quantity)
        )

        self.db.delete(sale)
        self.db.commit()
        return True

    def get_sales_analytics(self, user_id: UUID) -> SalesAnalytics:
        stats = self.db.query(
            func.sum(Sale.total_amount).label("total_revenue"),
            func.count(Sale.id).label("total_sales")
        ).filter(Sale.user_id == user_id).first()

        total_revenue = stats.total_revenue or 0.0
        total_sales = stats.total_sales or 0

        # Top selling commodity
        top_commodity = self.db.query(
            Sale.commodity_id,
            func.sum(Sale.total_amount).label("revenue")
        ).filter(Sale.user_id == user_id).group_by(Sale.commodity_id).order_by(text("revenue DESC")).first()

        top_commodity_name = None
        if top_commodity:
            commodity = self.db.query(Commodity).get(top_commodity.commodity_id)
            if commodity:
                top_commodity_name = commodity.name

        return SalesAnalytics(
            total_revenue=total_revenue,
            total_sales_count=total_sales,
            top_selling_commodity=top_commodity_name
        )
