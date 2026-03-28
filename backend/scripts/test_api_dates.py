"""
Deep test: Check if the API resource contains multi-day data or only today's data.
Fetches a larger sample and checks unique dates.
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx

API_KEY = "579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15"
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"


def check_all_dates():
    """Fetch multiple pages and collect all unique dates."""
    print("Fetching records to check date distribution...")

    all_dates = {}
    offsets = [0, 5000, 10000, 15000]

    with httpx.Client(timeout=60.0) as client:
        for offset in offsets:
            params = {
                "api-key": API_KEY,
                "format": "json",
                "limit": 1000,
                "offset": offset,
            }

            resp = client.get(BASE_URL, params=params)
            if resp.status_code != 200:
                print(f"  offset {offset}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            records = data.get("records", [])
            total = data.get("total", "?")

            print(f"  offset {offset}: got {len(records)} records (total: {total})")

            for r in records:
                date = r.get("arrival_date", "unknown")
                all_dates[date] = all_dates.get(date, 0) + 1

            if not records:
                break

            import time
            time.sleep(1)

    print(f"\nUnique dates found: {len(all_dates)}")
    for date, count in sorted(all_dates.items()):
        print(f"  {date}: {count} records")


def check_state_filter():
    """Verify state filter works (confirming API filters do work)."""
    print("\nTesting state filter (Kerala)...")

    with httpx.Client(timeout=30.0) as client:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 5,
            "offset": 0,
            "filters[state.keyword]": "Kerala",
        }
        resp = client.get(BASE_URL, params=params)
        data = resp.json()
        total = data.get("total", 0)
        records = data.get("records", [])
        print(f"  Kerala: {total} records")
        if records:
            print(f"  Sample: {records[0].get('market', '?')} - {records[0].get('commodity', '?')} - {records[0].get('arrival_date', '?')}")


def check_alternative_resources():
    """Check if there are alternative resources with historical data."""
    print("\nChecking alternative resource IDs for historical data...")

    # Known Agmarknet resource IDs
    resource_ids = {
        "9ef84268-d588-465a-a308-a864a43d0070": "Current daily prices (what we're using)",
        "35985678-0d79-46b4-9ed6-6f13308a1d24": "Commodity-wise daily prices (alternative)",
    }

    with httpx.Client(timeout=30.0) as client:
        for rid, desc in resource_ids.items():
            url = f"https://api.data.gov.in/resource/{rid}"
            params = {
                "api-key": API_KEY,
                "format": "json",
                "limit": 3,
                "offset": 0,
            }
            try:
                resp = client.get(url, params=params)
                data = resp.json()
                total = data.get("total", 0)
                records = data.get("records", [])
                dates = set(r.get("arrival_date", "?") for r in records)
                print(f"\n  Resource: {rid}")
                print(f"  Description: {desc}")
                print(f"  Total records: {total}")
                print(f"  Dates in sample: {dates}")
                if records:
                    print(f"  Fields: {list(records[0].keys())}")
            except Exception as e:
                print(f"\n  Resource: {rid} - ERROR: {e}")

            import time
            time.sleep(1)


if __name__ == "__main__":
    check_all_dates()
    check_state_filter()
    check_alternative_resources()
