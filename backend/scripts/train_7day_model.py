"""
Train 7-day direct multi-step XGBoost price forecasting models.

Architecture:
  - One model per commodity, trained on all its districts simultaneously
  - 7 separate XGBRegressor instances per commodity (direct multi-step)
  - Features: lag 1/2/3/7/14/21/30, rolling 7/14/30 mean+std, calendar, district_enc
  - Target: log1p(price_modal) at t+1 … t+7 → expm1 at serving time
  - Empirical 80% prediction bands from p10/p90 of test residuals per horizon
  - Temporal split: train 2015–2023, test 2024–2025 (no shuffling)

Outputs per commodity (ml/artifacts/v5/):
  {slug}_lgbm_7d.joblib       — {1: XGBRegressor, …, 7: XGBRegressor}
  {slug}_7d_meta.json         — metrics, district_encoder, residual quantiles
  {slug}_7d_history.parquet   — last 90 days of district prices (serving cold-start)

Run:
  cd backend
  python scripts/train_7day_model.py [--min-rows 100000] [--min-districts 50]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

# ── paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.features_7d import (
    FEATURE_COLS,
    LAG_DAYS,
    MIN_SERIES_ROWS,
    N_HORIZONS,
    ROLL_WINDOWS,
    TARGET_COLS,
    build_features_from_series,
)

PARQUET_PATH = REPO_ROOT / "agmarknet_daily_10yr.parquet"
OUTPUT_DIR = REPO_ROOT / "ml" / "artifacts" / "v5"

# Train / test split date
TRAIN_END = pd.Timestamp("2023-12-31")
TEST_START = pd.Timestamp("2024-01-01")

# XGBoost hyperparameters (tuned for 7-day ag price forecasting)
XGB_PARAMS: dict = dict(
    n_estimators=400,
    learning_rate=0.05,
    max_depth=5,
    min_child_weight=20,       # prevents overfitting on sparse districts
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=1.0,
    tree_method="hist",        # fast exact histogram method
    device="cpu",
    random_state=42,
    verbosity=0,
    n_jobs=-1,
)
EARLY_STOPPING_ROUNDS = 30


# ── helpers ────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 1.0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


# ── data loading ───────────────────────────────────────────────────────────────

def load_parquet() -> pd.DataFrame:
    """Load only the 4 columns training needs; filter via PyArrow to save RAM."""
    import pyarrow.parquet as pq
    import pyarrow.compute as pc

    print(f"Loading parquet from {PARQUET_PATH} …")
    table = pq.read_table(
        PARQUET_PATH,
        columns=["date", "commodity", "district", "price_modal"],
    )
    table = table.filter(pc.greater(table["price_modal"], 0))
    df = table.to_pandas()
    df["date"] = pd.to_datetime(df["date"])
    print(f"  {len(df):,} rows, {df['commodity'].nunique()} commodities")
    return df


def get_tier1_commodities(
    df: pd.DataFrame,
    min_rows: int,
    min_districts: int,
) -> list[str]:
    stats = (
        df.groupby("commodity")
        .agg(rows=("price_modal", "count"), districts=("district", "nunique"))
        .query("rows >= @min_rows and districts >= @min_districts")
        .sort_values("rows", ascending=False)
    )
    commodities = stats.index.tolist()
    print(f"\nTier 1 commodities ({min_rows:,}+ rows, {min_districts}+ districts): {len(commodities)}")
    for c in commodities[:10]:
        r, d = stats.loc[c, ["rows", "districts"]]
        print(f"  {c}: {int(r):,} rows, {int(d)} districts")
    if len(commodities) > 10:
        print(f"  … and {len(commodities) - 10} more")
    return commodities


def aggregate_to_district_day(
    df: pd.DataFrame,
    commodity: str,
    clip_outliers: bool = True,
    start_year: int | None = None,
) -> pd.DataFrame:
    """Aggregate mandi-level data to district-day level using median price.

    Args:
        clip_outliers: If True, clip price_modal to [p1, p99] per commodity
                       before aggregating. Removes corrupt/unit-mismatch records.
        start_year: If set, exclude data before this year (handles sparse early years).
    """
    sub = df[df["commodity"] == commodity].copy()

    if start_year is not None:
        sub = sub[sub["date"].dt.year >= start_year]

    if clip_outliers and len(sub) > 100:
        p1 = sub["price_modal"].quantile(0.01)
        p99 = sub["price_modal"].quantile(0.99)
        sub = sub[(sub["price_modal"] >= p1) & (sub["price_modal"] <= p99)]

    agg = (
        sub.groupby(["district", "date"])["price_modal"]
        .median()
        .reset_index()
        .sort_values(["district", "date"])
    )
    return agg


# ── feature building ────────────────────────────────────────────────────────────

def build_commodity_matrix(
    agg: pd.DataFrame,
    district_encoder: dict[str, int],
    split_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build (X_train, y_train, X_test, y_test) for a commodity.

    Each district contributes its own time series of rows.
    District is encoded as an integer feature.
    Temporal split ensures no future leakage.
    """
    train_X_parts, train_y_parts = [], []
    test_X_parts, test_y_parts = [], []

    for district, grp in agg.groupby("district"):
        enc = district_encoder.get(district.lower())
        if enc is None:
            continue

        series = grp.set_index("date")["price_modal"].sort_index()
        feat_df = build_features_from_series(series, enc)
        if feat_df.empty:
            continue

        train_mask = feat_df.index <= split_date
        test_mask = feat_df.index > split_date

        if train_mask.sum() < MIN_SERIES_ROWS:
            continue

        train_X_parts.append(feat_df.loc[train_mask, FEATURE_COLS])
        train_y_parts.append(feat_df.loc[train_mask, TARGET_COLS])

        if test_mask.sum() > 0:
            test_X_parts.append(feat_df.loc[test_mask, FEATURE_COLS])
            test_y_parts.append(feat_df.loc[test_mask, TARGET_COLS])

    if not train_X_parts:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    return (
        pd.concat(train_X_parts),
        pd.concat(train_y_parts),
        pd.concat(test_X_parts) if test_X_parts else pd.DataFrame(),
        pd.concat(test_y_parts) if test_y_parts else pd.DataFrame(),
    )


# ── training ───────────────────────────────────────────────────────────────────

def train_horizon_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    horizon: int,
) -> XGBRegressor:
    """Train one XGBRegressor for a single horizon step with early stopping."""
    model = XGBRegressor(
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        **XGB_PARAMS,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    return model


def compute_residual_quantiles(
    y_true_log: np.ndarray,
    y_pred_log: np.ndarray,
) -> tuple[float, float]:
    """Return (p10, p90) of signed log-space residuals.

    Used to construct empirical 80% prediction intervals at serving time:
      log_low  = log_pred + p10  (p10 is negative → widens down)
      log_high = log_pred + p90  (p90 is positive → widens up)
    """
    residuals = y_true_log - y_pred_log
    return float(np.percentile(residuals, 10)), float(np.percentile(residuals, 90))


# ── per-commodity pipeline ─────────────────────────────────────────────────────

def train_commodity(
    agg: pd.DataFrame,
    commodity: str,
    output_dir: Path,
) -> dict | None:
    """Train and save a 7-day model for one commodity.

    Returns a summary dict, or None on failure.
    """
    slug = slugify(commodity)
    t0 = time.time()

    # District encoder: lowercase district name → integer
    districts = sorted(agg["district"].unique())
    district_encoder = {d.lower(): i for i, d in enumerate(districts)}

    # Validation split at end of training period (last 6 months of train)
    val_split = TRAIN_END - pd.Timedelta(days=180)

    X_train, y_train, X_test, y_test = build_commodity_matrix(
        agg, district_encoder, TRAIN_END
    )

    if X_train.empty or len(X_train) < 1000:
        print(f"  [{commodity}] skipped — insufficient training rows ({len(X_train)})")
        return None

    # Further split train → actual_train + internal_val for early stopping
    val_mask = X_train.index > val_split
    X_val_inner = X_train[val_mask].values
    y_val_inner = y_train[val_mask]
    X_tr = X_train[~val_mask].values
    y_tr = y_train[~val_mask]

    if len(X_val_inner) < 100:
        # Not enough for validation — use last 10% of train
        split_i = max(100, int(len(X_train) * 0.9))
        X_tr = X_train.values[:split_i]
        y_tr = y_train.iloc[:split_i]
        X_val_inner = X_train.values[split_i:]
        y_val_inner = y_train.iloc[split_i:]

    print(
        f"  [{commodity}] train={len(X_tr):,}  val={len(X_val_inner):,}  "
        f"test={len(X_test):,}  districts={len(districts)}"
    )

    # Train 7 horizon models
    models: dict[int, XGBRegressor] = {}
    meta_horizons: dict[str, float] = {}

    X_test_np = X_test.values if not X_test.empty else None

    for h in range(1, N_HORIZONS + 1):
        col = f"target_h{h}"
        model = train_horizon_model(
            X_tr, y_tr[col].values,
            X_val_inner, y_val_inner[col].values,
            h,
        )
        models[h] = model

        # Test metrics (on 2024–2025 holdout)
        if X_test_np is not None and len(X_test_np) > 0:
            log_pred = model.predict(X_test_np)
            log_true = y_test[col].values

            # Metrics in original price space
            pred_prices = np.expm1(log_pred)
            true_prices = np.expm1(log_true)

            meta_horizons[f"test_mape_h{h}"] = mape(true_prices, pred_prices)
            meta_horizons[f"test_r2_h{h}"] = r2(true_prices, pred_prices)

            p10, p90 = compute_residual_quantiles(log_true, log_pred)
            meta_horizons[f"residual_p10_h{h}"] = p10
            meta_horizons[f"residual_p90_h{h}"] = p90

    elapsed = time.time() - t0

    # ── save model artifact ─────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(models, output_dir / f"{slug}_lgbm_7d.joblib", compress=3)

    # ── save recent-price history (cold-start for DB-less environments) ─────
    last_90d_cutoff = agg["date"].max() - pd.Timedelta(days=90)
    history = agg[agg["date"] >= last_90d_cutoff][["date", "district", "price_modal"]]
    history.to_parquet(
        output_dir / f"{slug}_7d_history.parquet",
        index=False,
        compression="snappy",
    )

    # ── save meta ───────────────────────────────────────────────────────────
    # Determine unknown-district fallback: use median of all district encodings
    unknown_enc = int(np.median(list(district_encoder.values())))

    # Per-district median prices for informational use
    district_medians = (
        agg.groupby("district")["price_modal"].median().to_dict()
    )

    meta = {
        "commodity": commodity,
        "slug": slug,
        "version": "v5",
        "n_districts": len(districts),
        "districts": districts,
        "district_encoder": district_encoder,
        "unknown_district_enc": unknown_enc,
        "district_medians": {k: round(v, 2) for k, v in district_medians.items()},
        "last_data_date": str(agg["date"].max().date()),
        "train_end": str(TRAIN_END.date()),
        "test_start": str(TEST_START.date()),
        "n_train_rows": int(len(X_train)),
        "n_test_rows": int(len(X_test)),
        "feature_cols": FEATURE_COLS,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_seconds": round(elapsed, 1),
        **meta_horizons,
    }

    (output_dir / f"{slug}_7d_meta.json").write_text(
        json.dumps(meta, indent=2, default=str),
        encoding="utf-8",
    )

    # Print quick summary
    h1 = meta.get("test_mape_h1", float("nan"))
    h7 = meta.get("test_mape_h7", float("nan"))
    r2_h7 = meta.get("test_r2_h7", float("nan"))
    print(
        f"  [{commodity}] MAPE h1={h1:.1%} h7={h7:.1%}  R² h7={r2_h7:.3f}"
        f"  ({elapsed:.0f}s)"
    )
    return meta


# ── main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Train 7-day XGBoost price forecasting models")
    parser.add_argument("--min-rows", type=int, default=50_000, help="Min parquet rows per commodity (default 50000)")
    parser.add_argument("--min-districts", type=int, default=30, help="Min districts per commodity (default 30)")
    parser.add_argument("--commodity", type=str, default=None, help="Train only this commodity (e.g. 'Onion')")
    parser.add_argument("--limit", type=int, default=None, help="Train at most N commodities")
    parser.add_argument("--skip-existing", action="store_true", help="Skip commodities that already have a v5 meta artifact")
    args = parser.parse_args()

    df = load_parquet()

    if args.commodity:
        commodities = [args.commodity]
    else:
        commodities = get_tier1_commodities(df, args.min_rows, args.min_districts)

    if args.limit:
        commodities = commodities[: args.limit]

    if args.skip_existing:
        before = len(commodities)
        commodities = [
            c for c in commodities
            if not (OUTPUT_DIR / f"{slugify(c)}_7d_meta.json").exists()
        ]
        print(f"  --skip-existing: skipped {before - len(commodities)} already trained, {len(commodities)} remaining")

    print(f"\nTraining {len(commodities)} commodities → {OUTPUT_DIR}\n")

    successes, failures = [], []

    for i, commodity in enumerate(commodities, 1):
        print(f"[{i}/{len(commodities)}] {commodity}")
        try:
            # Per-commodity overrides for known data quality issues
            _start_year = 2017 if "Arhar Dal" in commodity else None
            agg = aggregate_to_district_day(
                df, commodity,
                clip_outliers=True,
                start_year=_start_year,
            )
            result = train_commodity(agg, commodity, OUTPUT_DIR)
            if result:
                successes.append(commodity)
            else:
                failures.append(commodity)
        except Exception as exc:
            print(f"  [{commodity}] ERROR: {exc}")
            failures.append(commodity)

    print(f"\n{'='*60}")
    print(f"Done. Trained: {len(successes)}  Failed: {len(failures)}")
    if failures:
        print(f"Failed: {failures}")
    print(f"Artifacts in: {OUTPUT_DIR}")

    # Print summary table
    if successes:
        print(f"\n{'Commodity':<35} {'h1 MAPE':>9} {'h7 MAPE':>9} {'R² h7':>8}")
        print("-" * 65)
        for slug in [slugify(c) for c in successes]:
            meta_path = OUTPUT_DIR / f"{slug}_7d_meta.json"
            if meta_path.exists():
                m = json.loads(meta_path.read_text(encoding="utf-8"))
                h1 = m.get("test_mape_h1", float("nan"))
                h7 = m.get("test_mape_h7", float("nan"))
                r2v = m.get("test_r2_h7", float("nan"))
                print(f"{m.get('commodity', slug):<35} {h1:>8.1%} {h7:>8.1%} {r2v:>8.3f}")


if __name__ == "__main__":
    main()
