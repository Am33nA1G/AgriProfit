"""Pydantic schemas for conservative directional advisories."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DirectionProbabilities(BaseModel):
    """Normalized class probabilities from the directional model."""
    down: float = Field(default=0.0, ge=0.0, le=1.0)
    flat: float = Field(default=0.0, ge=0.0, le=1.0)
    up: float = Field(default=0.0, ge=0.0, le=1.0)


class DirectionalAdvisoryResponse(BaseModel):
    """Farmer-facing directional advisory with hard abstention support."""
    commodity: str
    district: str
    horizon_days: int = 7
    signal: str = Field(description="up | flat | down | abstain")
    recommendation_available: bool
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence_label: str = Field(description="high | medium | low | abstain")
    probabilities: Optional[DirectionProbabilities] = None
    current_price: Optional[float] = None
    last_price_date: Optional[str] = None
    data_freshness_days: int = 0
    recent_7d_change_pct: Optional[float] = None
    model_balanced_accuracy: Optional[float] = None
    validation_samples: int = 0
    min_required_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reason: Optional[str] = None
    disclaimer: str = (
        "Experimental directional advisory. Verify with current local mandi conditions before acting."
    )
