"""
Test the historical Agmarknet resource with date filtering.
Resource: 35985678-0d79-46b4-9ed6-6f13308a1d24 (77M records)
"""
import sys
import os
import json
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx

API_KEY = "579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15"
RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


def fetch(extra_params, timeout=180.0):
    params = {"api-key": API_KEY, "format": "json"}
    params.update(extra_params)
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()


def test_date_filter():
    """Test date filtering on the historical resource."""
    print("=" * 60)
    print("TEST: Date Filtering on Historical Resource")
    print("=" * 60)

    # Try different filter key formats
    test_date = "01/01/2026"
    filter_keys = [
        "filters[Arrival_Date]",
        "filters[arrival_date]",
        "filters[Arrival_Date.keyword]",
    ]

    for fk in filter_keys:
        try:
            data = fetch({"limit": 3, "offset": 0, fk: test_date}, timeout=180)
            total = data.get("total", 0)
            records = data.get("records", [])
            print(f"  {fk}={test_date}: {total:>8} records")
            if records:
                print(f"    Sample: {json.dumps(records[0], indent=4, ensure_ascii=False)}")
        except Exception as e:
            print(f"  {fk}={test_date}: ERROR - {type(e).__name__}: {str(e)[:80]}")
        time.sleep(1)


def test_gap_dates():
    """Check availability for dates in our gap range."""
    print("\n" + "=" * 60)
    print("TEST: Gap Range Date Availability")
    print("=" * 60)

    # We know the first resource (daily) only has today's data.
    # Test if historical resource has data for our gap dates.
    dates = [
        "30/10/2025",
        "01/11/2025",
        "15/11/2025",
        "01/12/2025",
        "15/12/2025",
        "01/01/2026",
        "15/01/2026",
        "01/02/2026",
        "10/02/2026",
    ]

    # Use whichever filter key works from above
    for date_str in dates:
        try:
            data = fetch({
                "limit": 3,
                "offset": 0,
                "filters[Arrival_Date]": date_str,
            }, timeout=180)
            total = data.get("total", 0)
            records = data.get("records", [])
            commodities = set(r.get("Commodity", "?")[:20] for r in records)
            print(f"  {date_str}: {total:>8} records  samples={commodities if records else '{}'}")
        except Exception as e:
            print(f"  {date_str}: ERROR - {type(e).__name__}: {str(e)[:80]}")
        time.sleep(1.5)


def test_daily_resource_with_date():
    """Also re-test the daily resource with the proper approach:
    just sync today's data daily going forward."""
    print("\n" + "=" * 60)
    print("TEST: Daily Resource (9ef84268) - Today's Data")
    print("=" * 60)

    DAILY_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
    daily_url = f"https://api.data.gov.in/resource/{DAILY_RESOURCE}"

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 5,
        "offset": 0,
    }

    with httpx.Client(timeout=60.0) as client:
        resp = client.get(daily_url, params=params)
        data = resp.json()
        total = data.get("total", 0)
        records = data.get("records", [])

        print(f"  Total today: {total} records")
        print(f"  Date: {records[0].get('arrival_date', '?') if records else '?'}")
        print(f"  States sample: {set(r.get('state', '?') for r in records)}")


if __name__ == "__main__":
    test_date_filter()
    test_gap_dates()
    test_daily_resource_with_date()
    print("\nDone!")
