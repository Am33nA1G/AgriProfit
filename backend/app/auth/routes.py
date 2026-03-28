"""
Authentication routes for OTP-based phone verification.

This module provides endpoints for:
- Requesting OTP codes sent via SMS
- Verifying OTP codes and receiving JWT tokens
- Phone number validation (Indian mobile numbers)
- Profile completion for new users
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.auth.service import AuthService, send_otp_sms
from app.auth.otp import generate_otp
from app.auth.security import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter, RATE_LIMIT_CRITICAL
from app.core.logging_config import log_auth_failure, get_logger
from app.core.ip_protection import IPProtectionService, get_client_ip
from app.models import User

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class OTPRequestSchema(BaseModel):
    """
    Schema for requesting an OTP code.

    The phone number must be a valid 10-digit Indian mobile number
    starting with 6, 7, 8, or 9.
    """
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="10-digit Indian mobile number",
        json_schema_extra={"example": "9876543210"}
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Phone number must contain only digits")
        if v[0] not in "6789":
            raise ValueError("Phone number must start with 6, 7, 8, or 9")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phone_number": "9876543210"
            }
        }
    )


class OTPVerifySchema(BaseModel):
    """
    Schema for verifying an OTP code.

    Both phone number and 6-digit OTP code are required.
    """
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="10-digit Indian mobile number",
        json_schema_extra={"example": "9876543210"}
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit OTP code received via SMS",
        json_schema_extra={"example": "123456"}
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Phone number must contain only digits")
        if v[0] not in "6789":
            raise ValueError("Phone number must start with 6, 7, 8, or 9")
        return v

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phone_number": "9876543210",
                "otp": "123456"
            }
        }
    )


class OTPResponse(BaseModel):
    """Schema for OTP request response."""
    message: str = Field(..., description="Success message")
    expires_in_seconds: int = Field(..., description="OTP validity period in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "OTP sent successfully",
                "expires_in_seconds": 300
            }
        }
    )


class TokenResponse(BaseModel):
    """
    Schema for authentication response containing JWT token.
    """
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication"
    )
    refresh_token: str | None = Field(
        default=None,
        description="Refresh token for obtaining new access tokens"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')"
    )
    is_new_user: bool = Field(
        ...,
        description="True if user was just created, False if existing user"
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "is_new_user": False
            }
        }
    )


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str = Field(..., description="Error message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Invalid OTP"
            }
        }
    )


# =============================================================================
# ROUTES
# =============================================================================

@router.post(
    "/request-otp",
    response_model=OTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Request OTP Code",
    description="Request a 6-digit OTP code to be sent via SMS to the provided phone number.",
    responses={
        200: {
            "description": "OTP sent successfully",
            "model": OTPResponse,
        },
        400: {
            "description": "Invalid phone number format",
            "content": {
                "application/json": {
                    "example": {"detail": "Phone number must start with 6, 7, 8, or 9"}
                }
            }
        },
        429: {
            "description": "Rate limit exceeded - cooldown period active",
            "content": {
                "application/json": {
                    "example": {"detail": "Please wait 45 seconds before requesting a new OTP"}
                }
            }
        },
    }
)
@limiter.limit(RATE_LIMIT_CRITICAL)
async def request_otp(
    request: Request,
    response: Response,
    otp_request: OTPRequestSchema,
    db: Session = Depends(get_db),
) -> OTPResponse:
    """
    Request an OTP code for phone number authentication.

    This endpoint initiates the authentication flow by generating a 6-digit
    OTP code and sending it via SMS to the provided phone number. The OTP
    is valid for 5 minutes.

    A cooldown period of 60 seconds is enforced between OTP requests for
    the same phone number to prevent abuse.

    Args:
        request: HTTP request (for rate limiting)
        otp_request: OTPRequestSchema containing the phone number
        db: Database session (injected)

    Returns:
        OTPResponse with success message and expiry time

    Raises:
        HTTPException 400: Invalid phone number format
        HTTPException 429: Cooldown period not elapsed (rate limited)

    Example:
        >>> response = client.post("/auth/request-otp", json={"phone_number": "9876543210"})
        >>> assert response.status_code == 200
        >>> assert response.json()["expires_in_seconds"] == 300
    """
    service = AuthService(db)

    # Check cooldown using settings
    can_request, seconds_remaining = service.can_request_otp(
        otp_request.phone_number, 
        cooldown_seconds=settings.otp_cooldown_seconds
    )
    if not can_request:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {seconds_remaining} seconds before requesting a new OTP",
        )

    # Generate OTP
    if settings.enable_test_otp and settings.test_otp:
        otp = settings.test_otp
    else:
        otp = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # Create OTP request
    service.create_otp_request(otp_request.phone_number, otp, expires_at)

    # In development with no SMS provider, log the OTP to the console
    if settings.is_development and not settings.sms_provider:
        print(f"\n{'='*50}")
        print(f"  [DEV] OTP for {otp_request.phone_number}: {otp}")
        print(f"{'='*50}\n")
        logger.warning(
            "[DEV] OTP for ***%s: %s (no SMS provider configured)",
            otp_request.phone_number[-4:], otp,
        )
    elif settings.sms_provider:
        send_otp_sms(otp_request.phone_number, otp)
    else:
        logger.info("[PROD] OTP generated for ***%s", otp_request.phone_number[-4:])

    # In production, send OTP via SMS
    return OTPResponse(
        message="OTP sent successfully",
        expires_in_seconds=300,
    )


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and Get Token",
    description="Verify the OTP code and receive a JWT access token for API authentication.",
    responses={
        200: {
            "description": "OTP verified successfully, token issued",
            "model": TokenResponse,
        },
        400: {
            "description": "Invalid or expired OTP",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_otp": {
                            "summary": "Invalid OTP",
                            "value": {"detail": "Invalid OTP"}
                        },
                        "expired_otp": {
                            "summary": "Expired OTP",
                            "value": {"detail": "OTP has expired"}
                        },
                        "no_otp": {
                            "summary": "No OTP request found",
                            "value": {"detail": "No OTP request found for this phone number"}
                        }
                    }
                }
            }
        },
    }
)
@limiter.limit(RATE_LIMIT_CRITICAL)
async def verify_otp(
    request: Request,
    response: Response,
    verify_data: OTPVerifySchema,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Verify OTP and receive JWT access token.

    This endpoint completes the authentication flow by verifying the OTP
    code. On successful verification:
    - If the user exists, a new JWT token is issued
    - If the user doesn't exist, a new account is created automatically

    The JWT token should be included in subsequent API requests as:
    `Authorization: Bearer <token>`

    Args:
        request: HTTP request (for rate limiting and IP logging)
        verify_data: OTPVerifySchema with phone number and OTP code
        db: Database session (injected)

    Returns:
        TokenResponse with JWT access token and user status

    Raises:
        HTTPException 400: Invalid OTP, expired OTP, or no OTP request found

    Example:
        >>> response = client.post("/auth/verify-otp", json={
        ...     "phone_number": "9876543210",
        ...     "otp": "123456"
        ... })
        >>> assert response.status_code == 200
        >>> token = response.json()["access_token"]
    """
    service = AuthService(db)
    ip_service = IPProtectionService(db)

    # Get client IP for logging and protection
    client_ip = get_client_ip(request)

    # Check if IP is blocked due to too many failures
    if ip_service.is_ip_blocked(client_ip):
        remaining = ip_service.get_block_remaining_seconds(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {remaining} seconds.",
        )

    # Verify OTP
    success, message = service.verify_otp(verify_data.phone_number, verify_data.otp)
    if not success:
        # Record failed attempt
        ip_service.record_attempt(
            ip_address=client_ip,
            success=False,
            phone_number=verify_data.phone_number,
            failure_reason=message,
        )
        # Log authentication failure
        log_auth_failure(
            phone_number=verify_data.phone_number,
            ip_address=client_ip or "unknown",
            reason=message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    # Record successful attempt and clear IP history
    ip_service.record_attempt(
        ip_address=client_ip,
        success=True,
        phone_number=verify_data.phone_number,
    )
    ip_service.clear_ip_attempts(client_ip)

    # Get or create user
    user, is_new = service.get_or_create_user(verify_data.phone_number)
    
    # Check if user is banned (CRITICAL SECURITY CHECK)
    if user.is_banned:
        log_auth_failure(
            phone_number=verify_data.phone_number,
            ip_address=client_ip or "unknown",
            reason="Account banned",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been banned. Please contact support for assistance.",
        )

    # Generate tokens
    tokens = service.generate_tokens(user)
    
    # Create refresh token
    from app.auth.security import create_refresh_token_for_user
    _, refresh_token = create_refresh_token_for_user(
        db, user, 
        device_info=request.headers.get("User-Agent"),
        ip_address=client_ip,
    )

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=refresh_token,
        token_type=tokens["token_type"],
        is_new_user=is_new,
    )


# =============================================================================
# REGISTRATION COMPLETION ENDPOINT
# =============================================================================

class CompleteProfileSchema(BaseModel):
    """
    Schema for completing user profile after OTP verification.
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
        json_schema_extra={"example": "Rajesh Kumar"}
    )
    age: int = Field(
        ...,
        ge=18,
        le=120,
        description="User's age in years",
        json_schema_extra={"example": 35}
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="User's state in India",
        json_schema_extra={"example": "Maharashtra"}
    )
    district: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's district",
        json_schema_extra={"example": "Pune"}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Rajesh Kumar",
                "age": 35,
                "state": "Maharashtra",
                "district": "Pune"
            }
        }
    )


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""
    id: str = Field(..., description="User ID")
    phone_number: str = Field(..., description="User's phone number")
    name: str | None = Field(None, description="User's full name")
    age: int | None = Field(None, description="User's age")
    state: str | None = Field(None, description="User's state")
    district: str | None = Field(None, description="User's district")
    role: str = Field(..., description="User role (farmer/admin)")
    language: str = Field(..., description="Preferred language")
    is_profile_complete: bool = Field(..., description="Whether profile is complete")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "phone_number": "9876543210",
                "name": "Rajesh Kumar",
                "age": 35,
                "state": "Maharashtra",
                "district": "Pune",
                "role": "farmer",
                "language": "en",
                "is_profile_complete": True
            }
        }
    )


@router.post(
    "/complete-profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete User Profile",
    description="Complete the user profile after OTP verification. Requires authentication.",
    responses={
        200: {
            "description": "Profile completed successfully",
            "model": UserProfileResponse,
        },
        401: {
            "description": "Unauthorized - invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        },
        400: {
            "description": "Invalid profile data",
            "content": {
                "application/json": {
                    "example": {"detail": "Profile already completed"}
                }
            }
        },
    }
)
async def complete_profile(
    profile_data: CompleteProfileSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Complete user profile with name, age, state, and district.

    This endpoint should be called after successful OTP verification
    for new users to complete their registration.

    Args:
        profile_data: CompleteProfileSchema with user details
        db: Database session (injected)
        current_user: Authenticated user from JWT token

    Returns:
        UserProfileResponse with updated user profile

    Raises:
        HTTPException 401: Invalid or missing authentication token
        HTTPException 400: Profile already completed
    """
    # Update user profile
    current_user.name = profile_data.name
    current_user.age = profile_data.age
    current_user.state = profile_data.state
    current_user.district = profile_data.district
    current_user.is_profile_complete = True
    
    db.commit()
    db.refresh(current_user)

    return UserProfileResponse(
        id=str(current_user.id),
        phone_number=current_user.phone_number,
        name=current_user.name,
        age=current_user.age,
        state=current_user.state,
        district=current_user.district,
        role=current_user.role,
        language=current_user.language,
        is_profile_complete=current_user.is_profile_complete,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Get the current authenticated user's profile.",
    responses={
        200: {
            "description": "User profile retrieved successfully",
            "model": UserProfileResponse,
        },
        401: {
            "description": "Unauthorized - invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        },
    }
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Get the current authenticated user's profile.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        UserProfileResponse with user profile data
    """
    return UserProfileResponse(
        id=str(current_user.id),
        phone_number=current_user.phone_number,
        name=current_user.name,
        age=current_user.age,
        state=current_user.state,
        district=current_user.district,
        role=current_user.role,
        language=current_user.language,
        is_profile_complete=current_user.is_profile_complete,
    )


# =============================================================================
# REFRESH TOKEN ENDPOINTS
# =============================================================================

class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., description="The refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""
    access_token: str
    token_type: str = "bearer"


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Use a refresh token to get a new access token.",
    responses={
        200: {"description": "New access token issued"},
        401: {"description": "Invalid or expired refresh token"},
    }
)
async def refresh_access_token(
    request: Request,
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> RefreshTokenResponse:
    """
    Refresh the access token using a valid refresh token.
    
    Use this endpoint when the access token expires to get a new one
    without requiring the user to re-authenticate with OTP.
    """
    from app.auth.security import verify_refresh_token, create_access_token
    
    user = verify_refresh_token(db, data.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    
    return RefreshTokenResponse(access_token=access_token)


class LogoutRequest(BaseModel):
    """Schema for logout request."""
    refresh_token: str = Field(..., description="The refresh token to revoke")
    logout_all: bool = Field(default=False, description="Revoke all sessions")


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    success: bool
    message: str


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Revoke refresh token(s) to log out.",
    responses={
        200: {"description": "Logged out successfully"},
        401: {"description": "Not authenticated"},
    }
)
async def logout(
    data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """
    Logout by revoking refresh tokens.
    
    If logout_all is True, all refresh tokens for the user are revoked,
    effectively logging out from all devices.
    """
    from app.auth.security import revoke_refresh_token, revoke_all_user_tokens
    
    if data.logout_all:
        count = revoke_all_user_tokens(db, current_user.id)
        return LogoutResponse(
            success=True,
            message=f"Logged out from all {count} sessions",
        )
    else:
        revoked = revoke_refresh_token(db, data.refresh_token)
        if not revoked:
            return LogoutResponse(
                success=False,
                message="Refresh token not found or already revoked",
            )
        return LogoutResponse(
            success=True,
            message="Logged out successfully",
        )

