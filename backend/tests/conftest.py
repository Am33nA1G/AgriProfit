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
            is_banned BOOLEAN NOT NULL DEFAULT 0,
            ban_reason TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            last_login TIMESTAMP
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
            image_url TEXT,
            view_count INTEGER NOT NULL DEFAULT 0,
            is_pinned BOOLEAN NOT NULL DEFAULT 0,
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
            FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        # Community likes table
        """
        CREATE TABLE IF NOT EXISTS community_likes (
            user_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        # Model training log table (Phase 4)
        """
        CREATE TABLE IF NOT EXISTS model_training_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity VARCHAR(200) NOT NULL,
            trained_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            n_series INTEGER NOT NULL,
            n_folds INTEGER NOT NULL,
            rmse_fold_1 NUMERIC(10, 4),
            rmse_fold_2 NUMERIC(10, 4),
            rmse_fold_3 NUMERIC(10, 4),
            rmse_fold_4 NUMERIC(10, 4),
            rmse_mean NUMERIC(10, 4) NOT NULL,
            mape_mean NUMERIC(10, 4) NOT NULL,
            artifact_path TEXT NOT NULL,
            skforecast_version VARCHAR(20) NOT NULL,
            xgboost_version VARCHAR(20) NOT NULL,
            excluded_districts TEXT
        )
        """,
        # Forecast cache table (Phase 4)
        """
        CREATE TABLE IF NOT EXISTS forecast_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity_name VARCHAR(200) NOT NULL,
            district_name VARCHAR(200) NOT NULL,
            generated_date DATE NOT NULL,
            forecast_horizon_days INTEGER NOT NULL,
            direction VARCHAR(10) NOT NULL,
            price_low NUMERIC(10, 2),
            price_mid NUMERIC(10, 2),
            price_high NUMERIC(10, 2),
            confidence_colour VARCHAR(10) NOT NULL,
            tier_label VARCHAR(30) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Crop yields table (harvest advisor)
        """
        CREATE TABLE IF NOT EXISTS crop_yields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state VARCHAR(100) NOT NULL,
            district VARCHAR(200) NOT NULL,
            crop_name VARCHAR(200) NOT NULL,
            year SMALLINT NOT NULL,
            area_ha NUMERIC(12, 2),
            production_t NUMERIC(12, 2),
            yield_kg_ha NUMERIC(10, 2) NOT NULL,
            data_source VARCHAR(50) NOT NULL DEFAULT 'ICRISAT'
        )
        """,
        # Yield model log table (harvest advisor)
        """
        CREATE TABLE IF NOT EXISTS yield_model_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trained_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            crop_category VARCHAR(50) NOT NULL,
            n_samples INTEGER NOT NULL,
            n_crops INTEGER NOT NULL,
            cv_r2_mean NUMERIC(6, 4) NOT NULL,
            cv_rmse_mean NUMERIC(10, 2) NOT NULL,
            artifact_path TEXT NOT NULL,
            sklearn_version VARCHAR(20)
        )
        """,
        # Open-Meteo weather cache table (harvest advisor)
        """
        CREATE TABLE IF NOT EXISTS open_meteo_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district VARCHAR(200) NOT NULL,
            state VARCHAR(100) NOT NULL,
            fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            forecast_json TEXT NOT NULL
        )
        """,
        # Forecast accuracy log — tracks predicted vs actual prices
        """
        CREATE TABLE IF NOT EXISTS forecast_accuracy_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity_name VARCHAR(200) NOT NULL,
            district_name VARCHAR(200) NOT NULL,
            model_version VARCHAR(20) NOT NULL,
            forecast_date DATE NOT NULL,
            target_date DATE NOT NULL,
            predicted_price NUMERIC(10, 2),
            actual_price NUMERIC(10, 2),
            absolute_pct_error REAL,
            checked_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Seasonal price stats — historical median prices by commodity/state/month
        """
        CREATE TABLE IF NOT EXISTS seasonal_price_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity_name VARCHAR(200) NOT NULL,
            state_name VARCHAR(100) NOT NULL,
            month SMALLINT NOT NULL,
            median_price NUMERIC(12, 2) NOT NULL,
            q1_price NUMERIC(12, 2) NOT NULL,
            q3_price NUMERIC(12, 2) NOT NULL,
            iqr_price NUMERIC(12, 2) NOT NULL,
            record_count INTEGER NOT NULL,
            years_of_data SMALLINT NOT NULL,
            is_best BOOLEAN NOT NULL DEFAULT 0,
            is_worst BOOLEAN NOT NULL DEFAULT 0,
            month_rank SMALLINT NOT NULL,
            computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (commodity_name, state_name, month)
        )
        """,
        # Sync log — persists data sync run results
        """
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status VARCHAR(20) NOT NULL,
            started_at TIMESTAMP NOT NULL,
            finished_at TIMESTAMP,
            records_fetched INTEGER NOT NULL DEFAULT 0,
            duration_seconds REAL NOT NULL DEFAULT 0,
            error TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Login attempts — tracks IP-based brute force attempts
        """
        CREATE TABLE IF NOT EXISTS login_attempts (
            id TEXT PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            phone_number VARCHAR(15),
            success BOOLEAN NOT NULL,
            failure_reason VARCHAR(100),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Refresh tokens — JWT refresh token storage
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            revoked BOOLEAN NOT NULL DEFAULT 0,
            revoked_at TIMESTAMP,
            device_info VARCHAR(255),
            ip_address VARCHAR(45),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
        "refresh_tokens",
        "login_attempts",
        "sync_log",
        "seasonal_price_stats",
        "forecast_accuracy_log",
        "open_meteo_cache",
        "yield_model_log",
        "crop_yields",
        "forecast_cache",
        "model_training_log",
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