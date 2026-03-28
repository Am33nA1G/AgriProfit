# Phase 6: Mandi Arbitrage Dashboard - Research

**Researched:** 2026-03-02
**Domain:** FastAPI arbitrage endpoint + Next.js dashboard (transport engine integration, freshness gating, profit-ranked results)
**Confidence:** HIGH — all critical paths are in-codebase and directly readable; no novel library required

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARB-01 | User selects commodity + origin district and sees top 3 destination mandis ranked by net profit after freight + spoilage | `compare_mandis()` in `service.py` already computes this; new endpoint wraps it with a 7-day freshness gate and hard limit of 3 results |
| ARB-02 | Arbitrage signals suppressed when net margin after transport < configurable threshold (default: 10% of modal price) | Net margin = `net_profit / gross_revenue`; threshold stored in `settings.arbitrage_margin_threshold_pct` (new setting); filter applied in service before returning results |
| ARB-03 | Dashboard only shows price data fresher than 7 days — stale pairs show warning, not current-looking data | `get_mandis_for_commodity()` currently uses 30-day window; new arbitrage service function uses strict 7-day window; response includes `price_date` and `is_stale` flag per mandi |
| ARB-04 | Each result row shows distance (km), travel time (hours), freight cost (Rs/quintal), spoilage estimate (%), net expected profit (Rs/quintal) | All five fields already exist in `MandiComparison` schema: `distance_km`, `travel_time_hours`, `costs.total_cost` (converted to per-quintal), `spoilage_percent`, `profit_per_kg * 100` |
| UI-04 | Arbitrage dashboard — commodity + origin district selector, ranked mandi table with net profit, distance, freshness indicator | Next.js page at `frontend/src/app/arbitrage/page.tsx`; reuse `transportService.compareCosts()` or new `arbitrageService`; table built with existing shadcn/ui Table + Badge components |
| UI-05 | All dashboards display coverage gap messages when feature unavailable (no silent failures) | `distance_note` field pattern from `TransportCompareResponse`; replicate for stale data warning; empty-state component already exists at `frontend/src/components/ui/empty-state.tsx` |
</phase_requirements>

---

## Summary

Phase 6 delivers a mandi arbitrage dashboard by composing the existing transport engine (`compare_mandis()`) with a 7-day price freshness gate and a configurable margin threshold. The backend engine — including freight calculation (`economics.py`), spoilage (`spoilage.py`), routing (`routing.py` with OSRM + haversine fallback), and risk scoring (`risk_engine.py`) — is complete and tested with 86 passing tests. The new work is thin: one new FastAPI endpoint (`GET /api/v1/arbitrage/{commodity}/{district}`) that wraps `compare_mandis()` with tighter freshness logic, plus one new Next.js page that displays the top-3 ranked results.

The core engineering problem in this phase is the **7-day freshness gate**: the existing `get_mandis_for_commodity()` function uses a 30-day lookback window and does not annotate individual mandi prices with their staleness. The arbitrage endpoint must use a strict 7-day cutoff and expose `price_date` and `days_since_update` per result so the UI can display an accurate freshness indicator. Results with data older than 7 days must be returned with `is_stale: true` and a warning string, not silently excluded (UI-05 requirement to show coverage gaps rather than empty results).

The frontend reuses the established pattern of the existing transport page (`frontend/src/app/transport/page.tsx`): commodity + district selectors calling the API via TanStack Query, results rendered in shadcn/ui Table with Badge verdict labels. The arbitrage page is simpler than the transport page — fixed quantity (1 quintal for normalised per-quintal comparison), no vehicle selector, no max-distance filter. The main new UI element is a freshness indicator badge (green/amber/red based on `days_since_update`).

**Primary recommendation:** Build a dedicated `GET /api/v1/arbitrage/{commodity}/{district}` endpoint that calls `compare_mandis()` with `limit=3` and adds: (1) strict 7-day freshness filter on the SQL side, (2) margin threshold gate (default 10%), (3) `is_stale` / `days_since_update` fields on each result. Do not modify the existing `/transport/compare` endpoint — it serves a different UX (farmer computes actual shipment cost; arbitrage shows normalised per-quintal signal).

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current | Arbitrage endpoint | Already the app framework; same router pattern as transport |
| SQLAlchemy | current | Price freshness query | Sync ORM used throughout; raw `text()` for performance-critical queries |
| Pydantic v2 | current | `ArbitrageResponse` schema | All schemas use Pydantic v2 `BaseModel`; `ConfigDict(from_attributes=True)` pattern |
| Next.js 15 (App Router) | 15.5.9 | Arbitrage page | Existing app uses App Router; new page at `frontend/src/app/arbitrage/page.tsx` |
| TanStack Query | 5.90.x | API data fetching | Already used on transport page; `useQuery` with `enabled` flag for on-demand fetch |
| shadcn/ui (Radix) | current | Table, Badge, Select, Card | Already installed; transport page proves the pattern |
| Recharts | 3.7.0 | Optional profit bar chart | Already installed; skip for MVP — ranked table is sufficient |
| Vitest + @testing-library/react | 1.6.x | Frontend tests | Existing test framework |
| pytest | current | Backend tests | Existing framework; `backend/tests/test_transport_*.py` pattern |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| axios | 1.13.x | HTTP client in frontend service | Already in `src/lib/api.ts`; arbitrage service follows same pattern as `transport.ts` |
| lucide-react | 0.563.x | Icons (TrendingUp, Clock, AlertTriangle) | Already used on transport page |
| sonner | 2.0.7 | Toast notifications for errors | Already used on transport page |
| zod | 4.3.6 | Form validation if needed | Already installed; commodity + district form validation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Dedicated `GET /arbitrage/{commodity}/{district}` | Reuse `POST /transport/compare` | Transport compare requires `quantity_kg`; arbitrage is normalised to 1 quintal; separate endpoint avoids confusion and allows tighter freshness logic |
| New `arbitrage.py` service module | Inline logic in routes.py | Follow existing pattern: service.py contains business logic, routes.py is thin; arbitrage warrants its own module due to freshness gate complexity |
| TanStack Query `useQuery` | `useState` + `useEffect` + fetch | TanStack Query already used on transport page; provides caching, loading/error states, retry — no reason to deviate |

**Installation:** No new packages needed for either backend or frontend.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── arbitrage/                    # NEW module (mirrors transport/ pattern)
│   ├── __init__.py
│   ├── schemas.py                # ArbitrageRequest, ArbitrageResult, ArbitrageResponse
│   ├── service.py                # get_arbitrage_results() — wraps compare_mandis() with freshness gate
│   └── routes.py                 # GET /arbitrage/{commodity}/{district}

backend/tests/
├── test_arbitrage_service.py     # Unit tests for freshness gate + margin threshold
└── test_arbitrage_api.py         # Integration tests via TestClient

frontend/src/app/arbitrage/
├── page.tsx                      # ArbitragePage — commodity + district selectors + results table
└── loading.tsx                   # Skeleton loading state (mirrors transport/loading.tsx)

frontend/src/services/
└── arbitrage.ts                  # arbitrageService.getResults(commodity, district)

frontend/src/app/arbitrage/__tests__/
└── page.test.tsx                 # Vitest unit tests
```

### Pattern 1: 7-Day Freshness Gate in SQL

**What:** Replace the 30-day lookback in `get_mandis_for_commodity()` with a 7-day window, and add `price_date` to the result so the endpoint can annotate each mandi with staleness.
**When to use:** Always for arbitrage endpoint. The existing transport endpoint's 30-day window is appropriate for that use case (farmer may need to plan a week out); arbitrage signals must be current.

```python
# Source: Adapted from service.py get_mandis_for_commodity() — same DISTINCT ON pattern
def get_arbitrage_mandis(commodity_id: str, db: Session, limit: int = 100) -> list[dict]:
    """
    Fetch mandis with price data within the last 7 days.
    Returns is_stale=False for all results (stale pairs are excluded or flagged separately).
    """
    from sqlalchemy import text
    from datetime import date, timedelta

    max_date = db.execute(
        text("SELECT MAX(price_date) FROM price_history WHERE commodity_id = CAST(:cid AS UUID)"),
        {"cid": str(commodity_id)}
    ).scalar()

    if not max_date:
        return []

    # CRITICAL: use max_date as reference, not date.today()
    # Data ends 2025-10-30; today() would produce empty results
    cutoff = max_date - timedelta(days=7)

    query = text("""
        WITH recent_prices AS (
            SELECT DISTINCT ON (ph.mandi_name)
                ph.mandi_name,
                ph.mandi_id,
                ph.modal_price,
                ph.price_date
            FROM price_history ph
            WHERE ph.commodity_id = CAST(:commodity_id AS UUID)
              AND ph.price_date >= :cutoff
              AND ph.modal_price > 0
            ORDER BY ph.mandi_name, ph.price_date DESC
        )
        SELECT
            rp.mandi_name,
            rp.modal_price,
            rp.price_date,
            (CURRENT_DATE - rp.price_date) AS days_since_update,
            m.id as mandi_id,
            m.state,
            m.district,
            m.latitude,
            m.longitude
        FROM recent_prices rp
        LEFT JOIN mandis m ON m.id = rp.mandi_id
        ORDER BY rp.modal_price DESC
        LIMIT :limit
    """)
    # CRITICAL: use max_date (not CURRENT_DATE) as the reference date to compute days_since_update
    # The price dataset ends 2025-10-30; CURRENT_DATE would show all data as 100+ days stale
```

**IMPORTANT DATA FRESHNESS ISSUE:** The price dataset ends 2025-10-30 (4+ months behind 2026-03-02). Using `date.today()` as the freshness reference will cause ALL data to appear stale. The arbitrage service MUST use `MAX(price_date)` for the dataset as the reference point. The UI must display "Data last updated [max_price_date] — signal may be outdated" as per the roadmap success criteria, rather than silently suppressing all results.

### Pattern 2: Margin Threshold Gate

**What:** After computing net profit per result, filter out results where margin < configurable threshold.
**When to use:** Always. ARB-02 requirement. Default 10%.

```python
# Source: Project decision from STATE.md — "Arbitrage threshold (10% net margin) is a configurable parameter"
# Add to backend/app/core/config.py Settings class:
arbitrage_margin_threshold_pct: float = Field(
    default=10.0,
    ge=0.0,
    le=50.0,
    description="Minimum net margin (%) required to show an arbitrage signal. Default: 10% of modal price.",
)

# In arbitrage/service.py:
def _exceeds_margin_threshold(comp: MandiComparison, threshold_pct: float) -> bool:
    """Return True if net margin exceeds threshold (net_profit / gross_revenue >= threshold_pct/100)."""
    if comp.gross_revenue <= 0:
        return False
    margin_pct = (comp.net_profit / comp.gross_revenue) * 100
    return margin_pct >= threshold_pct
```

### Pattern 3: GET endpoint (not POST)

**What:** Arbitrage is a read operation — commodity + district as path params or query params. Use `GET`, not `POST`.
**When to use:** This endpoint. The transport `/compare` endpoint uses POST because it accepts a complex body (quantity, vehicle preferences, distance filters). Arbitrage is simpler — commodity + district are the only required inputs.

```python
# Source: Existing FastAPI router pattern from transport/routes.py
router = APIRouter(prefix="/arbitrage", tags=["Arbitrage"])

@router.get(
    "/{commodity}/{district}",
    response_model=ArbitrageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Mandi Arbitrage Signals",
)
def get_arbitrage_signals(
    commodity: str,
    district: str,
    quantity_kg: float = Query(default=1000.0, ge=1.0, le=50000.0),
    max_distance_km: float | None = Query(default=None, gt=0, le=1000),
    db: Session = Depends(get_db),
) -> ArbitrageResponse:
    ...
```

### Pattern 4: ArbitrageResponse Schema

**What:** New Pydantic schema extending (not replacing) the existing MandiComparison fields.
**When to use:** For all arbitrage API responses.

```python
# Source: Pattern from transport/schemas.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import date

class ArbitrageResult(BaseModel):
    """Single arbitrage opportunity — top destination mandi."""
    mandi_name: str
    district: str
    state: str
    distance_km: float
    travel_time_hours: float
    freight_cost_per_quintal: float      # costs.total_cost / quantity_kg * 100
    spoilage_percent: float
    net_profit_per_quintal: float         # profit_per_kg * 100
    verdict: str                          # excellent / good / marginal
    is_interstate: bool
    price_date: date                      # Date of price data used
    days_since_update: int                # Age of price data (relative to MAX(price_date) in dataset)
    is_stale: bool                        # True if days_since_update > 7
    stale_warning: str | None             # "Data last updated [date] — signal may be outdated"
    model_config = ConfigDict(from_attributes=True)

class ArbitrageResponse(BaseModel):
    """Response from GET /api/v1/arbitrage/{commodity}/{district}."""
    commodity: str
    origin_district: str
    results: list[ArbitrageResult]        # Top 3 max, sorted by net_profit_per_quintal desc
    suppressed_count: int                 # How many mandis were suppressed by margin threshold
    threshold_pct: float                  # The margin threshold applied
    data_reference_date: date             # MAX(price_date) across dataset — what "fresh" means
    has_stale_data: bool                  # True if any result has is_stale=True
    distance_note: str | None            # Set when haversine fallback used
    model_config = ConfigDict(from_attributes=True)
```

### Pattern 5: Frontend — Arbitrage Page Structure

**What:** Commodity + district selectors, a results table showing top 3, freshness badges.
**When to use:** The arbitrage page. Mirrors the transport page pattern but simpler.

```typescript
// Source: Pattern from frontend/src/app/transport/page.tsx + frontend/src/services/transport.ts
"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { arbitrageService } from "@/services/arbitrage"

export default function ArbitragePage() {
    const [commodity, setCommodity] = useState<string>("")
    const [district, setDistrict] = useState<string>("")
    const [submitted, setSubmitted] = useState(false)

    const { data, isLoading, error } = useQuery({
        queryKey: ["arbitrage", commodity, district],
        queryFn: () => arbitrageService.getResults(commodity, district),
        enabled: submitted && !!commodity && !!district,
        staleTime: 5 * 60 * 1000, // 5 min cache — data won't change during session
    })

    // ... render selectors, results table, freshness badges
}
```

### Pattern 6: main.py Router Registration

**What:** Register the new arbitrage router in `backend/app/main.py`.
**When to use:** After creating `backend/app/arbitrage/routes.py`.

```python
# Source: Existing pattern in backend/app/main.py
from app.arbitrage.routes import router as arbitrage_router
# ...
app.include_router(arbitrage_router, prefix="/api/v1")
```

### Anti-Patterns to Avoid

- **Using `date.today()` for freshness threshold:** The dataset ends 2025-10-30. `date.today()` (2026-03-02) produces a 4-month gap, making ALL data appear stale. Always use `MAX(price_date)` as the reference date.
- **Modifying `get_mandis_for_commodity()` in `service.py`:** That function is shared with the transport endpoint. Adding a 7-day filter there breaks transport (which correctly uses 30-day window). Create a new function in `arbitrage/service.py`.
- **Passing raw `compare_mandis()` response to arbitrage endpoint:** `compare_mandis()` accepts `TransportCompareRequest` which requires `quantity_kg`. For arbitrage normalised per-quintal comparison, use 1 quintal (100 kg) as the fixed quantity, or compute per-quintal values from actual results. Do not expose `quantity_kg` as a required field in the arbitrage UI.
- **Mixing the arbitrage freshness gate with the transport freshness logic:** Keep them separate. Transport page shows 30-day data (trader planning). Arbitrage page shows 7-day data (time-sensitive signal). They serve different users.
- **Suppressing stale results silently:** ARB-03 says "stale data is flagged rather than shown as current." UI-05 says "no silent failures." Return stale results with `is_stale: true` and a warning, or return a response with `has_stale_data: true` and a dataset-level warning. Do NOT simply omit stale mandis from the response.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Freight calculation | Custom formula | `compute_freight()` from `economics.py` | Already accounts for diesel price, BATA, toll, breakdown reserve, RTO, interstate permit — 8 cost components |
| Spoilage estimation | Custom decay | `compute_spoilage()` from `spoilage.py` | Handles perishability by commodity category, travel hours, volatility; grade discount factored in |
| Road distance | Haversine only | `routing_service.get_distance_km()` | DB cache → OSRM → haversine fallback; parallel execution via ThreadPoolExecutor already implemented |
| Risk scoring | Custom logic | `compute_risk_score()` from `risk_engine.py` | Composite risk (volatility, distance, diesel, interstate) already implemented and tested |
| Price volatility | Custom stats | `compute_price_analytics()` from `price_analytics.py` | 7-day CV%, trend, confidence score — already exactly what arbitrage needs |
| Net profit calculation | New formula | `calculate_net_profit()` from `service.py` | Handles real freight + spoilage + hamali + mandi fee + commission + additional costs |
| Mandi comparison + ranking | New ranking | `compare_mandis()` from `service.py` | Full pipeline with behavioral corrections and verdict tiers — call it with `limit=3` |

**Key insight:** The transport engine is the most sophisticated part of this codebase. Phase 6 is an orchestration layer over it, not a new engine. The arbitrage endpoint's value is the 7-day freshness gate and the simplified UX (per-quintal, top 3), not new economic logic.

---

## Common Pitfalls

### Pitfall 1: The "Today's Date" Staleness Trap

**What goes wrong:** Developer writes `date.today() - timedelta(days=7)` as the freshness cutoff. With the dataset ending 2025-10-30, ALL mandis return zero results. The endpoint returns an empty list with no explanation.
**Why it happens:** Standard freshness logic assumes live data. This dataset has a 4+ month lag.
**How to avoid:** Always compute freshness relative to `MAX(price_date)` across the dataset for the given commodity. Expose `data_reference_date` in the API response so the UI can display "Based on data through [date]."
**Warning signs:** Empty results for any commodity when data visibly exists in the database.

### Pitfall 2: compare_mandis() Blocking the Event Loop

**What goes wrong:** The existing `compare_transport_options()` route handler is `def` (synchronous), not `async def`. This is intentional — FastAPI runs sync routes in a threadpool so blocking OSRM calls don't freeze the event loop. If the new arbitrage route is declared `async def`, the OSRM calls (which use `httpx.get()` synchronously) will block.
**Why it happens:** The OSRM async trap documented in project memory: "httpx.get() inside async def FastAPI handler blocks the event loop."
**How to avoid:** Make the new arbitrage route handler `def` (synchronous), not `async def`. FastAPI will run it in a threadpool automatically.
**Warning signs:** All API endpoints freeze when arbitrage endpoint is called simultaneously.

### Pitfall 3: Margin Threshold Applied to Gross Revenue, Not Modal Price

**What goes wrong:** ARB-02 says "10% of commodity modal price." Developer interprets this as "10% of gross_revenue" (i.e., margin = net_profit / gross_revenue). These are equivalent but the phrasing "10% of modal price" could be read as an absolute Rs threshold (modal_price * 0.10 = min net profit).
**Why it happens:** Ambiguous requirement language.
**How to avoid:** Implement as margin percentage: `(net_profit / gross_revenue) * 100 >= threshold_pct`. This scales correctly with price and quantity. Document the interpretation in the settings field description.
**Warning signs:** Threshold suppresses all low-price commodity results or passes all high-price commodity results regardless of actual transport costs.

### Pitfall 4: compare_mandis() Returns Full MandiComparison — price_date Not Directly Available

**What goes wrong:** `compare_mandis()` returns `MandiComparison` objects which do not include `price_date`. The freshness information is computed in `price_analytics_map` inside `compare_mandis()` but is not surfaced in the returned schema. Developer cannot annotate results with `is_stale` without reworking the comparison pipeline.
**Why it happens:** `MandiComparison.confidence_score` captures "stale" as a penalty but doesn't expose the actual price date.
**How to avoid:** Two options: (A) Add `price_date: date | None` field to `MandiComparison` schema (LOW risk — backward compatible), or (B) Make the arbitrage service call `get_arbitrage_mandis()` (new function with 7-day filter) and run a lighter comparison. Option A is cleaner and keeps the transport pipeline as the single source of truth. Add `latest_price_date` from `price_analytics_map` to `MandiComparison`.
**Warning signs:** Arbitrage response returns `is_stale: null` or all results show `days_since_update: 0`.

### Pitfall 5: Frontend — Stable Router Reference in Tests

**What goes wrong:** Vitest test for the arbitrage page renders an infinite loop due to unstable `useRouter` mock.
**Why it happens:** Documented in project memory: "If page has `useEffect(..., [router])`, the `useRouter` mock MUST return a stable object."
**How to avoid:** Define router mock once using `vi.hoisted()`, not inline in the factory function:
```typescript
const mockRouter = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => mockRouter }))
```
**Warning signs:** Vitest hangs indefinitely on arbitrage page test.

### Pitfall 6: `nyquist_validation` Not in config.json

**What goes wrong:** The `.planning/config.json` does not have a `workflow.nyquist_validation` key (only has `workflow.research`, `workflow.plan_check`, `workflow.verifier`, `workflow.auto_advance`). The Validation Architecture section of this research document cannot be conditionally skipped via that key.
**Resolution:** Config does not disable Nyquist validation (key absent = treat as enabled per research agent instructions). Validation Architecture section included below.

---

## Code Examples

Verified patterns from existing codebase:

### Arbitrage Service: Freshness-Gated Query

```python
# Source: Adapted from backend/app/transport/service.py get_mandis_for_commodity()
# Key change: 7-day window, MAX(price_date) reference, expose price_date per row

from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import timedelta

def get_arbitrage_mandis(commodity_id: str, db: Session, limit: int = 100) -> list[dict]:
    """Fetch mandis with price data within 7 days of the dataset's max_date."""
    max_date = db.execute(
        text("SELECT MAX(price_date) FROM price_history WHERE commodity_id = CAST(:cid AS UUID)"),
        {"cid": str(commodity_id)}
    ).scalar()
    if not max_date:
        return []

    cutoff = max_date - timedelta(days=7)

    query = text("""
        WITH recent_prices AS (
            SELECT DISTINCT ON (ph.mandi_name)
                ph.mandi_name,
                ph.mandi_id,
                ph.modal_price,
                ph.price_date
            FROM price_history ph
            WHERE ph.commodity_id = CAST(:commodity_id AS UUID)
              AND ph.price_date >= :cutoff
              AND ph.modal_price > 0
            ORDER BY ph.mandi_name, ph.price_date DESC
        )
        SELECT
            rp.mandi_name,
            rp.modal_price,
            rp.price_date,
            (:max_date - rp.price_date) AS days_since_update,
            m.id as mandi_id,
            m.state,
            m.district,
            m.latitude,
            m.longitude
        FROM recent_prices rp
        LEFT JOIN mandis m ON m.id = rp.mandi_id
        ORDER BY rp.modal_price DESC
        LIMIT :limit
    """)
    rows = db.execute(query, {
        "commodity_id": str(commodity_id),
        "cutoff": str(cutoff),
        "max_date": str(max_date),
        "limit": limit,
    }).fetchall()
    # ... build and return list[dict] with price_date, days_since_update
```

### Margin Threshold Filter

```python
# Source: Project constraint from STATE.md + ARB-02
def filter_by_margin_threshold(
    comparisons: list,
    threshold_pct: float,
) -> tuple[list, int]:
    """
    Filter arbitrage results by minimum net margin threshold.
    Returns (passing_results, suppressed_count).
    """
    passing = []
    suppressed = 0
    for comp in comparisons:
        if comp.gross_revenue > 0:
            margin_pct = (comp.net_profit / comp.gross_revenue) * 100
        else:
            margin_pct = 0.0
        if margin_pct >= threshold_pct:
            passing.append(comp)
        else:
            suppressed += 1
    return passing, suppressed
```

### config.py: New Setting

```python
# Source: Pattern from backend/app/core/config.py Settings class
arbitrage_margin_threshold_pct: float = Field(
    default=10.0,
    ge=0.0,
    le=50.0,
    description="Minimum net margin (%) to show arbitrage signal. 10% = net_profit/gross_revenue >= 0.10.",
)
```

### FastAPI Route Registration

```python
# Source: backend/app/main.py — exact pattern for adding new routers
from app.arbitrage.routes import router as arbitrage_router
# In main.py after existing include_router calls:
app.include_router(arbitrage_router, prefix="/api/v1")
```

### Frontend Service

```typescript
// Source: Pattern from frontend/src/services/transport.ts
import api from '@/lib/api';

export interface ArbitrageResult {
    mandi_name: string;
    district: string;
    state: string;
    distance_km: number;
    travel_time_hours: number;
    freight_cost_per_quintal: number;
    spoilage_percent: number;
    net_profit_per_quintal: number;
    verdict: string;
    is_interstate: boolean;
    price_date: string;       // ISO date string
    days_since_update: number;
    is_stale: boolean;
    stale_warning: string | null;
}

export interface ArbitrageResponse {
    commodity: string;
    origin_district: string;
    results: ArbitrageResult[];
    suppressed_count: number;
    threshold_pct: number;
    data_reference_date: string;  // ISO date — what "fresh" means
    has_stale_data: boolean;
    distance_note: string | null;
}

export const arbitrageService = {
    async getResults(commodity: string, district: string): Promise<ArbitrageResponse> {
        const response = await api.get(`/arbitrage/${encodeURIComponent(commodity)}/${encodeURIComponent(district)}`);
        return response.data;
    },
};
```

### Frontend Test: Stable Router Mock

```typescript
// Source: Project memory — Vitest Mock Pitfalls
// Apply to frontend/src/app/arbitrage/__tests__/page.test.tsx
import { vi } from "vitest";

const mockRouter = vi.hoisted(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: () => mockRouter,
    usePathname: () => "/arbitrage",
}));
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Haversine-only distance | OSRM + DB cache + haversine fallback | Phase completed 2026-02-28 | Road distances are accurate; fallback handled automatically |
| Legacy loading/unloading constants (Rs/kg flat rate) | Regional hamali rates via `compute_hamali()` | Phase completed 2026-02-28 | Loading/unloading cost now varies by state |
| Single `loading_cost` / `unloading_cost` fields | `loading_hamali` / `unloading_hamali` fields (legacy fields retained for backward compat) | 2026-02-28 | Both field names exist in schema; use `loading_hamali` for new code |
| Mandi price window: ad-hoc | 30-day DISTINCT ON window with date-bounded CTE | 2026-02-28 | Safe on 25M-row table; Phase 6 narrows to 7 days |

**Current transport endpoint URL:** `POST /api/v1/transport/compare`
**New arbitrage endpoint URL:** `GET /api/v1/arbitrage/{commodity}/{district}`
**Note:** REQUIREMENTS.md SERV-01 specifies `/api/v1/arbitrage/{commodity}/{district}` as the endpoint path — this is the correct path to implement.

---

## Open Questions

1. **Should MandiComparison schema be extended with `latest_price_date`?**
   - What we know: `price_analytics_map` inside `compare_mandis()` has `latest_price_date` per mandi but it is not returned in `MandiComparison`
   - What's unclear: Whether modifying the shared schema breaks the transport endpoint or its tests
   - Recommendation: Add `price_date: date | None = Field(default=None, ...)` to `MandiComparison` — backward compatible (nullable with default). Populate it in `compare_mandis()` from `price_analytics_map`. The transport endpoint will silently pass it through without UI changes. This is cleaner than duplicating the compare pipeline in `arbitrage/service.py`.

2. **Per-quintal vs per-kg normalisation in API response**
   - What we know: Price history stores prices in Rs per quintal (100 kg). `calculate_net_profit()` works in Rs per kg. `profit_per_kg` is already computed.
   - What's unclear: Whether to return `profit_per_kg * 100` or `net_profit / quantity_kg * 100` in the response (they should be equal; confirm)
   - Recommendation: Return `profit_per_kg * 100` as `net_profit_per_quintal` (a multiplication, no DB roundtrip). Document the conversion clearly in schema description.

3. **Coverage gap: what if origin district has no price data?**
   - What we know: `get_source_coordinates()` resolves district → lat/lon for transport, not for pricing. Arbitrage requires origin price data to compute the "price differential" signal. The current transport engine doesn't use origin price — it uses destination prices only.
   - What's unclear: Whether "origin district price" is actually needed for the arbitrage calculation, or whether the engine purely compares net profit after transport (which uses destination price as revenue)
   - Recommendation: The transport engine is correct — it ranks destinations by net profit (destination price - transport costs), NOT by price differential between origin and destination. ARB-01 says "ranked by net profit after freight + spoilage," which is what `compare_mandis()` already computes. No origin price needed. The farmer's "current price" is implicitly what they'd get by selling locally; the arbitrage signal is "can you do better by trucking it?"

4. **Should the freshness gate exclude stale mandis or include them with a warning?**
   - What we know: ARB-03: "stale pairs show a warning rather than current-looking price." UI-05: "no silent failures." The roadmap says "stale pairs show 'Data last updated [date] — signal may be outdated' warning."
   - Recommendation: Include stale mandis in the response with `is_stale: true` and `stale_warning` populated. Do NOT exclude them. The UI decides whether to show them dimmed or with a warning badge. An empty results page with no explanation violates UI-05.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest (pytest.ini in `backend/`) |
| Frontend framework | Vitest 1.6.x (vitest.config.ts in `frontend/`) |
| Backend quick run | `cd backend && python -m pytest tests/test_arbitrage_service.py -x -v` |
| Backend full suite | `cd backend && python -m pytest tests/ -v --tb=short` |
| Frontend quick run | `cd frontend && npx vitest run src/app/arbitrage/__tests__/` |
| Frontend full suite | `cd frontend && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARB-01 | Top 3 mandis returned, ranked by net_profit_per_quintal desc | unit | `pytest tests/test_arbitrage_service.py::TestArbitrageService::test_returns_top_3_ranked -x` | ❌ Wave 0 |
| ARB-01 | GET /arbitrage/{commodity}/{district} returns 200 with results list | integration | `pytest tests/test_arbitrage_api.py::TestArbitrageEndpoint::test_successful_arbitrage -x` | ❌ Wave 0 |
| ARB-02 | Results with margin < 10% are suppressed; suppressed_count incremented | unit | `pytest tests/test_arbitrage_service.py::TestArbitrageService::test_margin_threshold_filters_results -x` | ❌ Wave 0 |
| ARB-02 | Zero results returned + suppressed_count > 0 when all mandis below threshold | unit | `pytest tests/test_arbitrage_service.py::TestArbitrageService::test_all_suppressed_returns_empty -x` | ❌ Wave 0 |
| ARB-03 | 7-day freshness: mandis with price_date older than cutoff excluded from main results | unit | `pytest tests/test_arbitrage_service.py::TestArbitrageService::test_7day_freshness_gate -x` | ❌ Wave 0 |
| ARB-03 | Stale mandis returned with is_stale=True and stale_warning populated | unit | `pytest tests/test_arbitrage_service.py::TestArbitrageService::test_stale_results_have_warning -x` | ❌ Wave 0 |
| ARB-03 | MAX(price_date) used as reference, not date.today() | unit | `pytest tests/test_arbitrage_service.py::TestArbitrageService::test_reference_date_is_max_price_date -x` | ❌ Wave 0 |
| ARB-04 | Each result contains all 5 required fields: distance_km, travel_time_hours, freight_cost_per_quintal, spoilage_percent, net_profit_per_quintal | unit | `pytest tests/test_arbitrage_service.py::TestArbitrageService::test_result_fields_complete -x` | ❌ Wave 0 |
| UI-04 | Commodity + district selectors render; results table shows on submit | unit (Vitest) | `npx vitest run src/app/arbitrage/__tests__/page.test.tsx` | ❌ Wave 0 |
| UI-04 | Results table shows distance, travel time, freight, spoilage, net profit columns | unit (Vitest) | `npx vitest run src/app/arbitrage/__tests__/page.test.tsx` | ❌ Wave 0 |
| UI-05 | Freshness warning banner shown when has_stale_data=true | unit (Vitest) | `npx vitest run src/app/arbitrage/__tests__/page.test.tsx` | ❌ Wave 0 |
| UI-05 | Empty state shown when suppressed_count > 0 and results empty | unit (Vitest) | `npx vitest run src/app/arbitrage/__tests__/page.test.tsx` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/test_arbitrage_service.py tests/test_arbitrage_api.py -x -v`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v --tb=short` + `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps (all new — no existing test files for arbitrage)

- [ ] `backend/tests/test_arbitrage_service.py` — covers ARB-01, ARB-02, ARB-03, ARB-04
- [ ] `backend/tests/test_arbitrage_api.py` — integration tests via TestClient; covers ARB-01, ARB-02
- [ ] `frontend/src/app/arbitrage/__tests__/page.test.tsx` — covers UI-04, UI-05
- [ ] `frontend/src/services/arbitrage.ts` — new service file (not a test, but required before tests)
- [ ] `backend/app/arbitrage/__init__.py` — module init
- [ ] `backend/app/arbitrage/schemas.py` — `ArbitrageResult`, `ArbitrageResponse`
- [ ] `backend/app/arbitrage/service.py` — `get_arbitrage_results()`, `get_arbitrage_mandis()`
- [ ] `backend/app/arbitrage/routes.py` — `GET /arbitrage/{commodity}/{district}`

*(No framework installs needed — pytest and Vitest are both configured)*

---

## Sources

### Primary (HIGH confidence)

- `backend/app/transport/service.py` — `compare_mandis()`, `get_mandis_for_commodity()`, `calculate_net_profit()` — read directly from codebase
- `backend/app/transport/schemas.py` — `MandiComparison`, `TransportCompareResponse` — read directly
- `backend/app/transport/economics.py` — `compute_freight()`, vehicle rates, constants — read directly
- `backend/app/transport/spoilage.py` — `compute_spoilage()`, `compute_hamali()` — confirmed via service.py imports
- `backend/app/transport/routing.py` — OSRM + haversine fallback — read directly
- `backend/app/transport/price_analytics.py` — `compute_price_analytics()`, 7-day query pattern — read directly
- `backend/app/core/config.py` — Settings fields, how to add new configurable threshold — read directly
- `backend/app/main.py` — Router registration pattern — read directly
- `frontend/src/services/transport.ts` — Frontend service pattern for arbitrage service — read directly
- `frontend/src/app/transport/page.tsx` — Frontend page pattern for arbitrage page — read (large file, confirmed pattern)
- `frontend/package.json` — Confirmed all needed libraries already installed
- `.planning/STATE.md` — Project decisions: "Arbitrage threshold (10% net margin) is configurable"
- `.planning/REQUIREMENTS.md` — ARB-01 through ARB-04, UI-04, UI-05, SERV-01 endpoint path
- `.planning/ROADMAP.md` — Phase 6 success criteria, dependency chain

### Secondary (MEDIUM confidence)

- Project memory (MEMORY.md) — Transport engine architecture, OSRM async trap, Windows compatibility notes, Vitest mock pitfalls — cross-verified against actual source files

### Tertiary (LOW confidence)

- None — all findings verified against in-codebase source

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries confirmed installed in package.json and requirements; no new dependencies
- Architecture: HIGH — all engine modules read directly; new code is orchestration over existing functions
- Pitfalls: HIGH — OSRM async trap and date.today() freshness issue verified from codebase; Vitest mock pitfall documented in project memory and cross-checked against existing tests
- Test mapping: HIGH — pytest.ini and vitest.config.ts both read; test file locations confirmed from glob search

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable stack — no fast-moving dependencies)
