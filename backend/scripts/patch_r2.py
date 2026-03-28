"""patch_r2.py — Recompute R² for commodities trained with the buggy version.

Loads each prophet model + meta, re-evaluates R² on Prophet predictions
against national test data from parquet, and patches the meta JSON.

Usage:
    backend/.venv/Scripts/python.exe backend/scripts/patch_r2.py
"""
import sys
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import logging
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

import joblib  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET_PATH = REPO_ROOT / "agmarknet_daily_10yr.parquet"
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"

TEST_HORIZON = 365


def build_fourier_exog(date_index: pd.DatetimeIndex) -> pd.DataFrame:
    doy = date_index.day_of_year.values.astype(float)
    dow = date_index.day_of_week.values.astype(float)
    month = date_index.month.values.astype(float)
    return pd.DataFrame(
        {
            "sin_annual":  np.sin(2 * np.pi * doy / 365.25),
            "cos_annual":  np.cos(2 * np.pi * doy / 365.25),
            "sin_semi":    np.sin(4 * np.pi * doy / 365.25),
            "cos_semi":    np.cos(4 * np.pi * doy / 365.25),
            "sin_weekly":  np.sin(2 * np.pi * dow / 7),
            "cos_weekly":  np.cos(2 * np.pi * dow / 7),
            "sin_monthly": np.sin(2 * np.pi * month / 12),
            "cos_monthly": np.cos(2 * np.pi * month / 12),
        },
        index=date_index,
    )


def compute_prophet_r2(prophet_model, national_test: pd.DataFrame) -> float:
    try:
        future = national_test.copy()
        exog = build_fourier_exog(pd.DatetimeIndex(national_test["ds"]))
        for col in exog.columns:
            future[col] = exog[col].values
        prophet_pred = prophet_model.predict(future)["yhat"].values
        y_true = national_test["y"].values
        n = min(len(prophet_pred), len(y_true))
        return float(r2_score(y_true[:n], prophet_pred[:n]))
    except Exception as e:
        print(f"    R² computation failed: {e}")
        return 0.0


def main():
    print(f"Loading parquet: {PARQUET_PATH}")
    parquet = pd.read_parquet(
        PARQUET_PATH, columns=["date", "commodity", "district", "price_modal"]
    )
    print(f"Loaded {len(parquet):,} rows")

    # Pre-group by commodity (lowercase key) once to avoid repeated 25M-row scans
    print("Grouping by commodity...")
    commodity_groups: dict[str, pd.DataFrame] = {}
    for commodity_name, group in parquet.groupby("commodity"):
        commodity_groups[str(commodity_name).lower()] = group
    print(f"Found {len(commodity_groups)} unique commodities in parquet\n")
    del parquet  # free memory

    meta_files = sorted(ARTIFACTS_DIR.glob("*_meta.json"))
    print(f"Found {len(meta_files)} meta files to patch\n")

    patched = skipped = failed = 0
    for meta_path in meta_files:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        # Skip if already has a non-zero R²
        if meta.get("r2_score", 0.0) > 0.0:
            print(f"[SKIP] {meta_path.name} (r2={meta['r2_score']:.4f})")
            skipped += 1
            continue

        # Derive commodity name from slug
        slug = meta_path.stem.replace("_meta", "")
        prophet_path = ARTIFACTS_DIR / f"{slug}_prophet.joblib"
        if not prophet_path.exists():
            print(f"[MISS] {slug} — prophet model missing")
            failed += 1
            continue

        # Look up pre-grouped data
        lookup_key = slug.replace("_", " ").lower()
        df = commodity_groups.get(lookup_key)
        if df is None:
            # Try replacing underscores and special chars
            print(f"[WARN] {slug} — no parquet data, skipping")
            failed += 1
            continue

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna(subset=["price_modal"])
        df = df[df["price_modal"] > 0]

        national = (
            df.groupby("date")["price_modal"]
            .mean()
            .reset_index()
            .rename(columns={"date": "ds", "price_modal": "y"})
            .sort_values("ds")
        )
        idx = pd.date_range(national["ds"].min(), national["ds"].max(), freq="D")
        national = national.set_index("ds").reindex(idx).ffill().bfill()
        national.index.name = "ds"
        national = national.reset_index()

        split = max(0, len(national) - TEST_HORIZON)
        national_test = national.iloc[split:].copy()

        if len(national_test) < 30:
            print(f"[SKIP] {slug} — test set too small")
            skipped += 1
            continue

        try:
            prophet_model = joblib.load(prophet_path)
            r2 = compute_prophet_r2(prophet_model, national_test)
            meta["r2_score"] = r2
            meta_path.write_text(json.dumps(meta, indent=2))
            print(f"[OK]  {slug}: R²={r2:.4f}")
            patched += 1
        except Exception as e:
            print(f"[ERR] {slug}: {e}")
            failed += 1

    print(f"\nDone. Patched={patched} Skipped={skipped} Failed={failed}")


if __name__ == "__main__":
    main()
