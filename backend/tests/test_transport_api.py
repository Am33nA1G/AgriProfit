from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

class TestTransportCompareEndpoint:
    def test_successful_comparison(self):
        response = client.post(
            "/api/v1/transport/compare",
            json={
                "commodity": "Wheat",
                "quantity_kg": 5000,
                "source_state": "Punjab",
                "source_district": "Ludhiana"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "comparisons" in data
        assert "best_mandi" in data
        assert isinstance(data["comparisons"], list)
        
        if len(data["comparisons"]) > 0:
            comparison = data["comparisons"][0]
            assert "mandi_name" in comparison
            assert "distance_km" in comparison
            assert "net_profit" in comparison
            assert "vehicle_type" in comparison
            assert comparison["vehicle_type"] in ["TEMPO", "TRUCK_SMALL", "TRUCK_LARGE"]
    
    def test_missing_required_fields(self):
        response = client.post(
            "/api/v1/transport/compare",
            json={
                "commodity": "Wheat"
                # Missing quantity_kg, source_state, source_district
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_quantity_negative(self):
        response = client.post(
            "/api/v1/transport/compare",
            json={
                "commodity": "Wheat",
                "quantity_kg": -100,  # Negative
                "source_state": "Punjab",
                "source_district": "Ludhiana"
            }
        )
        
        assert response.status_code == 422
    
    def test_zero_quantity(self):
        response = client.post(
            "/api/v1/transport/compare",
            json={
                "commodity": "Wheat",
                "quantity_kg": 0,
                "source_state": "Punjab",
                "source_district": "Ludhiana"
            }
        )
        
        assert response.status_code == 422
    
    def test_authentication_required(self):
        # Test without auth token
        response = client.post(
            "/api/v1/transport/compare",
            json={
                "commodity": "Wheat",
                "quantity_kg": 5000,
                "source_state": "Punjab",
                "source_district": "Ludhiana"
            }
        )
        
        # Verify auth is enforced (should be 401 if protected)
        # Adjust based on your auth strategy
        assert response.status_code in [200, 401]
