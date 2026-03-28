"""
Test data.gov.in API connection and explore data structure.
Quick diagnostic to verify API key, understand response format,
and test date filtering for the backfill.
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import httpx

API_KEY = "579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15"
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


def test_basic_connection():
    """Test basic API connectivity."""
    print("=" * 60)
    print("TEST 1: Basic API Connection")
    print("=" * 60)

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 5,
        "offset": 0,
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(BASE_URL, params=params)
        print(f"Status: {resp.status_code}")

        if resp.status_code != 200:
            print(f"ERROR: {resp.text[:500]}")
            return False

        data = resp.json()
        print(f"Total records available: {data.get('total', 'unknown')}")
        print(f"Records in response: {data.get('count', 'unknown')}")

        records = data.get("records", [])
        if records:
            print(f"\nSample record fields: {list(records[0].keys())}")
            print(f"\nFirst record:")
            print(json.dumps(records[0], indent=2, ensure_ascii=False))

        return True


def test_date_filter():
    """Test filtering by arrival_date."""
    print("\n" + "=" * 60)
    print("TEST 2: Date Filtering")
    print("=" * 60)

    # Try filtering by a recent date
    test_date = "01/11/2025"

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 5,
        "offset": 0,
        "filters[arrival_date]": test_date,
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(BASE_URL, params=params)
        data = resp.json()

        total = data.get("total", 0)
        count = data.get("count", 0)
        records = data.get("records", [])

        print(f"Filter: arrival_date = {test_date}")
        print(f"Total matching: {total}")
        print(f"Records returned: {count}")

        if records:
            print(f"\nSample record:")
            print(json.dumps(records[0], indent=2, ensure_ascii=False))
        else:
            print("No records found for this date.")

        return total > 0


def test_recent_dates():
    """Check what dates have data available."""
    print("\n" + "=" * 60)
    print("TEST 3: Recent Date Availability")
    print("=" * 60)

    # Check a range of recent dates
    from datetime import datetime, timedelta

    dates_to_check = []
    # Check last 7 days, plus a few from November 2025
    for days_ago in [0, 1, 2, 3, 7, 14, 30]:
        d = datetime.now() - timedelta(days=days_ago)
        dates_to_check.append(d.strftime("%d/%m/%Y"))

    # Also check specific dates around the gap boundary
    dates_to_check.extend([
        "30/10/2025",
        "31/10/2025",
        "01/11/2025",
        "15/11/2025",
        "01/12/2025",
        "01/01/2026",
        "01/02/2026",
    ])

    with httpx.Client(timeout=30.0) as client:
        for date_str in dates_to_check:
            params = {
                "api-key": API_KEY,
                "format": "json",
                "limit": 1,
                "offset": 0,
                "filters[arrival_date]": date_str,
            }

            try:
                resp = client.get(BASE_URL, params=params)
                data = resp.json()
                total = data.get("total", 0)
                print(f"  {date_str}: {total:>6} records")
            except Exception as e:
                print(f"  {date_str}: ERROR - {e}")

            import time
            time.sleep(0.5)  # Rate limiting


def test_no_filter_latest():
    """Check what dates appear in the most recent unfiltered results."""
    print("\n" + "=" * 60)
    print("TEST 4: Latest Records (No Date Filter)")
    print("=" * 60)

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 20,
        "offset": 0,
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(BASE_URL, params=params)
        data = resp.json()
        records = data.get("records", [])

        dates = set()
        for r in records:
            dates.add(r.get("arrival_date", "unknown"))

        print(f"Dates in latest {len(records)} records:")
        for d in sorted(dates):
            print(f"  {d}")


if __name__ == "__main__":
    print("data.gov.in API Connection Test")
    print(f"Resource ID: {RESOURCE_ID}")
    print()

    if not test_basic_connection():
        print("\nBASIC CONNECTION FAILED - check API key and network")
        sys.exit(1)

    test_date_filter()
    test_recent_dates()
    test_no_filter_latest()

    print("\n" + "=" * 60)
    print("API CONNECTION TEST COMPLETE")
    print("=" * 60)
