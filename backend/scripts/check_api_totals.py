"""Quick check: how many records per day does the historical API have?"""
import sys
import time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import httpx

API_KEY = "579b464db66ec23bdd000001d55108bb212f421a449b34595f56cb15"
RESOURCE_ID = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

dates = [
    "01/11/2025", "15/11/2025", "01/12/2025",
    "15/12/2025", "01/01/2026", "15/01/2026",
    "01/02/2026",
]

with httpx.Client(timeout=180.0) as client:
    for d in dates:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 1,
            "offset": 0,
            "filters[arrival_date]": d,
        }
        try:
            resp = client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            total = data.get("total", 0)
            print(f"{d}: {total:>10,} total records")
        except Exception as e:
            print(f"{d}: ERROR - {e}")
        time.sleep(2)
