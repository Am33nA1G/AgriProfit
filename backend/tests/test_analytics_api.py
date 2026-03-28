import pytest
from uuid import uuid4
from datetime import date, datetime, timedelta

from tests.utils import get_auth_headers, create_test_commodity, create_test_mandi
from app.models import PriceHistory, CommunityPost

@pytest.fixture
def test_commodity(test_db):
    return create_test_commodity(test_db, name="AnalyticsCommodity")

@pytest.fixture
def test_mandi(test_db):
    return create_test_mandi(test_db, name="AnalyticsMandi")

@pytest.fixture
def test_prices(test_db, test_commodity, test_mandi):
    """Fixture to create multiple price records with different dates."""
    prices = []
    today = date.today()
    for i in range(5):
        price = PriceHistory(
            id=uuid4(),
            commodity_id=test_commodity.id,
            mandi_id=test_mandi.id,
            price_date=today - timedelta(days=i),
            modal_price=2000 + i * 10,
            min_price=1900 + i * 10,
            max_price=2100 + i * 10,
            created_at=datetime.utcnow() - timedelta(days=i),
            updated_at=datetime.utcnow() - timedelta(days=i),
        )
        test_db.add(price)
        prices.append(price)
    test_db.commit()
    return prices

@pytest.fixture
def test_post(test_db, test_user):
    """Fixture to create a test community post."""
    post = CommunityPost(
        id=uuid4(),
        user_id=test_user.id,
        title="Analytics Test Post",
        content="Analytics test post content.",
        post_type="discussion",
        district="KL-TVM",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(post)
    test_db.commit()
    test_db.refresh(post)
    return post

def test_get_price_trends(client, test_commodity, test_mandi, test_prices):
    """Test GET /analytics/trends/{commodity_id} returns a list."""
    response = client.get(f"/api/v1/analytics/trends/{test_commodity.id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for trend in data:
        assert "price_date" in trend
        assert "modal_price" in trend

def test_get_price_trends_with_filters(client, test_commodity, test_mandi, test_prices):
    """Test GET /analytics/trends/{commodity_id}?mandi_id=X&days=30 returns a list."""
    response = client.get(
        f"/api/v1/analytics/trends/{test_commodity.id}?mandi_id={test_mandi.id}&days=30"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for trend in data:
        assert trend.get("mandi_id") == str(test_mandi.id)

def test_get_price_statistics(client, test_commodity, test_mandi, test_prices):
    """Test GET /analytics/statistics/{commodity_id}."""
    response = client.get(f"/api/v1/analytics/statistics/{test_commodity.id}")
    assert response.status_code == 200
    data = response.json()
    assert "avg_price" in data
    assert "min_price" in data
    assert "max_price" in data

def test_get_market_summary(client):
    """Test GET /analytics/summary returns all counts."""
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "total_mandis" in data
    assert "total_commodities" in data
    assert "total_price_records" in data

def test_get_top_commodities(client, test_prices):
    """Test GET /analytics/top-commodities?limit=10&days=30 returns a list."""
    response = client.get("/api/v1/analytics/top-commodities?limit=10&days=30")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_user_activity(client, test_token, test_user, test_post):
    """Test GET /analytics/user-activity/{user_id} returns activity object."""
    headers = get_auth_headers(test_token)
    response = client.get(f"/api/v1/analytics/user-activity/{test_user.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "posts_count" in data
    assert "username" in data

def test_get_user_activity_unauthorized(client, test_user):
    """Test GET /analytics/user-activity/{user_id} without token, verify 401."""
    response = client.get(f"/api/v1/analytics/user-activity/{test_user.id}")
    assert response.status_code == 401