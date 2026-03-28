"""API tests for directional advisory endpoints."""
from __future__ import annotations

from unittest.mock import patch

from app.advisory.schemas import DirectionProbabilities, DirectionalAdvisoryResponse


def _make_response(**overrides) -> DirectionalAdvisoryResponse:
    payload = {
        "commodity": "Onion",
        "district": "Pune",
        "horizon_days": 7,
        "signal": "up",
        "recommendation_available": True,
        "confidence_score": 0.79,
        "confidence_label": "medium",
        "probabilities": DirectionProbabilities(down=0.10, flat=0.11, up=0.79),
        "current_price": 2450.0,
        "last_price_date": "2026-03-08",
        "data_freshness_days": 1,
        "recent_7d_change_pct": 4.3,
        "model_balanced_accuracy": 0.61,
        "validation_samples": 220,
        "min_required_confidence": 0.70,
    }
    payload.update(overrides)
    return DirectionalAdvisoryResponse(**payload)


def test_advisory_endpoint_returns_200(client):
    mock_response = _make_response()

    with patch("app.advisory.routes.DirectionalAdvisoryService") as mock_service:
        mock_service.return_value.get_advisory.return_value = mock_response
        resp = client.get("/api/v1/advisory/Onion/Pune")

    assert resp.status_code == 200
    body = resp.json()
    assert body["signal"] == "up"
    assert body["recommendation_available"] is True
    assert body["probabilities"]["up"] == 0.79


def test_advisory_endpoint_returns_abstain_payload(client):
    mock_response = _make_response(
        signal="abstain",
        recommendation_available=False,
        confidence_score=0.58,
        confidence_label="abstain",
        reason="Model confidence 0.58 is below the deployment threshold of 0.70.",
    )

    with patch("app.advisory.routes.DirectionalAdvisoryService") as mock_service:
        mock_service.return_value.get_advisory.return_value = mock_response
        resp = client.get("/api/v1/advisory/Onion/Pune")

    assert resp.status_code == 200
    body = resp.json()
    assert body["signal"] == "abstain"
    assert body["recommendation_available"] is False
    assert "deployment threshold" in body["reason"]


def test_advisory_commodities_endpoint(client):
    with patch("app.advisory.routes.DirectionalAdvisoryService") as mock_service:
        mock_service.return_value.list_commodities.return_value = ["onion", "tomato"]
        resp = client.get("/api/v1/advisory/commodities")

    assert resp.status_code == 200
    assert resp.json() == ["onion", "tomato"]
