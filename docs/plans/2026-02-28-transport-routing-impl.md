# Transport Routing — OSRM + Verdict Tiers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace haversine × 1.35 distance estimates with real OSRM road distances (DB-cached, fallback-safe), extract the 958-line coordinates dict to JSON, and add a tiered verdict system (excellent/good/marginal/not_viable) to every mandi comparison.

**Architecture:** New `routing.py` module owns OSRM calls, DB caching, and fallback logic. `service.py` calls it and adds verdict computation. Schemas get three new fields on `MandiComparison` and one on `TransportCompareResponse`. Hardcoded constants in `routes.py` are replaced with imports from `service.py`.

**Tech Stack:** FastAPI, SQLAlchemy (sync Session), httpx, Alembic, pytest

**Design doc:** `docs/plans/2026-02-28-transport-routing-design.md`

---

### Task 1: Extract DISTRICT_COORDINATES to JSON

**Files:**
- Create: `backend/app/transport/district_coords.json`
- Modify: `backend/app/transport/service.py` (top of file, constants section)

**Step 1: Extract the dict to JSON**

In `service.py`, lines 64–1022 contain `DISTRICT_COORDINATES = { ... }`. Extract the dict body to a new file. The JSON keys are district names (strings), values are `[lat, lon]` arrays.

Run in the `backend/` directory:
```python
# one-time helper — run manually, then delete
import ast, json
src = open("app/transport/service.py").read()
tree = ast.parse(src)
# find the DISTRICT_COORDINATES assignment and eval it
# Easiest: copy the dict body into a temp script and json.dump it
```
Alternatively, write `district_coords.json` manually by copying the dict (it's a straightforward mapping).

The file should look like:
```json
{
  "Anantapur": [14.6819, 77.6006],
  "Chittoor": [13.2172, 79.1003],
  ...
}
```

**Step 2: Replace the dict in service.py**

Remove lines 61–1022 (the `DISTRICT_COORDINATES = { ... }` block) and replace with:

```python
import json as _json
import pathlib as _pathlib

DISTRICT_COORDINATES: dict[str, tuple[float, float]] = {
    k: tuple(v)
    for k, v in _json.loads(
        (_pathlib.Path(__file__).parent / "district_coords.json").read_text(encoding="utf-8")
    ).items()
}
```

**Step 3: Verify no breakage**

```bash
cd backend
python -c "from app.transport.service import DISTRICT_COORDINATES; print(len(DISTRICT_COORDINATES), 'districts')"
```
Expected: `900+ districts`

**Step 4: Run existing tests**

```bash
cd backend
python -m pytest tests/test_transport_service.py -v
```
Expected: 22 passed

**Step 5: Commit**

```bash
git add backend/app/transport/district_coords.json backend/app/transport/service.py
git commit -m "refactor: extract DISTRICT_COORDINATES to district_coords.json"
```

---

### Task 2: Add config settings for routing

**Files:**
- Modify: `backend/app/core/config.py`

**Step 1: Add two settings to the `Settings` class**

Find the last field in the `Settings` class and add after it:

```python
# =========================================================================
# ROUTING
# =========================================================================
osrm_base_url: str = Field(
    default="http://router.project-osrm.org/route/v1/driving",
    description="OSRM routing API base URL. Override to use self-hosted instance.",
)
routing_provider: str = Field(
    default="osrm",
    description="Routing provider identifier (osrm, osrm_self_hosted). For metrics/logging.",
)
```

**Step 2: Verify settings load**

```bash
cd backend
python -c "from app.core.config import settings; print(settings.osrm_base_url)"
```
Expected: `http://router.project-osrm.org/route/v1/driving`

**Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat: add osrm_base_url and routing_provider config settings"
```

---

### Task 3: Create RoadDistanceCache model and Alembic migration

**Files:**
- Create: `backend/app/models/road_distance_cache.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/a2b3c4d5e6f7_add_road_distance_cache.py`

**Step 1: Create the SQLAlchemy model**

Create `backend/app/models/road_distance_cache.py`:

```python
"""Road distance cache model — stores OSRM-computed route distances."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.database.session import Base


class RoadDistanceCache(Base):
    __tablename__ = "road_distance_cache"
    __table_args__ = (
        UniqueConstraint("origin_key", "destination_key", name="uq_road_distance_route"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    origin_key: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_key: Mapped[str] = mapped_column(String(32), nullable=False)
    src_lat: Mapped[float] = mapped_column(Float, nullable=False)
    src_lon: Mapped[float] = mapped_column(Float, nullable=False)
    dst_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dst_lon: Mapped[float] = mapped_column(Float, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # 'osrm' or 'estimated'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

**Step 2: Export from models `__init__.py`**

Add to `backend/app/models/__init__.py`:
```python
from app.models.road_distance_cache import RoadDistanceCache
```

**Step 3: Create the Alembic migration**

Create `backend/alembic/versions/a2b3c4d5e6f7_add_road_distance_cache.py`:

```python
"""add_road_distance_cache

Revision ID: a2b3c4d5e6f7
Revises: f9e8d7c6b5a4
Create Date: 2026-02-28 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f9e8d7c6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "road_distance_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("origin_key", sa.String(32), nullable=False),
        sa.Column("destination_key", sa.String(32), nullable=False),
        sa.Column("src_lat", sa.Float(), nullable=False),
        sa.Column("src_lon", sa.Float(), nullable=False),
        sa.Column("dst_lat", sa.Float(), nullable=False),
        sa.Column("dst_lon", sa.Float(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("origin_key", "destination_key", name="uq_road_distance_route"),
    )


def downgrade() -> None:
    op.drop_table("road_distance_cache")
```

**Step 4: Verify migration syntax**

```bash
cd backend
python -c "from alembic.versions.a2b3c4d5e6f7_add_road_distance_cache import upgrade, downgrade; print('OK')"
```

**Step 5: Commit**

```bash
git add backend/app/models/road_distance_cache.py backend/app/models/__init__.py \
        backend/alembic/versions/a2b3c4d5e6f7_add_road_distance_cache.py
git commit -m "feat: add RoadDistanceCache model and migration"
```

---

### Task 4: Write routing tests (TDD — write tests first)

**Files:**
- Create: `backend/tests/test_transport_routing.py`

**Step 1: Write three failing tests**

Create `backend/tests/test_transport_routing.py`:

```python
"""Tests for RoutingService — OSRM call, DB cache, fallback behavior."""
import pytest
from unittest.mock import MagicMock, patch
import httpx

from app.transport.routing import RoutingService


@pytest.fixture
def routing():
    return RoutingService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    # Simulate no cache hit by default
    db.query.return_value.filter_by.return_value.first.return_value = None
    return db


class TestRoutingServiceOSRMSuccess:
    def test_osrm_success_returns_distance_and_osrm_source(self, routing, mock_db):
        """OSRM returns valid response → distance_km from response, source='osrm'."""
        osrm_payload = {
            "code": "Ok",
            "routes": [{"distance": 85500.0}],  # 85.5 km
        }
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = osrm_payload
            mock_get.return_value = mock_resp

            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert dist == pytest.approx(85.5, rel=0.01)
        assert source == "osrm"

    def test_osrm_success_writes_to_db_cache(self, routing, mock_db):
        """OSRM success → result persisted to road_distance_cache table."""
        osrm_payload = {"code": "Ok", "routes": [{"distance": 100000.0}]}
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = osrm_payload
            mock_get.return_value = mock_resp

            routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestRoutingServiceFallback:
    def test_osrm_timeout_returns_estimated_source(self, routing, mock_db):
        """OSRM timeout → fallback distance returned, source='estimated'."""
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert source == "estimated"
        assert dist > 0

    def test_osrm_timeout_does_not_write_to_cache(self, routing, mock_db):
        """Estimated distances must NOT be cached — allow OSRM retry next request."""
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_after_fallback_next_call_retries_osrm(self, routing, mock_db):
        """After a fallback (no cache write), next call must still hit OSRM, not cache."""
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        # DB still has no cache entry (add was never called)
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"code": "Ok", "routes": [{"distance": 50000.0}]}
            mock_get.return_value = mock_resp

            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert source == "osrm"
        mock_get.assert_called_once()


class TestRoutingServiceCache:
    def test_cache_hit_returns_without_calling_osrm(self, routing, mock_db):
        """Cache hit → return immediately, never call OSRM."""
        cached = MagicMock()
        cached.distance_km = 120.5
        cached.source = "osrm"
        mock_db.query.return_value.filter_by.return_value.first.return_value = cached

        with patch("httpx.get") as mock_get:
            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert dist == 120.5
        assert source == "osrm"
        mock_get.assert_not_called()
```

**Step 2: Run tests — expect ImportError (module doesn't exist yet)**

```bash
cd backend
python -m pytest tests/test_transport_routing.py -v
```
Expected: `ImportError: cannot import name 'RoutingService' from 'app.transport.routing'`

**Step 3: Commit the tests**

```bash
git add backend/tests/test_transport_routing.py
git commit -m "test: add RoutingService tests (failing — TDD)"
```

---

### Task 5: Implement RoutingService

**Files:**
- Create: `backend/app/transport/routing.py`

**Step 1: Implement `routing.py`**

Create `backend/app/transport/routing.py`:

```python
"""
Routing service for road distance calculation.

Uses OSRM for accurate road distances with DB-backed cache.
Falls back to haversine × 1.35 multiplier if OSRM is unavailable.
Estimated distances are NOT cached — OSRM is retried on next request.
"""
import math
from typing import Literal

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.road_distance_cache import RoadDistanceCache


# Fallback multiplier: haversine (straight-line) → estimated road distance.
# 1.35 is a conservative average for India's road network.
# Plains: ~1.2–1.3; Hills/Northeast: ~1.8–2.5; National average: ~1.35
FALLBACK_MULTIPLIER = 1.35

DistanceSource = Literal["osrm", "estimated"]


def _make_key(lat: float, lon: float) -> str:
    """Build a compact cache key from coordinates rounded to 4 decimal places (~11m)."""
    return f"{round(lat, 4)}:{round(lon, 4)}"


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RoutingService:
    """
    Resolves road distances between two coordinate pairs.

    Lookup order:
    1. DB cache (road_distance_cache table)
    2. OSRM HTTP call — result saved to cache
    3. Fallback: haversine × 1.35 — NOT cached, retried on next request
    """

    def get_distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        db: Session,
    ) -> tuple[float, DistanceSource]:
        """
        Return (distance_km, source) where source is 'osrm' or 'estimated'.
        """
        origin_key = _make_key(lat1, lon1)
        destination_key = _make_key(lat2, lon2)

        # 1. Cache lookup
        cached = (
            db.query(RoadDistanceCache)
            .filter_by(origin_key=origin_key, destination_key=destination_key)
            .first()
        )
        if cached:
            return cached.distance_km, cached.source  # type: ignore[return-value]

        # 2. OSRM call
        osrm_dist = self._call_osrm(lat1, lon1, lat2, lon2)
        if osrm_dist is not None:
            row = RoadDistanceCache(
                origin_key=origin_key,
                destination_key=destination_key,
                src_lat=lat1,
                src_lon=lon1,
                dst_lat=lat2,
                dst_lon=lon2,
                distance_km=osrm_dist,
                source="osrm",
            )
            db.add(row)
            db.commit()
            return osrm_dist, "osrm"

        # 3. Fallback — not cached so OSRM is retried next time
        estimated = round(_haversine(lat1, lon1, lat2, lon2) * FALLBACK_MULTIPLIER, 2)
        return estimated, "estimated"

    def _call_osrm(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float | None:
        """
        Call OSRM routing API. Returns distance in km or None on any failure.
        Note: OSRM uses lon,lat order (not lat,lon).
        """
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


# Module-level singleton
routing_service = RoutingService()
```

**Step 2: Run routing tests**

```bash
cd backend
python -m pytest tests/test_transport_routing.py -v
```
Expected: all 7 routing tests PASS

**Step 3: Commit**

```bash
git add backend/app/transport/routing.py
git commit -m "feat: implement RoutingService with OSRM, DB cache, and fallback"
```

---

### Task 6: Add verdict logic and wire RoutingService into service.py

**Files:**
- Modify: `backend/app/transport/service.py`

**Step 1: Add `compute_verdict` function**

After the `calculate_net_profit` function, add:

```python
def compute_verdict(
    net_profit: float,
    gross_revenue: float,
    profit_per_kg: float,
    rank: int,
    total: int,
) -> tuple[str, str]:
    """
    Compute a tiered sell verdict for a farmer.

    Tiers by profit margin (net_profit / gross_revenue):
      excellent  >= 20%  — strong return
      good       10–19%  — worth the trip
      marginal    1–9%   — thin margin
      not_viable  <= 0%  — loss after costs
    """
    if gross_revenue <= 0:
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

**Step 2: Update `compare_mandis` to use RoutingService and compute_verdict**

In `compare_mandis`, replace:
```python
dist = haversine_distance(source_lat, source_lon, m["latitude"], m["longitude"])
road_dist = dist * ROAD_DISTANCE_MULTIPLIER
```
with:
```python
from app.transport.routing import routing_service
road_dist, dist_source = routing_service.get_distance_km(
    source_lat, source_lon, m["latitude"], m["longitude"], db
)
```

Then update the `MandiComparison` construction to include the new fields.
First, sort the raw list by net_profit to get rank (do this after building a preliminary list, or build with index). The cleanest approach: build comparisons list, then assign rank+verdict in a second pass after sorting:

```python
# Build comparisons without verdict first
raw_comparisons: list[MandiComparison] = []
has_estimated = False
for m in raw_mandis:
    ...
    road_dist, dist_source = routing_service.get_distance_km(
        source_lat, source_lon, m["latitude"], m["longitude"], db
    )
    if dist_source == "estimated":
        has_estimated = True
    ...
    comp = MandiComparison(
        ...
        distance_source=dist_source,
        verdict="not_viable",       # placeholder
        verdict_reason="",          # placeholder
    )
    raw_comparisons.append(comp)

# Sort by net_profit descending, then assign rank-aware verdicts
raw_comparisons.sort(key=lambda x: x.net_profit, reverse=True)
total = len(raw_comparisons)
for rank, comp in enumerate(raw_comparisons, start=1):
    tier, reason = compute_verdict(
        comp.net_profit, comp.gross_revenue, comp.profit_per_kg, rank, total
    )
    comp.verdict = tier
    comp.verdict_reason = reason

return raw_comparisons[:request.limit], has_estimated
```

Note: `compare_mandis` now returns a tuple `(list[MandiComparison], bool)`. Update `routes.py` accordingly (Task 8).

**Step 3: Write a verdict unit test in test_transport_service.py**

Add to `TestCalculateNetProfit` class:

```python
def test_compute_verdict_tiers(self):
    from app.transport.service import compute_verdict

    # excellent: 25% margin
    tier, reason = compute_verdict(2500, 10000, 25.0, 1, 5)
    assert tier == "excellent"
    assert "₹25/kg" in reason
    assert "#1 of 5" in reason

    # good: 15% margin
    tier, _ = compute_verdict(1500, 10000, 15.0, 2, 5)
    assert tier == "good"

    # marginal: 5% margin
    tier, _ = compute_verdict(500, 10000, 5.0, 3, 5)
    assert tier == "marginal"

    # not_viable: negative
    tier, reason = compute_verdict(-300, 10000, -3.0, 4, 5)
    assert tier == "not_viable"
    assert "Loss" in reason

    # guard: gross_revenue = 0
    tier, _ = compute_verdict(0, 0, 0, 1, 1)
    assert tier == "not_viable"
```

**Step 4: Run tests**

```bash
cd backend
python -m pytest tests/test_transport_service.py tests/test_transport_routing.py -v
```
Expected: all pass

**Step 5: Commit**

```bash
git add backend/app/transport/service.py backend/tests/test_transport_service.py
git commit -m "feat: add compute_verdict and wire RoutingService into compare_mandis"
```

---

### Task 7: Update schemas with new fields

**Files:**
- Modify: `backend/app/transport/schemas.py`

**Step 1: Add fields to `MandiComparison`**

After the `recommendation` field, add:

```python
verdict: str = Field(
    default="not_viable",
    description="Sell verdict: excellent / good / marginal / not_viable",
)
verdict_reason: str = Field(
    default="",
    description="Human-readable explanation of the verdict",
)
distance_source: str = Field(
    default="estimated",
    description="Distance data source: 'osrm' (accurate) or 'estimated' (haversine fallback)",
)
```

**Step 2: Add field to `TransportCompareResponse`**

After `total_mandis_analyzed`, add:

```python
distance_note: str | None = Field(
    default=None,
    description="Set when any distance used the haversine fallback instead of live routing data",
)
```

**Step 3: Run tests**

```bash
cd backend
python -m pytest tests/test_transport_service.py tests/test_transport_routing.py -v
```
Expected: all pass

**Step 4: Commit**

```bash
git add backend/app/transport/schemas.py
git commit -m "feat: add verdict, verdict_reason, distance_source, distance_note to schemas"
```

---

### Task 8: Fix routes.py — remove hardcoded business constants

**Files:**
- Modify: `backend/app/transport/routes.py`

**Step 1: Fix `/calculate` endpoint**

Replace the hardcoded hamali costs (lines ~92–93):
```python
# BEFORE
loading_cost = quantity_kg * 0.40
unloading_cost = quantity_kg * 0.40
```
```python
# AFTER
from app.transport.service import LOADING_COST_PER_KG, UNLOADING_COST_PER_KG
loading_cost = quantity_kg * LOADING_COST_PER_KG
unloading_cost = quantity_kg * UNLOADING_COST_PER_KG
```

**Step 2: Fix `/vehicles` endpoint**

Replace the hardcoded return dict with values read from the `VEHICLES` constant:
```python
# AFTER
return {
    "vehicles": {
        vtype.value: {
            "capacity_kg": spec["capacity_kg"],
            "cost_per_km": spec["cost_per_km"],
            "description": spec["description"],
        }
        for vtype, spec in VEHICLES.items()
    },
    "loading_cost_per_kg": LOADING_COST_PER_KG,
    "unloading_cost_per_kg": UNLOADING_COST_PER_KG,
    "mandi_fee_rate": MANDI_FEE_RATE,
    "commission_rate": COMMISSION_RATE,
}
```

**Step 3: Update `/compare` endpoint to handle new return value**

`compare_mandis` now returns `(comparisons, has_estimated)`. Update:
```python
comparisons, has_estimated = compare_mandis(request, db)
best_mandi = comparisons[0] if comparisons else None
distance_note = (
    "Some distances are estimated — routing service unavailable."
    if has_estimated else None
)
return TransportCompareResponse(
    commodity=request.commodity,
    quantity_kg=request.quantity_kg,
    source_district=request.source_district,
    comparisons=comparisons,
    best_mandi=best_mandi,
    total_mandis_analyzed=len(comparisons),
    distance_note=distance_note,
)
```

**Step 4: Run all transport tests**

```bash
cd backend
python -m pytest tests/test_transport_service.py tests/test_transport_routing.py tests/test_transport_api.py -v
```
Expected: all pass

**Step 5: Commit**

```bash
git add backend/app/transport/routes.py
git commit -m "fix: remove hardcoded business constants from routes.py, wire distance_note"
```

---

### Task 9: Final verification

**Step 1: Run all backend tests**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```
Expected: all existing tests pass, routing tests pass, no regressions

**Step 2: Smoke test the import chain**

```bash
cd backend
python -c "
from app.transport.service import compare_mandis, compute_verdict, DISTRICT_COORDINATES
from app.transport.routing import routing_service, RoutingService
from app.transport.schemas import MandiComparison, TransportCompareResponse
from app.models.road_distance_cache import RoadDistanceCache
from app.core.config import settings
print('osrm_base_url:', settings.osrm_base_url)
print('routing_provider:', settings.routing_provider)
print('districts loaded:', len(DISTRICT_COORDINATES))
print('All imports OK')
"
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: transport routing — OSRM + DB cache + verdict tiers + JSON coords"
```

---

## Summary of Changes

| What | Why |
|---|---|
| `district_coords.json` | service.py shrinks from 1362 → ~420 lines |
| `routing.py` | Real road distances; single place to swap to self-hosted OSRM |
| `road_distance_cache` table | Persistent cache; each route pair called once ever |
| `compute_verdict()` | Farmers get a clear excellent/good/marginal/not_viable signal |
| `distance_source` + `distance_note` | Transparent fallback — frontend can show "distances are approximate" |
| routes.py fixes | Business constants belong in service.py, not route handlers |

## Upgrade to Self-Hosted OSRM

When traffic grows, set in `.env`:
```
OSRM_BASE_URL=http://your-osrm-server:5000/route/v1/driving
ROUTING_PROVIDER=osrm_self_hosted
```
No code changes required. Existing cache remains valid.
