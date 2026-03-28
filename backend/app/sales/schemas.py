from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class SaleBase(BaseModel):
    commodity_id: UUID
    quantity: float = Field(..., gt=0, description="Quantity sold")
    unit: str = Field(..., min_length=1, max_length=20)
    price_per_unit: float = Field(..., gt=0, description="Price per kg (Rs.)")
    buyer_name: str | None = Field(None, max_length=100)
    sale_date: date = Field(default_factory=date.today)

class SaleCreate(SaleBase):
    pass

class SaleResponse(SaleBase):
    id: UUID
    user_id: UUID
    total_amount: float
    commodity_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def extract_commodity_name(cls, data):
        """Extract commodity name from relationship if available."""
        if hasattr(data, 'commodity') and data.commodity:
            # SQLAlchemy model object
            return {
                'id': data.id,
                'user_id': data.user_id,
                'commodity_id': data.commodity_id,
                'quantity': data.quantity,
                'unit': data.unit,
                'price_per_unit': data.price_per_unit,
                'buyer_name': data.buyer_name,
                'sale_date': data.sale_date,
                'total_amount': data.total_amount,
                'commodity_name': data.commodity.name,
                'created_at': data.created_at,
            }
        return data

class SalesAnalytics(BaseModel):
    total_revenue: float
    total_sales_count: int
    top_selling_commodity: str | None
