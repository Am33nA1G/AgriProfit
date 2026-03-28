import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models import User

# Configuration from centralized settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
JWT_ISSUER = "agriprofit-api"
JWT_AUDIENCE = "agriprofit-app"

# Use HTTPBearer for simple "Bearer <token>" auth
security = HTTPBearer()


def hash_value(value: str) -> str:
    """Hash a value using SHA256 (suitable for OTPs)."""
    return hashlib.sha256(value.encode()).hexdigest()


def verify_hashed_value(plain_value: str, hashed_value: str) -> bool:
    """Verify a plain value against a hashed value."""
    return hash_value(plain_value) == hashed_value


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with security claims."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": datetime.now(timezone.utc),
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token with issuer/audience verification."""
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # HTTPBearer returns credentials object
    if not token:
        raise credentials_exception
        
    payload = decode_token(token.credentials)
    if payload is None:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        uuid_id = UUID(user_id)
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(
        User.id == uuid_id,
        User.deleted_at.is_(None),
    ).first()

    if user is None:
        raise credentials_exception
    
    # Check if user is banned (CRITICAL SECURITY CHECK)
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been banned. Please contact support for assistance.",
        )

    return user


# Optional security for public endpoints that can benefit from auth context
optional_security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    token: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User | None:
    """Get the current user if authenticated, otherwise return None."""
    if not token:
        return None

    payload = decode_token(token.credentials)
    if payload is None:
        return None

    user_id: str | None = payload.get("sub")
    if user_id is None:
        return None

    try:
        uuid_id = UUID(user_id)
    except ValueError:
        return None

    user = db.query(User).filter(
        User.id == uuid_id,
        User.deleted_at.is_(None),
    ).first()

    return user


def require_role(required_role: str):
    """Dependency factory that requires a specific role."""
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}",
            )
        return current_user

    return role_checker


def require_admin():
    """Dependency that requires admin role."""
    return require_role("admin")


# =============================================================================
# REFRESH TOKEN HELPERS
# =============================================================================

def create_refresh_token_for_user(db: Session, user: User, device_info: str = None, 
                                  ip_address: str = None) -> tuple:
    """
    Create a new refresh token for a user.
    
    Returns:
        tuple: (RefreshToken model, plaintext token string)
    """
    from app.models import RefreshToken
    
    token_model, plaintext_token = RefreshToken.create_for_user(
        user_id=user.id,
        expires_days=30,
        device_info=device_info,
        ip_address=ip_address,
    )
    db.add(token_model)
    db.commit()
    db.refresh(token_model)
    
    return token_model, plaintext_token


def verify_refresh_token(db: Session, plaintext_token: str) -> User | None:
    """
    Verify a refresh token and return the associated user.
    
    Returns:
        User if valid, None if invalid/expired/revoked
    """
    from app.models import RefreshToken
    
    token_hash = RefreshToken.hash_token(plaintext_token)
    
    token_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
    ).first()
    
    if not token_record or not token_record.is_valid():
        return None
    
    # Update last used
    from datetime import datetime, timezone
    token_record.last_used_at = datetime.now(timezone.utc)
    db.commit()
    
    # Get user
    user = db.query(User).filter(
        User.id == token_record.user_id,
        User.deleted_at.is_(None),
    ).first()
    
    return user


def revoke_refresh_token(db: Session, plaintext_token: str) -> bool:
    """
    Revoke a refresh token.
    
    Returns:
        True if revoked, False if not found
    """
    from app.models import RefreshToken
    
    token_hash = RefreshToken.hash_token(plaintext_token)
    
    token_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
    ).first()
    
    if not token_record:
        return False
    
    token_record.revoke()
    db.commit()
    return True


def revoke_all_user_tokens(db: Session, user_id) -> int:
    """
    Revoke all refresh tokens for a user (logout from all devices).
    
    Returns:
        Number of tokens revoked
    """
    from app.models import RefreshToken
    from datetime import datetime, timezone
    
    count = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,
    ).update({
        "revoked": True,
        "revoked_at": datetime.now(timezone.utc),
    })
    db.commit()
    return count