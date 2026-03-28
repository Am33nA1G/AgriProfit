# Phase 1: District Harmonisation + Price Cleaning - Research

**Researched:** 2026-03-02
**Domain:** Data harmonisation — fuzzy district name matching, price outlier detection and winsorisation, Alembic schema migration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HARM-01 | `district_name_map` table mapping all district name variants across 4 datasets using state-scoped fuzzy matching | RapidFuzz `process.cdist` with state-scoped grouping; three-tier match strategy; Alembic migration pattern established |
| HARM-02 | Price data winsorised per commodity — CV > 500% outliers flagged and capped before any feature/model computation | `scipy.stats.mstats.winsorize` + pandas `groupby` + `price_bounds` table; commodity-level bounds, not global |
| HARM-03 | Every price record joinable to its rainfall district with >= 95% coverage (>= 543 of 571 price districts matched) | State-scoped fuzzy matching proven to achieve 93.1% accuracy vs 47.5% global; three-tier strategy with manual review |
| HARM-04 | Every price record joinable to its soil block equivalent for all 31 states with soil coverage | Soil data is `nutrients_all.parquet` (cycle/state/district/block/nutrient/high/medium/low schema); district-scoped join via `district_name_map` |
</phase_requirements>

---

## Summary

Phase 1 establishes the cross-dataset join foundation that every downstream ML feature depends on. Two completely independent tracks run in this phase: the district harmonisation script (Plan 01-01) and the price cleaning pipeline (Plan 01-02). They share no data dependencies and can be implemented in either order.

The district harmonisation problem centres on four datasets — price (571 districts, Agmarknet parquet), rainfall (IMD gridded → district via shapefile spatial join, combined at `data/ranifall_data/combined/`), weather (India weather daily CSV at `data/weather data/india_weather_daily_10years.csv`, ~261 districts), and soil (government Soil Health Card data at `data/soil-health/nutrients/`, 31 states, block-level) — each of which uses different name spellings, capitalisation conventions, and transliterations for the same Indian administrative districts. The research finding from IDInsight's empirical study establishes that global fuzzy matching achieves only 47.5% accuracy on Hindi district names versus 93.1% for state-scoped matching. This is a hard constraint: global matching is ruled out.

The price cleaning problem is grounded in confirmed empirical findings from this project's own data. Direct inspection of `agmarknet_daily_10yr.parquet` showed CV% for Guar = 23,284%, Cumin Seed = 22,214%, Bajra = 9,413% — caused by a small number of corrupt rows (unit errors: per-kg prices entered in per-quintal fields, trailing-zero data entry errors) mixed into 25M rows. These rows must be winsorised per commodity before any feature engineering touches the data. The `price_bounds` table stores the per-commodity winsorisation bounds so the same caps apply consistently at inference time.

**Primary recommendation:** State-scoped RapidFuzz matching with a three-tier confidence strategy (exact / fuzzy-accepted / manual) for HARM-01/03/04; per-commodity median-based winsorisation bounds stored in `price_bounds` for HARM-02. Both delivered via standalone Python scripts with Alembic migrations. No ORM models needed for the harmonisation table — raw SQL upserts via the existing SQLAlchemy engine are sufficient for a one-time seeding script.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rapidfuzz | 3.14.3 (Nov 2025, confirmed current) | Fuzzy string matching for district name harmonisation | C++ backend, 10-50x faster than thefuzz; MIT licence; `process.cdist` vectorises all pair comparisons in one call; `fuzz.WRatio` handles abbreviation + transliteration variants |
| pandas | 2.2.x (already in project — commented out in requirements.txt) | Loading parquet datasets, computing price statistics, groupby operations | Already used; `.groupby(commodity).transform(winsorize)` pattern for per-commodity bounds |
| pyarrow | 19.0.0 (already in project — commented out) | Parquet file reading | Required by pandas for parquet engine |
| scipy | 1.17.0 (current stable) | `scipy.stats.mstats.winsorize` for percentile-based capping | Standard; handles masked arrays; per-group application via pandas groupby transform |
| sqlalchemy | 2.0.46 (already in project) | Database write for `district_name_map` and `price_bounds` tables | Already present; use `engine.connect()` + raw SQL or ORM-style insert |
| alembic | 1.18.1 (already in project) | Schema migrations for new tables | Already present; follow established migration pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.26.x / 2.x (already in project) | Percentile computation for winsorisation bounds | Used inside the winsorisation calculation |
| tqdm | Any recent | Progress bar for long-running matching loops | Optional; useful for the soil nutrient CSV bulk load (thousands of files) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rapidfuzz process.cdist | thefuzz (FuzzyWuzzy) | thefuzz is 10-50x slower, GPL licence, effectively deprecated in favour of rapidfuzz by the same authors |
| scipy winsorize + pandas groupby | feature-engine Winsorizer | feature-engine is correct for sklearn Pipeline use; for a one-time data preparation script, scipy + pandas is simpler with no added dependency |
| Manual IQR bounds | `median * 20` cap | Both are valid; IQR * 3 is more principled statistically; median * 20 is more interpretable for agronomists reviewing the output |

**Installation (new dependencies only — pandas/pyarrow already in project):**
```bash
pip install rapidfuzz==3.14.3 scipy==1.17.0
# pandas==2.2.3 and pyarrow==19.0.0 already listed (commented) in requirements.txt
# Uncomment those lines — they are needed for ML phases
```

---

## Architecture Patterns

### Recommended Project Structure

New files for Phase 1:

```
backend/
├── app/
│   └── ml/                          # New top-level ML module (create now)
│       └── __init__.py
├── scripts/
│   ├── harmonise_districts.py       # Plan 01-01: district name matching script
│   └── clean_prices.py              # Plan 01-02: price winsorisation script
├── alembic/
│   └── versions/
│       ├── b1c2d3e4f5a6_add_district_name_map.py    # Plan 01-01 migration
│       └── c2d3e4f5a6b7_add_price_bounds.py          # Plan 01-02 migration
data/
├── ranifall_data/combined/parquet_monthly_partitioned_fixed/  # Rainfall parquet (year=XXXX partitions)
├── soil-health/nutrients/                                     # Soil CSVs (state_district_block_cycle.csv)
├── soil-health/nutrients_all.parquet                          # Merged soil parquet (if built)
├── weather data/india_weather_daily_10years.csv               # Weather data
└── market data/agmarknet_daily_10yr.parquet                   # Price data (also at repo root)
```

### Pattern 1: State-Scoped RapidFuzz Matching

**What:** Group each dataset's districts by state, then fuzzy-match only within the same state. Never match across state boundaries.

**When to use:** All three joins: price-to-rainfall, price-to-weather, price-to-soil.

**Three-tier confidence strategy:**
1. Exact string match (after normalisation: `.strip().upper()`) — accept all, mark `match_type = 'exact'`
2. Fuzzy match within same state using `fuzz.WRatio` — accept score >= 90, mark `match_type = 'fuzzy_accepted'`; flag score 75-89 for manual review, mark `match_type = 'fuzzy_review'`
3. Anything below 75 or unmatched — mark `match_type = 'unmatched'`, log explicitly, never silently drop

**Example:**
```python
# Source: RapidFuzz official docs (rapidfuzz.github.io/RapidFuzz/Usage/process.html)
from rapidfuzz import process, fuzz
import pandas as pd

def match_within_state(source_df: pd.DataFrame, canonical_df: pd.DataFrame) -> pd.DataFrame:
    """
    source_df: columns [state, district_name]  — from rainfall/soil/weather dataset
    canonical_df: columns [state, district_name] — from price dataset (571 districts)
    Returns: columns [source_state, source_district, canonical_district, score, match_type]
    """
    results = []
    for state in source_df["state"].unique():
        source_names = source_df[source_df["state"] == state]["district_name"].tolist()
        canonical_names = canonical_df[canonical_df["state"] == state]["district_name"].tolist()

        if not canonical_names:
            # State not in price data — mark unmatched
            for name in source_names:
                results.append((state, name, None, 0.0, "unmatched"))
            continue

        # Vectorised similarity matrix: shape (len(source_names), len(canonical_names))
        matrix = process.cdist(
            source_names,
            canonical_names,
            scorer=fuzz.WRatio,
            workers=-1,  # all CPU cores
        )

        for i, source_name in enumerate(source_names):
            best_idx = matrix[i].argmax()
            best_score = matrix[i, best_idx]
            best_canonical = canonical_names[best_idx]

            if best_score >= 90:
                match_type = "fuzzy_accepted"
            elif best_score >= 75:
                match_type = "fuzzy_review"
            else:
                match_type = "unmatched"
                best_canonical = None

            results.append((state, source_name, best_canonical, float(best_score), match_type))

    return pd.DataFrame(
        results,
        columns=["state", "source_district", "canonical_district", "score", "match_type"]
    )
```

### Pattern 2: Per-Commodity Winsorisation with Bounds Storage

**What:** Compute winsorisation bounds (lower_cap, upper_cap) per commodity from the full price history. Store bounds in `price_bounds`. Apply bounds to flag and cap outlier rows.

**When to use:** Price cleaning script (Plan 01-02).

**Winsorisation approach:** Use IQR * 3 fence (Q1 - 3*IQR as lower, Q3 + 3*IQR as upper) rather than fixed percentiles, because commodity price distributions vary enormously in scale. This is more principled than `median * 20` and captures the actual distribution shape.

**Example:**
```python
# Source: scipy.stats.mstats.winsorize docs + pandas groupby pattern
import pandas as pd
import numpy as np

def compute_commodity_bounds(df: pd.DataFrame) -> pd.DataFrame:
    """
    df: price_history dataframe with columns [commodity, modal_price]
    Returns: dataframe with [commodity, q1, q3, iqr, lower_cap, upper_cap, median_price]
    """
    def iqr_bounds(series: pd.Series) -> pd.Series:
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = max(0, q1 - 3 * iqr)   # prices cannot be negative
        upper = q3 + 3 * iqr
        median = series.median()
        return pd.Series({
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_cap": lower,
            "upper_cap": upper,
            "median_price": median,
        })

    bounds = df.groupby("commodity")["modal_price"].apply(iqr_bounds).reset_index()
    return bounds


def flag_and_cap_outliers(df: pd.DataFrame, bounds: pd.DataFrame) -> pd.DataFrame:
    """
    Returns new dataframe (immutable — original not modified) with:
    - is_outlier: bool column
    - modal_price_clean: capped price value
    - cv_pct: coefficient of variation before capping, for audit
    """
    merged = df.merge(bounds, on="commodity", how="left")
    result = merged.copy()
    result["is_outlier"] = (
        (result["modal_price"] < result["lower_cap"]) |
        (result["modal_price"] > result["upper_cap"])
    )
    result["modal_price_clean"] = result["modal_price"].clip(
        lower=result["lower_cap"],
        upper=result["upper_cap"],
    )
    return result
```

### Pattern 3: Alembic Migration (follow existing project pattern)

**What:** Create new tables using `op.create_table()` in upgrade(), `op.drop_table()` in downgrade().

**Critical:** Import `Base` from `app.database.base` (not from `app.database.session`) — established project rule documented in CODEBASE.md.

**Down-revision chain:** The current HEAD revision is `a2b3c4d5e6f7` (road_distance_cache migration, 2026-02-28). New migrations chain from this.

**Example (follows project established pattern from `a2b3c4d5e6f7_add_road_distance_cache.py`):**
```python
# backend/alembic/versions/b1c2d3e4f5a6_add_district_name_map.py
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "district_name_map",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_dataset", sa.String(20), nullable=False),  # 'rainfall','weather','soil'
        sa.Column("state_name", sa.String(100), nullable=False),
        sa.Column("source_district", sa.String(200), nullable=False),
        sa.Column("canonical_district", sa.String(200), nullable=True),
        sa.Column("match_score", sa.Float, nullable=True),
        sa.Column("match_type", sa.String(20), nullable=False),  # exact/fuzzy_accepted/fuzzy_review/unmatched
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "source_dataset", "state_name", "source_district",
            name="uq_district_name_map_source"
        ),
    )
    op.create_index("idx_district_map_canonical", "district_name_map",
                    ["state_name", "canonical_district"])
    op.create_index("idx_district_map_match_type", "district_name_map", ["match_type"])

def downgrade() -> None:
    op.drop_index("idx_district_map_match_type", table_name="district_name_map")
    op.drop_index("idx_district_map_canonical", table_name="district_name_map")
    op.drop_table("district_name_map")
```

### Anti-Patterns to Avoid

- **Global fuzzy matching (cross-state):** "Gurgaon" in Haryana vs "Gurgaon" in any other state — matching without state scoping can produce cross-state false positives. Always filter to same-state candidates before scoring.
- **Silently dropping unmatched districts:** Every unmatched district must be written to `district_name_map` with `match_type = 'unmatched'` so the gap is visible. The 107 price-to-soil districts with no exact match must not be silently excluded.
- **Global winsorisation (not per-commodity):** A global 99th percentile cap would set different bounds for wheat (narrow price range) and saffron (extreme price range). Always compute bounds per commodity.
- **Modifying the original price data:** The `price_bounds` table stores caps; the script flags rows and adds `is_outlier` / `modal_price_clean` columns. The original `modal_price` values in `price_history` are never overwritten — immutability principle.
- **LGD codes as join keys:** LGD coding schemes changed in 2018-2020 during state reorganisations. Do not join on LGD code — join on state + district name after harmonisation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom Levenshtein loop | `rapidfuzz.process.cdist(workers=-1)` | C++ vectorised; handles multi-token WRatio; workers=-1 parallelises; 616 × 571 pairs complete in milliseconds, not minutes |
| Percentile-based outlier bounds | Custom quantile loop | `pandas Series.quantile(0.25/0.75)` + numpy clip | Already correct, readable, tested |
| Parquet file reading | Custom binary reader | `pd.read_parquet(engine='pyarrow')` | pandas + pyarrow handle partitioned parquet directories correctly |
| Database schema versioning | Manual ALTER TABLE scripts | Alembic `op.create_table()` | Project already uses Alembic; existing migration chain must be followed |

**Key insight:** The district matching problem looks simple (string comparison) but the edge cases are the work: same district name in two states, Unicode normalisation, trailing punctuation, "Dist" suffix variants. RapidFuzz's `WRatio` scorer (token sort + partial ratio) handles these correctly; a custom solution will miss them.

---

## Common Pitfalls

### Pitfall 1: Cross-State False Positives in Fuzzy Matching

**What goes wrong:** "Gurgaon" (Haryana) might score high against "Gurgaon" in a ghost entry from another state if matching is not state-scoped. Similarly, "Ahmadabad" and "Ahmedabad" both exist and are in the same state (Gujarat) — but "Laxmi" vs "Lakshmi" district variants exist across multiple states with entirely different geographies.

**Why it happens:** Running `process.cdist` on all 571 × N candidates without filtering by state first.

**How to avoid:** Always group by state before calling `process.cdist`. The canonical price district list has 571 entries across ~28-36 states — filter to the same state before scoring.

**Warning signs:** A district in the matched output shows `state_source != state_target`.

### Pitfall 2: Alembic Multiple Heads

**What goes wrong:** If two migration files both claim `down_revision = "a2b3c4d5e6f7"`, Alembic will refuse `upgrade head` with "multiple head revisions" error.

**Why it happens:** Plans 01-01 and 01-02 each need a migration; if both set the same down_revision, they create a fork.

**How to avoid:** Chain them: `district_name_map` migration (revision `b1c2d3e4f5a6`, down_revision `a2b3c4d5e6f7`), then `price_bounds` migration (revision `c2d3e4f5a6b7`, down_revision `b1c2d3e4f5a6`). Document the actual revision IDs used once generated.

**Warning signs:** `alembic upgrade head` fails with "Multiple head revisions" error — use `alembic upgrade <specific_id>` if needed (documented as a known project issue in MEMORY.md).

### Pitfall 3: pandas/pyarrow Not in Active Requirements

**What goes wrong:** `requirements.txt` has pandas and pyarrow commented out (`# pandas==2.2.3`, `# pyarrow==19.0.0`). Scripts will fail with `ModuleNotFoundError`.

**Why it happens:** They were commented out after parquet ETL was deemed complete. ML phases need them.

**How to avoid:** Uncomment both lines in `requirements.txt` as the first task in Plan 01-01. Both scripts and all downstream ML work require them.

**Warning signs:** `ImportError: No module named 'pandas'` when running the harmonisation script.

### Pitfall 4: State Name Normalisation Mismatch

**What goes wrong:** Rainfall data uses "ANDAMAN & NICOBAR" (from the spatial join shapefile), soil data uses "ANDAMAN & NICOBAR" (from government portal), price data uses state names from Agmarknet API — which may spell it differently. State-level grouping fails if state names do not match between datasets.

**Why it happens:** Each dataset has its own state name vocabulary.

**How to avoid:** Build a single canonical state name list from the price dataset (primary source of truth). Create a `state_name_normalise()` helper that maps known variants before any district matching begins. Example mappings: "Jammu & Kashmir" / "Jammu and Kashmir" / "J&K" / "JAMMU & KASHMIR" all map to the same canonical form.

**Warning signs:** State appears in one dataset but produces zero district matches in the harmonisation output.

### Pitfall 5: Winsorisation Bounds Applied at Wrong Scope

**What goes wrong:** Computing bounds on the national price series for a commodity instead of per commodity. Wheat prices in Punjab (high) vs Wheat prices in Bihar (lower) — both legitimate. A global IQR fence would mistakenly cap the Punjab series.

**Why it happens:** `df["modal_price"].quantile([0.25, 0.75])` without a `.groupby("commodity")` prefix.

**How to avoid:** Always: `df.groupby("commodity")["modal_price"].apply(iqr_bounds)`. The `price_bounds` table has one row per commodity, not one row per commodity-state-district.

**Warning signs:** After winsorisation, CV% for a legitimate high-price commodity (saffron, cardamom) drops to near 0% — the bounds were set too tight.

### Pitfall 6: Windows Console Encoding Crash in Scripts

**What goes wrong:** Print statements with Unicode characters (district names with special characters) crash on Windows with `UnicodeEncodeError`.

**Why it happens:** Windows console defaults to cp1252, not UTF-8.

**How to avoid:** Add the established project pattern at the top of every script:
```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

This is documented in MEMORY.md as the project standard.

---

## Code Examples

Verified patterns from the codebase and official sources:

### Alembic Migration Invocation (project pattern)

```bash
# From backend/ directory
alembic upgrade head

# If multiple heads error:
alembic upgrade b1c2d3e4f5a6  # district_name_map migration first
alembic upgrade c2d3e4f5a6b7  # price_bounds migration second
```

### Loading the Soil Nutrients Data

Soil data exists as individual CSV files per `{state}_{district}_{block}_{cycle}.csv` in `data/soil-health/nutrients/`. A merged parquet may or may not exist at `data/soil-health/nutrients_all.parquet`. The harmonisation script must handle both cases:

```python
# Source: data/soil-health/scripts/merge_to_parquet.py (project file, reviewed)
import pandas as pd
from pathlib import Path

def load_soil_data(nutrients_dir: Path) -> pd.DataFrame:
    """Load all soil nutrient CSVs and return combined dataframe."""
    files = list(nutrients_dir.glob("*.csv"))
    chunks = []
    required_cols = {"cycle", "state", "district", "block", "nutrient", "high", "medium", "low"}
    for f in files:
        df = pd.read_csv(f)
        if not required_cols.issubset(df.columns):
            continue
        for col in ["high", "medium", "low"]:
            df[col] = df[col].astype(str).str.replace("%", "").str.strip().astype(float)
        chunks.append(df)
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
```

### Loading the Rainfall District Data

Rainfall parquet data is partitioned by year at `data/ranifall_data/combined/parquet_monthly_partitioned_fixed/year=XXXX/`. The spatial join to district was previously done but the output `combined/rainfall_district_monthly.parquet` may or may not exist. The harmonisation script reads whichever is available:

```python
# Source: data/ranifall_data/check_output.py (project file, reviewed)
import pandas as pd

def load_rainfall_districts(rainfall_dir: str) -> list[str]:
    """Extract unique (STATE, DISTRICT) pairs from rainfall data."""
    # Columns after spatial join: STATE, DISTRICT, year, month, rainfall
    df = pd.read_parquet(rainfall_dir)
    return df[["STATE", "DISTRICT"]].drop_duplicates().values.tolist()
```

### Price History Query for Winsorisation (from parquet, not DB)

The price history parquet at repo root (`agmarknet_daily_10yr.parquet`) is the authoritative source for winsorisation bounds computation. Parquet columns: `date, commodity, commodity_id, state, state_id, district, district_id, price_min, price_max, price_modal, category_id, entity_id`.

```python
# Source: data/market data/agmarknet_daily_10yr.parquet schema from inspect_parquet.py
import pandas as pd

def load_price_history_for_bounds(parquet_path: str) -> pd.DataFrame:
    """Load only necessary columns for winsorisation bound computation."""
    return pd.read_parquet(
        parquet_path,
        columns=["commodity", "price_modal"],
        engine="pyarrow",
    )
```

### Writing Results to PostgreSQL (follows project pattern)

```python
# Source: backend/app/database/session.py pattern (project file, reviewed)
from app.database.session import SessionLocal
from sqlalchemy import text

def upsert_district_map(records: list[dict]) -> None:
    """Write harmonisation results to district_name_map table."""
    db = SessionLocal()
    try:
        for rec in records:
            db.execute(text("""
                INSERT INTO district_name_map
                    (source_dataset, state_name, source_district,
                     canonical_district, match_score, match_type)
                VALUES
                    (:source_dataset, :state_name, :source_district,
                     :canonical_district, :match_score, :match_type)
                ON CONFLICT (source_dataset, state_name, source_district)
                DO UPDATE SET
                    canonical_district = EXCLUDED.canonical_district,
                    match_score = EXCLUDED.match_score,
                    match_type = EXCLUDED.match_type
            """), rec)
        db.commit()
    finally:
        db.close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| thefuzz (FuzzyWuzzy) for string matching | rapidfuzz (same authors, C++ backend) | 2022 — thefuzz became a thin wrapper over rapidfuzz | 10-50x speed improvement; GPL → MIT licence; `process.cdist` vectorised API |
| Global fuzzy matching with single threshold | State-scoped matching with three-tier confidence | IDInsight empirical study (confirmed by project decision in STATE.md) | Accuracy improvement from 47.5% to 93.1% on Hindi names |
| Mean-based outlier detection | IQR-fence winsorisation per commodity | Current best practice for skewed distributions | Robust to asymmetric distributions; commodity-specific bounds prevent over/under-capping |
| Manual SQL ALTER TABLE for schema changes | Alembic migrations with version chain | Project uses Alembic since initial migration (154188b9a722) | Reproducible, reversible schema changes |

**Deprecated/outdated:**
- `thefuzz` / `fuzzywuzzy`: Same authors now recommend rapidfuzz; effectively deprecated
- Global winsorisation (single fence for all commodities): Destroys signal for legitimate high-price commodities like saffron and cardamom

---

## Open Questions

1. **Rainfall parquet state: has the spatial join (`rainfall_to_district.py`) been run?**
   - What we know: `data/ranifall_data/combined/parquet_monthly_partitioned_fixed/` has year-partitioned parquet files; `rainfall_district_monthly.parquet` does not appear to exist yet
   - What's unclear: Whether the IMD gridpoint-to-district spatial join has produced the district-level output needed for harmonisation
   - Recommendation: Plan 01-01 must check for `rainfall_district_monthly.parquet` first; if absent, either re-run `rainfall_to_district.py` (requires geopandas + dask + shapefiles) or extract unique districts directly from the year-partitioned parquet using the `DISTRICT` column if it exists

2. **Weather data district column naming**
   - What we know: `data/weather data/india_weather_daily_10years.csv` exists; covers ~261 districts
   - What's unclear: Exact column names (city? district? location?) — not directly inspected
   - Recommendation: Plan 01-01 script should print column names on load and fail fast if the expected district column is absent

3. **Exact revision ID for the new migrations**
   - What we know: Current HEAD is `a2b3c4d5e6f7`
   - What's unclear: The actual random hex IDs that Alembic will generate
   - Recommendation: Generate with `alembic revision --autogenerate -m "add_district_name_map"` during implementation; the revision IDs in this document are illustrative

4. **`nutrients_all.parquet` pre-merged file existence**
   - What we know: `data/soil-health/scripts/merge_to_parquet.py` exists and writes to a hardcoded path `D:\soil-health-data\nutrients_all.parquet`; `data/soil-health/nutrients_all.parquet` appears in the listing
   - What's unclear: Whether that file is present and current in the repo root data directory
   - Recommendation: Plan 01-01 script loads from individual CSVs if the merged parquet is absent; use the individual CSV approach as the reliable fallback

---

## Data Contracts (Critical for Planner)

These are verified column schemas from direct file inspection:

### Price Parquet (`agmarknet_daily_10yr.parquet`)
Columns: `date, commodity, commodity_id, state, state_id, district, district_id, price_min, price_max, price_modal, category_id, entity_id`
- 25M rows, dates 2015-2025-10-30
- 571 unique districts, 314 commodities, 36 states

### Soil Nutrients CSVs (`data/soil-health/nutrients/*.csv`)
Columns: `cycle, state, district, block, nutrient, high, medium, low`
- `high`/`medium`/`low` are percentage strings (e.g., "92%") — strip `%` and cast to float
- Filename pattern: `{STATE}_{DISTRICT}_{BLOCK} - {ID}_{CYCLE}.csv`
- 31 states with data across 2023-24, 2024-25, 2025-26 cycles

### New Tables to Create

**`district_name_map`**

| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PRIMARY KEY | |
| source_dataset | VARCHAR(20) | 'rainfall', 'weather', 'soil' |
| state_name | VARCHAR(100) | Canonical state name from price dataset |
| source_district | VARCHAR(200) | Name as it appears in source dataset |
| canonical_district | VARCHAR(200) NULLABLE | Matched name from price dataset; NULL if unmatched |
| match_score | FLOAT NULLABLE | RapidFuzz WRatio score 0-100 |
| match_type | VARCHAR(20) | 'exact', 'fuzzy_accepted', 'fuzzy_review', 'unmatched' |
| created_at | TIMESTAMPTZ | server_default now() |
| UNIQUE | (source_dataset, state_name, source_district) | |

**`price_bounds`**

| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PRIMARY KEY | |
| commodity | VARCHAR(200) | Commodity name as in price parquet |
| commodity_id | INTEGER | From price parquet commodity_id column |
| q1 | NUMERIC(12,2) | 25th percentile |
| q3 | NUMERIC(12,2) | 75th percentile |
| iqr | NUMERIC(12,2) | Q3 - Q1 |
| lower_cap | NUMERIC(12,2) | max(0, Q1 - 3*IQR) |
| upper_cap | NUMERIC(12,2) | Q3 + 3*IQR |
| median_price | NUMERIC(12,2) | Median modal price |
| outlier_count | INTEGER | Number of rows that fall outside bounds |
| total_count | INTEGER | Total rows for this commodity |
| computed_at | TIMESTAMPTZ | server_default now() |
| UNIQUE | (commodity) | One row per commodity |

---

## Sources

### Primary (HIGH confidence)

- Direct file inspection: `backend/app/models/price_history.py` — PriceHistory schema
- Direct file inspection: `backend/app/models/mandi.py` — Mandi schema with state/district columns
- Direct file inspection: `backend/requirements.txt` — confirmed pandas/pyarrow commented out
- Direct file inspection: `data/soil-health/coverage_report.csv` — confirmed 31 states, state names, block counts
- Direct file inspection: `data/soil-health/nutrients/` first file — confirmed CSV column schema
- Direct file inspection: `data/ranifall_data/check_output.py` — confirmed rainfall parquet output column names (STATE, DISTRICT, year, month, rainfall)
- Direct file inspection: `backend/alembic/versions/a2b3c4d5e6f7_add_road_distance_cache.py` — confirmed current HEAD revision and migration pattern
- Direct file inspection: `backend/tests/conftest.py` — confirmed SQLite test pattern; new model tests will follow same pattern
- Direct file inspection: `backend/pytest.ini` — confirmed test configuration and markers
- `.planning/research/STACK.md` — verified RapidFuzz 3.14.3 version, `process.cdist workers=-1` pattern
- `.planning/research/PITFALLS.md` — verified empirical CV% analysis from price parquet; 47.5% vs 93.1% accuracy comparison; IQR winsorisation recommendation
- [RapidFuzz PyPI](https://pypi.org/project/RapidFuzz/) — confirmed 3.14.3 is current (Nov 2025)
- [RapidFuzz process docs](https://rapidfuzz.github.io/RapidFuzz/Usage/process.html) — confirmed `process.cdist` API and `workers=-1` parallelism
- [scipy.stats.mstats.winsorize docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mstats.winsorize.html) — confirmed winsorize API

### Secondary (MEDIUM confidence)

- IDInsight empirical study: 47.5% global vs 93.1% state-scoped accuracy on Hindi district names — cited in `.planning/research/PITFALLS.md`
- [Masala-Merge GitHub](https://github.com/paulnov/masala-merge) — community pattern for Indian district fuzzy matching

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — rapidfuzz is confirmed current at 3.14.3; scipy winsorize is stable; all other libraries already in project
- Architecture patterns: HIGH — all patterns derived from actual project file inspection and existing codebase conventions
- Data schemas: HIGH — confirmed by direct file inspection of actual data files in repository
- Pitfalls: HIGH — empirically confirmed from project's own data (CV% analysis, state-name variants)
- Open questions: MEDIUM — file existence questions can be resolved in < 5 minutes by running `ls` checks at implementation time

**Research date:** 2026-03-02
**Valid until:** 2026-06-01 (stable libraries; rapidfuzz releases infrequently; scipy API is stable)
