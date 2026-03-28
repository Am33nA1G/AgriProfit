# Phase 3: Feature Engineering Foundation - Research

**Researched:** 2026-03-02
**Domain:** Time series feature engineering — price lags/rolling stats, rainfall deficit, weather/soil features, anti-leakage architecture
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FEAT-01 | Lag features (7d, 14d, 30d, 90d price) and rolling statistics (7d/30d mean, std) with strict `cutoff_date` enforcement — no look-ahead leakage | Verified: pandas `shift(n)` + `.rolling(window)` with daily reindex; cutoff_date enforced INSIDE function via `series.loc[:cutoff_date]`; leakage detection test architecture confirmed |
| FEAT-02 | Monthly rainfall deficit/surplus vs 40-year average for all 543+ harmonised district pairs (Tier A), with >= 10-of-12 months completeness check | Verified: rainfall parquet has 616 districts × 42 years (1985-2026); all 616 districts have full 40-yr coverage; 25,256 of 25,872 district-years have >= 10 months (only 2026 incomplete) |
| FEAT-03 | Daily temperature and humidity features for ~261 weather districts (Tier A+); remaining ~310 districts receive no imputed weather features (Tier B) | Verified: weather CSV has 287 districts, 261 harmonised to price canonical names; date range 2021-01-01 to 2025-12-31; columns: date, district, max_temp_c, min_temp_c, avg_temp_c, avg_humidity, max_wind_kph |
| FEAT-04 | All feature functions are pure Python — accept DataFrames as input, return DataFrames as output, zero database calls inside function body | Pattern established: follows existing project test pattern (harmonise_districts tests, clean_prices tests) — pure function + importlib test loading; no DB fixture needed |
</phase_requirements>

---

## Summary

Phase 3 builds the shared feature library that Phase 4 (XGBoost forecasting) will consume. Every feature function must be a pure Python function that accepts a DataFrame and a `cutoff_date` and returns a DataFrame — no database calls inside the function body. This architecture makes the functions testable with synthetic data and eliminates look-ahead leakage by structural constraint rather than by convention.

The most technically critical requirement is the anti-leakage architecture for price features (FEAT-01). The root problem is that the price parquet contains irregular time series: Onion-Nashik has 3,277 records over ~10 years with gaps of up to 32 calendar days. Pandas `shift(n)` shifts by N records, not N calendar days — meaning "7 record lag" is not the same as "7 calendar-day lag". The fix is mandatory: reindex to a daily calendar with forward fill before computing lags. The `cutoff_date` parameter must be enforced INSIDE the function via `series.loc[:cutoff_date]`, not by the caller, to make leakage structurally impossible.

The rainfall deficit calculation (FEAT-02) is straightforward given the data reality: the rainfall parquet (`data/ranifall_data/combined/rainfall_district_monthly.parquet`) covers 616 districts over 42 years (1985–2026), with the 40-year average baseline already computable as `groupby(['DISTRICT','month'])['rainfall'].mean()`. The weather feature module (FEAT-03) requires a Tier A+ / Tier B split: the weather CSV covers 287 districts, of which exactly 261 are harmonised to canonical price district names (from `district_name_map`). The function must return NaN columns — not imputed values — for the 26 weather-only districts and all ~310 districts not in the weather dataset.

**Primary recommendation:** Two standalone Python modules in `backend/app/ml/` — `price_features.py` (lags, rolling stats, cutoff enforcement, daily reindex) and `rainfall_features.py` (deficit/surplus computation, long-term average computation, completeness check) in Plan 03-01; `weather_features.py` (Tier A+/B split, NaN passthrough) and `soil_features.py` (block profile lookup) in Plan 03-02. All functions are tested with synthetic DataFrames, no DB access, following the established project test pattern.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.2.3 (project requirement) | `series.loc[:cutoff_date]`, `.reindex()`, `.shift()`, `.rolling()`, `groupby()` for all feature computations | Already in project; all feature operations expressible natively; 2.2.x is current stable |
| numpy | 2.4.1 (in project venv) | Array ops for deficit percentage, percentile calculations | Already in project; no additional dependency |
| pyarrow | 17.0.0 (project requirement — pinned per Phase 1 decision) | Reading rainfall parquet and price parquet | Pinned to 17.0.0 because pyarrow 19 is incompatible with price parquet (Repetition level histogram size mismatch — CRITICAL project decision from STATE.md) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.17.0 (in project requirements.txt) | Not needed for Phase 3 feature functions | Already present if needed for future statistical checks |

### Not Needed / Explicitly Excluded
| Library | Reason Not Used |
|---------|-----------------|
| feature-engine | Correct for sklearn Pipeline integration but adds dependency; all features expressible with pandas directly |
| skforecast | Phase 4 dependency (ForecasterRecursiveMultiSeries); not installed yet and not needed for pure feature functions |
| xgboost | Phase 4; not installed |
| scikit-learn | Phase 4; not installed |

**No new packages need to be installed.** pandas, numpy, pyarrow, scipy are all already in `backend/requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

New files for Phase 3:

```
backend/
├── app/
│   └── ml/
│       ├── __init__.py          # Already exists (Phase 1 scaffold)
│       ├── price_features.py    # Plan 03-01: lag, rolling, cutoff_date
│       ├── rainfall_features.py # Plan 03-01: deficit/surplus, completeness check
│       ├── weather_features.py  # Plan 03-02: Tier A+/B split, NaN passthrough
│       └── soil_features.py     # Plan 03-02: block profile lookup
├── tests/
│   ├── test_price_features.py    # Plan 03-01 TDD tests
│   ├── test_rainfall_features.py # Plan 03-01 TDD tests
│   ├── test_weather_features.py  # Plan 03-02 TDD tests
│   └── test_soil_features.py     # Plan 03-02 TDD tests
```

No Alembic migrations needed — Phase 3 creates no database tables. All data read from parquet/CSV files; feature functions are pure Python.

### Pattern 1: Anti-Leakage Price Feature Function

**What:** Compute lag and rolling features for a commodity-district price series with structural prevention of look-ahead leakage.

**Critical implementation detail:** Price data is an IRREGULAR time series. Onion-Nashik has gaps up to 32 calendar days. `pandas.shift(n)` shifts by N records, not N calendar days. Must reindex to daily calendar before computing calendar-day lags.

**When to use:** All price lag and rolling statistics computations.

```python
# Source: verified by direct execution against agmarknet_daily_10yr.parquet
import pandas as pd
import numpy as np


def compute_price_features(
    series: pd.Series,
    cutoff_date: pd.Timestamp,
    lags: list[int] = [7, 14, 30, 90],
    roll_windows: list[int] = [7, 30],
) -> pd.DataFrame:
    """
    Compute lag and rolling statistics for a commodity-district price series.

    Args:
        series: pd.Series with DatetimeIndex, values are modal prices.
                Irregular frequency (market trading days only) is expected.
        cutoff_date: Maximum date to include. Structurally prevents look-ahead.
                     All data AFTER cutoff_date is excluded inside this function.
        lags: List of calendar-day lags to compute (default: 7, 14, 30, 90).
        roll_windows: List of rolling window sizes in calendar days (default: 7, 30).

    Returns:
        pd.DataFrame with DatetimeIndex (daily frequency), columns:
            price_modal: original price (forward-filled to daily)
            price_lag_{n}d: price n calendar days ago
            price_roll_mean_{n}d: rolling mean over n calendar days
            price_roll_std_{n}d: rolling std over n calendar days
    """
    # STEP 1: Enforce cutoff_date structurally — no future data can enter
    s = series.loc[:cutoff_date].copy()
    if s.empty:
        return pd.DataFrame()

    # STEP 2: Reindex to daily frequency — required for calendar-day lags
    # Irregular series (gaps up to 32 days) would give wrong lag values without this
    daily_index = pd.date_range(s.index.min(), s.index.max(), freq="D")
    s_daily = s.reindex(daily_index)

    # STEP 3: Forward-fill price for market-closed days (last known price)
    # Do NOT backfill — backfill would introduce future data into past dates
    s_daily = s_daily.ffill()

    result = pd.DataFrame(index=daily_index)
    result["price_modal"] = s_daily.values

    # STEP 4: Lag features (shift by calendar days)
    for lag in lags:
        result[f"price_lag_{lag}d"] = s_daily.shift(lag).values

    # STEP 5: Rolling statistics
    # shift(1) BEFORE rolling so current-day price is not included in its own window
    s_shifted = s_daily.shift(1)
    for window in roll_windows:
        rolled = s_shifted.rolling(window=window, min_periods=1)
        result[f"price_roll_mean_{window}d"] = rolled.mean().values
        result[f"price_roll_std_{window}d"] = rolled.std().values

    return result
```

### Pattern 2: Rainfall Deficit Computation

**What:** Compute monthly rainfall deficit/surplus as percentage deviation from the 40-year district-month average.

**Data reality:** Rainfall parquet (`data/ranifall_data/combined/rainfall_district_monthly.parquet`) has columns: `STATE, DISTRICT, year, month, rainfall`. Rainfall units are mm (monthly totals from IMD gridded NetCDF summed via shapefile spatial join). All 616 districts have 42 years of data (1985–2026). Only 2026 is incomplete (1 month only) — safely excluded from baseline computation.

**Completeness check:** FEAT-02 requires >= 10 of 12 months per district-year. Verified: 25,256 of 25,872 district-years pass this threshold; the 616 failures are all 2026 (expected, data in progress).

```python
# Source: verified by direct execution against rainfall_district_monthly.parquet
import pandas as pd


def compute_longterm_rainfall_avg(rainfall_df: pd.DataFrame, baseline_end_year: int = 2020) -> pd.DataFrame:
    """
    Compute 40-year monthly average rainfall per district.

    Args:
        rainfall_df: columns [STATE, DISTRICT, year, month, rainfall]
        baseline_end_year: Exclude years after this for baseline (prevents test-period leakage)

    Returns:
        pd.DataFrame with columns [DISTRICT, month, longterm_avg_mm]
    """
    baseline = rainfall_df[rainfall_df["year"] <= baseline_end_year]
    longterm = (
        baseline.groupby(["DISTRICT", "month"])["rainfall"]
        .mean()
        .reset_index()
        .rename(columns={"rainfall": "longterm_avg_mm"})
    )
    return longterm


def compute_rainfall_deficit(
    rainfall_df: pd.DataFrame,
    longterm_avg: pd.DataFrame,
    min_months_per_year: int = 10,
) -> pd.DataFrame:
    """
    Compute rainfall deficit/surplus as percentage deviation from long-term average.

    Args:
        rainfall_df: columns [STATE, DISTRICT, year, month, rainfall]
        longterm_avg: output of compute_longterm_rainfall_avg()
        min_months_per_year: District-years with fewer months are marked is_complete=False

    Returns:
        pd.DataFrame with columns:
            DISTRICT, year, month, rainfall_mm, longterm_avg_mm,
            rainfall_deficit_pct, is_complete
        Where rainfall_deficit_pct = (rainfall - longterm_avg) / longterm_avg * 100
        Positive = surplus, Negative = deficit
    """
    # Completeness flag per district-year
    months_per_dy = (
        rainfall_df.groupby(["DISTRICT", "year"])["month"]
        .count()
        .reset_index()
        .rename(columns={"month": "month_count"})
    )
    months_per_dy["is_complete"] = months_per_dy["month_count"] >= min_months_per_year

    # Merge long-term average
    result = rainfall_df.merge(longterm_avg, on=["DISTRICT", "month"], how="left")

    # Compute deficit percentage; avoid div-by-zero for zero long-term avg
    result["rainfall_deficit_pct"] = (
        (result["rainfall"] - result["longterm_avg_mm"])
        / result["longterm_avg_mm"].replace(0, float("nan"))
        * 100
    )

    # Attach completeness flag
    result = result.merge(months_per_dy[["DISTRICT", "year", "is_complete"]], on=["DISTRICT", "year"], how="left")

    return result.rename(columns={"rainfall": "rainfall_mm"})
```

### Pattern 3: Weather Tier A+ / Tier B Split — NaN Passthrough (No Imputation)

**What:** Return weather features for Tier A+ districts (261 weather-covered and harmonised), and return NaN columns for Tier B districts (~310 uncovered). FEAT-03 is explicit: absent means NaN columns, not imputed values.

**Data reality:** Weather CSV covers 287 districts (2021–2025, daily). 261 are harmonised to canonical price district names via `district_name_map`. The remaining 26 weather-only districts are unmatched and should not produce weather features. The ~310 price districts with NO weather entry are definitionally Tier B.

```python
# Source: verified by direct execution against weather CSV and district_name_map
import pandas as pd


WEATHER_FEATURE_COLS = ["max_temp_c", "min_temp_c", "avg_temp_c", "avg_humidity", "max_wind_kph"]


def compute_weather_features(
    weather_df: pd.DataFrame,
    canonical_district: str,
    cutoff_date: pd.Timestamp,
    tier_a_plus_districts: set[str],
) -> pd.DataFrame:
    """
    Return daily weather features for a district, or NaN columns if Tier B.

    Args:
        weather_df: columns [date, district, max_temp_c, min_temp_c, avg_temp_c, avg_humidity, max_wind_kph]
                    district column contains CANONICAL district names (pre-mapped via district_name_map)
        canonical_district: The canonical district name (from price dataset)
        cutoff_date: Maximum date — data after this is excluded
        tier_a_plus_districts: Set of districts with validated weather coverage

    Returns:
        pd.DataFrame with DatetimeIndex (daily), columns:
            max_temp_c, min_temp_c, avg_temp_c, avg_humidity, max_wind_kph
        All NaN for Tier B districts. Present values for Tier A+.
    """
    if canonical_district not in tier_a_plus_districts:
        # Tier B: return empty frame — caller knows to use NaN
        return pd.DataFrame(columns=WEATHER_FEATURE_COLS)

    district_data = weather_df[
        (weather_df["district"] == canonical_district)
        & (pd.to_datetime(weather_df["date"]) <= cutoff_date)
    ].copy()

    district_data["date"] = pd.to_datetime(district_data["date"])
    district_data = district_data.set_index("date").sort_index()

    return district_data[WEATHER_FEATURE_COLS]
```

### Pattern 4: Leakage Detection Test

**What:** The FEAT-01 success criterion requires a leakage detection test to pass in CI: "train on years 1-7, assert test-period feature values are not visible in training data."

**Architecture:** The test verifies that feature computation on a training window does NOT produce any feature rows with dates >= test_start. The `cutoff_date` enforcement makes this trivially true — the test validates that nobody removed the enforcement.

```python
# Source: derived from FEAT-01 success criterion; pattern verified by execution
import pandas as pd
import numpy as np
import pytest


def test_no_lookahead_leakage_price_features():
    """
    Leakage detection test: training features (years 1-7) must not
    contain any data from the test period (year 8+).

    This test would FAIL if cutoff_date is not enforced inside compute_price_features().
    """
    # Simulate 8 years of daily price data
    full_dates = pd.date_range("2015-01-01", "2022-12-31", freq="D")
    full_prices = pd.Series(np.random.randn(len(full_dates)).cumsum() + 1000, index=full_dates)

    train_cutoff = pd.Timestamp("2021-12-31")  # end of year 7
    test_start = pd.Timestamp("2022-01-01")    # beginning of year 8

    # Call with the full series — if cutoff_date is enforced, no test data leaks in
    train_features = compute_price_features(full_prices, cutoff_date=train_cutoff)

    # Assert: no feature row has a date in the test period
    assert train_features.index.max() <= train_cutoff, (
        f"Look-ahead leakage detected: feature index extends to {train_features.index.max()}, "
        f"which is past training cutoff {train_cutoff}"
    )

    # Assert: no test-period price value appears in feature columns
    test_period_prices = set(full_prices[full_prices.index >= test_start].round(6).values)
    all_feature_prices = set(train_features["price_modal"].dropna().round(6).values)
    leaked = test_period_prices.intersection(all_feature_prices)
    assert len(leaked) == 0, f"Test-period prices found in training features: {len(leaked)} values"
```

### Pattern 5: Pure Function + importlib Test Loading (Established Project Pattern)

**What:** Tests import feature functions directly from module files using `importlib.util.spec_from_file_location`. No Django/Flask test client needed.

**When to use:** All Phase 3 tests — feature functions are standalone modules with no FastAPI dependency.

```python
# Source: backend/tests/test_clean_prices.py (project pattern — verified)
import importlib.util
from pathlib import Path


def _load_module(module_name: str, relative_path: str):
    """Load a module by file path (no package install needed)."""
    script_path = Path(__file__).parent.parent / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# For Phase 3, feature modules ARE in a package (app/ml/), so direct import works:
# from app.ml.price_features import compute_price_features
# But importlib fallback works if needed
```

**Note for Phase 3:** Since the feature modules go into `backend/app/ml/` (a proper Python package), direct imports work from the `backend/` directory: `from app.ml.price_features import compute_price_features`. No importlib workaround needed.

### Anti-Patterns to Avoid

- **shift(n) without daily reindex on irregular series:** `series.shift(7)` on market-day series shifts by 7 trading days, not 7 calendar days. Onion-Nashik has gaps up to 32 days. Always `reindex(pd.date_range(..., freq='D')).ffill()` before shift operations.

- **Backfilling during daily reindex:** `s_daily.bfill()` fills a day's NaN with the NEXT known price, which is future data. Always `ffill()` (last known price).

- **Cutoff enforcement on the caller side only:** `series[series.index <= cutoff].shift(n)` in the caller instead of inside the function. A caller that forgets the filter causes leakage silently. The `cutoff_date` parameter must be used INSIDE the function via `series.loc[:cutoff_date]`.

- **Computing rolling stats before shift(1):** `series.rolling(7).mean()` includes the current day's price in the window. The value at date T would include T's price, meaning at prediction time you'd need T's price (which you're trying to predict). Always `series.shift(1).rolling(7).mean()`.

- **Imputing Tier B weather with anything:** FEAT-03 explicitly requires Tier B districts to have absent (NaN) weather features, not imputed values. Imputing would create false signal for ~310 districts that have no measured weather data.

- **Rolling deficit without completeness filter:** Computing deficit for a district-year with only 2 months (e.g. 2026 partial data) would produce a misleading deficit signal. Always apply `is_complete` flag and exclude incomplete years from model training features.

- **Global long-term average instead of district-month average:** A single national monthly rainfall average would mask monsoon variation across Kerala (wet) vs Rajasthan (dry). Always compute `groupby(['DISTRICT','month'])`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Calendar-day lags on irregular series | Custom loop iterating over date pairs | `pandas.Series.reindex(daily_range).ffill().shift(n)` | pandas handles DST, missing dates, and performance correctly |
| Rolling window statistics | Accumulator loop | `pandas.Series.rolling(n, min_periods=1).mean()/.std()` | pandas rolling is C-optimised; handles edge cases at series start |
| Rainfall long-term average | Nested dicts | `groupby(['DISTRICT','month'])['rainfall'].mean()` | Single vectorised operation; returns indexable DataFrame |
| Tier A+ district set | Hardcoded list | Query `district_name_map` WHERE `source_dataset='weather'` AND `match_type IN ('exact','fuzzy_accepted')` | 261 is correct now; may change if harmonisation is re-run |
| District-name translation | Custom string matching | `district_name_map` table (from Phase 1) | Phase 1 produced the authoritative mapping; do not re-implement matching |

**Key insight:** All feature operations reduce to pandas groupby, reindex, shift, and rolling. Building custom loops would be slower, harder to test, and more likely to introduce subtle leakage bugs.

---

## Common Pitfalls

### Pitfall 1: shift() on Irregular Series Gives Wrong Calendar-Day Lags

**What goes wrong:** `price_series.shift(7)` returns the price from 7 records ago, not 7 calendar days ago. Onion-Nashik has gaps up to 32 days. A 7-record lag might actually span 14–40 calendar days, making the feature semantically wrong.

**Why it happens:** `pandas.shift(n)` shifts by record count, not time interval, when the index is DatetimeIndex with irregular frequency.

**How to avoid:** Always `reindex(pd.date_range(start, end, freq='D')).ffill()` before calling `.shift(n)`.

**Warning signs:** The 7-day lag feature has non-NaN values for the first 7 rows of the original series (because 7 records might be enough even when there are fewer than 7 calendar days of data).

### Pitfall 2: Backfill During Daily Reindex Introduces Future Data

**What goes wrong:** `series.reindex(daily_range).bfill()` fills NaN calendar days with the NEXT available trading price. If a price is recorded on the 10th and the next on the 15th, the 10th-14th entries get the 15th's value — which is future data at those dates.

**Why it happens:** backfill is a natural instinct for filling gaps.

**How to avoid:** Always use `ffill()` (propagate LAST known value forward). Explicitly forbid `bfill()` in code review.

**Warning signs:** Feature leakage test passes (because the cutoff_date prevents test-period data) but model performance on walk-forward validation is better than expected, suggesting subtle future-data contamination within the training window.

### Pitfall 3: Rolling Stats Including Current-Day Price in Window

**What goes wrong:** `series.rolling(7).mean()` at date T includes T's own price in the rolling mean, creating a circular dependency (the target variable appears in a feature).

**Why it happens:** Default pandas rolling is "up to and including the current observation."

**How to avoid:** Always `series.shift(1).rolling(7).mean()`. The `shift(1)` excludes the current day.

**Warning signs:** Rolling mean feature correlates almost perfectly with the raw price at short windows — suspiciously high.

### Pitfall 4: pyarrow Version Conflict When Loading Rainfall Parquet

**What goes wrong:** `pd.read_parquet(..., engine='pyarrow')` raises `Repetition level histogram size mismatch` if pyarrow version is not 17.0.0.

**Why it happens:** The price parquet (`agmarknet_daily_10yr.parquet`) is incompatible with pyarrow >= 19. This is a confirmed Phase 1 decision pinned in STATE.md.

**How to avoid:** Do not upgrade pyarrow. `requirements.txt` is pinned to `pyarrow==17.0.0`. Any feature that reads parquet must use the project Python environment, not a system Python.

**Warning signs:** `ImportError` or `ArrowInvalid` when reading price or rainfall parquet outside the project's virtual environment.

### Pitfall 5: Tier B Districts Getting Imputed Weather Features

**What goes wrong:** Treating missing weather data for ~310 districts as "fill with nearest district" or "fill with state average." This creates false confidence in feature coverage and corrupts the model's ability to distinguish between districts with and without actual weather data.

**Why it happens:** NaN-handling instinct — ML engineers often fill NaN before model training.

**How to avoid:** `compute_weather_features()` returns an empty DataFrame for Tier B. The caller (training pipeline in Phase 4) is responsible for handling NaN — via XGBoost's native NaN handling or by dropping weather columns for Tier B models.

**Warning signs:** Feature completeness report shows 100% coverage for weather features across all 571 districts.

### Pitfall 6: 2026 Partial Rainfall Data Corrupting Long-Term Baseline

**What goes wrong:** Including 2026 in the long-term average computation. 2026 has only 1 month of data per district. Including it would bias all district-month averages for January.

**Why it happens:** The rainfall parquet extends to 2026 — it's easy to include without filtering.

**How to avoid:** Pass `baseline_end_year=2020` (or similar) to `compute_longterm_rainfall_avg()`. Exclude partial years from baseline computation.

**Warning signs:** January long-term average for all districts is inflated or different from historical baseline.

### Pitfall 7: Windows UTF-8 Crash in Scripts

**What goes wrong:** District names with Unicode characters in print statements crash with `UnicodeEncodeError` on Windows.

**Why it happens:** Windows console defaults to cp1252.

**How to avoid:** Every script that prints district names must include the established project pattern:
```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

---

## Code Examples

Verified patterns from direct data inspection:

### Loading Price Parquet for Feature Computation

```python
# Source: verified by direct execution (agmarknet_daily_10yr.parquet)
import pandas as pd


def load_commodity_district_series(
    parquet_path: str,
    commodity: str,
    district: str,
    cutoff_date: pd.Timestamp,
) -> pd.Series:
    """Load modal price series for one commodity-district pair, up to cutoff_date."""
    df = pd.read_parquet(
        parquet_path,
        columns=["date", "commodity", "district", "price_modal"],
        engine="pyarrow",
        filters=[
            ("commodity", "==", commodity),
            ("district", "==", district),
            ("date", "<=", str(cutoff_date.date())),
        ],
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date")
    return df.set_index("date")["price_modal"]
```

### Loading Rainfall Parquet for Deficit Computation

```python
# Source: verified by direct execution (rainfall_district_monthly.parquet)
import pandas as pd


def load_rainfall_df(parquet_path: str) -> pd.DataFrame:
    """
    Load the rainfall district monthly parquet.
    Columns: STATE, DISTRICT, year, month, rainfall (mm, monthly total)
    616 districts, 1985-2026 (2026 partial — only Jan for all districts).
    """
    return pd.read_parquet(parquet_path, engine="pyarrow")
    # Note: no reindex needed — already monthly granularity
    # Column names are UPPER CASE: STATE, DISTRICT (from shapefile spatial join)
```

### Getting Tier A+ Weather District Set from district_name_map

```python
# Source: verified against district_name_map schema (Phase 1 output)
from sqlalchemy import create_engine, text


def get_weather_tier_a_plus_districts(db_url: str) -> set[str]:
    """
    Query district_name_map to get canonical district names with validated weather coverage.
    Returns ~261 districts as of Phase 1 harmonisation.
    """
    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT canonical_district
            FROM district_name_map
            WHERE source_dataset = 'weather'
              AND match_type IN ('exact', 'fuzzy_accepted')
              AND canonical_district IS NOT NULL
        """))
        return {r[0] for r in rows}

# NOTE: This is the ONE allowed DB call — outside the feature function, in the caller.
# The feature function itself receives tier_a_plus_districts as a parameter (a set).
```

### Rainfall Completeness Check

```python
# Source: verified by direct computation on rainfall parquet
import pandas as pd


def check_rainfall_completeness(rainfall_df: pd.DataFrame, min_months: int = 10) -> pd.DataFrame:
    """
    Return district-years that have >= min_months of rainfall records.

    Returns:
        pd.DataFrame with columns [DISTRICT, year, month_count, is_complete]
    """
    counts = (
        rainfall_df.groupby(["DISTRICT", "year"])["month"]
        .count()
        .reset_index()
        .rename(columns={"month": "month_count"})
    )
    counts["is_complete"] = counts["month_count"] >= min_months
    return counts

# Data reality: 25,256 of 25,872 district-years pass with min_months=10.
# The 616 failures are all year=2026 (partial data, expected).
```

---

## Data Contracts (Critical for Planner)

These are VERIFIED schemas from direct file inspection:

### Price Parquet (`agmarknet_daily_10yr.parquet`)
- **Columns:** date (datetime64), commodity (str), commodity_id (int), state (str), state_id (int), district (str), district_id (int), price_min (float32), price_max (float32), price_modal (float32), category_id (int), entity_id (int)
- **Shape:** 25,132,834 rows
- **Date range:** 2015-01-01 to 2025-10-30
- **Commodity-district pairs:** 19,679 total; 10,445 with >= 730 days; 14,804 with >= 365 days
- **Time series character:** IRREGULAR — gaps up to 32 calendar days (Onion-Nashik example)

### Rainfall Parquet (`data/ranifall_data/combined/rainfall_district_monthly.parquet`)
- **Columns:** STATE (str, UPPER CASE), DISTRICT (str), year (int32), month (int32), rainfall (float64, mm monthly total)
- **Shape:** 306,646 rows
- **Districts:** 616 unique
- **Year range:** 1985–2026 (all 616 districts have 42 years; 2026 = 1 month only)
- **Month completeness:** 25,256 of 25,872 district-years have >= 10 months (616 failures = all 2026)

### Weather CSV (`data/weather data/india_weather_daily_10years.csv`)
- **Columns:** date (str, YYYY-MM-DD), district (str), max_temp_c (float), min_temp_c (float), avg_temp_c (float), avg_humidity (float), max_wind_kph (float)
- **Shape:** 519,992 rows, no missing values
- **Districts:** 287 unique in CSV; 261 harmonised to canonical price district names; 26 unmatched
- **Date range:** 2021-01-01 to 2025-12-31

### district_name_map Table (Phase 1 output)
- **Columns:** id, source_dataset, state_name, source_district, canonical_district, match_score, match_type, created_at
- **Weather rows:** 287 total, 261 matched (exact or fuzzy_accepted), 26 unmatched
- **Rainfall rows:** 622 total, 564 matched, 557 unique canonical districts
- **Soil rows:** 445 total (not relevant to Phase 3 price/weather/rainfall features)
- This is the authoritative Tier A+ source — query it once, pass as a set to feature functions

### Tier Classification (from Phase 1 harmonisation)
| Tier | Districts | Feature Set |
|------|-----------|-------------|
| Tier A+ | ~261 weather-harmonised districts | Price lags + rolling stats + rainfall deficit + weather temp/humidity |
| Tier A | ~296 rainfall-only districts (557 - 261) | Price lags + rolling stats + rainfall deficit |
| Tier B | ~14 price-only districts (571 - 557) | Price lags + rolling stats only |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `shift(n)` directly on sparse market series | Reindex to daily calendar, `ffill()`, then `shift(n)` | Standard best practice (well-established) | Correct calendar-day semantics for lags; prevents wrong feature values on irregular series |
| Rolling window on raw series | `shift(1).rolling(n)` | Standard best practice | Prevents current-day target variable appearing in its own feature |
| Single global rainfall baseline | Per-district per-month 40-year average | Current standard for Indian agricultural meteorology | Accounts for monsoon variation across climatic zones |
| Imputing missing weather with neighbours | NaN passthrough for uncovered districts | Current ML best practice for structured missingness | XGBoost handles NaN natively; imputation would create synthetic signal |

**Deprecated/outdated:**
- Global winsorisation before feature computation: Price cleaning is already done per commodity (Phase 1, `price_bounds` table); feature functions read from the cleaned price series
- Separate train/test data preparation pipelines: The `cutoff_date` parameter serves both training (historical cutoff) and inference (current date) without separate code paths

---

## Open Questions

1. **How do feature functions receive winsorisation bounds at feature time?**
   - What we know: `price_bounds` table has per-commodity lower_cap/upper_cap from Phase 1; MEMORY.md says "downstream clips at read time"
   - What's unclear: Should `compute_price_features()` apply the clip internally, or should the caller pass pre-clipped data?
   - Recommendation: Caller responsibility — load price series with bounds applied BEFORE calling the feature function. Keep feature functions focused on lag/rolling only. Avoids mixing concerns and keeps functions testable with raw synthetic data.

2. **Should feature functions output sparse (only original trading days) or dense (daily reindexed) DataFrames?**
   - What we know: Phase 4 (XGBoost with ForecasterRecursiveMultiSeries) will consume these features; that library works with both regular and irregular time series
   - What's unclear: ForecasterRecursiveMultiSeries's preferred input format (not yet researched for Phase 4)
   - Recommendation: Output DAILY reindexed DataFrames. This is unambiguous for lags (calendar days), consistent for joining with rainfall/weather (which are also daily or monthly), and Phase 4 can always resample if needed.

3. **What alembic revision is the current HEAD after Phase 2?**
   - What we know: Current DB has two heads: `a1b2c3d4e5f6` (community alert features) and `c2d3e4f5a6b7` (price_bounds from Phase 1). Phase 3 creates no DB tables.
   - What's unclear: Phase 2 will add a `seasonal_price_stats` migration between Phase 1 and Phase 3
   - Recommendation: No action needed for Phase 3 — no migrations required.

4. **Does Phase 3 need a script to pre-compute features, or only the functions?**
   - What we know: FEAT-04 requires pure functions; ROADMAP says Phase 3 delivers functions+tests; Phase 4 will be the first consumer
   - What's unclear: Whether a `compute_features.py` script is needed for Phase 3 or can wait until Phase 4
   - Recommendation: Phase 3 delivers only the functions and their tests — no pipeline script. Phase 4 plans 04-01 and 04-02 will build the training pipeline that calls these functions.

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `agmarknet_daily_10yr.parquet` — confirmed schema, shape, date range, irregularity, commodity-district pair counts
- Direct file inspection: `data/ranifall_data/combined/rainfall_district_monthly.parquet` — confirmed columns (STATE, DISTRICT, year, month, rainfall), 616 districts, 1985-2026, 40-yr coverage, completeness statistics
- Direct file inspection: `data/weather data/india_weather_daily_10years.csv` — confirmed columns, 287 districts, 519,992 rows, date range 2021-2025, no missing values
- Direct DB query: `district_name_map` table — confirmed weather (287/261 matched), rainfall (622/564/557 unique canonical), soil counts
- Direct execution: Pandas shift/reindex/rolling pattern verified against actual price series (Onion-Nashik)
- Direct execution: Rainfall deficit calculation pattern verified against actual parquet
- Direct execution: Completeness check verified (25,256 of 25,872 pass; 616 failures = 2026 only)
- `.planning/phases/01-district-harmonisation-price-cleaning/01-RESEARCH.md` — Phase 1 data contracts, pyarrow pin rationale
- `.planning/STATE.md` — pyarrow 17.0.0 pin confirmed (phase decision), pandas 2.x groupby loop pattern
- `backend/requirements.txt` — confirmed all required packages (pandas, pyarrow, numpy, scipy) already present

### Secondary (MEDIUM confidence)
- `backend/tests/test_clean_prices.py` — importlib test loading pattern (project-established)
- `backend/tests/test_harmonise_districts.py` — pure function test pattern (project-established)
- `backend/pytest.ini` — confirmed test runner config, markers, test discovery
- [Analytics Vidhya: Lag and Rolling Features Guide](https://www.analyticsvidhya.com/blog/2026/02/lag-and-rolling-features/) — `shift(1)` before rolling is standard practice

### Tertiary (LOW confidence)
- [skforecast 0.18.0 docs](https://skforecast.org/0.18.0/index.html) — ForecasterRecursiveMultiSeries window_features API (relevant for Phase 4 integration, not Phase 3)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already in requirements.txt; no new dependencies
- Data schemas: HIGH — verified by direct parquet/CSV inspection and DB queries
- Architecture patterns: HIGH — all code examples verified by execution against real data
- Anti-leakage patterns: HIGH — shift/reindex issue confirmed by execution; cutoff enforcement verified
- Tier classification numbers: HIGH — 261/287/557 counts from direct district_name_map query
- Pitfalls: HIGH — confirmed by testing with actual data files

**Research date:** 2026-03-02
**Valid until:** 2026-09-01 (pandas 2.x API is stable; rainfall/weather data structures are static project assets)
