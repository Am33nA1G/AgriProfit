from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database.session import get_db
from app.auth.security import get_current_user
from app.models.user import User
from app.inventory.schemas import InventoryCreate, InventoryResponse, InventoryUpdate
from app.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# =============================================================================
# ANALYSIS RESPONSE SCHEMAS
# =============================================================================

class MandiRecommendation(BaseModel):
    """Recommended mandi for selling a commodity."""
    mandi_id: str
    mandi_name: str
    state: str
    district: str
    modal_price: float
    min_price: float
    max_price: float
    price_date: str
    estimated_revenue: float
    estimated_min_revenue: float
    estimated_max_revenue: float
    is_local: bool = False
    # Transport-aware fields (populated when user location is known)
    distance_km: float | None = None
    transport_cost: float | None = None
    net_profit: float | None = None
    verdict: str | None = None
    verdict_reason: str | None = None


class CommodityAnalysis(BaseModel):
    """Analysis result for a single commodity in inventory."""
    commodity_id: str
    commodity_name: str
    quantity: float
    unit: str
    best_mandis: list[MandiRecommendation] = []
    recommended_mandi: str | None = None
    recommended_price: float | None = None
    estimated_min_revenue: float = 0
    estimated_max_revenue: float = 0
    message: str | None = None


class InventoryAnalysisResponse(BaseModel):
    """Complete inventory analysis response."""
    total_items: int
    analysis: list[CommodityAnalysis]
    total_estimated_min_revenue: float
    total_estimated_max_revenue: float


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/", response_model=list[InventoryResponse])
def get_inventory(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = InventoryService(db)
    items = service.get_user_inventory(current_user.id, skip, limit)
    # Start manual hydration if check is needed or rely on lazy loading response model
    # Pydantic's from_attributes should handle relationship if eager loaded or session active
    return items


@router.post("/", response_model=InventoryResponse)
def add_inventory(
    item_in: InventoryCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    service = InventoryService(db)
    return service.add_inventory(current_user.id, item_in)


@router.post("/analyze", response_model=InventoryAnalysisResponse)
def analyze_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze user's inventory and suggest best mandis for selling each commodity.
    
    Returns recommendations for where to sell each commodity based on:
    - Current market prices across different mandis
    - User's location (prioritizes local mandis)
    - Estimated revenue calculations
    
    This helps farmers make informed decisions about where to sell their produce.
    """
    service = InventoryService(db)
    
    # Get user's location for transport-cost-aware ranking
    user_state = current_user.state if hasattr(current_user, 'state') else None
    user_district = current_user.district if hasattr(current_user, 'district') else None
    
    # Run analysis
    analysis_results = service.analyze_inventory(current_user.id, user_state, user_district)
    
    # Calculate totals
    total_min = sum(r.get('estimated_min_revenue', 0) for r in analysis_results)
    total_max = sum(r.get('estimated_max_revenue', 0) for r in analysis_results)
    
    return InventoryAnalysisResponse(
        total_items=len(analysis_results),
        analysis=analysis_results,
        total_estimated_min_revenue=total_min,
        total_estimated_max_revenue=total_max,
    )


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory(
    inventory_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = InventoryService(db)
    item = service.get_inventory_item(inventory_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    service.delete_inventory(item)
    return
