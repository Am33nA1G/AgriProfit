"""Tests for risk_engine.py — composite risk score, stress test, behavioral scoring, guardrails."""
import pytest
from app.transport.risk_engine import (
    compute_risk_score, run_stress_test, apply_behavioral_corrections,
    check_guardrails, RiskResult, StressTestResult,
)


class TestRiskScore:
    def test_zero_risk_intrastate_short_stable(self):
        result = compute_risk_score(0.0, 50.0, 0.0, 98.0, 98.0, False, 0.0)
        assert result.risk_score < 20.0
        assert result.stability_class == "stable"

    def test_high_volatility_increases_risk(self):
        low = compute_risk_score(2.0, 100.0, 0.01, 98.0, 98.0, False, 0.3)
        high = compute_risk_score(20.0, 100.0, 0.01, 98.0, 98.0, False, 0.3)
        assert high.risk_score > low.risk_score

    def test_interstate_adds_regulatory_risk(self):
        intra = compute_risk_score(5.0, 200.0, 0.02, 98.0, 98.0, False, 0.3)
        inter = compute_risk_score(5.0, 200.0, 0.02, 98.0, 98.0, True, 0.3)
        assert inter.risk_score > intra.risk_score

    def test_stability_class_thresholds(self):
        low = compute_risk_score(1.0, 50.0, 0.001, 98.0, 98.0, False, 0.0)
        high = compute_risk_score(25.0, 900.0, 0.14, 115.0, 98.0, True, 1.0)
        assert low.stability_class == "stable"
        assert high.stability_class == "volatile"

    def test_risk_score_bounded_0_100(self):
        result = compute_risk_score(100.0, 10000.0, 1.0, 200.0, 98.0, True, 1.0)
        assert 0 <= result.risk_score <= 100


class TestStressTest:
    def test_stress_worsens_profit(self):
        # Consistent inputs: 5000 kg net * ₹30 * (1-0.04) - 30000 cost = 114000 profit
        normal_profit = 114_000.0
        result = run_stress_test(normal_profit, 5000.0, 30000.0, 30.0, 1500.0, 20000.0, 0.03, 0.04)
        assert result.worst_case_profit < normal_profit

    def test_result_is_stress_test_result(self):
        result = run_stress_test(1000.0, 100.0, 29000.0, 300.0, 5000.0, 20000.0, 0.03, 0.04)
        assert isinstance(result, StressTestResult)
        assert result.break_even_price_per_kg > 0
        assert isinstance(result.verdict_survives_stress, bool)

    def test_margin_of_safety_formula(self):
        result = run_stress_test(10000.0, 1000.0, 20000.0, 30.0, 1000.0, 15000.0, 0.0, 0.0)
        expected_mos = (10000.0 - result.worst_case_profit) / 10000.0 * 100
        assert result.margin_of_safety_pct == pytest.approx(expected_mos, rel=0.01)


class TestBehavioralCorrections:
    def test_far_distance_downgrades_verdict(self):
        result = apply_behavioral_corrections("excellent", 800.0, 20.0, 30.0)
        assert result in ("good", "marginal", "not_viable")

    def test_small_profit_diff_downgrades(self):
        result = apply_behavioral_corrections("excellent", 400.0, 3.0, 30.0)
        assert result in ("good", "marginal", "not_viable")

    def test_high_risk_downgrades_verdict(self):
        result = apply_behavioral_corrections("excellent", 100.0, 30.0, 80.0)
        assert result in ("good", "marginal", "not_viable")

    def test_no_downgrade_when_conditions_good(self):
        result = apply_behavioral_corrections("excellent", 200.0, 25.0, 25.0)
        assert result == "excellent"

    def test_max_downgrade_capped_at_2_tiers(self):
        result = apply_behavioral_corrections("excellent", 900.0, 2.0, 85.0)
        assert result in ("marginal", "not_viable")


class TestGuardrails:
    def test_extreme_roi_flagged(self):
        warning = check_guardrails(600.0, 0.30, 0.15, 5.0, 30.0)
        assert warning is not None and "ROI" in warning

    def test_extreme_margin_flagged(self):
        warning = check_guardrails(100.0, 0.60, 0.15, 5.0, 30.0)
        assert warning is not None and "Margin" in warning

    def test_very_low_cost_ratio_flagged(self):
        warning = check_guardrails(50.0, 0.30, 0.03, 5.0, 30.0)
        assert warning is not None

    def test_profit_exceeds_80_pct_price_flagged(self):
        warning = check_guardrails(50.0, 0.30, 0.15, 26.0, 30.0)
        assert warning is not None

    def test_normal_scenario_no_warning(self):
        warning = check_guardrails(150.0, 0.25, 0.15, 7.0, 30.0)
        assert warning is None
