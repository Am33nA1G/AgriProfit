"""
Geocoding utilities for getting lat/lon from addresses.
Uses Nominatim (OpenStreetMap) for free geocoding.
"""
import time
from typing import Optional, Tuple
import requests
from functools import lru_cache


class GeocodingService:
    """Service for geocoding addresses to coordinates."""
    
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "AgriProfit/1.0"
    
    # Rate limiting: Nominatim requires max 1 request per second
    _last_request_time = 0
    _min_request_interval = 1.0  # seconds
    
    @classmethod
    def _rate_limit(cls):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - cls._last_request_time
        if time_since_last < cls._min_request_interval:
            time.sleep(cls._min_request_interval - time_since_last)
        cls._last_request_time = time.time()
    
    @classmethod
    @lru_cache(maxsize=1000)
    def geocode_address(
        cls,
        address: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: str = "India"
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to lat/lon coordinates.
        
        Args:
            address: Full address or location name
            city: City/District name
            state: State name
            country: Country name (default: India)
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        # Build query string
        query_parts = []
        if address:
            query_parts.append(address)
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        if country:
            query_parts.append(country)
        
        query = ", ".join(query_parts)
        
        if not query:
            return None
        
        # Rate limiting
        cls._rate_limit()
        
        # Make request
        try:
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            }
            headers = {
                "User-Agent": cls.USER_AGENT
            }
            
            response = requests.get(
                cls.BASE_URL,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            if results and len(results) > 0:
                result = results[0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                return (lat, lon)
            
            return None
            
        except Exception as e:
            print(f"Geocoding error for '{query}': {e}")
            return None
    
    @classmethod
    def geocode_mandi(
        cls,
        name: str,
        address: Optional[str],
        district: str,
        state: str
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode a mandi location.
        
        Tries multiple strategies:
        1. Full address if available
        2. Name + District + State
        3. District + State
        
        Args:
            name: Mandi name
            address: Full address (optional)
            district: District name
            state: State name
            
        Returns:
            Tuple of (latitude, longitude) or None
        """
        # Strategy 1: Try full address first
        if address:
            coords = cls.geocode_address(address, district, state)
            if coords:
                return coords
        
        # Strategy 2: Try mandi name + district + state
        coords = cls.geocode_address(name, district, state)
        if coords:
            return coords
        
        # Strategy 3: Fall back to district + state center
        coords = cls.geocode_address(district, None, state)
        if coords:
            return coords
        
        return None

    @classmethod
    def get_district_coordinates(
        cls,
        district: str,
        state: str
    ) -> Optional[Tuple[float, float]]:
        """
        Get the coordinates for a district center.
        
        Args:
            district: District name
            state: State name
            
        Returns:
            Tuple of (latitude, longitude) or None
        """
        return cls.geocode_address(district, None, state)


# Singleton instance
geocoding_service = GeocodingService()
