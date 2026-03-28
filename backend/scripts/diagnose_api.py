"""
Backend API Diagnostic Script

Tests all major endpoints for:
- Response status (200 OK)
- Response time (< 1 second target)
- Data presence (non-empty response)
- Response format validity

Usage:
    python scripts/diagnose_api.py [base_url]
"""
import sys
import time
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package not installed. Run: pip install requests")
    sys.exit(1)

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

ENDPOINTS = [
    ("Health", "GET", "/health", None),
    ("Sync Status", "GET", "/sync/status", None),
    ("Commodities", "GET", "/api/v1/commodities/?limit=5", None),
    ("Categories", "GET", "/api/v1/commodities/categories", None),
    ("With Prices", "GET", "/api/v1/commodities/with-prices?limit=5", None),
    ("Mandis", "GET", "/api/v1/mandis/?limit=5", None),
    ("Mandi States", "GET", "/api/v1/mandis/states", None),
    ("Current Prices", "GET", "/api/v1/prices/current?limit=5", None),
    ("Price History", "GET", "/api/v1/prices/?limit=5", None),
    ("Top Movers", "GET", "/api/v1/prices/top-movers?limit=3", None),
    ("Historical Prices", "GET", "/api/v1/prices/historical?commodity=Tomato&days=7", None),
    ("Dashboard", "GET", "/api/v1/analytics/dashboard", None),
    ("Summary", "GET", "/api/v1/analytics/summary", None),
    ("Top Commodities", "GET", "/api/v1/analytics/top-commodities?limit=5", None),
    ("Top Mandis", "GET", "/api/v1/analytics/top-mandis?limit=5", None),
    ("Community Posts", "GET", "/api/v1/community/posts/?limit=3", None),
]

def test_endpoint(name, method, path, body):
    url = f"{BASE_URL}{path}"
    start = time.time()
    try:
        if method == "GET":
            resp = requests.get(url, timeout=10)
        elif method == "POST":
            resp = requests.post(url, json=body, timeout=10)
        else:
            return {"name": name, "ok": False, "error": f"Unknown method: {method}"}

        elapsed = time.time() - start
        data = None
        try:
            data = resp.json()
        except Exception:
            pass

        data_preview = json.dumps(data, default=str)[:200] if data else resp.text[:200]

        return {
            "name": name,
            "url": url,
            "status": resp.status_code,
            "ok": resp.status_code == 200,
            "latency_ms": round(elapsed * 1000),
            "data_preview": data_preview,
            "has_data": data is not None and (
                (isinstance(data, list) and len(data) > 0) or
                (isinstance(data, dict) and len(data) > 0) or
                (not isinstance(data, (list, dict)))
            ),
        }
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        return {"name": name, "url": url, "ok": False, "error": f"TIMEOUT ({round(elapsed*1000)}ms)", "latency_ms": round(elapsed*1000)}
    except requests.exceptions.ConnectionError:
        return {"name": name, "url": url, "ok": False, "error": "CONNECTION REFUSED - Is the server running?"}
    except Exception as e:
        elapsed = time.time() - start
        return {"name": name, "url": url, "ok": False, "error": str(e), "latency_ms": round(elapsed*1000)}


def main():
    print(f"\n{'='*60}")
    print(f"  AgriProfit API Diagnostic")
    print(f"  Base URL: {BASE_URL}")
    print(f"{'='*60}\n")

    results = []
    pass_count = 0
    fail_count = 0
    slow_count = 0

    for name, method, path, body in ENDPOINTS:
        result = test_endpoint(name, method, path, body)
        results.append(result)

        status = result.get("status", "ERR")
        latency = result.get("latency_ms", "?")

        if result["ok"]:
            pass_count += 1
            speed = "SLOW" if isinstance(latency, int) and latency > 1000 else "OK"
            if speed == "SLOW":
                slow_count += 1
            icon = "PASS" if speed == "OK" else "SLOW"
            has_data = "data" if result.get("has_data") else "empty"
            print(f"  [{icon}] {name:<20} HTTP {status}  {latency:>5}ms  [{has_data}]")
        else:
            fail_count += 1
            error = result.get("error", f"HTTP {status}")
            print(f"  [FAIL] {name:<20} {error}")

    print(f"\n{'='*60}")
    print(f"  Results: {pass_count} passed, {fail_count} failed, {slow_count} slow (>1s)")
    print(f"{'='*60}")

    if fail_count > 0:
        print(f"\n  Failed endpoints:")
        for r in results:
            if not r["ok"]:
                print(f"    - {r['name']}: {r.get('error', 'HTTP ' + str(r.get('status', '?')))}")

    if slow_count > 0:
        print(f"\n  Slow endpoints (>1s):")
        for r in results:
            if r["ok"] and isinstance(r.get("latency_ms"), int) and r["latency_ms"] > 1000:
                print(f"    - {r['name']}: {r['latency_ms']}ms")

    print()
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
