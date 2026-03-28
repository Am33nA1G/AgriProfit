"""
Build monthly weather features by merging daily weather CSV with rainfall parquet.

Produces data/features/weather_monthly_features.parquet with columns:
  district, year, month, avg_temp_c, avg_humidity,
  annual_rainfall_mm, annual_rainfall_deviation_pct

Rainfall is aggregated to annual per (district, year) with a 1985-2015
baseline to compute deviation %.  Temp/humidity remain monthly so the
downstream training matrix can average them to annual independently.

Usage:
    cd backend
    python -m scripts.build_weather_features
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    weather_csv = REPO_ROOT / "data" / "weather data" / "india_weather_daily_10years.csv"
    rainfall_pq = REPO_ROOT / "data" / "ranifall_data" / "combined" / "rainfall_district_monthly.parquet"
    output_dir = REPO_ROOT / "data" / "features"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weather_monthly_features.parquet"

    # --- Weather from CSV ---
    print(f"Loading weather CSV: {weather_csv.name}")
    wdf = pd.read_csv(weather_csv, parse_dates=["date"])
    wdf["year"] = wdf["date"].dt.year
    wdf["month"] = wdf["date"].dt.month

    weather_monthly = (
        wdf.groupby(["district", "year", "month"])
        .agg(avg_temp_c=("avg_temp_c", "mean"), avg_humidity=("avg_humidity", "mean"))
        .reset_index()
    )
    weather_monthly["district_lower"] = weather_monthly["district"].str.strip().str.lower()
    print(f"  Weather monthly: {weather_monthly.shape}")

    # --- Rainfall from parquet (annual aggregation) ---
    print(f"Loading rainfall parquet: {rainfall_pq.name}")
    rdf = pd.read_parquet(rainfall_pq, engine="pyarrow")

    # Normalise column names — handle both upper- and lower-case variants
    rdf.columns = rdf.columns.str.strip()
    col_map = {c: c.lower() for c in rdf.columns}
    rdf = rdf.rename(columns=col_map)
    if "rainfall" in rdf.columns and "rainfall_mm" not in rdf.columns:
        rdf = rdf.rename(columns={"rainfall": "rainfall_mm"})

    rdf["district_lower"] = rdf["district"].str.strip().str.lower()

    # 1. Deduplicate to one rainfall value per (district, year, month)
    #    The parquet may contain multiple rows per district-month (stations/sources).
    monthly_rain = (
        rdf.groupby(["district_lower", "year", "month"])["rainfall_mm"]
        .mean()
        .reset_index()
    )

    # 2. Annual rainfall per (district, year) — sum of 12 monthly means
    rain_annual = (
        monthly_rain.groupby(["district_lower", "year"])["rainfall_mm"]
        .sum()
        .reset_index()
        .rename(columns={"rainfall_mm": "annual_rainfall_mm"})
    )

    # 3. Baseline: mean monthly rainfall per district (1985-2015), then × 12
    baseline_months = monthly_rain[
        (monthly_rain["year"] >= 1985) & (monthly_rain["year"] <= 2015)
    ]
    baseline = (
        baseline_months.groupby("district_lower")["rainfall_mm"]
        .mean()                     # mean of deduplicated monthly rows → avg monthly
        .reset_index()
        .rename(columns={"rainfall_mm": "baseline_rainfall_mm"})
    )
    baseline["baseline_rainfall_mm"] = baseline["baseline_rainfall_mm"] * 12  # annualise

    # 3. Merge baseline with annual rainfall
    rain_annual = rain_annual.merge(baseline, on="district_lower", how="left")

    # 4. Rainfall deviation %
    rain_annual["annual_rainfall_deviation_pct"] = (
        (rain_annual["annual_rainfall_mm"] - rain_annual["baseline_rainfall_mm"])
        / rain_annual["baseline_rainfall_mm"].clip(lower=1.0)
        * 100.0
    )

    rain_annual = rain_annual[["district_lower", "year", "annual_rainfall_mm", "annual_rainfall_deviation_pct"]]
    print(f"  Rainfall annual: {rain_annual.shape}")

    # --- Merge weather (monthly) with rainfall (annual) on (district_lower, year) ---
    merged = weather_monthly.merge(rain_annual, on=["district_lower", "year"], how="left")
    merged = merged.rename(columns={"district": "district_name"})
    merged["district"] = merged["district_lower"]
    result = merged[["district", "year", "month", "avg_temp_c", "avg_humidity",
                      "annual_rainfall_mm", "annual_rainfall_deviation_pct"]].copy()

    result.to_parquet(output_path, engine="pyarrow", index=False)
    print(f"\nSaved: {output_path}")
    print(f"Shape: {result.shape}")
    print(result.head(3).to_string())


if __name__ == "__main__":
    main()
