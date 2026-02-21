"""
Fallback data client for reconciliation.

Uses the data.gov.in historical Agmarknet resource as primary fallback
(same resource proven in backfill_prices.py). A future Ashoka CEDA
integration can be added once their access method is confirmed.

The historical resource (35985678-0d79-46b4-9ed6-6f13308a1d24) supports
per-date filtering via ``filters[Arrival_Date]`` and contains the same
underlying DMI data as the real-time resource but with better coverage
for past dates.
"""
import logging
import time
from datetime import date
from typing import List, Dict, Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# data.gov.in historical Agmarknet resource
HISTORICAL_RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
HISTORICAL_BASE_URL = f"https://api.data.gov.in/resource/{HISTORICAL_RESOURCE_ID}"


class FallbackDataClient:
    """
    Fetches price data from the data.gov.in **historical** Agmarknet
    resource.  This is the same endpoint used by ``backfill_prices.py``
    and provides per-date filtering via ``filters[Arrival_Date]``.

    Records returned are in raw API format with keys:
        State, District, Market, Commodity, Variety,
        Arrival_Date, Min_Price, Max_Price, Modal_Price
    """

    REQUEST_DELAY = 2.0  # seconds between page requests
    MAX_RETRIES = 5
    BATCH_SIZE = 1000

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.data_gov_api_key
        if not self.api_key:
            raise ValueError(
                "data_gov_api_key is required for FallbackDataClient "
                "(set DATA_GOV_API_KEY in .env)"
            )
        self.client = httpx.Client(timeout=180.0)
        self.request_count = 0
        self._last_429 = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_date(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Fetch ALL price records for a single date.

        Args:
            target_date: The date to fetch data for.

        Returns:
            List of raw API records (capitalized keys).
        """
        date_str = target_date.strftime("%d/%m/%Y")
        logger.info("Fetching historical data for %s ...", target_date)

        all_records: List[Dict[str, Any]] = []
        offset = 0

        # First page
        data = self._request(date_str, limit=self.BATCH_SIZE, offset=0)
        total = int(data.get("total", 0))
        records = data.get("records", [])
        all_records.extend(records)

        if total == 0:
            logger.info("  No records available for %s", target_date)
            return []

        # Paginate
        while len(all_records) < total:
            offset += self.BATCH_SIZE
            time.sleep(self.REQUEST_DELAY)
            data = self._request(date_str, limit=self.BATCH_SIZE, offset=offset)
            page = data.get("records", [])
            if not page:
                break
            all_records.extend(page)

        logger.info(
            "  Fetched %d records for %s (%d API requests)",
            len(all_records),
            target_date,
            self.request_count,
        )
        return all_records

    def fetch_date_range(
        self, start: date, end: date
    ) -> Dict[date, List[Dict[str, Any]]]:
        """
        Fetch records for every date in [start, end].

        Returns:
            {date: [records]} mapping.
        """
        from datetime import timedelta

        result: Dict[date, List[Dict[str, Any]]] = {}
        current = start
        while current <= end:
            records = self.fetch_date(current)
            if records:
                result[current] = records
            time.sleep(self.REQUEST_DELAY)
            current += timedelta(days=1)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self, date_str: str, limit: int = 1000, offset: int = 0
    ) -> Dict[str, Any]:
        """Make a single paginated request with retries."""
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
            "offset": offset,
            "filters[Arrival_Date]": date_str,
        }

        last_exc: Optional[Exception] = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    wait = (
                        min(60 * attempt, 300)
                        if self._last_429
                        else min(2 ** attempt, 60)
                    )
                    logger.info("  Retry %d – waiting %ds ...", attempt, wait)
                    time.sleep(wait)

                resp = self.client.get(HISTORICAL_BASE_URL, params=params)
                self.request_count += 1

                if resp.status_code == 429:
                    self._last_429 = True
                    raise httpx.HTTPStatusError(
                        "429 Too Many Requests",
                        request=resp.request,
                        response=resp,
                    )

                self._last_429 = False
                resp.raise_for_status()
                return resp.json()

            except (httpx.HTTPError, httpx.ReadTimeout) as exc:
                last_exc = exc
                if "429" in str(exc):
                    self._last_429 = True
                logger.warning(
                    "  API error (attempt %d): %s", attempt + 1, type(exc).__name__
                )

        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
