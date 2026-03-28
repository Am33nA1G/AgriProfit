from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import User, Commodity, Mandi
from app.auth.security import create_access_token


def create_test_user(
    db: Session,
    phone_number: str = "9876543210",
    role: str = "farmer",
    district: str = "KL-TVM",
) -> User:
    """Create a test user with the given phone number."""
    user = User(
        id=uuid4(),
        phone_number=phone_number,
        role=role,
        district=district,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_admin(
    db: Session,
    phone_number: str = "9876543211",
    district: str = "KL-EKM",
) -> User:
    """Create a test admin user."""
    return create_test_user(
        db=db,
        phone_number=phone_number,
        role="admin",
        district=district,
    )


def create_test_commodity(
    db: Session,
    name: str = "Rice",
    name_local: str | None = None,
    category: str | None = None,
    unit: str | None = None,
) -> Commodity:
    """Create a test commodity with the given name."""
    commodity = Commodity(
        id=uuid4(),
        name=name,
        name_local=name_local,
        category=category,
        unit=unit,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(commodity)
    db.commit()
    db.refresh(commodity)
    return commodity


def create_test_mandi(
    db: Session,
    name: str = "Test Mandi",
    district: str = "KL-TVM",
    state: str = "Kerala",
    market_code: str | None = None,
) -> Mandi:
    """Create a test mandi with the given name."""
    mandi = Mandi(
        id=uuid4(),
        name=name,
        district=district,
        state=state,
        market_code=market_code or f"MKT-{uuid4().hex[:8].upper()}",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(mandi)
    db.commit()
    db.refresh(mandi)
    return mandi


def get_auth_headers(token: str) -> dict:
    """Return headers dict with Authorization Bearer token."""
    return {"Authorization": f"Bearer {token}"}


def get_token_for_user(user: User) -> str:
    """Generate a JWT token for the given user."""
    return create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )


def get_auth_headers_for_user(user: User) -> dict:
    """Generate auth headers for the given user."""
    token = get_token_for_user(user)
    return get_auth_headers(token)