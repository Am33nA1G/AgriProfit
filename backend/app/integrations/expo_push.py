"""
Expo Push Notification utility.

Sends push notifications via the Expo Push API.
Handles DeviceNotRegistered errors by deactivating invalid tokens.
"""
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notifications(
    db: Session,
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> list[str]:
    """
    Send push notifications to a list of Expo push tokens.

    Returns list of ticket IDs for successful sends.
    Deactivates tokens that return DeviceNotRegistered.
    """
    if not tokens:
        return []

    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "data": data or {},
            "sound": "default",
            "priority": "high",
        }
        for token in tokens
    ]

    ticket_ids: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            tickets = result.get("data", [])
            invalid_tokens: list[str] = []

            for i, ticket in enumerate(tickets):
                if ticket.get("status") == "ok":
                    ticket_ids.append(ticket.get("id", ""))
                elif ticket.get("status") == "error":
                    details = ticket.get("details", {})
                    if details.get("error") == "DeviceNotRegistered":
                        # Mark token as invalid
                        if i < len(tokens):
                            invalid_tokens.append(tokens[i])

            # Deactivate invalid tokens
            if invalid_tokens:
                _deactivate_tokens(db, invalid_tokens)

    except httpx.HTTPError as e:
        logger.error(f"Expo push notification error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending push notifications: {e}")

    return ticket_ids


def _deactivate_tokens(db: Session, tokens: list[str]) -> None:
    """Mark push tokens as inactive when Expo reports DeviceNotRegistered."""
    try:
        from app.models.device_push_token import DevicePushToken
        db.query(DevicePushToken).filter(
            DevicePushToken.expo_push_token.in_(tokens)
        ).update({"is_active": False}, synchronize_session=False)
        db.commit()
        logger.info(f"Deactivated {len(tokens)} invalid push tokens")
    except Exception as e:
        logger.error(f"Error deactivating push tokens: {e}")
        db.rollback()
