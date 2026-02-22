import pytest
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.session import get_db
from app.database.base import Base
from app.models import User
from app.auth.security import create_access_token


# Test database configuration - use in-memory SQLite
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def create_sqlite_tables(engine):
    """Create SQLite-compatible tables without PostgreSQL-specific constraints."""
    # List of CREATE TABLE statements
    create_statements = [
        # Users table
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            phone_number VARCHAR(10) NOT NULL UNIQUE,
            role VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            age INTEGER,
            state VARCHAR(50),
            district TEXT,
            language VARCHAR(10) NOT NULL DEFAULT 'en',
            is_profile_complete BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            last_login TIMESTAMP,
            is_banned BOOLEAN NOT NULL DEFAULT 0,
            ban_reason TEXT
        )
        """,
        # OTP requests table
        """
        CREATE TABLE IF NOT EXISTS otp_requests (
            id TEXT PRIMARY KEY,
            phone_number VARCHAR(10) NOT NULL,
            otp_hash VARCHAR(255) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            verified BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Mandis table
        """
        CREATE TABLE IF NOT EXISTS mandis (
            id TEXT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            state VARCHAR(100) NOT NULL,
            district VARCHAR(100) NOT NULL,
            address VARCHAR(500),
            market_code VARCHAR(50) NOT NULL UNIQUE,
            latitude FLOAT,
            longitude FLOAT,
            pincode VARCHAR(10),
            phone VARCHAR(20),
            email VARCHAR(100),
            website VARCHAR(200),
            opening_time TEXT,
            closing_time TEXT,
            operating_days TEXT,
            has_weighbridge BOOLEAN NOT NULL DEFAULT 0,
            has_storage BOOLEAN NOT NULL DEFAULT 0,
            has_loading_dock BOOLEAN NOT NULL DEFAULT 0,
            has_cold_storage BOOLEAN NOT NULL DEFAULT 0,
            payment_methods TEXT,
            commodities_accepted TEXT,
            rating FLOAT,
            total_reviews INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Commodities table
        """
        CREATE TABLE IF NOT EXISTS commodities (
            id TEXT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            name_local VARCHAR(100),
            category VARCHAR(50),
            unit VARCHAR(20),
            description TEXT,
            growing_months TEXT,
            harvest_months TEXT,
            peak_season_start INTEGER,
            peak_season_end INTEGER,
            major_producing_states TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Price history table
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id TEXT PRIMARY KEY,
            commodity_id TEXT NOT NULL,
            mandi_id TEXT,
            mandi_name TEXT,
            price_date DATE NOT NULL,
            modal_price NUMERIC(10, 2) NOT NULL,
            min_price NUMERIC(10, 2),
            max_price NUMERIC(10, 2),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (commodity_id) REFERENCES commodities(id) ON DELETE CASCADE,
            FOREIGN KEY (mandi_id) REFERENCES mandis(id) ON DELETE CASCADE
        )
        """,
        # Price forecasts table
        """
        CREATE TABLE IF NOT EXISTS price_forecasts (
            id TEXT PRIMARY KEY,
            commodity_id TEXT NOT NULL,
            mandi_id TEXT,
            mandi_name TEXT,
            forecast_date DATE NOT NULL,
            predicted_price NUMERIC(10, 2) NOT NULL,
            confidence_level NUMERIC(5, 4),
            model_version TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (commodity_id) REFERENCES commodities(id) ON DELETE CASCADE,
            FOREIGN KEY (mandi_id) REFERENCES mandis(id) ON DELETE CASCADE
        )
        """,
        # Community posts table
        """
        CREATE TABLE IF NOT EXISTS community_posts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            post_type VARCHAR(20) NOT NULL,
            district TEXT,
            is_admin_override BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        # Notifications table
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            post_id TEXT,
            related_id TEXT,
            title TEXT,
            message TEXT NOT NULL,
            notification_type VARCHAR(50),
            is_read BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE SET NULL
        )
        """,
        # Admin actions table
        """
        CREATE TABLE IF NOT EXISTS admin_actions (
            id TEXT PRIMARY KEY,
            admin_id TEXT NOT NULL,
            target_user_id TEXT,
            target_resource_id TEXT,
            action_type VARCHAR(50) NOT NULL,
            description TEXT,
            action_metadata TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE RESTRICT,
            FOREIGN KEY (target_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        """,
        # Inventory table
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            commodity_id TEXT NOT NULL,
            quantity FLOAT NOT NULL,
            unit VARCHAR(20) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (commodity_id) REFERENCES commodities(id) ON DELETE RESTRICT
        )
        """,
        # Sales table
        """
        CREATE TABLE IF NOT EXISTS sales (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            commodity_id TEXT NOT NULL,
            quantity NUMERIC(10, 2) NOT NULL,
            unit VARCHAR(20) NOT NULL,
            price_per_unit NUMERIC(10, 2) NOT NULL,
            total_amount NUMERIC(12, 2) NOT NULL,
            buyer_name VARCHAR(100),
            sale_date DATE NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (commodity_id) REFERENCES commodities(id) ON DELETE RESTRICT
        )
        """,
        # Community replies table
        """
        CREATE TABLE IF NOT EXISTS community_replies (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        # Community likes table
        """
        CREATE TABLE IF NOT EXISTS community_likes (
            id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (post_id, user_id)
        )
        """,
        # Uploaded files table
        """
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id TEXT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            original_filename VARCHAR(255),
            content_type VARCHAR(100),
            file_size VARCHAR(50),
            user_id TEXT NOT NULL,
            created_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        # Refresh tokens table
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            revoked BOOLEAN DEFAULT 0,
            revoked_at TIMESTAMP,
            device_info VARCHAR(255),
            ip_address VARCHAR(45),
            created_at TIMESTAMP,
            last_used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        # Device push tokens table
        """
        CREATE TABLE IF NOT EXISTS device_push_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expo_push_token VARCHAR(255) NOT NULL,
            device_platform VARCHAR(10) NOT NULL,
            device_model VARCHAR(100),
            app_version VARCHAR(20),
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE (user_id, expo_push_token)
        )
        """,
    ]

    with engine.connect() as conn:
        for statement in create_statements:
            conn.execute(text(statement))
        conn.commit()


def drop_sqlite_tables(engine):
    """Drop all tables in reverse order to handle foreign keys."""
    tables = [
        "device_push_tokens",
        "refresh_tokens",
        "uploaded_files",
        "community_likes",
        "community_replies",
        "sales",
        "inventory",
        "admin_actions",
        "notifications",
        "community_posts",
        "price_forecasts",
        "price_history",
        "commodities",
        "mandis",
        "otp_requests",
        "users",
    ]
    with engine.connect() as conn:
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.commit()


@pytest.fixture(scope="function")
def test_db():
    """Create test database tables and provide a session."""
    # Create all tables using SQLite-compatible SQL
    create_sqlite_tables(test_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        drop_sqlite_tables(test_engine)


@pytest.fixture(scope="function")
def override_get_db(test_db):
    """Override the get_db dependency."""
    def _override_get_db():
        try:
            yield test_db
        finally:
            pass
    return _override_get_db


@pytest.fixture(scope="function")
def client(override_get_db):
    """Create a test client with overridden database dependency."""
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(test_db) -> User:
    """Create and return a test user (farmer role)."""
    user = User(
        id=uuid4(),
        phone_number="9876543210",
        role="farmer",
        district="KL-TVM",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin_user(test_db) -> User:
    """Create and return a test admin user."""
    admin = User(
        id=uuid4(),
        phone_number="9876543211",
        role="admin",
        district="KL-EKM",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def test_token(test_user) -> str:
    """Generate a valid JWT token for the test user."""
    return create_access_token(
        data={"sub": str(test_user.id), "role": test_user.role}
    )


@pytest.fixture(scope="function")
def test_admin_token(test_admin_user) -> str:
    """Generate a valid JWT token for the test admin user."""
    return create_access_token(
        data={"sub": str(test_admin_user.id), "role": test_admin_user.role}
    )


@pytest.fixture(scope="function")
def auth_headers(test_token) -> dict:
    """Return authorization headers with test user token."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture(scope="function")
def admin_auth_headers(test_admin_token) -> dict:
    """Return authorization headers with admin user token."""
    return {"Authorization": f"Bearer {test_admin_token}"}