"""
Data.gov.in API Client

Fetches real-time mandi prices from the Ministry of Agriculture's open data portal.
API Endpoint: https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070
"""
import os
import time
import logging
from datetime import datetime
from typing import Optional
from functools import lru_cache

import httpx

logger = logging.getLogger(__name__)


class DataGovClient:
    """Client for data.gov.in API to fetch mandi prices.

    Supports automatic API key rotation: when the active key fails with an
    auth error or timeout, the next key in the list is tried before giving up.
    Add extra free keys via DATA_GOV_API_KEYS_FALLBACK (comma-separated).
    """

    BASE_URL = "https://api.data.gov.in/resource"
    RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

    # Adaptive page delay: starts at BASE, increases on 429, resets on success
    _PAGE_DELAY_BASE = 1.0
    _PAGE_DELAY_MAX = 10.0

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the client.

        Args:
            api_key: Override key. When None, all keys are loaded from settings.
        """
        if api_key:
            self._keys = [api_key]
        else:
            try:
                from app.core.config import settings
                self._keys = settings.all_data_gov_keys
            except Exception:
                self._keys = []

        if not self._keys:
            env_key = os.getenv("DATA_GOV_API_KEY")
            if env_key:
                self._keys = [env_key]

        if not self._keys:
            raise ValueError("No DATA_GOV_API_KEY configured")

        self._key_index = 0  # index of currently active key
        self._page_delay = self._PAGE_DELAY_BASE  # adaptive delay between paginated requests
        # Connect timeout 10s, read timeout 30s — data.gov.in responds in <5s when healthy.
        # Keeping timeout low means 502 hangs fail fast instead of wasting 60+ seconds.
        self.client = httpx.Client(timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0))

    @property
    def api_key(self) -> str:
        """Currently active API key."""
        return self._keys[self._key_index]

    def _rotate_key(self) -> bool:
        """Advance to the next key. Returns True if a new key is available."""
        if self._key_index + 1 < len(self._keys):
            self._key_index += 1
            logger.warning(
                "Rotating to fallback API key #%d/%d",
                self._key_index + 1,
                len(self._keys),
            )
            return True
        return False
    
    def _build_url(self, **params) -> str:
        """Build API URL with parameters."""
        base_params = {
            "api-key": self.api_key,
            "format": "json",
        }
        base_params.update(params)
        
        query = "&".join(f"{k}={v}" for k, v in base_params.items() if v is not None)
        return f"{self.BASE_URL}/{self.RESOURCE_ID}?{query}"
    
    def fetch_prices(
        self,
        limit: int = 1000,
        offset: int = 0,
        state: Optional[str] = None,
        district: Optional[str] = None,
        commodity: Optional[str] = None,
        market: Optional[str] = None,
        arrival_date: Optional[str] = None,
        retries: int = 3,
    ) -> dict:
        """
        Fetch mandi prices with optional filters.

        Args:
            limit: Max records to fetch (max 1000)
            offset: Records to skip for pagination
            state: Filter by state name
            district: Filter by district name
            commodity: Filter by commodity name
            market: Filter by market name
            arrival_date: Filter by arrival date (DD/MM/YYYY format)
            retries: Number of retries for failed requests

        Returns:
            API response dict with 'records', 'total', 'count' etc.
        """
        filters = {}
        if state:
            filters["filters[state.keyword]"] = state
        if district:
            filters["filters[district]"] = district
        if commodity:
            filters["filters[commodity]"] = commodity
        if market:
            filters["filters[market]"] = market
        if arrival_date:
            filters["filters[arrival_date]"] = arrival_date
        
        import time
        last_exception = None

        # Try every key; within each key allow `retries` attempts
        for key_attempt in range(len(self._keys)):
            url = self._build_url(limit=limit, offset=offset, **filters)
            for attempt in range(retries + 1):
                try:
                    if attempt > 0:
                        wait = min(3 ** attempt, 30)  # 3s, 9s, 27s (capped at 30s)
                        logger.info("Retrying request (attempt %d/%d, key #%d, wait %ds)…",
                                    attempt, retries, self._key_index + 1, wait)
                        time.sleep(wait)

                    response = self.client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    # Success — reset adaptive page delay
                    self._page_delay = self._PAGE_DELAY_BASE
                    logger.info(
                        "Fetched %d records (total: %d) using key #%d",
                        data.get("count", 0), data.get("total", 0), self._key_index + 1,
                    )
                    return data

                except httpx.HTTPStatusError as e:
                    last_exception = e
                    if e.response.status_code in (401, 403):
                        # Auth failure — key is invalid/revoked, rotate immediately
                        logger.warning("Key #%d auth error (%d), rotating…",
                                       self._key_index + 1, e.response.status_code)
                        break  # break inner loop, try next key
                    if e.response.status_code == 429:
                        # Rate limited — respect Retry-After header or double page delay
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            wait = min(float(retry_after), 60)
                        else:
                            wait = min(self._page_delay * 2, self._PAGE_DELAY_MAX)
                        self._page_delay = min(self._page_delay * 2, self._PAGE_DELAY_MAX)
                        logger.warning(
                            "Rate limited (429). Waiting %.1fs, page delay now %.1fs",
                            wait, self._page_delay,
                        )
                        time.sleep(wait)
                        continue  # retry same attempt without incrementing
                    logger.warning("HTTP error: %s", e)

                except (httpx.TimeoutException, httpx.TransportError) as e:
                    last_exception = e
                    logger.warning("Network error (key #%d, attempt %d): %s",
                                   self._key_index + 1, attempt + 1, e)

            if not self._rotate_key():
                break  # no more keys to try

        logger.error("All %d key(s) exhausted — data.gov.in unreachable.", len(self._keys))
        raise last_exception
    
    def fetch_all_prices(self, batch_size: int = 1000) -> list[dict]:
        """
        Fetch ALL price records using pagination.
        
        Args:
            batch_size: Records per request (default 1000, max 1000)
            
        Returns:
            List of all price records
        """
        all_records = []
        offset = 0
        
        # First request to get total count
        data = self.fetch_prices(limit=batch_size, offset=0)
        total = int(data.get("total", 0))
        all_records.extend(data.get("records", []))
        
        logger.info(f"Fetching {total} total records from data.gov.in...")
        
        # Paginate through remaining records
        while len(all_records) < total:
            offset += batch_size
            
            # Adaptive delay — increases automatically if API returns 429
            time.sleep(self._page_delay)
            
            data = self.fetch_prices(limit=batch_size, offset=offset)
            records = data.get("records", [])
            if not records:
                break
            all_records.extend(records)
            logger.info(f"Progress: {len(all_records)}/{total} records")
        
        logger.info(f"Fetched {len(all_records)} total records")
        return all_records
    
    def fetch_prices_for_dates(
        self,
        dates: list[datetime],
        batch_size: int = 1000,
    ) -> list[dict]:
        """
        Fetch all price records for specific dates (incremental sync).

        Iterates over the given dates, fetching all pages for each date,
        and returns the combined records.

        Args:
            dates: List of dates to fetch (each filtered via exact arrival_date match).
            batch_size: Records per page (default/max 1000).

        Returns:
            Combined list of all records across the requested dates.
        """
        all_records: list[dict] = []

        for dt in dates:
            date_str = dt.strftime("%d/%m/%Y")
            offset = 0
            day_total = None

            while True:
                data = self.fetch_prices(
                    limit=batch_size,
                    offset=offset,
                    arrival_date=date_str,
                )
                records = data.get("records", [])
                if day_total is None:
                    day_total = int(data.get("total", 0))

                if not records:
                    break

                all_records.extend(records)
                offset += batch_size

                if offset >= day_total:
                    break

                time.sleep(self._page_delay)

            logger.info(
                "Fetched %d records for %s", day_total or 0, date_str,
            )

        logger.info(
            "Incremental fetch complete: %d records across %d day(s)",
            len(all_records), len(dates),
        )
        return all_records

    def get_unique_states(self) -> list[str]:
        """Get list of unique states from API data."""
        # Fetch a sample to extract states
        data = self.fetch_prices(limit=5000)
        records = data.get("records", [])
        states = sorted(set(r.get("state", "") for r in records if r.get("state")))
        return states
    
    def get_unique_commodities(self) -> list[str]:
        """Get list of unique commodities from API data."""
        data = self.fetch_prices(limit=5000)
        records = data.get("records", [])
        commodities = sorted(set(r.get("commodity", "") for r in records if r.get("commodity")))
        return commodities
    
    def parse_arrival_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse arrival_date from API format (DD/MM/YYYY).
        
        Args:
            date_str: Date string in DD/MM/YYYY format
            
        Returns:
            datetime object or None if parsing fails
        """
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except (ValueError, TypeError):
            return None
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# Singleton instance
_client: Optional[DataGovClient] = None


def get_data_gov_client() -> DataGovClient:
    """Get or create the singleton DataGovClient instance."""
    global _client
    if _client is None:
        _client = DataGovClient()
    return _client
