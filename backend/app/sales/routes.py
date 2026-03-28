from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.security import get_current_user
from app.models.user import User
from app.sales.schemas import SaleCreate, SaleResponse, SalesAnalytics
from app.sales.service import SalesService

router = APIRouter(prefix="/sales", tags=["Sales"])

@router.get("/", response_model=list[SaleResponse])
def get_sales(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = SalesService(db)
    return service.get_user_sales(current_user.id, skip, limit)

@router.post("/", response_model=SaleResponse)
def record_sale(
    sale_in: SaleCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    service = SalesService(db)
    return service.create_sale(current_user.id, sale_in)

@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(
    sale_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = SalesService(db)
    deleted = service.delete_sale(current_user.id, sale_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found",
        )
    return None

@router.get("/analytics", response_model=SalesAnalytics)
def get_sales_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = SalesService(db)
    return service.get_sales_analytics(current_user.id)
