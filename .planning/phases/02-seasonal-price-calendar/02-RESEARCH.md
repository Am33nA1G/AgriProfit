# Phase 2: Seasonal Price Calendar - Research

**Researched:** 2026-03-02
**Domain:** Pre-aggregated time-series statistics from Parquet, FastAPI read-only endpoint, Recharts bar/line chart in Next.js
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEAS-01 | User selects any of 314 commodities + any state, sees monthly price chart (average +/- std) over last 10 years | pandas groupby(commodity, state, month) with median+IQR from parquet; FastAPI endpoint reads `seasonal_price_stats` |
| SEAS-02 | Calendar highlights cheapest and most expensive months with labels | `best_months` and `worst_month` columns derived during aggregation; endpoint returns pre-computed ranks |
| SEAS-03 | Calendar shows data confidence — fewer than 3 years of data shows low-confidence warning | `years_of_data` column in `seasonal_price_stats`; endpoint returns it; UI checks it before rendering |
| SEAS-04 | Calendar data pre-aggregated in `seasonal_price_stats` table — no ad-hoc full-table scans | `train_seasonal.py` reads parquet, upserts into table; endpoint only queries that table, never `price_history` |
| UI-01 | Seasonal price calendar page: commodity + state selector, monthly bar/line chart, best/worst month highlights | Next.js page with Recharts BarChart/ComposedChart, Select components from Radix UI, coverage gap message |
| UI-05 | All dashboards display coverage gap messages when feature unavailable for selected region | SeasonalCalendar page shows inline warning when `years_of_data < 3` or no data for selection |
</phase_requirements>

---

## Summary

Phase 2 delivers the first farmer-facing ML feature: a seasonal price calendar that answers "when is the best month to sell this commodity in this state?" It is a deliberately simple phase — pure SQL aggregation from historical data, no model training, no ML inference. The entire computational work happens offline in a training script (`train_seasonal.py`) that reads the 25M-row price parquet and writes one aggregate row per (commodity, state, month) into a `seasonal_price_stats` PostgreSQL table. The FastAPI endpoint then serves requests by querying only that 12-row-per-selection summary table.

The key architectural constraint is that the 25M-row `price_history` table must never be scanned at request time. A query scanning it without an indexed date range takes 60+ seconds (documented in MEMORY.md). The pre-aggregation table eliminates this risk entirely: at query time, the endpoint executes a simple `SELECT ... WHERE commodity_name = ? AND state_name = ?` against a table with at most ~314 × 36 × 12 = ~135,648 rows — sub-millisecond.

For the frontend, Recharts 3.7.0 is already installed. The project already uses Radix UI Select, TanStack Query v5, Zustand, and Tailwind. No new frontend dependencies are needed. The seasonal calendar page follows the same structure as the transport page: commodity + state selectors, a `useQuery` hook, and a Recharts chart rendering the response. The project already has 28 Indian states listed in `transport/page.tsx` — this list can be reused directly.

**Primary recommendation:** Pre-aggregate from parquet using pandas groupby in a standalone `train_seasonal.py` script. Store results in `seasonal_price_stats` (one row per commodity+state+month). FastAPI endpoint reads only that table. Next.js page uses Recharts ComposedChart with Bar (median price) and ErrorBar (IQR) to show distribution spread. All work is offline except the read endpoint.

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.2.3 (active in requirements.txt) | Load parquet, groupby aggregation | Already used in Phase 1; `groupby(['commodity','state','month']).agg(median, quantile)` is the exact pattern |
| pyarrow | 17.0.0 (active in requirements.txt) | Parquet engine for pandas | Required by pandas parquet reader; project-confirmed version |
| SQLAlchemy | 2.0.46 (active) | Raw SQL upsert from script | Follow clean_prices.py pattern exactly |
| alembic | 1.18.1 (active) | `seasonal_price_stats` table migration | Follow c2d3e4f5a6b7_add_price_bounds.py pattern |
| FastAPI | 0.128.0 (active) | Seasonal endpoint at `/api/v1/seasonal/{commodity}/{state}` | Existing router pattern |
| pydantic | 2.12.5 (active) | Response schema for seasonal data | Follow transport/schemas.py pattern |
| recharts | 3.7.0 (active in frontend) | Monthly bar/line chart with IQR spread | Already installed; ComposedChart + Bar + ErrorBar |
| @tanstack/react-query | 5.90.20 (active in frontend) | Data fetching with loading/error states | Already used in transport page |
| @radix-ui/react-select | 2.0.0 (active in frontend) | Commodity and state dropdown selectors | Already used throughout the app |

### No New Dependencies Required

All required libraries for both the aggregation script and the frontend are already installed and active in the project.

---

## Architecture Patterns

### Recommended Project Structure

New files for Phase 2:

```
backend/
├── app/
│   ├── ml/
│   │   ├── __init__.py              # Already exists
│   │   └── seasonal/
│   │       ├── __init__.py          # New
│   │       └── aggregator.py        # Pure functions: compute_monthly_stats(), identify_best_worst_months()
│   └── seasonal/                    # New FastAPI module
│       ├── __init__.py
│       ├── routes.py                # GET /api/v1/seasonal/{commodity}/{state}
│       └── schemas.py               # MonthlyStatPoint, SeasonalCalendarResponse
├── scripts/
│   └── train_seasonal.py            # Aggregation script: reads parquet, upserts seasonal_price_stats
├── alembic/
│   └── versions/
│       └── d3e4f5a6b7c8_add_seasonal_price_stats.py
└── tests/
    └── test_seasonal.py             # Unit tests for pure aggregator functions

frontend/
└── src/
    └── app/
        └── seasonal/
            ├── page.tsx             # Seasonal Calendar page
            └── __tests__/
                └── seasonal.test.tsx
```

### Pattern 1: Offline Aggregation Script (train_seasonal.py)

**What:** Reads the 25M-row parquet, groups by (commodity, state, month), computes median + IQR, identifies best/worst months, and upserts into `seasonal_price_stats`.

**When to use:** Run once after Phase 1 completes (price_bounds already seeded). Repeatable — upsert with ON CONFLICT handles re-runs.

**Key computation steps:**
1. Load parquet with only needed columns: `commodity`, `state`, `price_modal`, `date`
2. Parse `date` to extract `month` (integer 1-12)
3. Apply price bounds from `price_bounds` table to cap outliers at read time (use `modal_price_clean = clip(price_modal, lower_cap, upper_cap)`)
4. Group by `(commodity, state, month)`, compute: median, Q1, Q3, IQR, count, years_of_data
5. For each (commodity, state) pair, rank months by median — top 2 = best, bottom 1 = worst
6. Upsert into `seasonal_price_stats`

**Example:**
```python
# Source: clean_prices.py pattern + pandas 2.x groupby approach from STATE.md
import pandas as pd
from sqlalchemy import text
from app.database.session import SessionLocal

def compute_monthly_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    df: columns [commodity, state, price_modal, month]
        price_modal already outlier-capped
    Returns: one row per (commodity, state, month) with aggregated stats
    """
    agg = (
        df.groupby(["commodity", "state", "month"])
        .agg(
            median_price=("price_modal", "median"),
            q1_price=("price_modal", lambda s: s.quantile(0.25)),
            q3_price=("price_modal", lambda s: s.quantile(0.75)),
            record_count=("price_modal", "count"),
        )
        .reset_index()
    )
    agg["iqr_price"] = agg["q3_price"] - agg["q1_price"]
    return agg


def compute_years_of_data(df: pd.DataFrame) -> pd.DataFrame:
    """Compute years_of_data per (commodity, state) — needed for confidence flag."""
    years = (
        df.groupby(["commodity", "state"])["year"]
        .nunique()
        .reset_index()
        .rename(columns={"year": "years_of_data"})
    )
    return years


def identify_best_worst_months(agg: pd.DataFrame) -> pd.DataFrame:
    """
    For each (commodity, state), rank months by median_price.
    Returns agg with added columns: month_rank (1=highest price), is_best (top 2), is_worst (bottom 1)

    IMPORTANT: pandas 2.x groupby().rank() — use explicit method='average' to avoid MultiIndex.
    Follow the STATE.md decision: explicit for-loop over groupby() for pandas 2.x compat.
    """
    rows = []
    for (commodity, state), group in agg.groupby(["commodity", "state"]):
        sorted_group = group.sort_values("median_price", ascending=False).copy()
        sorted_group["month_rank"] = range(1, len(sorted_group) + 1)
        sorted_group["is_best"] = sorted_group["month_rank"] <= 2
        sorted_group["is_worst"] = sorted_group["month_rank"] == len(sorted_group)
        rows.append(sorted_group)
    if not rows:
        return agg.assign(month_rank=0, is_best=False, is_worst=False)
    return pd.concat(rows, ignore_index=True)
```

### Pattern 2: seasonal_price_stats Table Schema

**What:** One row per (commodity_name, state_name, month). Stores pre-computed statistics. Read-only at request time.

**Why this structure:** Querying `WHERE commodity_name = ? AND state_name = ?` returns exactly 12 rows (Jan-Dec). No joins, no aggregations at request time. Total table size: at most ~135K rows — tiny.

```sql
-- Proposed schema for the Alembic migration
CREATE TABLE seasonal_price_stats (
    id          SERIAL PRIMARY KEY,
    commodity_name  VARCHAR(200)    NOT NULL,
    state_name      VARCHAR(100)    NOT NULL,
    month           SMALLINT        NOT NULL,  -- 1=Jan ... 12=Dec
    median_price    NUMERIC(12, 2)  NOT NULL,
    q1_price        NUMERIC(12, 2)  NOT NULL,
    q3_price        NUMERIC(12, 2)  NOT NULL,
    iqr_price       NUMERIC(12, 2)  NOT NULL,
    record_count    INTEGER         NOT NULL,
    years_of_data   SMALLINT        NOT NULL,  -- distinct calendar years with data
    is_best         BOOLEAN         NOT NULL DEFAULT FALSE,  -- top 2 months by median price
    is_worst        BOOLEAN         NOT NULL DEFAULT FALSE,  -- bottom 1 month by median price
    month_rank      SMALLINT        NOT NULL,  -- 1=highest median price, 12=lowest
    computed_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_seasonal_commodity_state_month
        UNIQUE (commodity_name, state_name, month)
);
CREATE INDEX idx_seasonal_commodity_state
    ON seasonal_price_stats (commodity_name, state_name);
```

### Pattern 3: FastAPI Seasonal Endpoint

**What:** Single GET endpoint. Reads 12 rows from `seasonal_price_stats`. Returns structured response. No joins to other tables.

**URL design:** `GET /api/v1/seasonal/{commodity}/{state}` — matches REQUIREMENTS.md SERV-01 URL spec for Phase 4.

**Key response fields:** 12 monthly data points with median, q1, q3, is_best, is_worst, plus top-level `years_of_data` and `low_confidence` flag.

```python
# Source: follows analytics/routes.py + transport/routes.py patterns
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(prefix="/seasonal", tags=["Seasonal"])

@router.get(
    "/{commodity}/{state}",
    response_model=SeasonalCalendarResponse,
    status_code=status.HTTP_200_OK,
)
def get_seasonal_calendar(
    commodity: str,
    state: str,
    db: Session = Depends(get_db),
) -> SeasonalCalendarResponse:
    rows = db.execute(
        text("""
            SELECT month, median_price, q1_price, q3_price,
                   iqr_price, record_count, years_of_data,
                   is_best, is_worst, month_rank
            FROM seasonal_price_stats
            WHERE commodity_name = :commodity
              AND state_name = :state
            ORDER BY month ASC
        """),
        {"commodity": commodity, "state": state},
    ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No seasonal data for commodity '{commodity}' in state '{state}'",
        )

    years_of_data = rows[0].years_of_data
    return SeasonalCalendarResponse(
        commodity=commodity,
        state=state,
        months=[MonthlyStatPoint(**dict(r._mapping)) for r in rows],
        years_of_data=years_of_data,
        low_confidence=years_of_data < 3,
    )
```

### Pattern 4: Next.js Seasonal Calendar Page

**What:** Commodity + state selectors, Recharts ComposedChart showing monthly median price with IQR as error bars, best/worst month badges.

**Follows transport/page.tsx pattern:** `"use client"`, `useQuery` for data fetching, `Select` from `@radix-ui/react-select`, `AppLayout` wrapper, `Card` components.

**Chart approach:** Use Recharts `ComposedChart` with `Bar` for median prices and `ErrorBar` on the Bar for IQR spread (showing Q1-Q3 range). Colour bars green for `is_best`, red for `is_worst`, default for others. This gives an immediate visual signal without needing to read labels.

```tsx
// Source: recharts docs + transport/page.tsx patterns already in codebase
import {
  ComposedChart, Bar, ErrorBar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts"

// Each data point: { month: "Jan", median_price: 450, errorY: [450-q1, q3-450], is_best, is_worst }
const chartData = months.map(m => ({
  month: MONTH_NAMES[m.month - 1],
  median_price: m.median_price,
  errorY: [m.median_price - m.q1_price, m.q3_price - m.median_price],
  is_best: m.is_best,
  is_worst: m.is_worst,
}))

// Bar fill: green for best months, red for worst, neutral otherwise
const getBarFill = (entry: typeof chartData[0]) => {
  if (entry.is_best) return "#16a34a"   // green-600
  if (entry.is_worst) return "#dc2626"  // red-600
  return "#6b7280"                       // gray-500
}
```

**Low-confidence warning (UI-05):** When `low_confidence === true` or no data found, render a visible alert component (same pattern as transport page's "unknown district" error states):
```tsx
{response.low_confidence && (
  <div className="rounded-md border border-yellow-500 bg-yellow-50 p-3 text-yellow-800 text-sm">
    Warning: Only {response.years_of_data} year(s) of data available for this
    selection. Seasonal patterns may not be reliable.
  </div>
)}
```

### Anti-Patterns to Avoid

- **Querying price_history at request time:** Never add a seasonal endpoint that computes aggregations from `price_history` on the fly. The 25M-row table without strict date bounds causes 60+ second timeouts (documented in MEMORY.md).
- **Using price_history.modal_price without applying price_bounds caps:** Raw `price_modal` contains unit-corruption outliers. Always apply `clip(price_modal, lower_cap, upper_cap)` using the `price_bounds` table before computing medians. The aggregation script must join `price_bounds` before computing stats.
- **Storing commodity UUID instead of name in seasonal_price_stats:** The parquet uses commodity name (string) as primary identifier; the DB uses UUID. Joining across both systems at query time is fragile. Store the name as-is from the parquet — it is already standardised.
- **pandas 2.x groupby().apply() returning pd.Series:** Creates MultiIndex. Use explicit for-loop over groupby() to build dict-of-rows and then pd.DataFrame(rows). Documented in STATE.md as a confirmed Phase 1 lesson.
- **Not handling the pyarrow 17.0.0 constraint:** The project uses pyarrow 17.0.0 (not 19.x) due to a "Repetition level histogram size mismatch" error with the price parquet. Do not upgrade pyarrow in requirements.txt.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Monthly median + IQR computation | Custom loop over price rows | `pandas groupby().agg(median, quantile)` | Vectorised, correct for large DataFrames; handles NaN automatically |
| Chart with error bars showing spread | Custom SVG or D3 | Recharts `ErrorBar` on `Bar` | Already installed; `ErrorBar` accepts `[lower, upper]` array; no new dependency |
| State/commodity selector with search | Custom dropdown | Radix UI `Select` (already installed) | Accessible, consistent with rest of app |
| Loading/error states | Custom spinner logic | TanStack Query `isLoading`, `isError`, `error` | Already used in transport page; consistent UX |
| Alembic migration | Manual ALTER TABLE | Alembic `op.create_table()` | Follow c2d3e4f5a6b7_add_price_bounds.py pattern exactly |

**Key insight:** The aggregation math (median, percentiles, year-count) is straightforward — the work is in the data pipeline hygiene: applying outlier caps from `price_bounds` before aggregating, handling missing months gracefully, and storing just enough metadata (`years_of_data`) to drive the confidence warning without another query.

---

## Common Pitfalls

### Pitfall 1: Forgetting to Apply Price Bounds Before Aggregating

**What goes wrong:** Computing median price directly from raw `price_modal` in the parquet. Guar CV=23,284%, Cumin Seed CV=22,214% — a single corrupt row in any month can make that month's median astronomically wrong.

**Why it happens:** The parquet has corrupt unit-error rows. The `price_bounds` table was created in Phase 1 specifically to provide caps for downstream computation. If the aggregation script doesn't join `price_bounds` and clip before groupby, the seasonal stats will be meaningless for volatile commodities.

**How to avoid:** In `train_seasonal.py`, before any groupby:
```python
bounds = pd.read_sql("SELECT commodity, lower_cap, upper_cap FROM price_bounds", engine)
df = df.merge(bounds, on="commodity", how="left")
df["price_modal"] = df["price_modal"].clip(
    lower=df["lower_cap"], upper=df["upper_cap"]
)
```

**Warning signs:** Onion seasonal chart shows one month with price 100x higher than all others.

### Pitfall 2: Alembic Down-Revision Chain

**What goes wrong:** Creating `seasonal_price_stats` migration with `down_revision = "b1c2d3e4f5a6"` when the actual HEAD is `c2d3e4f5a6b7` (price_bounds, the last Phase 1 migration). This creates a fork and `alembic upgrade head` fails with "multiple head revisions".

**Why it happens:** Phase 1 has two migrations chained: `b1c2d3e4f5a6` → `c2d3e4f5a6b7`. New Phase 2 migration must chain from `c2d3e4f5a6b7`.

**How to avoid:** Phase 2 migration must have `down_revision = "c2d3e4f5a6b7"`. Verify with `alembic current` before creating the migration.

**Warning signs:** `alembic upgrade head` fails with "Multiple head revisions" error.

### Pitfall 3: Recharts ErrorBar Direction

**What goes wrong:** Using `ErrorBar` with a single value, which Recharts interprets as symmetric ±value. For price data the IQR is asymmetric (Q1 and Q3 are not equidistant from median).

**Why it happens:** `ErrorBar` accepts either a number (symmetric) or a 2-element array `[lower, upper]` (asymmetric). Passing `iqr_price / 2` gives wrong error bar bounds.

**How to avoid:** Pass `errorY={[median - q1, q3 - median]}` — a 2-element array of the actual distances below and above the median.

**Warning signs:** Error bars look symmetric even though Q1 and Q3 are clearly asymmetric in the data.

### Pitfall 4: No Data vs Low Confidence — Different UX Required

**What goes wrong:** Treating "0 rows returned for this commodity+state" the same as "12 rows but only 1 year of data". The first is a true coverage gap ("Data not available"); the second is a data quality warning ("Low confidence").

**Why it happens:** Both are "not ideal" but require different UI messaging per UI-05.

**How to avoid:**
- 404 from endpoint → show "No seasonal data available for [commodity] in [state]" (coverage gap message, UI-05)
- 200 with `low_confidence: true` → show yellow warning banner above the chart (the chart still renders)
- Both states must be handled explicitly in the frontend

**Warning signs:** A state/commodity with 1 year of data renders with no warning and looks identical to high-confidence data.

### Pitfall 5: Month Ranking Boundary Condition

**What goes wrong:** Some (commodity, state) combinations may have fewer than 12 months of data (e.g., a commodity only traded March-October). Assigning `is_worst` to the bottom-ranked month when there are only 5 months means that month may not actually be "bad" — it's just the worst of a short series.

**Why it happens:** The ranking is relative within the available data, not absolute.

**How to avoid:** Only set `is_worst = True` when `years_of_data >= 3` AND `record_count >= 10` for that month. Months with sparse data should not be labelled worst. Consider setting `is_best = False` and `is_worst = False` for the entire series when `years_of_data < 3`.

**Warning signs:** A commodity shows "Avoid selling in April" but April only has 2 data points from a single year.

### Pitfall 6: Windows UTF-8 Console Crash in train_seasonal.py

**What goes wrong:** `print()` statements with state names containing special characters (e.g., "Jammu & Kashmir") crash with `UnicodeEncodeError` on Windows.

**Why it happens:** Windows console defaults to cp1252.

**How to avoid:** Add at top of `train_seasonal.py` (project standard per MEMORY.md):
```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Recharts ComposedChart with IQR ErrorBar

```tsx
// Source: recharts.org/api/ErrorBar + transport/page.tsx structure
import {
  ComposedChart, Bar, ErrorBar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend
} from "recharts"

const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

interface SeasonalChartProps {
  months: MonthlyStatPoint[]
}

export function SeasonalChart({ months }: SeasonalChartProps) {
  const data = months.map(m => ({
    name: MONTH_NAMES[m.month - 1],
    median: Number(m.median_price),
    errorY: [
      Number(m.median_price) - Number(m.q1_price),
      Number(m.q3_price) - Number(m.median_price)
    ] as [number, number],
    is_best: m.is_best,
    is_worst: m.is_worst,
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 20, right: 20, bottom: 5, left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis unit=" ₹" />
        <Tooltip formatter={(v: number) => [`₹${v.toFixed(0)}`, "Median Price"]} />
        <Bar dataKey="median" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.is_best ? "#16a34a" : entry.is_worst ? "#dc2626" : "#6b7280"}
            />
          ))}
          <ErrorBar dataKey="errorY" width={4} strokeWidth={2} stroke="#374151" />
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  )
}
```

### Alembic Migration for seasonal_price_stats

```python
# backend/alembic/versions/d3e4f5a6b7c8_add_seasonal_price_stats.py
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "c2d3e4f5a6b7"  # last Phase 1 migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "seasonal_price_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity_name", sa.String(200), nullable=False),
        sa.Column("state_name", sa.String(100), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("median_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("q1_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("q3_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("iqr_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("years_of_data", sa.SmallInteger(), nullable=False),
        sa.Column("is_best", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_worst", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("month_rank", sa.SmallInteger(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "commodity_name", "state_name", "month",
            name="uq_seasonal_commodity_state_month",
        ),
    )
    op.create_index(
        "idx_seasonal_commodity_state",
        "seasonal_price_stats",
        ["commodity_name", "state_name"],
    )

def downgrade() -> None:
    op.drop_index("idx_seasonal_commodity_state", table_name="seasonal_price_stats")
    op.drop_table("seasonal_price_stats")
```

### FastAPI Pydantic Schemas

```python
# backend/app/seasonal/schemas.py
from pydantic import BaseModel, ConfigDict, Field

class MonthlyStatPoint(BaseModel):
    month: int = Field(..., ge=1, le=12, description="Month number (1=Jan, 12=Dec)")
    median_price: float = Field(..., description="Median modal price (Rs/quintal)")
    q1_price: float = Field(..., description="25th percentile price")
    q3_price: float = Field(..., description="75th percentile price")
    iqr_price: float = Field(..., description="Interquartile range")
    record_count: int = Field(..., description="Number of daily price observations")
    years_of_data: int = Field(..., description="Distinct calendar years with data")
    is_best: bool = Field(..., description="True for top-2 months by median price")
    is_worst: bool = Field(..., description="True for bottom-1 month by median price")
    month_rank: int = Field(..., description="1=highest median price, 12=lowest")

    model_config = ConfigDict(from_attributes=True)


class SeasonalCalendarResponse(BaseModel):
    commodity: str
    state: str
    months: list[MonthlyStatPoint]
    years_of_data: int = Field(..., description="Max years of data across all months")
    low_confidence: bool = Field(
        ..., description="True when years_of_data < 3 — show UI warning"
    )

    model_config = ConfigDict(from_attributes=True)
```

### pandas Aggregation Core (train_seasonal.py)

```python
# Source: clean_prices.py pattern (Phase 1) adapted for monthly aggregation
import pandas as pd
from sqlalchemy import create_engine, text

def load_and_prepare(parquet_path: str, engine) -> pd.DataFrame:
    """
    Load parquet, apply price bounds caps, extract month and year.
    Returns DataFrame with columns: commodity, state, price_modal, month, year
    """
    df = pd.read_parquet(
        parquet_path,
        columns=["commodity", "state", "price_modal", "date"],
        engine="pyarrow",
    )
    df = df.dropna(subset=["price_modal"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    # Apply price bounds caps (crucial — prevents outlier corruption)
    bounds = pd.read_sql(
        "SELECT commodity, lower_cap, upper_cap FROM price_bounds",
        con=engine,
    )
    df = df.merge(bounds, on="commodity", how="left")
    df["price_modal"] = df["price_modal"].clip(
        lower=df["lower_cap"], upper=df["upper_cap"]
    )
    return df.drop(columns=["lower_cap", "upper_cap"])


def compute_seasonal_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate to (commodity, state, month) level.
    Returns DataFrame ready for upsert into seasonal_price_stats.
    """
    # Compute years_of_data per (commodity, state)
    years_df = (
        df.groupby(["commodity", "state"])["year"]
        .nunique()
        .reset_index()
        .rename(columns={"year": "years_of_data"})
    )

    # Compute monthly stats — explicit for-loop for pandas 2.x safety (per STATE.md)
    agg_rows = []
    for (commodity, state, month), group in df.groupby(["commodity", "state", "month"]):
        prices = group["price_modal"]
        q1 = float(prices.quantile(0.25))
        q3 = float(prices.quantile(0.75))
        agg_rows.append({
            "commodity_name": commodity,
            "state_name": state,
            "month": month,
            "median_price": float(prices.median()),
            "q1_price": q1,
            "q3_price": q3,
            "iqr_price": q3 - q1,
            "record_count": len(group),
        })
    agg = pd.DataFrame(agg_rows)

    # Join years_of_data
    agg = agg.merge(
        years_df.rename(columns={"commodity": "commodity_name", "state": "state_name"}),
        on=["commodity_name", "state_name"],
        how="left",
    )
    agg["years_of_data"] = agg["years_of_data"].fillna(0).astype(int)

    # Rank months per (commodity, state) — pandas 2.x safe explicit loop
    ranked_rows = []
    for (commodity, state), group in agg.groupby(["commodity_name", "state_name"]):
        sorted_g = group.sort_values("median_price", ascending=False).copy()
        sorted_g["month_rank"] = range(1, len(sorted_g) + 1)
        # Only mark best/worst if data is sufficiently complete
        if group["years_of_data"].iloc[0] >= 3:
            sorted_g["is_best"] = sorted_g["month_rank"] <= 2
            sorted_g["is_worst"] = sorted_g["month_rank"] == len(sorted_g)
        else:
            sorted_g["is_best"] = False
            sorted_g["is_worst"] = False
        ranked_rows.append(sorted_g)

    return pd.concat(ranked_rows, ignore_index=True)
```

### Upsert to seasonal_price_stats

```python
# Source: clean_prices.py upsert_price_bounds() pattern
def upsert_seasonal_stats(stats_df: pd.DataFrame, engine) -> int:
    """Upsert all rows into seasonal_price_stats. Returns rows written."""
    upsert_sql = text("""
        INSERT INTO seasonal_price_stats
            (commodity_name, state_name, month, median_price, q1_price, q3_price,
             iqr_price, record_count, years_of_data, is_best, is_worst, month_rank, computed_at)
        VALUES
            (:commodity_name, :state_name, :month, :median_price, :q1_price, :q3_price,
             :iqr_price, :record_count, :years_of_data, :is_best, :is_worst, :month_rank, now())
        ON CONFLICT (commodity_name, state_name, month) DO UPDATE SET
            median_price   = EXCLUDED.median_price,
            q1_price       = EXCLUDED.q1_price,
            q3_price       = EXCLUDED.q3_price,
            iqr_price      = EXCLUDED.iqr_price,
            record_count   = EXCLUDED.record_count,
            years_of_data  = EXCLUDED.years_of_data,
            is_best        = EXCLUDED.is_best,
            is_worst       = EXCLUDED.is_worst,
            month_rank     = EXCLUDED.month_rank,
            computed_at    = now()
    """)
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        count = 0
        for _, row in stats_df.iterrows():
            db.execute(upsert_sql, {
                "commodity_name": row["commodity_name"],
                "state_name":     row["state_name"],
                "month":          int(row["month"]),
                "median_price":   round(float(row["median_price"]), 2),
                "q1_price":       round(float(row["q1_price"]), 2),
                "q3_price":       round(float(row["q3_price"]), 2),
                "iqr_price":      round(float(row["iqr_price"]), 2),
                "record_count":   int(row["record_count"]),
                "years_of_data":  int(row["years_of_data"]),
                "is_best":        bool(row["is_best"]),
                "is_worst":       bool(row["is_worst"]),
                "month_rank":     int(row["month_rank"]),
            })
            count += 1
        db.commit()
    finally:
        db.close()
    return count
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Query price_history at request time for aggregations | Pre-aggregate into summary table, serve from there | This project's architecture decision (MEMORY.md, Phase 1 lessons) | Eliminates 60+ second timeouts; 12-row SELECT vs 25M-row scan |
| Symmetric error bars (±1 std deviation) | Asymmetric IQR error bars (Q1 to Q3 range) | Recharts ErrorBar supports asymmetric via 2-element array | More honest representation of price distribution skew |
| Single "average" price per month | Median + IQR (Q1, Q3) per month | Standard practice for skewed data | Agricultural prices are log-normally distributed; median resists extreme outliers better than mean |
| Ad-hoc confidence thresholds | Explicit `years_of_data` column with hard threshold (< 3 years = low confidence) | SEAS-03 requirement | Eliminates ambiguity about when to show warning |

**Deprecated/outdated for this project:**
- Parquet service as data source at request time: deprecated in MEMORY.md — "Parquet service deprecated - all queries use DB now." The aggregation script is the one allowed path from parquet to DB.
- Global (not per-commodity) price statistics: carry-over from Phase 1; per-commodity bounds are now in `price_bounds` and must be applied.

---

## Data Contracts (Critical for Planner)

### Price Parquet Columns Used

From Phase 1 Research (confirmed by direct inspection):
- `commodity` (string): Commodity name, e.g., "Onion", "Tomato" — 314 unique values
- `state` (string): State name as in Agmarknet — 36 states
- `price_modal` (float): Modal price (Rs/quintal) — may contain unit-corruption outliers; cap with `price_bounds` before use
- `date` (string/date): Price date — parse to extract `month` (1-12) and `year`

### price_bounds Table (Phase 1 output — already populated)

| Column | Use in Phase 2 |
|--------|---------------|
| `commodity` | Join key for applying caps |
| `lower_cap` | Lower clip bound for price_modal |
| `upper_cap` | Upper clip bound for price_modal |

### Spot-Check Validation Required

Per Phase 2 success criteria, two known patterns must be verified after `train_seasonal.py` runs:
1. **Onion**: `is_best = TRUE` for month IN (10, 11) for major onion-producing states (Maharashtra, Madhya Pradesh, Rajasthan)
2. **Tomato**: `is_best = TRUE` for month = 7 in West Bengal, OR month IN (2, 3) in Karnataka

If these are wrong, the issue is data quality, not code quality. The verification should be a simple SQL query in the verification step:
```sql
SELECT month, median_price, is_best, is_worst, years_of_data
FROM seasonal_price_stats
WHERE commodity_name = 'Onion' AND state_name = 'Maharashtra'
ORDER BY month;
```

### Alembic Migration Chain

Current chain (Phase 1 complete):
```
a2b3c4d5e6f7 (road_distance_cache)
  → b1c2d3e4f5a6 (district_name_map)
  → c2d3e4f5a6b7 (price_bounds)   ← current HEAD
  → d3e4f5a6b7c8 (seasonal_price_stats)   ← Phase 2 new migration
```

---

## Open Questions

1. **State name normalisation between parquet and future API params**
   - What we know: The parquet uses Agmarknet state names (e.g., "Uttar Pradesh", "West Bengal"). The frontend will pass these as URL path params.
   - What's unclear: Whether URL-encoding of state names with spaces ("Uttar Pradesh" → "Uttar%20Pradesh") is handled correctly by FastAPI path params vs query params.
   - Recommendation: Use query parameters instead of path params for the commodity and state to avoid URL-encoding issues: `GET /api/v1/seasonal?commodity=Onion&state=Maharashtra`. Alternatively, keep path params and let FastAPI handle decoding (it does this correctly for path parameters).

2. **Partial month coverage: some months may have zero rows**
   - What we know: Not all 314 commodities trade in all 12 months in all states. A (commodity, state, month) triple may have zero records.
   - What's unclear: Should missing months be stored as NULL rows or simply absent?
   - Recommendation: Store only months that have `record_count >= 1`. The frontend should render absent months as greyed-out bars at 0. Document this decision in the plan.

3. **Script runtime estimate for 25M rows**
   - What we know: clean_prices.py (Phase 1) loaded all 25M rows with 3 columns in roughly 60-90 seconds on typical hardware. The seasonal aggregation needs 4 columns and a groupby.
   - What's unclear: Exact runtime on the dev machine.
   - Recommendation: Load parquet in one pass with columns `["commodity", "state", "price_modal", "date"]`. Join price_bounds (314 rows) before groupby. Expect 3-8 minutes total. Document in train_seasonal.py docstring.

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — validation architecture section omitted per instructions.

---

## Sources

### Primary (HIGH confidence)

- Direct file inspection: `backend/requirements.txt` — confirmed pandas 2.2.3, pyarrow 17.0.0, scipy 1.17.0, SQLAlchemy 2.0.46 all active (not commented out)
- Direct file inspection: `frontend/package.json` — confirmed recharts 3.7.0, @tanstack/react-query 5.90.20, @radix-ui/react-select 2.0.0 all installed
- Direct file inspection: `backend/scripts/clean_prices.py` — confirmed aggregation script pattern (parquet load, groupby, upsert via SessionLocal)
- Direct file inspection: `backend/app/models/price_history.py` — confirmed PriceHistory schema, indexes
- Direct file inspection: `backend/alembic/versions/c2d3e4f5a6b7_add_price_bounds.py` — confirmed current HEAD migration and pattern
- Direct file inspection: `backend/app/transport/routes.py` and `schemas.py` — confirmed FastAPI endpoint structure to replicate
- Direct file inspection: `backend/app/analytics/routes.py` and `schemas.py` — confirmed endpoint + schema pattern
- Direct file inspection: `backend/tests/conftest.py` — confirmed SQLite in-memory test pattern for new tests
- Direct file inspection: `frontend/src/app/transport/page.tsx` — confirmed Recharts, Select, useQuery frontend patterns already in codebase
- `.planning/STATE.md` — confirmed pyarrow 17.0.0 constraint, pandas 2.x groupby loop pattern, price_history immutability rule
- `.planning/phases/01-district-harmonisation-price-cleaning/01-RESEARCH.md` — confirmed parquet columns, alembic chain, price_bounds schema

### Secondary (MEDIUM confidence)

- Recharts ErrorBar documentation (recharts.org/api/ErrorBar) — ErrorBar accepts `[lower, upper]` 2-element array for asymmetric error bars; confirmed by reading the transport page which uses similar Recharts patterns

### Tertiary (LOW confidence — not required, patterns already known from codebase)

- None needed — all required patterns exist in the current codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed and active; no new libraries needed
- Architecture patterns: HIGH — all patterns derived from existing codebase (clean_prices.py, transport routes, analytics routes, transport page.tsx)
- Data contracts: HIGH — parquet schema confirmed in Phase 1 research; price_bounds table already seeded
- Pitfalls: HIGH — outlier-cap pitfall and alembic chain pitfall are empirically confirmed from Phase 1; others derived from direct code inspection
- Recharts ErrorBar asymmetric: MEDIUM — API confirmed via documentation, but not yet used in this codebase

**Research date:** 2026-03-02
**Valid until:** 2026-06-01 (all libraries stable; recharts 3.x API stable; no ML dependencies)
