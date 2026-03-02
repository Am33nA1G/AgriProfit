"""
Price cleaning pipeline: per-commodity IQR winsorisation.

Reads the price parquet, computes IQR-based lower_cap and upper_cap per commodity,
flags outlier rows, and upserts all bounds into the price_bounds PostgreSQL table.

The price_history table is NEVER modified — original modal_price values are preserved.
The price_bounds table stores the persistent caps for use at inference time.

Usage:
    python backend/scripts/clean_prices.py
"""
import sys
import os
from pathlib import Path

# Windows UTF-8 console fix (project standard from MEMORY.md)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from sqlalchemy import text

# Add backend/ to sys.path so app imports work when run as a script
_BACKEND_DIR = Path(__file__).parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.database.session import SessionLocal

# Path to price parquet — repo root / agmarknet_daily_10yr.parquet
_PARQUET_PATH = Path(__file__).parent.parent.parent / "agmarknet_daily_10yr.parquet"


# ---------------------------------------------------------------------------
# Pure computation functions (no DB, no I/O — easily unit-testable)
# ---------------------------------------------------------------------------

def compute_commodity_bounds(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-commodity IQR winsorisation bounds from a price DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: commodity, commodity_id, price_modal.
        Input DataFrame is NOT modified.

    Returns
    -------
    pd.DataFrame
        One row per commodity with columns:
        commodity, commodity_id, q1, q3, iqr, lower_cap, upper_cap, median_price
    """
    def _iqr_bounds(series: pd.Series) -> dict:
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower_cap = max(0.0, q1 - 3.0 * iqr)
        upper_cap = q3 + 3.0 * iqr
        median_price = float(series.median())
        return {
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_cap": lower_cap,
            "upper_cap": upper_cap,
            "median_price": median_price,
        }

    # Pick the first commodity_id seen per commodity (stable, deterministic)
    commodity_id_map = (
        df[["commodity", "commodity_id"]]
        .drop_duplicates("commodity")
        .set_index("commodity")["commodity_id"]
    )

    # Compute bounds per commodity — build list of dicts for clarity and pandas 2.x compat
    rows = []
    for commodity, group in df.groupby("commodity"):
        bounds_dict = _iqr_bounds(group["price_modal"])
        bounds_dict["commodity"] = commodity
        bounds_dict["commodity_id"] = commodity_id_map.get(commodity)
        rows.append(bounds_dict)

    bounds_stats = pd.DataFrame(rows)

    # Reorder columns to match the expected output contract
    return bounds_stats[
        ["commodity", "commodity_id", "q1", "q3", "iqr", "lower_cap", "upper_cap", "median_price"]
    ].reset_index(drop=True)


def flag_and_cap_outliers(df: pd.DataFrame, bounds: pd.DataFrame) -> pd.DataFrame:
    """
    Flag outlier rows and produce capped clean prices.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: commodity, price_modal.
        Input DataFrame is NOT modified.
    bounds : pd.DataFrame
        Output of compute_commodity_bounds() — must contain:
        commodity, lower_cap, upper_cap.

    Returns
    -------
    pd.DataFrame
        A NEW DataFrame (copy of df) with two additional columns:
        - is_outlier (bool): True when price_modal is outside [lower_cap, upper_cap]
        - modal_price_clean (float): price_modal capped to [lower_cap, upper_cap]
    """
    # Merge on commodity — left join so all df rows are kept
    merged = df.merge(
        bounds[["commodity", "lower_cap", "upper_cap"]],
        on="commodity",
        how="left",
    )

    # Flag outliers: price_modal outside the per-commodity bounds
    merged["is_outlier"] = (
        (merged["price_modal"] < merged["lower_cap"]) |
        (merged["price_modal"] > merged["upper_cap"])
    )

    # Cap prices: clip to [lower_cap, upper_cap] — produces modal_price_clean
    merged["modal_price_clean"] = merged["price_modal"].clip(
        lower=merged["lower_cap"], upper=merged["upper_cap"]
    )

    # Return a new DataFrame without the helper bound columns
    result = merged.drop(columns=["lower_cap", "upper_cap"]).copy()
    return result


# ---------------------------------------------------------------------------
# Database write
# ---------------------------------------------------------------------------

def upsert_price_bounds(bounds_df: pd.DataFrame, counts_df: pd.DataFrame) -> None:
    """
    Upsert per-commodity price bounds into the price_bounds table.

    Parameters
    ----------
    bounds_df : pd.DataFrame
        Output of compute_commodity_bounds().
    counts_df : pd.DataFrame
        Must contain: commodity, outlier_count, total_count.
    """
    # Join bounds with counts
    full = bounds_df.merge(counts_df, on="commodity", how="left")

    db = SessionLocal()
    try:
        upsert_sql = text("""
            INSERT INTO price_bounds
                (commodity, commodity_id, q1, q3, iqr, lower_cap, upper_cap,
                 median_price, outlier_count, total_count, computed_at)
            VALUES
                (:commodity, :commodity_id, :q1, :q3, :iqr, :lower_cap, :upper_cap,
                 :median_price, :outlier_count, :total_count, now())
            ON CONFLICT (commodity) DO UPDATE SET
                commodity_id   = EXCLUDED.commodity_id,
                q1             = EXCLUDED.q1,
                q3             = EXCLUDED.q3,
                iqr            = EXCLUDED.iqr,
                lower_cap      = EXCLUDED.lower_cap,
                upper_cap      = EXCLUDED.upper_cap,
                median_price   = EXCLUDED.median_price,
                outlier_count  = EXCLUDED.outlier_count,
                total_count    = EXCLUDED.total_count,
                computed_at    = now()
        """)

        rows_written = 0
        for _, row in full.iterrows():
            params = {
                "commodity":     row["commodity"],
                "commodity_id":  int(row["commodity_id"]) if pd.notna(row["commodity_id"]) else None,
                "q1":            round(float(row["q1"]), 2),
                "q3":            round(float(row["q3"]), 2),
                "iqr":           round(float(row["iqr"]), 2),
                "lower_cap":     round(float(row["lower_cap"]), 2),
                "upper_cap":     round(float(row["upper_cap"]), 2),
                "median_price":  round(float(row["median_price"]), 2),
                "outlier_count": int(row["outlier_count"]) if pd.notna(row.get("outlier_count")) else 0,
                "total_count":   int(row["total_count"]) if pd.notna(row.get("total_count")) else 0,
            }
            db.execute(upsert_sql, params)
            rows_written += 1

        db.commit()
        print(f"  Upserted {rows_written} commodity bounds into price_bounds table.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Full price cleaning pipeline.

    Steps:
    1. Load price parquet (3 columns only — memory efficient)
    2. Compute per-commodity IQR bounds (pure function)
    3. Flag and cap outliers (pure function, returns new DataFrame)
    4. Compute outlier_count and total_count per commodity
    5. Upsert bounds into price_bounds table
    6. Print summary report
    """
    print("=== Price Cleaning Pipeline ===")
    print(f"Parquet path: {_PARQUET_PATH}")

    # Step 1: Load parquet — only 3 columns needed (memory-efficient)
    print("\n[1/5] Loading price parquet (3 columns)...")
    df = pd.read_parquet(
        _PARQUET_PATH,
        columns=["commodity", "commodity_id", "price_modal"],
    )
    # Drop rows with null price_modal
    df = df.dropna(subset=["price_modal"]).reset_index(drop=True)
    print(f"  Loaded {len(df):,} rows, {df['commodity'].nunique()} commodities")

    # Step 2: Compute per-commodity IQR bounds
    print("\n[2/5] Computing per-commodity IQR bounds...")
    bounds = compute_commodity_bounds(df)
    print(f"  Computed bounds for {len(bounds)} commodities")

    # Step 3: Flag and cap outliers
    print("\n[3/5] Flagging and capping outliers...")
    flagged = flag_and_cap_outliers(df, bounds)
    outlier_total = flagged["is_outlier"].sum()
    print(f"  Flagged {outlier_total:,} outlier rows "
          f"({outlier_total/len(flagged)*100:.2f}% of total)")

    # Step 4: Compute per-commodity counts
    print("\n[4/5] Computing per-commodity counts...")
    counts = (
        flagged.groupby("commodity")
        .agg(
            total_count=("is_outlier", "count"),
            outlier_count=("is_outlier", "sum"),
        )
        .reset_index()
    )
    counts["outlier_count"] = counts["outlier_count"].astype(int)
    counts["total_count"] = counts["total_count"].astype(int)

    # Step 5: Upsert to DB
    print("\n[5/5] Upserting bounds into price_bounds table...")
    upsert_price_bounds(bounds, counts)

    # --- Summary Report ---
    print("\n=== Summary Report ===")

    # Merge bounds with counts for reporting
    report = bounds.merge(counts, on="commodity")
    report["cv_pct"] = (
        (report["q3"] - report["lower_cap"]) / report["median_price"].replace(0, float("nan"))
    ) * 100

    # Compute actual CV% from raw data for better reporting
    raw_cv = (
        df.groupby("commodity")["price_modal"]
        .agg(lambda s: (s.std() / s.mean() * 100) if s.mean() > 0 else 0)
        .reset_index()
        .rename(columns={"price_modal": "cv_pct_raw"})
    )
    report = report.merge(raw_cv, on="commodity")

    total_commodities = len(report)
    print(f"\nTotal commodities: {total_commodities}")
    print(f"Total rows processed: {len(df):,}")
    print(f"Total outlier rows: {outlier_total:,} ({outlier_total/len(df)*100:.3f}%)")

    print("\nTop 10 commodities by outlier_count:")
    top_outliers = report.nlargest(10, "outlier_count")[
        ["commodity", "outlier_count", "total_count", "upper_cap"]
    ]
    for _, row in top_outliers.iterrows():
        pct = row["outlier_count"] / row["total_count"] * 100 if row["total_count"] > 0 else 0
        print(f"  {row['commodity']:<30} outliers={row['outlier_count']:>6,}  "
              f"({pct:5.1f}%)  upper_cap={row['upper_cap']:>12,.2f}")

    print("\nTop 10 commodities by raw CV% (most volatile):")
    top_cv = report.nlargest(10, "cv_pct_raw")[
        ["commodity", "cv_pct_raw", "upper_cap", "outlier_count"]
    ]
    for _, row in top_cv.iterrows():
        print(f"  {row['commodity']:<30} CV={row['cv_pct_raw']:>10,.1f}%  "
              f"upper_cap={row['upper_cap']:>12,.2f}  outliers={row['outlier_count']:>6,}")

    # Spot-check: known corrupt commodities
    print("\nSpot-check on known corrupt commodities:")
    for name in ["Guar", "Cumin Seed", "Bajra"]:
        matches = report[report["commodity"].str.contains(name, case=False)]
        if len(matches) > 0:
            row = matches.iloc[0]
            print(f"  {row['commodity']}: "
                  f"upper_cap={row['upper_cap']:,.2f}  "
                  f"outliers={row['outlier_count']:,}/{row['total_count']:,}  "
                  f"CV={row['cv_pct_raw']:,.1f}%")
        else:
            print(f"  {name}: NOT FOUND in parquet")

    print("\n=== Pipeline complete. price_history.modal_price was NOT modified. ===")


if __name__ == "__main__":
    main()
