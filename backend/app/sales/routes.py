from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.security import get_current_user
from app.models.user import User
from app.sales.schemas import SaleCreate, SaleUpdate, SaleResponse, SalesAnalytics
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
    try:
        return service.create_sale(current_user.id, sale_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.put("/{sale_id}", response_model=SaleResponse)
def update_sale(
    sale_id: UUID,
    update_data: SaleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a sale record (quantity, unit, price, buyer, date)."""
    service = SalesService(db)
    try:
        updated = service.update_sale(current_user.id, sale_id, update_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found",
        )
    return updated

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
