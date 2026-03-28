from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import User
from app.users.schemas import UserUpdate, KERALA_DISTRICTS


# Valid roles
VALID_ROLES = ("farmer", "admin")


class UserService:
    """Service class for User operations."""

    def __init__(self, db: Session):
        self.db = db

    def _validate_phone(self, phone_number: str) -> None:
        """Validate phone number format."""
        if not phone_number:
            raise ValueError("Phone number is required")
        if len(phone_number) != 10:
            raise ValueError("Phone number must be 10 digits")
        if phone_number[0] not in "6789":
            raise ValueError("Phone number must start with 6, 7, 8, or 9")
        if not phone_number.isdigit():
            raise ValueError("Phone number must contain only digits")

    def _validate_role(self, role: str) -> None:
        """Validate user role."""
        if role not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(VALID_ROLES)}")

    def _validate_district(self, district: str | None) -> None:
        """Validate district if provided."""
        if district is not None and district not in KERALA_DISTRICTS:
            raise ValueError(f"District must be one of: {', '.join(KERALA_DISTRICTS)}")

    def get_by_id(self, user_id: UUID) -> User | None:
        """Get a user by ID."""
        return self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
        ).first()

    def get_by_phone(self, phone_number: str) -> User | None:
        """Get a user by phone number."""
        return self.db.query(User).filter(
            User.phone_number == phone_number,
            User.deleted_at.is_(None),
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        role: str | None = None,
        district: str | None = None,
    ) -> list[User]:
        """Get all users with optional filtering."""
        query = self.db.query(User).filter(User.deleted_at.is_(None))

        if role:
            if role not in VALID_ROLES:
                return []
            query = query.filter(User.role == role)

        if district:
            if district not in KERALA_DISTRICTS:
                return []
            query = query.filter(User.district == district)

        return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    def create(
        self,
        phone_number: str,
        role: str = "farmer",
        language: str = "en",
        district: str | None = None,
    ) -> User:
        """Create a new user."""
        # Validate inputs
        self._validate_phone(phone_number)
        self._validate_role(role)
        self._validate_district(district)

        if language not in ("en", "ml"):
            raise ValueError("Language must be 'en' or 'ml'")

        try:
            user = User(
                phone_number=phone_number,
                role=role,
                language=language,
                district=district,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def update(self, user_id: UUID, user_data: UserUpdate) -> User | None:
        """Update an existing user."""
        user = self.get_by_id(user_id)

        if not user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)

        if not update_data:
            return user

        try:
            for field, value in update_data.items():
                setattr(user, field, value)

            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def update_user(self, user: User, user_data: UserUpdate) -> User:
        """Update a user object directly."""
        update_data = user_data.model_dump(exclude_unset=True)

        if not update_data:
            return user

        try:
            for field, value in update_data.items():
                setattr(user, field, value)

            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def soft_delete(self, user_id: UUID) -> bool:
        """Soft delete a user by setting deleted_at."""
        user = self.get_by_id(user_id)

        if not user:
            return False

        try:
            user.deleted_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def restore(self, user_id: UUID) -> User | None:
        """Restore a soft-deleted user."""
        user = self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.isnot(None),
        ).first()

        if not user:
            return None

        try:
            user.deleted_at = None
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def count(self, role: str | None = None, district: str | None = None) -> int:
        """Count users with optional filtering."""
        query = self.db.query(User).filter(User.deleted_at.is_(None))

        if role:
            if role not in VALID_ROLES:
                return 0
            query = query.filter(User.role == role)

        if district:
            if district not in KERALA_DISTRICTS:
                return 0
            query = query.filter(User.district == district)

        return query.count()

    def is_profile_complete(self, user: User) -> bool:
        """Check if user profile is complete."""
        return user.district is not None

    def get_by_district(self, district: str) -> list[User]:
        """Get all users in a specific district."""
        if district not in KERALA_DISTRICTS:
            return []

        return self.db.query(User).filter(
            User.district == district,
            User.deleted_at.is_(None),
        ).order_by(User.created_at.desc()).all()
    
    