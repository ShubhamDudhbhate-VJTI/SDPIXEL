"""Tests for utils/final_risk.py"""

import pytest
from utils.final_risk import (
    THRESHOLD_RED,
    THRESHOLD_YELLOW,
    WEIGHT_DATA,
    WEIGHT_VISUAL,
    compute_final_risk,
)


class TestComputeFinalRisk:
    # -----------------------------------------------------------------------
    # Return type and shape
    # -----------------------------------------------------------------------

    def test_returns_tuple(self):
        result = compute_final_risk(0.5, 0.5)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_float(self):
        score, _ = compute_final_risk(0.5, 0.5)
        assert isinstance(score, float)

    def test_second_element_is_string(self):
        _, decision = compute_final_risk(0.5, 0.5)
        assert isinstance(decision, str)

    def test_decision_values_are_valid(self):
        for data_r in [0.0, 0.3, 0.5, 0.8, 1.0]:
            for vis_r in [0.0, 0.3, 0.5, 0.8, 1.0]:
                _, decision = compute_final_risk(data_r, vis_r)
                assert decision in ("RED", "YELLOW", "GREEN")

    # -----------------------------------------------------------------------
    # Formula verification — with data_risk
    # -----------------------------------------------------------------------

    def test_formula_with_both_risks(self):
        # 0.4 * 0.5 + 0.6 * 0.5 = 0.2 + 0.3 = 0.5
        score, _ = compute_final_risk(0.5, 0.5)
        assert score == pytest.approx(0.5)

    def test_formula_weights_asymmetric(self):
        # visual_risk has higher weight (0.6)
        score_high_visual, _ = compute_final_risk(0.0, 1.0)
        score_high_data, _   = compute_final_risk(1.0, 0.0)
        assert score_high_visual == pytest.approx(WEIGHT_VISUAL)
        assert score_high_data   == pytest.approx(WEIGHT_DATA)

    def test_all_zeros_returns_zero_green(self):
        score, decision = compute_final_risk(0.0, 0.0)
        assert score == 0.0
        assert decision == "GREEN"

    def test_all_ones_returns_one_red(self):
        score, decision = compute_final_risk(1.0, 1.0)
        assert score == pytest.approx(1.0)
        assert decision == "RED"

    # -----------------------------------------------------------------------
    # Formula verification — data_risk is None
    # -----------------------------------------------------------------------

    def test_none_data_risk_uses_visual_only(self):
        score, _ = compute_final_risk(None, 0.75)
        assert score == pytest.approx(0.75)

    def test_none_data_risk_zero_visual(self):
        score, decision = compute_final_risk(None, 0.0)
        assert score == 0.0
        assert decision == "GREEN"

    def test_none_data_risk_one_visual(self):
        score, decision = compute_final_risk(None, 1.0)
        assert score == pytest.approx(1.0)
        assert decision == "RED"

    # -----------------------------------------------------------------------
    # Decision thresholds
    # -----------------------------------------------------------------------

    def test_exactly_at_red_threshold(self):
        # final_risk == THRESHOLD_RED → RED
        _, decision = compute_final_risk(None, THRESHOLD_RED)
        assert decision == "RED"

    def test_just_below_red_threshold(self):
        _, decision = compute_final_risk(None, THRESHOLD_RED - 0.001)
        assert decision == "YELLOW"

    def test_exactly_at_yellow_threshold(self):
        _, decision = compute_final_risk(None, THRESHOLD_YELLOW)
        assert decision == "YELLOW"

    def test_just_below_yellow_threshold(self):
        _, decision = compute_final_risk(None, THRESHOLD_YELLOW - 0.001)
        assert decision == "GREEN"

    def test_just_above_green(self):
        _, decision = compute_final_risk(None, 0.0)
        assert decision == "GREEN"

    # -----------------------------------------------------------------------
    # Clamping
    # -----------------------------------------------------------------------

    def test_result_clamped_to_one(self):
        # Pass values > 1 — should still clamp to 1.0
        score, _ = compute_final_risk(2.0, 2.0)
        assert score == 1.0

    def test_result_clamped_to_zero(self):
        score, _ = compute_final_risk(-1.0, -1.0)
        assert score == 0.0

    def test_none_data_with_high_visual_clamped(self):
        score, _ = compute_final_risk(None, 1.5)
        assert score == 1.0

    # -----------------------------------------------------------------------
    # Threshold constants are as specified
    # -----------------------------------------------------------------------

    def test_red_threshold_constant(self):
        assert THRESHOLD_RED == pytest.approx(0.7)

    def test_yellow_threshold_constant(self):
        assert THRESHOLD_YELLOW == pytest.approx(0.4)

    def test_weight_constants(self):
        assert WEIGHT_DATA   == pytest.approx(0.4)
        assert WEIGHT_VISUAL == pytest.approx(0.6)

    # -----------------------------------------------------------------------
    # Scenario tests
    # -----------------------------------------------------------------------

    def test_clean_scan_no_manifest(self):
        # No YOLO hits, similar to reference, no SHAP, no manifest
        # visual_risk ≈ 0.06 (from ssim default 0.3: 0.6*0 + 0.2*0 + 0.2*0.3 = 0.06)
        score, decision = compute_final_risk(None, 0.06)
        assert decision == "GREEN"
        assert score < THRESHOLD_YELLOW

    def test_weapons_detected_no_manifest(self):
        # suspicious_score=1, uncertain_ratio=0.5, ssim_risk=0.3, no shap
        # visual = 0.6*1 + 0.2*0.5 + 0.2*0.3 = 0.6 + 0.1 + 0.06 = 0.76
        score, decision = compute_final_risk(None, 0.76)
        assert decision == "RED"

    def test_medium_risk_scenario(self):
        # data_risk = 0.35, visual_risk = 0.45
        # final = 0.4*0.35 + 0.6*0.45 = 0.14 + 0.27 = 0.41
        score, decision = compute_final_risk(0.35, 0.45)
        assert score == pytest.approx(0.41)
        assert decision == "YELLOW"
