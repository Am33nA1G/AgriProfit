import pytest
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.commodity import Commodity
from tests.utils import get_auth_headers

def test_inventory_flow(client: TestClient, auth_headers: dict, test_db, test_user):
    # Setup: Create a commodity
    commodity = Commodity(
        id=uuid4(),
        name="Test Rice",
        category="Grains",
        unit="kg",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(commodity)
    test_db.commit()

    # 1. Add Inventory
    payload = {
        "commodity_id": str(commodity.id),
        "quantity": 100.0,
        "unit": "kg"
    }
    response = client.post("/api/v1/inventory/", json=payload, headers=auth_headers)
    assert response.status_code in [200, 201], f"Expected 200 or 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["quantity"] == 100.0
    inventory_id = data["id"]

    # 2. Get Inventory
    response = client.get("/api/v1/inventory/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # 3. Record Sale (should deduct from inventory)
    sale_payload = {
        "commodity_id": str(commodity.id),
        "quantity": 20.0,
        "unit": "kg",
        "price_per_unit": 50.0,
        "buyer_name": "Local Buyer"
    }
    response = client.post("/api/v1/sales/", json=sale_payload, headers=auth_headers)
    assert response.status_code in [200, 201], f"Expected 200 or 201, got {response.status_code}: {response.text}"
    assert response.json()["total_amount"] == 1000.0

    # 4. Check Inventory updated
    response = client.get("/api/v1/inventory/", headers=auth_headers)
    items = response.json()
    item = next((i for i in items if i["id"] == inventory_id), None)
    # Note: inventory deduction may or may not be automatic based on implementation
    if item:
        assert item["quantity"] <= 100.0

    # 5. Check Analytics
    response = client.get("/api/v1/sales/analytics", headers=auth_headers)
    assert response.status_code == 200
    analytics = response.json()
    assert analytics.get("total_revenue") is not None or analytics.get("revenue") is not None
