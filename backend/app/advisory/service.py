"""Service layer for conservative directional market advisories."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.advisory.schemas import DirectionProbabilities, DirectionalAdvisoryResponse
from app.ml.direction_features import (
    build_feature_frame,
    prepare_price_history,
    select_latest_feature_row,
    slugify,
    vectorize_features,
)
from app.ml.direction_loader import (
    list_direction_commodities,
    load_direction_bundle,
    load_direction_meta,
)
from app.models import Commodity, Mandi, PriceHistory


def _to_float(value: Decimal | float | int | None) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _confidence_label(score: Optional[float], threshold: Optional[float]) -> str:
    if score is None or threshold is None:
        return "abstain"
    if score >= max(0.85, threshold + 0.10):
        return "high"
    if score >= threshold:
        return "medium"
    return "low"


class DirectionalAdvisoryService:
    """Load directional artifacts and return abstention-first advisories."""

    def __init__(self, db: Session):
        self.db = db

    def list_commodities(self) -> list[str]:
        """Return commodities with advisory artifacts."""
        return list_direction_commodities()

    def model_health(self) -> dict:
        """Return summary metadata for all advisory models."""
        rows = []
        for slug in list_direction_commodities():
            meta = load_direction_meta(slug)
            if not meta:
                continue
            rows.append(
                {
                    "commodity": slug,
                    "deployable": bool(meta.get("deployable", False)),
                    "balanced_accuracy": meta.get("balanced_accuracy"),
                    "macro_f1": meta.get("macro_f1"),
                    "recommended_confidence_threshold": meta.get(
                        "recommended_confidence_threshold"
                    ),
                    "selective_accuracy": meta.get("selective_accuracy"),
                    "selective_coverage": meta.get("selective_coverage"),
                    "validation_samples": meta.get("validation_samples"),
                    "covered_districts": len(meta.get("covered_districts", [])),
                    "last_data_date": meta.get("last_data_date"),
                    "trained_at": meta.get("trained_at"),
                }
            )
        return {
            "models": rows,
            "total": len(rows),
            "deployable": sum(1 for row in rows if row["deployable"]),
        }

    def get_advisory(self, commodity: str, district: str) -> DirectionalAdvisoryResponse:
        """Return a 7-day directional advisory or abstain with a reason."""
        slug = slugify(commodity)
        meta = load_direction_meta(slug)
        if meta is None:
            return self._abstain(
                commodity=commodity,
                district=district,
                reason="No validated directional advisory model is available for this commodity.",
            )

        if not meta.get("deployable", False):
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                reason="This model is trained but has not passed the validation bar for farmer-facing use.",
            )

        covered = {item.lower(): item for item in meta.get("covered_districts", [])}
        if covered and district.strip().lower() not in covered:
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                reason="This district is outside the validated coverage for the advisory model.",
            )

        history = self._fetch_district_history(commodity, district)
        if history.empty:
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                reason="No district price history was found for this commodity.",
            )

        latest_raw = history.sort_values("price_date").tail(1)
        current_price = (
            _to_float(latest_raw["modal_price"].iloc[0]) if not latest_raw.empty else None
        )
        latest_price_value = latest_raw["price_date"].iloc[0] if not latest_raw.empty else None
        if latest_price_value is not None and hasattr(latest_price_value, "date"):
            latest_price_value = latest_price_value.date()
        last_price_date = (
            latest_price_value.isoformat()
            if latest_price_value is not None and hasattr(latest_price_value, "isoformat")
            else None
        )
        freshness_days = (
            (date.today() - date.fromisoformat(last_price_date)).days
            if last_price_date
            else 0
        )
        max_staleness_days = int(meta.get("max_data_staleness_days", 30))

        if freshness_days > max_staleness_days:
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                current_price=current_price,
                last_price_date=last_price_date,
                data_freshness_days=freshness_days,
                reason=(
                    f"Latest district price data is {freshness_days} days old, above the advisory limit "
                    f"of {max_staleness_days} days."
                ),
            )

        min_history_days = int(meta.get("min_history_days", 120))
        if history["price_date"].nunique() < min_history_days:
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                current_price=current_price,
                last_price_date=last_price_date,
                data_freshness_days=freshness_days,
                reason=(
                    f"Only {history['price_date'].nunique()} days of district history are available; "
                    f"at least {min_history_days} are required."
                ),
            )

        bundle = load_direction_bundle(slug)
        if bundle is None or "model" not in bundle:
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                current_price=current_price,
                last_price_date=last_price_date,
                data_freshness_days=freshness_days,
                reason="The advisory artifact could not be loaded.",
            )

        prepared = prepare_price_history(history)
        feature_frame = build_feature_frame(prepared)
        latest_feature = select_latest_feature_row(feature_frame)
        if latest_feature.empty:
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                current_price=current_price,
                last_price_date=last_price_date,
                data_freshness_days=freshness_days,
                reason="Not enough recent history is available to build the past-only advisory features.",
            )

        feature_columns = bundle.get("feature_columns") or meta.get("feature_columns", [])
        class_labels = bundle.get("class_labels") or meta.get(
            "class_labels",
            ["down", "flat", "up"],
        )
        matrix, _ = vectorize_features(latest_feature, feature_columns=feature_columns)
        model = bundle["model"]

        if not hasattr(model, "predict_proba"):
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                current_price=current_price,
                last_price_date=last_price_date,
                data_freshness_days=freshness_days,
                reason="The advisory model does not expose calibrated class probabilities.",
            )

        probabilities_raw = model.predict_proba(matrix)[0]
        best_idx = int(np.argmax(probabilities_raw))
        signal = str(class_labels[best_idx])
        confidence_score = float(probabilities_raw[best_idx])
        min_required_confidence = float(
            meta.get("recommended_confidence_threshold", 0.70)
        )

        probabilities = DirectionProbabilities(
            down=(
                round(float(probabilities_raw[class_labels.index("down")]), 4)
                if "down" in class_labels
                else 0.0
            ),
            flat=(
                round(float(probabilities_raw[class_labels.index("flat")]), 4)
                if "flat" in class_labels
                else 0.0
            ),
            up=(
                round(float(probabilities_raw[class_labels.index("up")]), 4)
                if "up" in class_labels
                else 0.0
            ),
        )

        recent_7d_change_pct = latest_feature.get("recent_7d_change_pct")
        recent_change_value = None
        if recent_7d_change_pct is not None and not recent_7d_change_pct.empty:
            recent_change_value = round(float(recent_7d_change_pct.iloc[0]), 2)

        if confidence_score < min_required_confidence:
            return self._abstain(
                commodity=commodity,
                district=district,
                meta=meta,
                current_price=current_price,
                last_price_date=last_price_date,
                data_freshness_days=freshness_days,
                confidence_score=confidence_score,
                probabilities=probabilities,
                recent_7d_change_pct=recent_change_value,
                reason=(
                    f"Model confidence {confidence_score:.2f} is below the deployment threshold "
                    f"of {min_required_confidence:.2f}."
                ),
            )

        return DirectionalAdvisoryResponse(
            commodity=commodity,
            district=district,
            horizon_days=int(meta.get("horizon_days", 7)),
            signal=signal,
            recommendation_available=True,
            confidence_score=round(confidence_score, 4),
            confidence_label=_confidence_label(confidence_score, min_required_confidence),
            probabilities=probabilities,
            current_price=current_price,
            last_price_date=last_price_date,
            data_freshness_days=freshness_days,
            recent_7d_change_pct=recent_change_value,
            model_balanced_accuracy=meta.get("balanced_accuracy"),
            validation_samples=int(meta.get("validation_samples", 0)),
            min_required_confidence=min_required_confidence,
        )

    def _abstain(
        self,
        commodity: str,
        district: str,
        reason: str,
        meta: dict | None = None,
        current_price: float | None = None,
        last_price_date: str | None = None,
        data_freshness_days: int = 0,
        confidence_score: float | None = None,
        probabilities: DirectionProbabilities | None = None,
        recent_7d_change_pct: float | None = None,
    ) -> DirectionalAdvisoryResponse:
        """Build a consistent abstention response."""
        min_required_confidence = None
        if meta and meta.get("recommended_confidence_threshold") is not None:
            min_required_confidence = float(meta["recommended_confidence_threshold"])

        return DirectionalAdvisoryResponse(
            commodity=commodity,
            district=district,
            horizon_days=int(meta.get("horizon_days", 7)) if meta else 7,
            signal="abstain",
            recommendation_available=False,
            confidence_score=(
                round(confidence_score, 4) if confidence_score is not None else None
            ),
            confidence_label="abstain",
            probabilities=probabilities,
            current_price=current_price,
            last_price_date=last_price_date,
            data_freshness_days=data_freshness_days,
            recent_7d_change_pct=recent_7d_change_pct,
            model_balanced_accuracy=meta.get("balanced_accuracy") if meta else None,
            validation_samples=int(meta.get("validation_samples", 0)) if meta else 0,
            min_required_confidence=min_required_confidence,
            reason=reason,
        )

    def _fetch_district_history(self, commodity: str, district: str) -> pd.DataFrame:
        """Query district-level daily prices from the transactional DB."""
        rows = (
            self.db.query(
                PriceHistory.price_date.label("price_date"),
                func.avg(PriceHistory.modal_price).label("modal_price"),
            )
            .join(Commodity, PriceHistory.commodity_id == Commodity.id)
            .join(Mandi, PriceHistory.mandi_id == Mandi.id)
            .filter(func.lower(Commodity.name) == commodity.strip().lower())
            .filter(func.lower(Mandi.district) == district.strip().lower())
            .filter(PriceHistory.modal_price > 0)
            .group_by(PriceHistory.price_date)
            .order_by(PriceHistory.price_date.asc())
            .all()
        )

        if not rows:
            return pd.DataFrame(columns=["price_date", "district", "modal_price"])

        frame = pd.DataFrame(rows, columns=["price_date", "modal_price"])
        frame["district"] = district.strip()
        return frame[["price_date", "district", "modal_price"]]
