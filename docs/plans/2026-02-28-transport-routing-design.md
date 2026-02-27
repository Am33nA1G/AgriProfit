# Transport Routing Redesign — Design Doc
**Date:** 2026-02-28
**Status:** Approved

## Goal
Replace the haversine × 1.35 distance estimate with real road distances via OSRM, extract the 958-line DISTRICT_COORDINATES dict to JSON, and add a tiered verdict system so farmers get a clear, reliable sell/don't-sell signal.

---

## New Files
| File | Purpose |
|---|---|
| `backend/app/transport/routing.py` | RoutingService — OSRM call, DB cache, fallback |
| `backend/app/transport/district_coords.json` | Extracted coordinates (was inline in service.py) |
| `backend/alembic/versions/XXXX_road_distance_cache.py` | Migration for cache table |
| `backend/tests/test_transport_routing.py` | Routing unit tests |

## Modified Files
| File | Change |
|---|---|
| `backend/app/transport/service.py` | Use RoutingService; add `compute_verdict()`; load JSON coords; fix fallback multiplier 1.4→1.35 |
| `backend/app/transport/schemas.py` | Add `verdict`, `verdict_reason`, `distance_source`, `distance_note` fields |
| `backend/app/transport/routes.py` | Remove hardcoded business constants (₹0.40/kg, old rates) |
| `backend/app/core/config.py` | Add `osrm_base_url`, `routing_provider` settings |

---

## DB Cache Table: `road_distance_cache`

```sql
CREATE TABLE road_distance_cache (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_key      VARCHAR(32) NOT NULL,   -- f"{round(lat,4)}:{round(lon,4)}"
    destination_key VARCHAR(32) NOT NULL,   -- f"{round(lat,4)}:{round(lon,4)}"
    src_lat     FLOAT NOT NULL,
    src_lon     FLOAT NOT NULL,
    dst_lat     FLOAT NOT NULL,
    dst_lon     FLOAT NOT NULL,
    distance_km FLOAT NOT NULL,
    source      VARCHAR(20) NOT NULL,       -- 'osrm' or 'estimated'
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (origin_key, destination_key)
);
```

- `FLOAT` not `NUMERIC` — rounding happens before insert, not in the DB
- Unique index on `(origin_key, destination_key)` — fast, debuggable, safe
- Estimated distances are **never cached** — let OSRM retry next time

---

## RoutingService (`routing.py`)

```python
class RoutingService:
    def get_distance_km(self, lat1, lon1, lat2, lon2, db) -> tuple[float, str]:
        # 1. Build cache keys
        ok = f"{round(lat1,4)}:{round(lon1,4)}"
        dk = f"{round(lat2,4)}:{round(lon2,4)}"
        # 2. Check DB cache
        cached = db.query(RoadDistanceCache).filter_by(origin_key=ok, destination_key=dk).first()
        if cached:
            return cached.distance_km, cached.source
        # 3. Try OSRM
        dist = self._call_osrm(lat1, lon1, lat2, lon2)
        if dist is not None:
            db.add(RoadDistanceCache(origin_key=ok, destination_key=dk, ...source="osrm"))
            db.commit()
            return dist, "osrm"
        # 4. Fallback — NOT cached so OSRM is retried next request
        return round(haversine_distance(lat1, lon1, lat2, lon2) * 1.35, 2), "estimated"
```

### OSRM Call

```python
def _call_osrm(self, lat1, lon1, lat2, lon2) -> float | None:
    url = f"{settings.osrm_base_url}/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "false", "alternatives": "false", "steps": "false"}
    try:
        r = httpx.get(url, params=params, timeout=3.0)
        if r.status_code != 200:
            return None
        data = r.json()
        routes = data.get("routes")
        if not routes:
            return None
        return round(routes[0]["distance"] / 1000.0, 2)
    except Exception:
        return None
```

- Timeout: **3 seconds** (mobile-first, farmer UX)
- Params: `overview=false&alternatives=false&steps=false` — minimal payload
- All failure modes (network, bad JSON, empty routes) return `None` → fallback

---

## Config Additions (`config.py`)

```python
osrm_base_url: str = "http://router.project-osrm.org/route/v1/driving"
routing_provider: str = "osrm"  # future: "google", "here", "valhalla"
```

Upgrading to self-hosted: set `OSRM_BASE_URL=http://your-server:5000/route/v1/driving` in `.env`. No code changes needed.

---

## Verdict Tiers (`compute_verdict` in service.py)

```python
def compute_verdict(net_profit, gross_revenue, profit_per_kg, rank, total) -> tuple[str, str]:
    if gross_revenue <= 0:          # guard: avoid division by zero
        return "not_viable", "No revenue data available"
    margin = net_profit / gross_revenue
    rank_ctx = f" · #{rank} of {total} mandis"
    if margin >= 0.20:
        return "excellent", f"Strong return — ₹{profit_per_kg:.0f}/kg net{rank_ctx}"
    elif margin >= 0.10:
        return "good", f"Worth the trip — ₹{profit_per_kg:.0f}/kg net{rank_ctx}"
    elif margin > 0:
        return "marginal", f"Thin margin — ₹{profit_per_kg:.0f}/kg net, weigh carefully{rank_ctx}"
    else:
        return "not_viable", f"Loss of ₹{abs(profit_per_kg):.0f}/kg after all costs{rank_ctx}"
```

- Ranking is by **net_profit descending** only
- `gross_revenue == 0` guard returns `not_viable` immediately

---

## Schema Changes

### `MandiComparison` (3 new fields)
```python
verdict:         Literal["excellent", "good", "marginal", "not_viable"] = "not_viable"
verdict_reason:  str = ""
distance_source: Literal["osrm", "estimated"] = "estimated"
```

### `TransportCompareResponse` (1 new field)
```python
distance_note: str | None = None
# Set to "Some distances are estimated — routing service unavailable."
# when any(c.distance_source == "estimated" for c in comparisons)
# Note: do NOT mention OSRM by name in public API response
```

---

## routes.py Fixes

`/calculate` endpoint — replace hardcoded constants with imports from service.py:
- `quantity * 0.40` → `quantity * LOADING_COST_PER_KG` and `* UNLOADING_COST_PER_KG`
- Add missing cost components (toll, mandi_fee, commission) or clearly document it's a simplified estimate

`/vehicles` endpoint — replace hardcoded strings with `VEHICLES` dict values from service.py.

**Principle:** Routes layer must never contain business constants. All rates live in service.py or config.py.

---

## Tests (`test_transport_routing.py`)

Three mandatory cases:
1. **OSRM success** — mock httpx returns valid response → `distance_source == "osrm"`, row written to DB cache
2. **OSRM timeout** — mock httpx raises `httpx.TimeoutException` → `distance_source == "estimated"`, **no row written** to DB cache
3. **Fallback retry** — after a timeout (no cache write), next call still hits OSRM (not served from cache)

---

## Upgrade Path to Self-Hosted OSRM

When traffic grows:
1. Deploy OSRM Docker: `docker run -p 5000:5000 osrm/osrm-backend`
2. Set env: `OSRM_BASE_URL=http://your-server:5000/route/v1/driving`
3. Optionally set `ROUTING_PROVIDER=osrm_self_hosted` for logging/metrics distinction
4. Existing DB cache remains valid — no migration needed
