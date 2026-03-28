import pytest
from uuid import uuid4
from datetime import datetime

from tests.utils import get_auth_headers
from app.models import CommunityPost

@pytest.fixture
def test_post(test_db, test_user):
    """Fixture to create a test community post."""
    post = CommunityPost(
        id=uuid4(),
        user_id=test_user.id,
        title="Test Post Title",
        content="Test post content with at least 10 chars",
        post_type="discussion",
        district="Test District",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(post)
    test_db.commit()
    test_db.refresh(post)
    return post

def test_create_post(client, test_token, test_user):
    """Test POST /community/posts/ with valid data."""
    headers = get_auth_headers(test_token)
    data = {
        "title": "Test Post Title",
        "content": "Hello, this is a test post!",
        "post_type": "discussion"
    }
    response = client.post("/api/v1/community/posts/", json=data, headers=headers)
    assert response.status_code == 201
    resp = response.json()
    assert resp["content"] == data["content"]
    assert resp["title"] == data["title"]
    assert resp["post_type"] == data["post_type"]
    assert resp["user_id"] == str(test_user.id)
    assert "id" in resp

def test_create_post_unauthorized(client):
    """Test POST /community/posts/ without token, should return 401."""
    data = {
        "title": "Unauthorized Post",
        "content": "Unauthorized post content",
        "post_type": "discussion"
    }
    response = client.post("/api/v1/community/posts/", json=data)
    assert response.status_code == 401

def test_get_post_by_id(client, test_post):
    """Test GET /community/posts/{id}."""
    response = client.get(f"/api/v1/community/posts/{test_post.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_post.id)
    assert data["content"] == test_post.content

def test_list_posts(client, test_post):
    """Test GET /community/posts/ with pagination."""
    response = client.get("/api/v1/community/posts/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(p["id"] == str(test_post.id) for p in data["items"])

def test_filter_posts_by_author(client, test_post, test_user):
    """Test GET /community/posts/?user_id=X."""
    response = client.get(f"/api/v1/community/posts/?user_id={test_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(p["user_id"] == str(test_user.id) for p in data["items"])

def test_update_post_success(client, test_token, test_post, test_user):
    """Test PUT /community/posts/{id} by author."""
    headers = get_auth_headers(test_token)
    update_data = {
        "title": "Updated Title",
        "content": "Updated post content",
        "post_type": "discussion"
    }
    response = client.put(f"/api/v1/community/posts/{test_post.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_post.id)
    assert data["content"] == "Updated post content"
    assert data["title"] == "Updated Title"

def test_update_post_forbidden(client, test_token, test_post, test_db):
    """Test PUT /community/posts/{id} by non-author, should return 403."""
    from app.models import User
    from tests.utils import get_token_for_user
    other_user = User(
        id=uuid4(),
        phone_number="9999999999",
        role="farmer",
        district="Other District",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(other_user)
    test_db.commit()
    test_db.refresh(other_user)
    other_token = get_token_for_user(other_user)
    headers = get_auth_headers(other_token)
    update_data = {
        "title": "Should Not Update",
        "content": "Should not update",
        "post_type": "discussion"
    }
    response = client.put(f"/api/v1/community/posts/{test_post.id}", json=update_data, headers=headers)
    assert response.status_code == 403

def test_delete_post_success(client, test_token, test_post, test_user):
    """Test DELETE /community/posts/{id} by author."""
    headers = get_auth_headers(test_token)
    response = client.delete(f"/api/v1/community/posts/{test_post.id}", headers=headers)
    assert response.status_code == 204  # No Content