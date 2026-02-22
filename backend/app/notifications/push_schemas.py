import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


EXPO_PUSH_TOKEN_RE = re.compile(r"^ExponentPushToken\[.+\]$")


class PushTokenRegister(BaseModel):
    expo_push_token: str
    device_platform: Literal["ios", "android"]
    device_model: str | None = None
    app_version: str | None = None

    @field_validator("expo_push_token")
    @classmethod
    def validate_expo_token(cls, v: str) -> str:
        if not EXPO_PUSH_TOKEN_RE.match(v):
            raise ValueError("Invalid Expo push token format. Expected: ExponentPushToken[...]")
        return v


class PushTokenResponse(BaseModel):
    id: UUID
    expo_push_token: str
    device_platform: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PushTokenDeactivate(BaseModel):
    expo_push_token: str
