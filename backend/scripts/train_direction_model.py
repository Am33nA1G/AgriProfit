"""
Train a conservative 7-day directional advisory model from the parquet price history.

Usage:
    cd backend
    python -m scripts.train_direction_model --commodity onion
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from xgboost import XGBClassifier

from app.ml.direction_features import (
    attach_direction_labels,
    build_feature_frame,
    filter_complete_feature_rows,
    prepare_price_history,
    slugify,
    vectorize_features,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PARQUET_PATH = REPO_ROOT / "agmarknet_daily_10yr.parquet"
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts" / "direction"
CLASS_LABELS = ["down", "flat", "up"]


def make_classifier() -> XGBClassifier:
    """Return a conservative multi-class XGBoost classifier."""
    return XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.05,
        reg_lambda=1.0,
        objective="multi:softprob",
        num_class=len(CLASS_LABELS),
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=42,
    )


def compute_sample_weights(y: pd.Series) -> np.ndarray:
    """Balance classes without dropping scarce but important signals."""
    counts = y.value_counts()
    total = float(len(y))
    n_classes = float(max(len(counts), 1))
    return y.map(lambda label: total / (n_classes * float(counts[label]))).to_numpy(
        dtype="float32"
    )


def build_walk_forward_splits(
    frame: pd.DataFrame,
    min_train_days: int,
    test_days: int = 30,
    n_splits: int = 4,
) -> list[tuple[pd.Series, pd.Series]]:
    """Build date-based train/test masks with a purged horizon boundary."""
    unique_dates = np.array(sorted(pd.to_datetime(frame["price_date"]).dt.normalize().unique()))
    if len(unique_dates) < (min_train_days + test_days):
        return []

    candidate_indices = list(range(min_train_days, len(unique_dates) - test_days + 1, test_days))
    selected = candidate_indices[-n_splits:]
    splits: list[tuple[pd.Series, pd.Series]] = []

    for idx in selected:
        train_end = pd.Timestamp(unique_dates[idx - 1])
        test_start = pd.Timestamp(unique_dates[idx])
        test_end = pd.Timestamp(unique_dates[min(idx + test_days - 1, len(unique_dates) - 1)])

        train_mask = frame["target_date"] <= train_end
        test_mask = (frame["price_date"] >= test_start) & (frame["target_date"] <= test_end)

        if int(train_mask.sum()) < 200 or int(test_mask.sum()) < 50:
            continue
        splits.append((train_mask, test_mask))

    return splits


def choose_confidence_threshold(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    min_coverage: float = 0.20,
) -> dict:
    """Choose an abstention threshold using pooled out-of-sample predictions."""
    max_probs = y_proba.max(axis=1)
    best = None

    for threshold in np.arange(0.55, 0.91, 0.05):
        mask = max_probs >= threshold
        coverage = float(mask.mean())
        if coverage < min_coverage:
            continue

        selective_true = y_true[mask]
        selective_pred = y_pred[mask]
        selective_accuracy = accuracy_score(selective_true, selective_pred)
        selective_balanced_accuracy = balanced_accuracy_score(selective_true, selective_pred)

        candidate = {
            "threshold": round(float(threshold), 2),
            "coverage": round(coverage, 4),
            "accuracy": round(float(selective_accuracy), 4),
            "balanced_accuracy": round(float(selective_balanced_accuracy), 4),
        }

        if best is None:
            best = candidate
            continue

        current_key = (candidate["accuracy"], candidate["balanced_accuracy"], candidate["threshold"])
        best_key = (best["accuracy"], best["balanced_accuracy"], best["threshold"])
        if current_key > best_key:
            best = candidate

    return best or {
        "threshold": 0.80,
        "coverage": 0.0,
        "accuracy": 0.0,
        "balanced_accuracy": 0.0,
    }


def train_one_commodity(
    commodity: str,
    parquet_path: Path,
    move_threshold: float,
    horizon_days: int,
    min_history_days: int,
    force: bool = False,
) -> bool:
    """Train a single commodity directional model and write its artifacts."""
    slug = slugify(commodity)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / f"{slug}_direction.joblib"
    meta_path = ARTIFACTS_DIR / f"{slug}_direction_meta.json"

    if artifact_path.exists() and meta_path.exists() and not force:
        print(f"[SKIP] {commodity}: advisory artifacts already exist")
        return True

    raw = pd.read_parquet(
        parquet_path,
        engine="pyarrow",
        columns=["date", "commodity", "district", "price_modal"],
        filters=[("commodity", "==", commodity)],
    )
    raw = raw.dropna(subset=["date", "district", "price_modal"])
    raw = raw[raw["price_modal"] > 0]
    if raw.empty:
        print(f"[SKIP] {commodity}: no usable price rows")
        return False

    history = prepare_price_history(
        raw_df=raw.rename(columns={"date": "price_date", "price_modal": "modal_price"}),
    )
    if history.empty:
        print(f"[SKIP] {commodity}: no usable district history after cleaning")
        return False

    feature_frame = build_feature_frame(history)
    labeled = attach_direction_labels(
        feature_frame,
        horizon_days=horizon_days,
        move_threshold=move_threshold,
    )
    labeled = filter_complete_feature_rows(labeled)
    if labeled.empty:
        print(f"[SKIP] {commodity}: not enough complete feature rows")
        return False

    district_counts = labeled.groupby("district").size()
    keep_districts = district_counts[district_counts >= min_history_days].index.tolist()
    if keep_districts:
        labeled = labeled[labeled["district"].isin(keep_districts)].reset_index(drop=True)

    if labeled["district"].nunique() == 0 or len(labeled) < 500:
        print(f"[SKIP] {commodity}: insufficient labeled samples ({len(labeled)})")
        return False

    X, feature_columns = vectorize_features(labeled)
    label_to_int = {label: idx for idx, label in enumerate(CLASS_LABELS)}
    y = labeled["target_label"].map(label_to_int).astype(int)

    splits = build_walk_forward_splits(
        labeled,
        min_train_days=max(min_history_days, 365),
    )
    if not splits:
        print(f"[SKIP] {commodity}: unable to build walk-forward splits")
        return False

    pooled_true: list[np.ndarray] = []
    pooled_pred: list[np.ndarray] = []
    pooled_proba: list[np.ndarray] = []

    for train_mask, test_mask in splits:
        X_train = X.loc[train_mask]
        X_test = X.loc[test_mask]
        y_train = y.loc[train_mask]
        y_test = y.loc[test_mask]
        if X_train.empty or X_test.empty:
            continue

        model = make_classifier()
        model.fit(
            X_train,
            y_train,
            sample_weight=compute_sample_weights(y_train),
        )
        pooled_true.append(y_test.to_numpy())
        pooled_pred.append(model.predict(X_test))
        pooled_proba.append(model.predict_proba(X_test))

    if not pooled_true:
        print(f"[SKIP] {commodity}: walk-forward validation produced no test folds")
        return False

    y_true = np.concatenate(pooled_true)
    y_pred = np.concatenate(pooled_pred)
    y_proba = np.vstack(pooled_proba)

    balanced_accuracy = balanced_accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    overall_accuracy = accuracy_score(y_true, y_pred)
    selective = choose_confidence_threshold(y_true, y_pred, y_proba)

    deployable = (
        balanced_accuracy >= 0.45
        and macro_f1 >= 0.40
        and selective["accuracy"] >= 0.55
        and selective["coverage"] >= 0.20
    )

    final_model = make_classifier()
    final_model.fit(
        X,
        y,
        sample_weight=compute_sample_weights(y),
    )

    bundle = {
        "model": final_model,
        "feature_columns": feature_columns,
        "class_labels": CLASS_LABELS,
        "horizon_days": horizon_days,
        "move_threshold": move_threshold,
    }
    joblib.dump(bundle, artifact_path)

    last_data_date = pd.to_datetime(history["price_date"]).max().date().isoformat()
    label_counts = labeled["target_label"].value_counts().to_dict()
    meta = {
        "commodity": commodity,
        "commodity_slug": slug,
        "deployable": deployable,
        "horizon_days": horizon_days,
        "move_threshold": move_threshold,
        "min_history_days": min_history_days,
        "max_data_staleness_days": 30,
        "class_labels": CLASS_LABELS,
        "feature_columns": feature_columns,
        "covered_districts": sorted(labeled["district"].unique().tolist()),
        "n_rows": int(len(labeled)),
        "n_districts": int(labeled["district"].nunique()),
        "label_counts": {key: int(value) for key, value in label_counts.items()},
        "balanced_accuracy": round(float(balanced_accuracy), 4),
        "macro_f1": round(float(macro_f1), 4),
        "overall_accuracy": round(float(overall_accuracy), 4),
        "recommended_confidence_threshold": selective["threshold"],
        "selective_accuracy": selective["accuracy"],
        "selective_balanced_accuracy": selective["balanced_accuracy"],
        "selective_coverage": selective["coverage"],
        "validation_samples": int(len(y_true)),
        "last_data_date": last_data_date,
        "trained_at": datetime.utcnow().isoformat(),
        "artifact_path": str(artifact_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(
        f"[OK] {commodity}: deployable={deployable} "
        f"bal_acc={balanced_accuracy:.3f} macro_f1={macro_f1:.3f} "
        f"selective_acc={selective['accuracy']:.3f} coverage={selective['coverage']:.3f}"
    )
    return True


def list_commodities(parquet_path: Path) -> list[str]:
    """Load the commodity list from parquet metadata."""
    frame = pd.read_parquet(parquet_path, engine="pyarrow", columns=["commodity"])
    return sorted(frame["commodity"].dropna().astype(str).unique().tolist())


def main() -> None:
    parser = argparse.ArgumentParser(description="Train conservative directional advisory models")
    parser.add_argument("--commodity", type=str, default=None, help="Train a single commodity")
    parser.add_argument(
        "--parquet-path",
        type=Path,
        default=DEFAULT_PARQUET_PATH,
        help="Path to the price parquet",
    )
    parser.add_argument(
        "--move-threshold",
        type=float,
        default=0.05,
        help="Move threshold as a fraction (default 0.05)",
    )
    parser.add_argument("--horizon-days", type=int, default=7, help="Forecast horizon in days")
    parser.add_argument(
        "--min-history-days",
        type=int,
        default=180,
        help="Minimum district history days",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing artifacts")
    args = parser.parse_args()

    if args.commodity:
        all_commodities = list_commodities(args.parquet_path)
        commodities = [item for item in all_commodities if item.lower() == args.commodity.lower()]
        if not commodities:
            print(f"Commodity '{args.commodity}' not found in parquet")
            return
    else:
        commodities = list_commodities(args.parquet_path)
    print(f"Training advisory models for {len(commodities)} commodity(s)")

    successes = 0
    for commodity in commodities:
        try:
            ok = train_one_commodity(
                commodity=commodity,
                parquet_path=args.parquet_path,
                move_threshold=args.move_threshold,
                horizon_days=args.horizon_days,
                min_history_days=args.min_history_days,
                force=args.force,
            )
            successes += int(ok)
        except Exception as exc:
            print(f"[ERR] {commodity}: {exc}")

    print(f"Finished. Successful trainings: {successes}/{len(commodities)}")


if __name__ == "__main__":
    main()
