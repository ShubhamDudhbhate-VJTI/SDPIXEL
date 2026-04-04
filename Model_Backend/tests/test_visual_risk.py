"""Tests for utils/visual_risk.py"""

import pytest
from utils.visual_risk import compute_visual_risk, ssim_score_to_risk


class TestSsimScoreToRisk:
    def test_none_returns_default(self):
        assert ssim_score_to_risk(None) == 0.3

    def test_below_0_5_returns_high_risk(self):
        assert ssim_score_to_risk(0.0) == 0.9
        assert ssim_score_to_risk(0.49) == 0.9
        assert ssim_score_to_risk(0.1) == 0.9

    def test_exactly_0_5_is_medium_risk(self):
        # 0.5 is NOT < 0.5, so it falls into the medium bucket
        assert ssim_score_to_risk(0.5) == 0.5

    def test_between_0_5_and_0_8_is_medium_risk(self):
        assert ssim_score_to_risk(0.6) == 0.5
        assert ssim_score_to_risk(0.79) == 0.5

    def test_exactly_0_8_is_low_risk(self):
        # 0.8 is NOT < 0.8, so it falls into the low-risk bucket
        assert ssim_score_to_risk(0.8) == 0.2

    def test_above_0_8_is_low_risk(self):
        assert ssim_score_to_risk(0.85) == 0.2
        assert ssim_score_to_risk(1.0) == 0.2

    def test_boundary_0_5_exactly(self):
        assert ssim_score_to_risk(0.5) == 0.5

    def test_boundary_0_8_exactly(self):
        assert ssim_score_to_risk(0.8) == 0.2


class TestComputeVisualRisk:
    # -----------------------------------------------------------------------
    # With shap_intensity_score provided
    # -----------------------------------------------------------------------

    def test_all_zeros_returns_zero(self):
        result = compute_visual_risk(0.0, 0.0, 0.0, 0.0)
        assert result == 0.0

    def test_all_ones_returns_one(self):
        result = compute_visual_risk(1.0, 1.0, 1.0, 1.0)
        assert result == pytest.approx(1.0)

    def test_formula_with_shap(self):
        # 0.5*1 + 0.2*0.5 + 0.2*0.3 + 0.1*0.6 = 0.5 + 0.1 + 0.06 + 0.06 = 0.72
        result = compute_visual_risk(1.0, 0.5, 0.3, 0.6)
        assert abs(result - 0.72) < 1e-9

    def test_weights_sum_to_one_with_shap(self):
        # All weights × 1.0 should equal exactly 1.0
        result = compute_visual_risk(1.0, 1.0, 1.0, 1.0)
        assert result == pytest.approx(1.0)

    def test_suspicious_score_dominates(self):
        # suspicious_score weight is 0.5 — it should have the most influence
        with_suspicious = compute_visual_risk(1.0, 0.0, 0.0, 0.0)
        without_suspicious = compute_visual_risk(0.0, 1.0, 1.0, 1.0)
        assert with_suspicious == pytest.approx(0.5)
        assert without_suspicious == pytest.approx(0.5)

    # -----------------------------------------------------------------------
    # With shap_intensity_score = None
    # -----------------------------------------------------------------------

    def test_none_shap_redistributes_weight(self):
        # Without SHAP: 0.6*1 + 0.2*0 + 0.2*0 = 0.6
        result = compute_visual_risk(1.0, 0.0, 0.0, None)
        assert result == pytest.approx(0.6)

    def test_none_shap_weights_still_sum_to_one(self):
        result = compute_visual_risk(1.0, 1.0, 1.0, None)
        assert result == pytest.approx(1.0)

    def test_none_shap_formula(self):
        # 0.6*0.5 + 0.2*0.25 + 0.2*0.3 = 0.3 + 0.05 + 0.06 = 0.41
        result = compute_visual_risk(0.5, 0.25, 0.3, None)
        assert result == pytest.approx(0.41)

    # -----------------------------------------------------------------------
    # Clamping
    # -----------------------------------------------------------------------

    def test_result_never_exceeds_one(self):
        # Passing values > 1.0 should still clamp to 1.0
        result = compute_visual_risk(2.0, 2.0, 2.0, 2.0)
        assert result == 1.0

    def test_result_never_below_zero(self):
        result = compute_visual_risk(-1.0, -1.0, -1.0, -1.0)
        assert result == 0.0

    # -----------------------------------------------------------------------
    # Specific scenario tests
    # -----------------------------------------------------------------------

    def test_no_detections_no_reference_no_shap(self):
        # Clean scan, no reference, no SHAP → only ssim default risk contributes
        # 0.6*0 + 0.2*0 + 0.2*0.3 = 0.06
        result = compute_visual_risk(0.0, 0.0, ssim_score_to_risk(None), None)
        assert result == pytest.approx(0.06)

    def test_prohibited_item_detected(self):
        # suspicious_score = 1.0, everything else zero
        result = compute_visual_risk(1.0, 0.0, ssim_score_to_risk(0.9), 0.0)
        # 0.5*1 + 0.2*0 + 0.2*0.2 + 0.1*0 = 0.5 + 0.04 = 0.54
        assert result == pytest.approx(0.54)
