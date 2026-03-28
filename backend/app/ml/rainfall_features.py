"""
Rainfall feature engineering — deficit/surplus computation and completeness checking.

DATA CONTRACT (verified against rainfall_district_monthly.parquet):
- Columns: STATE (str, UPPER CASE), DISTRICT (str), year (int32), month (int32), rainfall (float64, mm)
- 616 districts, 1985-2026 (2026 = 1 month only for all districts)
- 25,256 of 25,872 district-years have >= 10 months; 616 failures are all 2026
- Load with: pd.read_parquet(path, engine='pyarrow')  # pyarrow==17.0.0 required
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np


def compute_longterm_rainfall_avg(
    rainfall_df: pd.DataFrame,
    baseline_end_year: int = 2020,
) -> pd.DataFrame:
    """
    Compute long-term monthly average rainfall per district.

    Args:
        rainfall_df: columns [STATE, DISTRICT, year, month, rainfall]
        baseline_end_year: Exclude years after this to prevent test-period leakage.
                           Default 2020 gives a 36-year baseline (1985-2020).

    Returns:
        pd.DataFrame with columns [DISTRICT, month, longterm_avg_mm]
        One row per (DISTRICT, month) — 12 rows per district.
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
        min_months_per_year: District-years with fewer months are marked is_complete=False.

    Returns:
        pd.DataFrame with columns:
            DISTRICT, year, month, rainfall_mm, longterm_avg_mm,
            rainfall_deficit_pct, is_complete
        rainfall_deficit_pct: (rainfall - longterm_avg) / longterm_avg * 100
            Positive = surplus, Negative = deficit, NaN if longterm_avg is 0.
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

    # Compute deficit — avoid ZeroDivisionError for zero long-term avg
    result["rainfall_deficit_pct"] = (
        (result["rainfall"] - result["longterm_avg_mm"])
        / result["longterm_avg_mm"].replace(0, float("nan"))
        * 100
    )

    # Attach completeness flag
    result = result.merge(
        months_per_dy[["DISTRICT", "year", "is_complete"]],
        on=["DISTRICT", "year"],
        how="left",
    )

    return result.rename(columns={"rainfall": "rainfall_mm"})


def check_rainfall_completeness(
    rainfall_df: pd.DataFrame,
    min_months: int = 10,
) -> pd.DataFrame:
    """
    Return district-year completeness summary.

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
