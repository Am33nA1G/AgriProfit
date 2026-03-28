"""Test exact date filtering approaches on historical API."""
import sys
import time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx

API_KEY = "579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15"
RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


def fetch_retry(client, params, retries=5):
    for attempt in range(retries + 1):
        try:
            if attempt > 0:
                time.sleep(min(2 ** attempt, 30))
            resp = client.get(BASE_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == retries:
                raise
            print(f"  retry {attempt+1}...")


with httpx.Client(timeout=180.0) as client:
    # Test 1: Use a date starting with "13" (unique prefix)
    # 13/11/2025 should NOT match 13/12/2025 if exact
    print("TEST 1: Filter with 13/11/2025 (unique day prefix)")
    data = fetch_retry(client, {
        "api-key": API_KEY, "format": "json",
        "limit": 5, "offset": 0,
        "filters[arrival_date]": "13/11/2025",
    })
    total = data.get("total", 0)
    records = data.get("records", [])
    dates = set(r.get("Arrival_Date", "?") for r in records)
    print(f"  Total: {total:,}, Dates: {dates}")

    time.sleep(3)

    # Test 2: Use a longer/exact format
    print("\nTEST 2: Filter with full date (different format attempts)")
    for filter_val in ["13/11/2025", "2025-11-13", "13-Nov-2025", "13-11-2025"]:
        try:
            data = fetch_retry(client, {
                "api-key": API_KEY, "format": "json",
                "limit": 5, "offset": 0,
                "filters[arrival_date]": filter_val,
            })
            total = data.get("total", 0)
            records = data.get("records", [])
            dates = set(r.get("Arrival_Date", "?") for r in records)
            print(f"  '{filter_val}': total={total:,}, dates={dates}")
        except Exception as e:
            print(f"  '{filter_val}': ERROR - {e}")
        time.sleep(2)

    # Test 3: Try Arrival_Date (capitalized) field name
    print("\nTEST 3: Capitalized field name")
    for fk in ["filters[Arrival_Date]", "filters[Arrival_Date.keyword]"]:
        try:
            data = fetch_retry(client, {
                "api-key": API_KEY, "format": "json",
                "limit": 5, "offset": 0,
                fk: "13/11/2025",
            })
            total = data.get("total", 0)
            records = data.get("records", [])
            dates = set(r.get("Arrival_Date", "?") for r in records)
            print(f"  {fk}: total={total:,}, dates={dates}")
        except Exception as e:
            print(f"  {fk}: ERROR")
        time.sleep(2)

    # Test 4: Try the daily resource which might have proper filters
    print("\nTEST 4: Daily resource with state filter for volume estimate")
    DAILY_RES = "9ef84268-d588-465a-a308-a864a43d0070"
    daily_url = f"https://api.data.gov.in/resource/{DAILY_RES}"
    data = fetch_retry(client, {
        "api-key": API_KEY, "format": "json",
        "limit": 3, "offset": 0,
    })
    total = data.get("total", 0)
    records = data.get("records", [])
    print(f"  Daily resource total: {total:,}")
    if records:
        print(f"  Date: {records[0].get('arrival_date', '?')}")
        print(f"  Fields: {list(records[0].keys())}")
