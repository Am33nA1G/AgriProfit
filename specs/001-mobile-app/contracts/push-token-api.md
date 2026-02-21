# API Contract: Push Token Registration

**New endpoint — the only backend addition required.**

## POST /api/v1/notifications/push-token

Register or update a device push token for the authenticated user.

### Request

**Headers**:
- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Body**:
```json
{
  "expo_push_token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
  "device_platform": "android",
  "device_model": "Samsung Galaxy A12",
  "app_version": "1.0.0"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| expo_push_token | string | Yes | Must match `ExponentPushToken[...]` or `ExpoPushToken[...]` pattern |
| device_platform | string | Yes | Must be `ios` or `android` |
| device_model | string | No | Max 100 chars |
| app_version | string | No | Max 20 chars |

### Response

**201 Created** (new token registered):
```json
{
  "id": "uuid",
  "expo_push_token": "ExponentPushToken[xxx]",
  "device_platform": "android",
  "is_active": true,
  "created_at": "2026-02-21T10:00:00Z"
}
```

**200 OK** (existing token updated):
```json
{
  "id": "uuid",
  "expo_push_token": "ExponentPushToken[xxx]",
  "device_platform": "android",
  "is_active": true,
  "updated_at": "2026-02-21T10:00:00Z"
}
```

**Behavior**: Upsert on (user_id, expo_push_token). If token already exists for this user, update `device_model`, `app_version`, `is_active=true`, and `updated_at`.

### Error Responses

- `401 Unauthorized` — Missing or invalid auth token
- `422 Unprocessable Entity` — Invalid push token format
- `429 Too Many Requests` — Rate limited (write tier: 30/min)

---

## DELETE /api/v1/notifications/push-token

Deactivate the current device's push token (called on logout).

### Request

**Headers**:
- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Body**:
```json
{
  "expo_push_token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
}
```

### Response

**200 OK**:
```json
{
  "message": "Push token deactivated"
}
```

**Behavior**: Sets `is_active=false` on the matching (user_id, expo_push_token) record.

---

## Backend Push Send Function

Example utility for sending push notifications via Expo Push API:

```python
# backend/app/integrations/expo_push.py
import httpx
from typing import List

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

async def send_push_notifications(
    tokens: List[str],
    title: str,
    body: str,
    data: dict | None = None,
) -> dict:
    """Send push notifications via Expo Push API.

    Args:
        tokens: List of Expo push tokens
        title: Notification title
        body: Notification body text
        data: Optional data payload for deep linking

    Returns:
        Expo Push API response with ticket IDs
    """
    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
            "data": data or {},
        }
        for token in tokens
    ]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )
        result = response.json()

    # Handle invalid tokens — mark as inactive
    if "data" in result:
        for i, ticket in enumerate(result["data"]):
            if ticket.get("status") == "error":
                if ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                    # Token is invalid — deactivate in DB
                    await _deactivate_token(tokens[i])

    return result


async def _deactivate_token(token: str):
    """Mark a push token as inactive in the database."""
    from app.database.session import SessionLocal
    from app.models.device_push_token import DevicePushToken
    from sqlalchemy import update

    async with SessionLocal() as db:
        await db.execute(
            update(DevicePushToken)
            .where(DevicePushToken.expo_push_token == token)
            .values(is_active=False)
        )
        await db.commit()
```

---

## Integration Points

The `send_push_notifications` function should be called from:

1. **Notification creation** (`POST /notifications/` and `/notifications/bulk`) — after creating the in-app notification, also send push to all active tokens for the target user(s).
2. **Community alert creation** — when a post with `post_type='alert'` is created, send push to all users in the affected district.
3. **Community reply** — when a reply is added, send push to the original post author.
