"""
Seasonal price calendar aggregator.

Pure functions for computing monthly price statistics from 10 years of
Agmarknet price data. compute_seasonal_stats() is the core pure function —
no DB calls, no file I/O — accepting and returning DataFrames only.

load_and_prepare() and upsert_seasonal_stats() handle I/O (parquet read,
DB read for price_bounds, DB write for seasonal_price_stats).
"""
import pandas as pd
from pathlib import Path
from sqlalchemy import text


# ---------------------------------------------------------------------------
# I/O: load parquet + apply price_bounds caps
# ---------------------------------------------------------------------------

def load_and_prepare(parquet_path: str | Path, engine) -> pd.DataFrame:
    """
    Load price parquet and prepare for seasonal aggregation.

    Reads parquet with only needed columns, drops nulls, extracts month/year,
    and clips price_modal to per-commodity bounds from the price_bounds table.

    Parameters
    ----------
    parquet_path : str or Path
        Path to the agmarknet_daily_10yr.parquet file.
    engine : sqlalchemy.Engine
        SQLAlchemy engine for reading price_bounds table.

    Returns
    -------
    pd.DataFrame
        Columns: commodity, state, price_modal, month, year
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
    return df.drop(columns=["lower_cap", "upper_cap", "date"])


# ---------------------------------------------------------------------------
# PURE: compute seasonal stats (no DB, no I/O)
# ---------------------------------------------------------------------------

def compute_seasonal_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate price data to monthly statistics per (commodity, state).

    PURE function — no DB calls, no file I/O. Accepts a DataFrame and
    returns a DataFrame. Safe for unit testing without a running database.

    Parameters
    ----------
    df : pd.DataFrame
        Must have columns: commodity, state, price_modal, month, year.

    Returns
    -------
    pd.DataFrame
        One row per (commodity_name, state_name, month) with columns:
        commodity_name, state_name, month, median_price, q1_price,
        q3_price, iqr_price, record_count, years_of_data, month_rank,
        is_best, is_worst.
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "commodity_name", "state_name", "month", "median_price",
            "q1_price", "q3_price", "iqr_price", "record_count",
            "years_of_data", "month_rank", "is_best", "is_worst",
        ])

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
            "month": int(month),
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
        if sorted_g["years_of_data"].iloc[0] >= 3:
            sorted_g["is_best"] = sorted_g["month_rank"] <= 2
            sorted_g["is_worst"] = sorted_g["month_rank"] == len(sorted_g)
        else:
            sorted_g["is_best"] = False
            sorted_g["is_worst"] = False
        ranked_rows.append(sorted_g)

    return pd.concat(ranked_rows, ignore_index=True)


# ---------------------------------------------------------------------------
# I/O: upsert to seasonal_price_stats
# ---------------------------------------------------------------------------

def upsert_seasonal_stats(stats_df: pd.DataFrame, engine) -> int:
    """
    Upsert all rows into seasonal_price_stats using ON CONFLICT.

    Parameters
    ----------
    stats_df : pd.DataFrame
        Output of compute_seasonal_stats().
    engine : sqlalchemy.Engine
        Not used directly — we use SessionLocal for transaction safety.

    Returns
    -------
    int
        Number of rows written.
    """
    from app.database.session import SessionLocal

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
