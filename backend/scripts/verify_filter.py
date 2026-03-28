"""Verify the date filter is actually filtering correctly."""
import sys
import time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx

API_KEY = "579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15"
RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


def fetch_with_retry(client, params, retries=5):
    for attempt in range(retries + 1):
        try:
            if attempt > 0:
                wait = min(2 ** attempt, 30)
                print(f"  Retry {attempt}/{retries} after {wait}s...")
                time.sleep(wait)
            resp = client.get(BASE_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == retries:
                raise
            print(f"  Error: {e}")


filter_date = "05/02/2026"

with httpx.Client(timeout=180.0) as client:
    # Fetch first page
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 20,
        "offset": 0,
        "filters[arrival_date]": filter_date,
    }
    data = fetch_with_retry(client, params)
    total = data.get("total", 0)
    records = data.get("records", [])

    print(f"Filter: arrival_date = {filter_date}")
    print(f"Total: {total:,}")
    print(f"Records in page: {len(records)}")

    # Check dates in response
    dates = {}
    for r in records:
        d = r.get("Arrival_Date", "?")
        dates[d] = dates.get(d, 0) + 1

    print(f"\nDates in first 20 records:")
    for d, cnt in sorted(dates.items()):
        print(f"  {d}: {cnt} records")

    # Check a middle page
    time.sleep(3)
    mid_offset = min(total // 2, 50000)
    params["offset"] = mid_offset
    data = fetch_with_retry(client, params)
    records = data.get("records", [])

    dates = {}
    for r in records:
        d = r.get("Arrival_Date", "?")
        dates[d] = dates.get(d, 0) + 1

    print(f"\nDates at offset {mid_offset}:")
    for d, cnt in sorted(dates.items()):
        print(f"  {d}: {cnt} records")

    # Check last page
    time.sleep(3)
    end_offset = max(0, total - 20)
    params["offset"] = end_offset
    data = fetch_with_retry(client, params)
    records = data.get("records", [])

    dates = {}
    for r in records:
        d = r.get("Arrival_Date", "?")
        dates[d] = dates.get(d, 0) + 1

    print(f"\nDates at offset {end_offset} (last page):")
    for d, cnt in sorted(dates.items()):
        print(f"  {d}: {cnt} records")
