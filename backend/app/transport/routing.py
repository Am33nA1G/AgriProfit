"""
Routing service for road distance calculation.

Uses OSRM for accurate road distances with DB-backed cache.
Falls back to haversine × 1.35 multiplier if OSRM is unavailable.
Estimated distances are NOT cached — OSRM is retried on next request.
"""
import math
from typing import Literal

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.road_distance_cache import RoadDistanceCache


# Fallback multiplier: haversine (straight-line) → estimated road distance.
# 1.35 is a conservative average for India's road network.
# Plains: ~1.2–1.3; Hills/Northeast: ~1.8–2.5; National average: ~1.35
FALLBACK_MULTIPLIER = 1.35

DistanceSource = Literal["osrm", "estimated"]


def _make_key(lat: float, lon: float) -> str:
    """Build a compact cache key from coordinates rounded to 4 decimal places (~11m)."""
    return f"{round(lat, 4)}:{round(lon, 4)}"


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RoutingService:
    """
    Resolves road distances between two coordinate pairs.

    Lookup order:
    1. DB cache (road_distance_cache table)
    2. OSRM HTTP call — result saved to cache
    3. Fallback: haversine × 1.35 — NOT cached, retried on next request
    """

    def get_distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        db: Session,
    ) -> tuple[float, DistanceSource]:
        """
        Return (distance_km, source) where source is 'osrm' or 'estimated'.
        """
        origin_key = _make_key(lat1, lon1)
        destination_key = _make_key(lat2, lon2)

        # 1. Cache lookup
        cached = (
            db.query(RoadDistanceCache)
            .filter_by(origin_key=origin_key, destination_key=destination_key)
            .first()
        )
        if cached:
            return cached.distance_km, cached.source  # type: ignore[return-value]

        # 2. OSRM call
        osrm_dist = self._call_osrm(lat1, lon1, lat2, lon2)
        if osrm_dist is not None:
            row = RoadDistanceCache(
                origin_key=origin_key,
                destination_key=destination_key,
                src_lat=lat1,
                src_lon=lon1,
                dst_lat=lat2,
                dst_lon=lon2,
                distance_km=osrm_dist,
                source="osrm",
            )
            db.add(row)
            db.commit()
            return osrm_dist, "osrm"

        # 3. Fallback — not cached so OSRM is retried next time
        estimated = round(_haversine(lat1, lon1, lat2, lon2) * FALLBACK_MULTIPLIER, 2)
        return estimated, "estimated"

    def _call_osrm(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float | None:
        """
        Call OSRM routing API. Returns distance in km or None on any failure.
        Note: OSRM uses lon,lat order (not lat,lon).
        """
        url = f"{settings.osrm_base_url}/{lon1},{lat1};{lon2},{lat2}"
        params = {"overview": "false", "alternatives": "false", "steps": "false"}
        try:
            r = httpx.get(url, params=params, timeout=1.5)
            if r.status_code != 200:
                return None
            data = r.json()
            routes = data.get("routes")
            if not routes:
                return None
            return round(routes[0]["distance"] / 1000.0, 2)
        except Exception:
            return None


# Module-level singleton
routing_service = RoutingService()
