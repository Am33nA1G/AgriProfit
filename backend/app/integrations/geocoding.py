"""
Geocoding Service

Provides geocoding functionality to fetch latitude/longitude for mandis
using the Nominatim/OpenStreetMap geocoding service with fallback to
a pre-populated district database for Indian locations.
"""
import logging
import time
from typing import Optional, Tuple
from urllib.parse import quote

import httpx

from app.integrations.district_geocodes import get_district_geocode

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    Service for geocoding mandi addresses to lat/lng coordinates.
    
    Uses Nominatim (OpenStreetMap) free geocoding API with rate limiting.
    Rate limit: 1 request per second as per Nominatim usage policy.
    """
    
    BASE_URL = "https://nominatim.openstreetmap.org"
    USER_AGENT = "AgriProfit/1.0 (Agricultural Market Platform)"
    
    def __init__(self):
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 1 second between requests
    
    def _rate_limit(self):
        """Enforce rate limiting (1 req/sec)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def geocode_mandi(
        self,
        mandi_name: str,
        district: str,
        state: str,
        country: str = "India"
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode a mandi address to latitude/longitude.
        
        Tries Nominatim first, falls back to district geocode database.
        
        Args:
            mandi_name: Name of the mandi/market
            district: District name
            state: State name
            country: Country name (default: India)
        
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        # First, try district database (fast, no API calls)
        district_coords = get_district_geocode(district, state)
        if district_coords:
            logger.info(
                f"Using district database geocode for '{mandi_name}' "
                f"({district}, {state}) -> {district_coords}"
            )
            return district_coords
        
        # Fallback to Nominatim (may be rate-limited)
        queries = [
            # Try district + state (better success rate than full address)
            f"{district}, {state}, {country}",
        ]
        
        for query in queries:
            self._rate_limit()
            
            try:
                coords = self._geocode_query(query)
                if coords:
                    logger.info(
                        f"Geocoded '{mandi_name}' ({district}, {state}) "
                        f"using Nominatim query '{query}' -> {coords}"
                    )
                    return coords
            except Exception as e:
                logger.warning(
                    f"Nominatim geocoding failed for query '{query}': {e}"
                )
                continue
        
        logger.warning(
            f"Failed to geocode mandi: {mandi_name}, {district}, {state}"
        )
        return None
    
    def _geocode_query(self, query: str) -> Optional[Tuple[float, float]]:
        """
        Execute a single geocoding query.
        
        Args:
            query: Search query string
        
        Returns:
            Tuple of (latitude, longitude) or None
        """
        url = f"{self.BASE_URL}/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        
        headers = {
            "User-Agent": self.USER_AGENT,
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            results = response.json()
            if not results:
                return None
            
            result = results[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            
            return (lat, lon)
    
    def geocode_district_center(
        self,
        district: str,
        state: str,
        country: str = "India"
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode just the district center (useful as fallback).
        
        Args:
            district: District name
            state: State name
            country: Country name (default: India)
        
        Returns:
            Tuple of (latitude, longitude) or None
        """
        query = f"{district}, {state}, {country}"
        self._rate_limit()
        
        try:
            coords = self._geocode_query(query)
            if coords:
                logger.info(
                    f"Geocoded district center '{district}, {state}' -> {coords}"
                )
            return coords
        except Exception as e:
            logger.warning(
                f"Failed to geocode district center '{district}, {state}': {e}"
            )
            return None


_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get the singleton GeocodingService instance."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
