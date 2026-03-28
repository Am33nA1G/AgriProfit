from uuid import UUID
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text
from app.models.sale import Sale
from app.models.inventory import Inventory
from app.models.commodity import Commodity
from app.sales.schemas import SaleCreate, SalesAnalytics

class SalesService:
    def __init__(self, db: Session):
        self.db = db

    def create_sale(self, user_id: UUID, sale_in: SaleCreate) -> Sale:
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

        # Deduct from inventory automatically
        # Find matching inventory items and reduce quantities
        inventory_items = self.db.query(Inventory).filter(
            Inventory.user_id == user_id,
            Inventory.commodity_id == sale_in.commodity_id,
            Inventory.unit == sale_in.unit
        ).order_by(Inventory.created_at).all()

        remaining_to_deduct = sale_in.quantity

        for item in inventory_items:
            if remaining_to_deduct <= 0:
                break
            
            if item.quantity > remaining_to_deduct:
                # Deduct partial quantity from this item
                item.quantity -= remaining_to_deduct
                self.db.add(item)  # Explicitly add to session for tracking
                remaining_to_deduct = 0
            else:
                # Use entire item quantity and remove the exhausted inventory record
                remaining_to_deduct -= item.quantity
                self.db.delete(item)

        # Note: We allow generating sales even if inventory is insufficient (flexible system),
        # but we still deduct what we can from available inventory.
        # In a strict system, we would raise an error here if insufficient inventory.
        
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

    def delete_sale(self, user_id: UUID, sale_id: UUID) -> bool:
        sale = self.db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.user_id == user_id,
        ).first()

        if not sale:
            return False

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
