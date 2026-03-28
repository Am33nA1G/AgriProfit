"""OpenMeteo weather client with DB cache."""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.open_meteo_cache import OpenMeteoCache

logger = logging.getLogger(__name__)

# Load district coords once at import.
# This file is at backend/app/harvest_advisor/weather_client.py
# district_coords.json is at backend/app/transport/district_coords.json
# Path: parent (harvest_advisor) -> parent (app) / transport / district_coords.json
_COORDS_PATH = Path(__file__).resolve().parent.parent / "transport" / "district_coords.json"

_DISTRICT_COORDS: dict[str, list[float]] = {}
if _COORDS_PATH.exists():
    with open(_COORDS_PATH, encoding="utf-8") as f:
        _DISTRICT_COORDS = json.load(f)


class OpenMeteoClient:
    """Fetch 16-day weather forecast from Open-Meteo with DB caching."""

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def fetch_forecast(self, district: str, state: str, db: Session) -> dict | None:
        """
        Fetch forecast for a district.

        1. Check DB cache (expires_at > now)
        2. Look up coords
        3. Call Open-Meteo API
        4. Upsert cache row (expires in 6h)
        """
        # 1. Cache lookup
        try:
            now = datetime.now(timezone.utc)
            row = db.execute(
                select(OpenMeteoCache).where(
                    OpenMeteoCache.district == district,
                    OpenMeteoCache.state == state,
                    OpenMeteoCache.expires_at > now,
                )
            ).scalar_one_or_none()

            if row is not None:
                return json.loads(row.forecast_json)
        except Exception as exc:
            logger.debug(f"Cache lookup failed for {district}: {exc}")

        # 2. Look up coordinates
        coords = _DISTRICT_COORDS.get(district)
        if coords is None:
            # Try case-insensitive match
            for key, val in _DISTRICT_COORDS.items():
                if key.lower() == district.lower():
                    coords = val
                    break
        if coords is None:
            logger.debug(f"No coordinates found for district={district}")
            return None

        lat, lon = coords[0], coords[1]

        # 3. Call Open-Meteo API
        try:
            resp = httpx.get(
                self.FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "forecast_days": 16,
                    "timezone": "Asia/Kolkata",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(f"Open-Meteo API call failed for {district}: {exc}")
            return None

        # 4. Upsert cache
        try:
            forecast_str = json.dumps(data)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=6)

            existing = db.execute(
                select(OpenMeteoCache).where(
                    OpenMeteoCache.district == district,
                    OpenMeteoCache.state == state,
                )
            ).scalar_one_or_none()

            if existing:
                existing.forecast_json = forecast_str
                existing.expires_at = expires_at
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                entry = OpenMeteoCache(
                    district=district,
                    state=state,
                    forecast_json=forecast_str,
                    expires_at=expires_at,
                )
                db.add(entry)
            db.commit()
        except Exception as exc:
            logger.debug(f"Cache upsert failed for {district}: {exc}")
            db.rollback()

        return data
