"""
generate_seasonal_json.py — Build per-commodity monthly price stat JSON files.

Writes ml/artifacts/v4/{slug}_seasonal.json — used by ForecastService._seasonal_fallback()
when model quality is insufficient (R² < 0.3 or Tier D).

This complements train_forecast_v4.py which writes seasonal JSON only for Tier D
commodities. Running this script ensures ALL commodities have a seasonal fallback
file regardless of tier.

Output format per commodity:
{
  "1": {"mean": 2400, "median": 2350, "p10": 1800, "p25": 2100, "p75": 2700, "p90": 3100},
  "2": { ... },
  ...  # months 1-12
}

Usage:
    cd backend
    python -m scripts.generate_seasonal_json
"""
import sys
import json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET_PATH = REPO_ROOT / "agmarknet_daily_10yr.parquet"
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts" / "v4"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def build_seasonal_stats(df: pd.DataFrame) -> dict:
    """Monthly price stats from historical data."""
    df = df.copy()
    df["month"] = pd.to_datetime(df["date"]).dt.month
    result = {}
    for month, grp in df.groupby("month"):
        prices = grp["price_modal"].dropna()
        prices = prices[prices > 0]
        if len(prices) < 10:
            continue
        result[str(int(month))] = {
            "mean":   round(float(prices.mean()), 2),
            "median": round(float(prices.median()), 2),
            "p10":    round(float(prices.quantile(0.10)), 2),
            "p25":    round(float(prices.quantile(0.25)), 2),
            "p75":    round(float(prices.quantile(0.75)), 2),
            "p90":    round(float(prices.quantile(0.90)), 2),
        }
    return result


def main():
    print(f"Loading parquet: {PARQUET_PATH}")
    parquet = pd.read_parquet(
        PARQUET_PATH,
        engine="pyarrow",
        columns=["date", "commodity", "price_modal"],
    )
    print(f"Loaded {len(parquet):,} rows")

    saved = 0
    skipped = 0
    for commodity, grp in parquet.groupby("commodity"):
        stats = build_seasonal_stats(grp)
        if not stats:
            skipped += 1
            continue
        slug = slugify(commodity)
        out = ARTIFACTS_DIR / f"{slug}_seasonal.json"
        out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
        saved += 1
        print(f"  [OK] {commodity} ({slug}) — {len(stats)} months")

    print(f"\nSeasonal calendars: {saved} saved, {skipped} skipped (insufficient data)")


if __name__ == "__main__":
    main()
