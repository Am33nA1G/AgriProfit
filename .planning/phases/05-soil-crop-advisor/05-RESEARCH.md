# Phase 5: Soil Crop Advisor - Research

**Researched:** 2026-03-02
**Domain:** Rule-based ICAR crop-soil suitability lookup, Soil Health Card data ingestion, FastAPI endpoint, Next.js drill-down UI
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SOIL-01 | User selects state + district + block; sees N/P/K/OC/pH % distributions (high/medium/low) for most recent cycle | `data/soil-health/nutrients/` CSVs follow `cycle,state,district,block,nutrient,high,medium,low` schema; 9,643 CSV files; `soil_profiles` table stores pre-parsed distributions |
| SOIL-02 | Block deficiency profile maps to ranked list of 3-5 suitable crops using ICAR NPK/pH thresholds; seasonal demand from Phase 4 shown alongside | Rule-based lookup in `soil_advisor/suitability.py` using `ICAR_THRESHOLDS` dict; `soil_crop_suitability` static table seeded by `seed_soil_suitability.py`; seasonal demand from `seasonal_price_stats` table |
| SOIL-03 | Every recommendation screen displays non-dismissable disclaimer "Block-average soil data for [block name] — not field-level measurement" | Frontend component always renders disclaimer card above crop list; backend echoes block_name in every response |
| SOIL-04 | Fertiliser advice per nutrient deficiency — when low% exceeds threshold, UI shows advice card | Advice generation in `soil_advisor/fertiliser.py`; triggered when `low_pct > DEFICIENCY_THRESHOLD` (default 50%); each nutrient has hardcoded fertiliser text |
| SOIL-05 | Soil advisor labelled "Available for 21 states"; uncovered states clearly marked unavailable | Coverage driven by `COVERED_STATES` set derived from coverage_report.csv; endpoint returns 404 with coverage_gap message for uncovered states |
| UI-03 | Soil advisor page: state → district → block drill-down, NPK/pH distribution bars, crop recommendation list, fertiliser advice cards | Next.js page at `/soil-advisor`; chained Select components; BarChart or Progress bars for distributions; pattern from transport page |
| UI-05 | All dashboards display coverage gap messages when feature unavailable for selected region | 404 response from endpoint triggers UI coverage gap banner (same pattern as Phase 2 seasonal calendar) |
</phase_requirements>

---

## Summary

Phase 5 delivers the Soil Crop Advisor feature. Unlike the XGBoost forecasting in Phase 4, this feature is deliberately rule-based: it reads pre-loaded block-level soil health distributions (already available in `data/soil-health/nutrients/`) and maps them to crop suitability using hardcoded ICAR NPK/pH threshold rules. The design decision recorded in STATE.md is explicit: "Soil advisor is rule-based ICAR lookup, not a live ML model — precomputed suitability scores, never field-level claims."

The phase has two plans. Plan 05-01 covers the seeding script (`seed_soil_suitability.py`) and the `soil_crop_suitability` static lookup table with its Alembic migration — both pure Python with no FastAPI required. Plan 05-02 covers the FastAPI endpoint at `/api/v1/soil-advisor/{state}/{district}/{block}` and the Next.js UI page at `/soil-advisor`. The endpoint does not call ML models; it queries pre-seeded DB tables and applies Python threshold rules inline per request.

The soil data schema is confirmed by direct file inspection: 9,643 CSV files named `{STATE}_{DISTRICT}_{BLOCK} - {ID}_{CYCLE}.csv`, each with exactly 5 nutrient rows (Nitrogen, Phosphorus, Potassium, Organic Carbon, Potential Of Hydrogen) in `cycle,state,district,block,nutrient,high,medium,low` format where high/medium/low are percentage strings (e.g., "97%"). The coverage_report.csv confirms 21 states across 3 cycles (2023-24, 2024-25, 2025-26). The most recent cycle varies by state — the endpoint must select the latest available cycle per block. The coverage label in SOIL-05 is "21 states" (REQUIREMENTS.md and ROADMAP.md both corrected from "31 states" in Phase 1 Plan 01-03).

**Primary recommendation:** Seed `soil_profiles` table from the CSV files in `data/soil-health/nutrients/`. Build a static `soil_crop_suitability` lookup table seeded from hardcoded ICAR thresholds in `seed_soil_suitability.py`. FastAPI endpoint queries both tables inline — no ML involved. Next.js UI follows the transport page pattern: chained Select dropdowns (state → district → block) with `useQuery` hooks, Progress bars for distributions, and a hardcoded disclaimer card that cannot be hidden.

**Critical data note:** The REQUIREMENTS.md text for SOIL-05 says "Available for 31 states" but STATE.md and the corrected ROADMAP.md say 21 states. The UI label MUST say "Available for 21 states" to match the actual data coverage confirmed in Phase 1 Plan 01-03.

---

## Standard Stack

### Core (all already installed — zero new Python dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.2.3 (active) | Parse 9,643 CSVs in seeding script, compute percentage integers | Already used in Phase 1 clean_prices.py; `pd.read_csv()` for each file |
| SQLAlchemy | 2.0.46 (active) | Raw SQL upsert from seeding script; query from endpoint | Follow price_bounds seeding pattern exactly |
| alembic | 1.18.1 (active) | Two new tables: `soil_profiles`, `soil_crop_suitability` | Follow c2d3e4f5a6b7_add_price_bounds.py pattern |
| FastAPI | 0.128.0 (active) | `/api/v1/soil-advisor/{state}/{district}/{block}` endpoint | Existing router pattern from transport/routes.py |
| pydantic | 2.12.5 (active) | `SoilAdvisorResponse` schema | Follow transport/schemas.py pattern |
| Next.js | 15.5.9 (active) | `/soil-advisor` page with drill-down Select components | Follow transport/page.tsx pattern |
| @radix-ui/react-select | 2.0.0 (active) | State → District → Block chained dropdown | Already used in transport page |
| @tanstack/react-query | 5.90.20 (active) | Data fetching with loading/error states | Already used throughout |
| recharts | 3.7.0 (active) | NPK/pH distribution bars (BarChart or LinearProgress) | Already installed; transport page uses it |
| lucide-react | 0.563.0 (active) | Icons for advice cards, disclaimer, coverage indicators | Already used throughout |

### No New Dependencies Required

All stack elements are already installed in both backend and frontend. This phase introduces zero new packages.

### Supporting Libraries (already in requirements.txt)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.17.0 (active) | Not needed for this phase — rule-based lookup only | Skip |
| tqdm | (not installed) | Optional progress bar for CSV bulk load | Add if seeding script takes > 60s |

**Installation (seeding script only, optional):**
```bash
pip install tqdm  # optional only if desired for CSV load progress bar
```

---

## Data Architecture

### Soil Data File Format (confirmed by inspection)

```
File naming: {STATE}_{DISTRICT}_{BLOCK} - {BLOCK_ID}_{CYCLE}.csv
Example: ANDHRA PRADESH_ANANTAPUR_ANANTAPUR - 4689_2024-25.csv

Columns: cycle, state, district, block, nutrient, high, medium, low
Nutrient values: "Nitrogen", "Phosphorus", "Potassium", "Organic Carbon", "Potential Of Hydrogen"
Percentage values: "97%" (string with % sign — must strip % and convert to int)
```

Sample rows from `ANDHRA PRADESH_ANANTAPUR_ANANTAPUR - 4689_2024-25.csv`:
```
2024-25,ANDHRA PRADESH,ANANTAPUR,ANANTAPUR - 4689,Nitrogen,0%,4%,96%
2024-25,ANDHRA PRADESH,ANANTAPUR,ANANTAPUR - 4689,Phosphorus,81%,17%,2%
2024-25,ANDHRA PRADESH,ANANTAPUR,ANANTAPUR - 4689,Potassium,83%,14%,3%
2024-25,ANDHRA PRADESH,ANANTAPUR,ANANTAPUR - 4689,Organic Carbon,0%,4%,96%
2024-25,ANDHRA PRADESH,ANANTAPUR,ANANTAPUR - 4689,Potential Of Hydrogen,0%,0%,100%
```

### Coverage Facts (from coverage_report.csv)

- **21 unique states** have soil data (confirmed after Phase 1 Plan 01-03 correction)
- **3 cycles present**: 2023-24, 2024-25, 2025-26 (most states have 2024-25 and 2025-26)
- **States covered**: Andhra Pradesh, Arunachal Pradesh, Assam, Bihar, Chhattisgarh, Goa, Gujarat, Haryana, Himachal Pradesh, Jammu & Kashmir, Jharkhand, Karnataka, Kerala, Ladakh, Madhya Pradesh, Maharashtra, Manipur, Meghalaya, Mizoram, Nagaland, Andaman & Nicobar
- **States NOT covered**: Odisha, Punjab, Rajasthan, Tamil Nadu, Telangana, Uttar Pradesh, Uttarakhand, West Bengal, Delhi, and others

---

## ICAR Soil Nutrient Thresholds (domain research findings)

These thresholds classify soils as Low/Medium/High. They are from TNAU (Tamil Nadu Agricultural University, an ICAR constituent) published soil rating chart, verified as the standard reference used by the India Soil Health Card scheme. The data source is the Soil Health Card scheme which uses ICAR/STCR guidelines.

**Confidence: MEDIUM** (verified by TNAU official reference and multiple ICAR publications, but exact values may vary slightly by state SAU; these are the national standard reference values)

### Nutrient Classification Thresholds

| Nutrient | Low | Medium | High | Unit |
|----------|-----|--------|------|------|
| Available Nitrogen (N) | < 240 | 240–480 | > 480 | kg/ha |
| Available Phosphorus (P) | < 11 | 11–22 | > 22 | kg/ha |
| Available Potassium (K) | < 110 | 110–280 | > 280 | kg/ha |
| Organic Carbon (OC) | < 0.5 | 0.5–0.75 | > 0.75 | % |
| pH | Acid: < 6.0 | Neutral: 6.0–8.5 | Alkaline: > 8.5 | — |

**Important note on the data:** The soil CSVs already contain the government's own Low/Medium/High classifications as percentage distributions. This means the raw data has already been classified using official thresholds. The phase does NOT need to re-apply the thresholds to raw NPK values — it uses the existing `high%`, `medium%`, `low%` distribution to determine deficiency.

**Deficiency rule:** A block is considered deficient in a nutrient when `low_pct > 50%`. A block with 96% of soils in the Low category is severely deficient.

### ICAR Crop-Soil Suitability Rules

The seed script hard-codes these threshold rules for 15-20 major Indian crops tracked in the price dataset. The following rules are based on established Indian agricultural science:

| Crop | N Requirement | P Requirement | K Requirement | Preferred pH |
|------|--------------|--------------|--------------|-------------|
| Rice (Paddy) | Medium-High | Low-Medium | Medium | 5.5–7.0 |
| Wheat | High | Medium | Medium | 6.0–7.5 |
| Maize | High | Medium-High | Medium | 5.5–7.0 |
| Soybean | Low (N-fix) | Medium-High | Medium | 6.0–7.0 |
| Groundnut | Low-Medium | Medium | Medium-High | 5.5–7.0 |
| Cotton | High | Medium | High | 6.0–7.5 |
| Sugarcane | High | Medium-High | High | 6.0–7.5 |
| Potato | Medium-High | Medium-High | High | 5.0–6.5 |
| Tomato | Medium | Medium | High | 5.5–7.0 |
| Onion | Medium | High | High | 6.0–7.5 |
| Chickpea | Low (N-fix) | Medium-High | Medium | 6.0–7.5 |
| Mustard/Rapeseed | Medium-High | Medium | Medium | 5.5–7.0 |
| Bajra (Pearl Millet) | Medium | Low-Medium | Low-Medium | 6.0–7.5 |
| Jowar (Sorghum) | Medium | Low-Medium | Low-Medium | 6.0–8.0 |
| Lentil | Low (N-fix) | Medium | Medium | 6.0–7.5 |

**Implementation approach for `soil_crop_suitability` table:**
Rather than complex range-matching logic at query time, the seeding script pre-computes a score for each (crop, deficiency_profile) combination. The approach is:

1. Define a crop's "tolerance" as which deficiency levels it can handle: `N_tolerance = ["low", "medium"]` means the crop is OK even with low N.
2. Rank crops by how well their tolerance matches the block's actual distribution.
3. Score = sum of (high_pct × N_weight + medium_pct × N_weight × 0.5) — higher means better N match.

In practice, the simplest correct approach is: for each block profile, run the matching at query time (not pre-seeded per block — the block count is too large). Pre-seed only the crop requirement thresholds. Apply matching at the endpoint.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── app/
│   └── soil_advisor/           # NEW module (follow transport/ pattern)
│       ├── __init__.py
│       ├── routes.py           # FastAPI router /api/v1/soil-advisor/{state}/{district}/{block}
│       ├── schemas.py          # SoilAdvisorResponse, SoilProfileData, CropRecommendation, FertiliserAdvice
│       ├── service.py          # SoilAdvisorService — queries DB + applies matching
│       ├── suitability.py      # ICAR_THRESHOLDS dict + rank_crops() pure function
│       └── fertiliser.py       # FERTILISER_ADVICE dict + generate_advice() pure function
├── scripts/
│   └── seed_soil_suitability.py  # Bulk CSV → soil_profiles table seeder
└── alembic/versions/
    └── {rev}_add_soil_advisor_tables.py  # soil_profiles + soil_crop_suitability tables
tests/
├── test_soil_suitability.py    # Unit tests for suitability.py (pure functions)
├── test_soil_fertiliser.py     # Unit tests for fertiliser.py (pure functions)
└── test_soil_advisor_api.py    # Integration tests via FastAPI TestClient

frontend/
└── src/
    └── app/
        └── soil-advisor/
            ├── page.tsx             # Soil Advisor page
            └── __tests__/
                └── soil-advisor.test.tsx
    └── services/
        └── soil-advisor.ts          # API service layer
```

### Pattern 1: Seeding Script (seed_soil_suitability.py)

**What:** Reads all 9,643 CSVs from `data/soil-health/nutrients/`, parses percentage strings, upserts into `soil_profiles` table. Idempotent via ON CONFLICT. Also seeds `soil_crop_suitability` from hardcoded ICAR thresholds.

**Key implementation steps:**
1. `glob.glob("data/soil-health/nutrients/*.csv")` — get all files
2. Parse each filename to extract state, district, block, cycle
3. Read CSV, strip `%` from high/medium/low values, convert to int
4. For each file: 5 nutrient rows → one `soil_profiles` upsert per (state, district, block, cycle, nutrient)
5. Use ON CONFLICT (state, district, block, cycle, nutrient) DO UPDATE to stay idempotent

**Example:**
```python
# Source: follows clean_prices.py + harmonise_districts.py patterns
import glob
import pandas as pd
from pathlib import Path
from sqlalchemy import text
from app.database.session import SessionLocal

def parse_pct(val: str) -> int:
    """'97%' -> 97, '0%' -> 0"""
    return int(str(val).strip().rstrip('%'))

def seed_soil_profiles(data_dir: str) -> int:
    pattern = str(Path(data_dir) / "*.csv")
    files = glob.glob(pattern)
    rows_upserted = 0
    with SessionLocal() as session:
        for fpath in files:
            df = pd.read_csv(fpath)
            for _, row in df.iterrows():
                session.execute(text("""
                    INSERT INTO soil_profiles
                        (state, district, block, cycle, nutrient, high_pct, medium_pct, low_pct)
                    VALUES
                        (:state, :district, :block, :cycle, :nutrient, :high, :medium, :low)
                    ON CONFLICT (state, district, block, cycle, nutrient)
                    DO UPDATE SET high_pct=EXCLUDED.high_pct, medium_pct=EXCLUDED.medium_pct,
                                  low_pct=EXCLUDED.low_pct
                """), {
                    "state": row["state"], "district": row["district"],
                    "block": row["block"], "cycle": row["cycle"],
                    "nutrient": row["nutrient"],
                    "high": parse_pct(row["high"]),
                    "medium": parse_pct(row["medium"]),
                    "low": parse_pct(row["low"]),
                })
                rows_upserted += 1
        session.commit()
    return rows_upserted
```

**Performance note:** 9,643 files × 5 rows = ~48,215 upserts. Use batch inserts (build list, executemany) rather than one execute per row to avoid 48K roundtrips. Target < 60 seconds total.

### Pattern 2: soil_profiles Table Schema (Alembic migration)

```sql
CREATE TABLE soil_profiles (
    id          SERIAL PRIMARY KEY,
    state       VARCHAR(100)    NOT NULL,
    district    VARCHAR(200)    NOT NULL,
    block       VARCHAR(300)    NOT NULL,
    cycle       VARCHAR(10)     NOT NULL,  -- e.g. '2024-25'
    nutrient    VARCHAR(50)     NOT NULL,  -- 'Nitrogen', 'Phosphorus', etc.
    high_pct    SMALLINT        NOT NULL,  -- 0-100
    medium_pct  SMALLINT        NOT NULL,
    low_pct     SMALLINT        NOT NULL,
    seeded_at   TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT uq_soil_profile UNIQUE (state, district, block, cycle, nutrient)
);
CREATE INDEX idx_soil_profile_location ON soil_profiles (state, district, block);
CREATE INDEX idx_soil_profile_state ON soil_profiles (state);
CREATE INDEX idx_soil_profile_cycle ON soil_profiles (cycle);
```

### Pattern 3: soil_crop_suitability Table Schema

This table is seeded once from ICAR thresholds. One row per crop + nutrient combination.

```sql
CREATE TABLE soil_crop_suitability (
    id              SERIAL PRIMARY KEY,
    crop_name       VARCHAR(200) NOT NULL,
    nutrient        VARCHAR(50)  NOT NULL,   -- 'Nitrogen', 'Phosphorus', etc.
    min_tolerance   VARCHAR(10)  NOT NULL,   -- 'low', 'medium', 'high' — minimum acceptable level
    ph_min          NUMERIC(4,1),            -- minimum acceptable pH
    ph_max          NUMERIC(4,1),            -- maximum acceptable pH
    fertiliser_advice TEXT        NOT NULL,  -- e.g., "Apply urea at 120 kg/ha before sowing"
    CONSTRAINT uq_crop_nutrient UNIQUE (crop_name, nutrient)
);
```

### Pattern 4: FastAPI Endpoint

**URL:** `GET /api/v1/soil-advisor/{state}/{district}/{block}`

**Logic:**
1. Check if state is in COVERED_STATES → 404 with coverage_gap message if not
2. Query `soil_profiles` for (state, district, block), most recent cycle
3. If no rows → 404 with "No soil data for this block"
4. Apply suitability matching: for each crop in `soil_crop_suitability`, check if block's deficiency profile meets crop's tolerance
5. Rank crops by score (descending), return top 3-5
6. Generate fertiliser advice for nutrients where `low_pct > 50`
7. Query `seasonal_price_stats` for each recommended crop + state to get demand signal (HIGH/MEDIUM/LOW)

```python
# Source: follows transport/routes.py pattern
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.session import get_db
from app.soil_advisor.schemas import SoilAdvisorResponse
from app.soil_advisor.service import get_soil_advice
from app.soil_advisor.suitability import COVERED_STATES

router = APIRouter(prefix="/soil-advisor", tags=["Soil Advisor"])

@router.get(
    "/{state}/{district}/{block}",
    response_model=SoilAdvisorResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Soil Crop Advisor",
)
def get_soil_advisor(
    state: str,
    district: str,
    block: str,
    db: Session = Depends(get_db),
) -> SoilAdvisorResponse:
    state_upper = state.upper()
    if state_upper not in COVERED_STATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "coverage_gap": True,
                "message": f"Soil data not available for {state}. "
                           f"Available for 21 states only.",
            },
        )
    return get_soil_advice(db, state, district, block)
```

### Pattern 5: Suitability Matching (pure function — testable without DB)

```python
# backend/app/soil_advisor/suitability.py
from typing import TypedDict

COVERED_STATES = {
    "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR",
    "CHHATTISGARH", "GOA", "GUJARAT", "HARYANA", "HIMACHAL PRADESH",
    "JAMMU & KASHMIR", "JHARKHAND", "KARNATAKA", "KERALA", "LADAKH",
    "MADHYA PRADESH", "MAHARASHTRA", "MANIPUR", "MEGHALAYA", "MIZORAM",
    "NAGALAND", "ANDAMAN & NICOBAR",
}

DEFICIENCY_THRESHOLD = 50  # % of soils in "low" category to flag deficiency

class BlockProfile(TypedDict):
    Nitrogen: dict         # {"high": 0, "medium": 4, "low": 96}
    Phosphorus: dict
    Potassium: dict
    Organic_Carbon: dict   # key normalised from "Organic Carbon"
    pH: dict               # key normalised from "Potential Of Hydrogen"

def is_deficient(profile: BlockProfile, nutrient: str) -> bool:
    """Returns True if > 50% of soils in block are in Low category."""
    return profile.get(nutrient, {}).get("low", 0) > DEFICIENCY_THRESHOLD

def score_crop(
    profile: BlockProfile,
    crop_tolerances: dict,  # {"N_min": "low", "P_min": "medium", "K_min": "medium", "pH_min": 5.5, "pH_max": 7.5}
) -> float:
    """
    Score how well a crop's tolerance matches the block's soil profile.
    Higher score = better match.
    Crops that tolerate low N score higher when block has high low_N%.
    """
    # ... implementation details in plan
    pass

def rank_crops(profile: BlockProfile, crop_suitability_rows: list) -> list:
    """Returns crops sorted by suitability score descending, top 5 only."""
    scored = [(row, score_crop(profile, row)) for row in crop_suitability_rows]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [row for row, score in scored[:5] if score > 0]
```

### Pattern 6: Next.js Drill-Down UI

```typescript
// Follow transport/page.tsx exactly for the chained Select pattern
// State → District → Block drill-down

// State selection: static list of 21 covered states + 15+ uncovered marked disabled
// District selection: populated from API once state is selected
// Block selection: populated from API once district is selected
// Results: shown when all 3 are selected

// Key difference from transport page:
// The disclaimer card must ALWAYS render when results are shown — no toggle, no dismiss

const SoilDisclaimer = ({ blockName }: { blockName: string }) => (
    <div className="border border-amber-200 bg-amber-50 rounded-md p-4 mb-4">
        <p className="text-sm text-amber-800 font-medium">
            Block-average soil data for {blockName} — not a field-level measurement
        </p>
    </div>
);
// This component renders BEFORE the crop list, cannot be dismissed
```

### Pattern 7: Distribution Visualization

Use Recharts `BarChart` (stacked) to show high/medium/low % for each nutrient:

```typescript
// Source: recharts 3.7.0 — already installed
import { BarChart, Bar, XAxis, YAxis, Legend, Tooltip } from 'recharts'

const distributionData = [
    { nutrient: 'N', high: 0, medium: 4, low: 96 },
    { nutrient: 'P', high: 83, medium: 17, low: 0 },
    { nutrient: 'K', high: 83, medium: 17, low: 0 },
    { nutrient: 'OC', high: 0, medium: 4, low: 96 },
    { nutrient: 'pH', high: 0, medium: 0, low: 100 },
]

<BarChart data={distributionData} layout="vertical">
    <Bar dataKey="high" fill="#22c55e" name="High" stackId="a" />
    <Bar dataKey="medium" fill="#f59e0b" name="Medium" stackId="a" />
    <Bar dataKey="low" fill="#ef4444" name="Low" stackId="a" />
</BarChart>
```

Alternative: simpler CSS progress bars with Tailwind (no Recharts needed) — three colored segments in a row. This is lighter and matches how soil cards are normally displayed. **Recommendation: use CSS progress bars** (three `<div>` elements with width matching %) rather than Recharts for the nutrient distribution — simpler to build, more mobile-friendly, and easier to test.

### Anti-Patterns to Avoid

- **Seeding per-block crop scores:** With thousands of blocks, pre-computing the full matrix is wasteful. Apply matching inline at query time — it's < 1ms for 20 crops × 5 nutrients.
- **Storing parsed % as floats:** Use `SMALLINT` (0-100) not `FLOAT`. The source data is integer percentages, not decimal.
- **Missing cycle selection logic:** The endpoint must pick the most recent cycle per block. Use `SELECT cycle ... ORDER BY cycle DESC LIMIT 1` — don't assume a fixed cycle.
- **State name case mismatch:** Source CSVs use ALLCAPS state names. The API receives mixed-case from the frontend. Always `.upper()` the state param before comparing to COVERED_STATES.
- **Blocking the event loop with sync DB calls in async endpoint:** Follow the project pattern — use `def` (synchronous) handlers with `Session = Depends(get_db)`. The project does NOT use `AsyncSession` (confirmed from existing routes).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy district-to-block resolution | Custom string matching in endpoint | Use exact match on `block` column (block names in CSV already normalized with numeric IDs) | Block IDs are stable; fuzzy matching adds latency and ambiguity |
| CSV bulk loading | Custom file parser | `pd.read_csv()` with dtype coercions | pandas handles encoding edge cases, malformed rows, BOM markers |
| API response pagination | Custom cursor/page logic | Return all blocks for a district in one call (max ~50 blocks) | Block count is small enough for one response |
| Seasonal demand signal from scratch | Reimplement seasonal calendar | Query `seasonal_price_stats` table (built in Phase 2) | Phase 2 already computes and stores this data |

**Key insight:** The suitability matching is intentionally simple — five nutrients × twenty crops = 100 comparisons per request, trivially fast in Python. Resist the urge to add ML or vector search. The value here is correctness of the ICAR rules, not algorithmic sophistication.

---

## Common Pitfalls

### Pitfall 1: "Potential Of Hydrogen" Nutrient Key

**What goes wrong:** Code treats `pH` as a standard numeric deficiency, applying the same `low_pct > 50` threshold. But pH deficiency (too acidic OR too alkaline) has different implications than NPK deficiency.
**Why it happens:** The CSV nutrient name is "Potential Of Hydrogen" — normalize it to "pH" consistently. The `low%` value for pH means "% of soils with pH below the neutral range" (acidic), which is meaningful but not the same as nutrient starvation.
**How to avoid:** In the suitability rules, treat pH as a range check (crop pH_min to pH_max) rather than deficiency-based. Flag blocks with pH `low_pct > 50` as "Acidic conditions" and adjust advice accordingly.
**Warning signs:** Crops that prefer neutral soils being recommended for severely acidic blocks.

### Pitfall 2: Multiple Cycles Per Block

**What goes wrong:** Query returns rows from multiple cycles (2023-24, 2024-25, 2025-26) and the endpoint returns stale or mixed data.
**Why it happens:** Each block may have data from 2-3 cycles; SQL `SELECT *` without ORDER + LIMIT returns all.
**How to avoid:** Always select the most recent cycle per block: `SELECT ... WHERE state=? AND district=? AND block=? ORDER BY cycle DESC LIMIT 5` (5 = 5 nutrients from the latest cycle). Or: `WHERE cycle = (SELECT MAX(cycle) FROM soil_profiles WHERE state=? AND district=? AND block=?)`.
**Warning signs:** Response returning 10-15 nutrient rows instead of exactly 5.

### Pitfall 3: State Name Mismatch — "JAMMU & KASHMIR" vs "JAMMU AND KASHMIR"

**What goes wrong:** The frontend sends "Jammu and Kashmir" but the CSV data uses "JAMMU & KASHMIR" (with ampersand). COVERED_STATES check fails and the state appears as "uncovered" even though data exists.
**Why it happens:** State name harmonisation was addressed in Phase 1 but only for the `district_name_map` table — the `soil_profiles` table uses the raw CSV names.
**How to avoid:** Apply the same `_STATE_NAME_OVERRIDES` normalisation from `harmonise_districts.py` when building the frontend state list and when looking up COVERED_STATES. Use the exact string as stored in `soil_profiles`.
**Warning signs:** J&K, Andaman & Nicobar, Dadra & Nagar Haveli returning coverage_gap errors unexpectedly.

### Pitfall 4: Block Names Include Numeric IDs

**What goes wrong:** API routes `/{block}` where block is "ANANTAPUR - 4689" (with a hyphen and ID number). URL encoding fails or partial block name is passed.
**Why it happens:** The raw CSV block names include the government block ID (e.g., "ANANTAPUR - 4689"). These are the primary identifiers in the data.
**How to avoid:** URL-encode the block parameter. Accept block as a query parameter (`?block=...`) rather than a path segment to avoid routing conflicts with hyphens. Or use block_id (integer) as the path parameter instead.
**Recommendation: Use `block` as a query parameter**, not a path segment. Final URL: `GET /api/v1/soil-advisor?state=...&district=...&block=...`
**Warning signs:** 404 errors for valid blocks that contain hyphens or special characters in the name.

### Pitfall 5: Coverage Label Mismatch

**What goes wrong:** UI shows "Available for 31 states" which was the old incorrect count. This misleads farmers in uncovered states who try to select data.
**Why it happens:** REQUIREMENTS.md SOIL-05 still says "31 states" in the first reference but was corrected to 21 in Phase 1. The actual data has 21 states.
**How to avoid:** Hard-code "Available for 21 states" in the UI. Do NOT read the number from the requirements text. The authoritative source is coverage_report.csv which shows 21 distinct states.
**Warning signs:** If testing shows more than 21 states returning data from the API.

### Pitfall 6: Seeding Script % String → Integer Conversion

**What goes wrong:** `int("97%")` raises `ValueError`. `float("97%")` also fails. Script crashes midway through 9,643 files.
**Why it happens:** The CSV values literally contain the `%` symbol (e.g., "97%", "0%").
**How to avoid:** `parse_pct = lambda v: int(str(v).strip().rstrip('%'))`. Test this on a sample before the bulk loop. Add a `try/except` with logging to skip malformed rows without crashing.
**Warning signs:** `ValueError: invalid literal for int()` in seeding script output.

---

## Code Examples

### Example 1: Query latest cycle profile for a block

```python
# Source: follows service.py patterns from transport module
def get_block_profile(db: Session, state: str, district: str, block: str) -> dict | None:
    """
    Returns dict like:
    {
        "cycle": "2025-26",
        "block_name": "ANANTAPUR - 4689",
        "Nitrogen": {"high": 0, "medium": 4, "low": 96},
        "Phosphorus": {"high": 81, "medium": 17, "low": 2},
        ...
    }
    """
    rows = db.execute(text("""
        SELECT nutrient, high_pct, medium_pct, low_pct, cycle
        FROM soil_profiles
        WHERE state = :state
          AND district = :district
          AND block = :block
          AND cycle = (
              SELECT MAX(cycle)
              FROM soil_profiles sp2
              WHERE sp2.state = :state
                AND sp2.district = :district
                AND sp2.block = :block
          )
        ORDER BY nutrient
    """), {"state": state.upper(), "district": district.upper(), "block": block}).fetchall()

    if not rows:
        return None

    profile = {"cycle": rows[0].cycle, "block_name": block}
    for row in rows:
        profile[row.nutrient] = {
            "high": row.high_pct,
            "medium": row.medium_pct,
            "low": row.low_pct,
        }
    return profile
```

### Example 2: Query all blocks for a district (for UI drill-down population)

```python
# Used by the frontend Select component to populate block options
def get_blocks_for_district(db: Session, state: str, district: str) -> list[str]:
    rows = db.execute(text("""
        SELECT DISTINCT block
        FROM soil_profiles
        WHERE state = :state AND district = :district
        ORDER BY block
    """), {"state": state.upper(), "district": district.upper()}).fetchall()
    return [row.block for row in rows]
```

### Example 3: Fertiliser advice generation (pure function)

```python
# backend/app/soil_advisor/fertiliser.py
FERTILISER_ADVICE = {
    "Nitrogen": {
        "message": "% of soils in this block are nitrogen-deficient — consider urea application before planting",
        "fertiliser": "Urea (46% N) at 120-150 kg/ha for cereals; 50-80 kg/ha for legumes",
    },
    "Phosphorus": {
        "message": "% of soils in this block are phosphorus-deficient — apply phosphatic fertiliser at sowing",
        "fertiliser": "DAP (18% N, 46% P₂O₅) at 100-125 kg/ha or SSP at 250-375 kg/ha",
    },
    "Potassium": {
        "message": "% of soils in this block are potassium-deficient — consider muriate of potash",
        "fertiliser": "MOP (60% K₂O) at 50-100 kg/ha based on crop requirement",
    },
    "Organic Carbon": {
        "message": "% of soils in this block have low organic carbon — incorporate organic matter",
        "fertiliser": "FYM (farmyard manure) at 10-15 t/ha or compost at 5-7 t/ha",
    },
}

def generate_fertiliser_advice(profile: dict, threshold: int = 50) -> list[dict]:
    """
    Returns advice cards for nutrients where low_pct exceeds threshold.
    """
    advice_cards = []
    for nutrient, template in FERTILISER_ADVICE.items():
        nutrient_data = profile.get(nutrient, {})
        low_pct = nutrient_data.get("low", 0)
        if low_pct > threshold:
            advice_cards.append({
                "nutrient": nutrient,
                "low_pct": low_pct,
                "message": f"{low_pct}% {template['message']}",
                "fertiliser_recommendation": template["fertiliser"],
            })
    return advice_cards
```

### Example 4: Pydantic Response Schema

```python
# backend/app/soil_advisor/schemas.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class NutrientDistribution(BaseModel):
    nutrient: str
    high_pct: int = Field(..., ge=0, le=100)
    medium_pct: int = Field(..., ge=0, le=100)
    low_pct: int = Field(..., ge=0, le=100)
    model_config = ConfigDict(from_attributes=True)

class CropRecommendation(BaseModel):
    crop_name: str
    suitability_score: float
    suitability_rank: int
    seasonal_demand: Optional[str] = None  # 'HIGH' | 'MEDIUM' | 'LOW' | None
    model_config = ConfigDict(from_attributes=True)

class FertiliserAdvice(BaseModel):
    nutrient: str
    low_pct: int
    message: str
    fertiliser_recommendation: str
    model_config = ConfigDict(from_attributes=True)

class SoilAdvisorResponse(BaseModel):
    state: str
    district: str
    block: str
    cycle: str
    disclaimer: str  # Always: "Block-average soil data for {block} — not field-level measurement"
    nutrient_distributions: list[NutrientDistribution]
    crop_recommendations: list[CropRecommendation]  # Top 3-5 crops
    fertiliser_advice: list[FertiliserAdvice]
    coverage_gap: bool = False
    model_config = ConfigDict(from_attributes=True)
```

### Example 5: Additional endpoints needed for UI drill-down

```python
# The UI needs three additional lightweight endpoints to populate the Select dropdowns
GET /api/v1/soil-advisor/states        → list of covered state names
GET /api/v1/soil-advisor/districts?state={state}   → list of districts for state
GET /api/v1/soil-advisor/blocks?state={state}&district={district}  → list of blocks
```

These are simple `SELECT DISTINCT` queries against `soil_profiles`. The main endpoint stays at:
`GET /api/v1/soil-advisor/profile?state={state}&district={district}&block={block}`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Field-level soil testing per farmer | Block-aggregate distribution (government SHC scheme) | 2015 (scheme launch) | Data covers 21+ states but has only block-level precision |
| ML-based suitability models | Rule-based ICAR threshold lookup | Design decision (STATE.md) | Faster, interpretable, no training data needed, explicitly bounded to official guidelines |
| Separate soil microservice | Integrated into existing FastAPI app | Project constraint | No new services; all routing via existing backend |

**Deprecated/outdated:**
- "31 states" coverage label: Phase 1 Plan 01-03 corrected this to 21 states — do not use 31 anywhere.
- Parquet-based queries: The project moved to DB-first queries (MEMORY.md: "Parquet service deprecated — all queries use DB now"). The seeding script reads from CSV/parquet but the endpoint queries DB only.

---

## Open Questions

1. **Block parameter in URL — path segment vs query param?**
   - What we know: Block names contain hyphens and spaces (e.g., "ANANTAPUR - 4689")
   - What's unclear: Whether FastAPI's path parameter handles URL-encoded "ANANTAPUR%20-%204689" reliably
   - Recommendation: Use query parameters (`?block=...`) for state, district, and block — avoids routing conflicts entirely. The plan should specify this explicitly.

2. **Seasonal demand signal availability (Phase 4 dependency)**
   - What we know: The roadmap says Phase 5 depends on Phase 4 being complete (seasonal demand signal available). The `seasonal_price_stats` table must exist.
   - What's unclear: Whether Phase 5 will actually run after Phase 4 completes (they can run in parallel after Phase 4 per ROADMAP.md)
   - Recommendation: Make the seasonal demand lookup optional (return `null` if `seasonal_price_stats` is empty or if Phase 4 hasn't run yet). The crop recommendation still works without demand signal.

3. **Which crops to include in the suitability lookup?**
   - What we know: The price dataset has 314 commodities. The ICAR thresholds are well-established for ~20 major crops.
   - What's unclear: Which of the 314 price commodities map cleanly to ICAR soil requirement data?
   - Recommendation: Seed suitability rules for the ~20 major food/cash crops that appear in both price data AND have well-documented ICAR soil requirements. Accept that not all 314 commodities will appear in recommendations. The plan should specify the crop list explicitly.

4. **District-level API endpoints for drill-down — stored in DB or hardcoded?**
   - What we know: The transport page has a hardcoded `STATE_DISTRICTS` dict in the frontend. The soil advisor needs state → district → block from the actual data.
   - What's unclear: Whether to serve district/block lists from the API or embed them in frontend.
   - Recommendation: Serve from API (query `soil_profiles` `DISTINCT district` and `DISTINCT block`). The block count (~hundreds per state) is too large to hardcode, and data is already in DB after seeding.

---

## Validation Architecture

Note: `workflow.nyquist_validation` key is absent from `.planning/config.json` (not set to false, just absent). The planning config shows standard workflow keys only. Based on the project's established pattern of comprehensive test coverage (86 transport tests), including tests for this phase.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (backend) + vitest (frontend) |
| Config file | `backend/pytest.ini` (testpaths = tests) |
| Quick run command | `pytest backend/tests/test_soil_suitability.py backend/tests/test_soil_fertiliser.py -x -q` |
| Full suite command | `pytest backend/tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SOIL-01 | Block profile returned with 5 nutrients, latest cycle | integration | `pytest backend/tests/test_soil_advisor_api.py::test_get_block_profile -x` | Wave 0 |
| SOIL-01 | State not covered returns 404 with coverage_gap | integration | `pytest backend/tests/test_soil_advisor_api.py::test_uncovered_state_returns_404 -x` | Wave 0 |
| SOIL-02 | rank_crops() returns top crops matching block's deficiency | unit | `pytest backend/tests/test_soil_suitability.py::test_rank_crops_nitrogen_deficient -x` | Wave 0 |
| SOIL-02 | Crops requiring low N ranked higher for N-deficient blocks | unit | `pytest backend/tests/test_soil_suitability.py::test_nitrogen_tolerant_crops_rank_higher -x` | Wave 0 |
| SOIL-03 | Response always contains disclaimer field with block name | integration | `pytest backend/tests/test_soil_advisor_api.py::test_disclaimer_always_present -x` | Wave 0 |
| SOIL-04 | generate_fertiliser_advice() returns advice for low_pct > 50 | unit | `pytest backend/tests/test_soil_fertiliser.py::test_advice_generated_above_threshold -x` | Wave 0 |
| SOIL-04 | No advice generated when low_pct <= 50 | unit | `pytest backend/tests/test_soil_fertiliser.py::test_no_advice_below_threshold -x` | Wave 0 |
| SOIL-05 | COVERED_STATES set contains exactly 21 states | unit | `pytest backend/tests/test_soil_suitability.py::test_covered_states_count -x` | Wave 0 |
| SOIL-05 | UI-facing uncovered state shows informative message (manual) | manual | N/A — visual inspection | N/A |
| UI-03 | API returns districts for a state | integration | `pytest backend/tests/test_soil_advisor_api.py::test_get_districts_for_state -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_soil_suitability.py backend/tests/test_soil_fertiliser.py -x -q`
- **Per wave merge:** `pytest backend/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps (new files needed before implementation)
- [ ] `backend/tests/test_soil_suitability.py` — covers SOIL-02, SOIL-05
- [ ] `backend/tests/test_soil_fertiliser.py` — covers SOIL-04
- [ ] `backend/tests/test_soil_advisor_api.py` — covers SOIL-01, SOIL-03, UI-03
- [ ] `backend/app/soil_advisor/__init__.py` — module scaffold
- [ ] Alembic migration for `soil_profiles` + `soil_crop_suitability` tables

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `data/soil-health/nutrients/ANDHRA PRADESH_ANANTAPUR_ANANTAPUR - 4689_2024-25.csv` — confirmed CSV schema (cycle/state/district/block/nutrient/high/medium/low), 5 nutrients per file
- Direct file inspection: `data/soil-health/coverage_report.csv` — confirmed 21 unique states, 3 cycles
- Project codebase: `backend/app/transport/` — all pattern references (routes.py, schemas.py, service.py)
- Project codebase: `backend/alembic/versions/c2d3e4f5a6b7_add_price_bounds.py` — Alembic migration pattern
- Project codebase: `backend/tests/conftest.py` — SQLite in-memory test pattern
- Project STATE.md: "Soil advisor is rule-based ICAR lookup, not a live ML model"
- Project REQUIREMENTS.md: SOIL-01 through SOIL-05, UI-03, UI-05 specifications

### Secondary (MEDIUM confidence)
- TNAU Soil Rating Chart (agritech.tnau.ac.in): N < 240 / 240-480 / > 480 kg/ha; P < 11 / 11-22 / > 22 kg/ha; K < 110 / 110-280 / > 280 kg/ha; OC < 0.5% / 0.5-0.75% / > 0.75%; pH < 6.0 acid, 6.0-8.5 neutral, > 8.5 alkaline. TNAU is an ICAR affiliated institution; these thresholds align with the Soil Health Card scheme classification.
- PMC article (PMC10844259): Confirmed crop-NPK-pH association research for India, 22 crops dataset including major food crops
- PIB Government of India (PRID=2104403): Confirmed Soil Health Card scheme covers 12 parameters including N, P, K, OC, pH

### Tertiary (LOW confidence)
- Crop-specific pH and NPK suitability ranges in the Architecture Patterns section are derived from general agricultural science consensus (ICAR publications, FAO guidelines, Kaggle crop recommendation dataset). These should be verified against specific ICAR state-level advisories before the plan is finalized. The plan should note these as starting values that may need adjustment.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all libraries confirmed installed and actively used
- Data schema: HIGH — directly confirmed from file inspection
- Coverage facts: HIGH — directly from coverage_report.csv
- Architecture patterns: HIGH — follows established project patterns
- ICAR thresholds (nutrient classification): MEDIUM — verified from TNAU/ICAR aligned source but exact values can vary by SAU
- Crop-specific suitability rules: LOW-MEDIUM — well-established agronomic principles but specific to research context, not verified from single authoritative ICAR publication
- Pitfalls: HIGH — derived from actual codebase patterns and confirmed data format

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable — rule-based system, no rapidly changing dependencies)
